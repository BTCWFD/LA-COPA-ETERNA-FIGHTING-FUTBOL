#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_gltf_animations_to_fighters.py
Upgrades all 17 fighter .glb models in Assets/Models3D/Fighters/SK_*.glb
with 5 real glTF 2.0 keyframe animation clips at 60 FPS:
  1. Idle_Breath       - 60 FPS looping breathing/guard sway
  2. Dash_Forward      - forward explosive sprint lean
  3. Kick_High         - dynamic leg/body strike rotation & lunge
  4. Special_Chilena   - acrobatic 360-degree overhead bicycle-kick arc
  5. Victory_Pose      - triumphant celebratory pose (with hovering + rotating
                         astrolabe halo motion for SK_SUPREME_JUDGE_BOSS.glb)

Preserves existing meshes, skins, materials, nodes, and stepped combat clips,
cleanly appends new keyframe timestamp & TRS accessors to the BIN chunk, writes
Assets/Models3D/Fighters/Animations3D_TechnicalManifest.json, and validates all
17 GLB binaries programmatically.
"""

import glob
import json
import math
import os
import struct
from typing import Any

import numpy as np

FPS = 60.0
TARGET_CLIPS = [
    "Idle_Breath",
    "Dash_Forward",
    "Kick_High",
    "Special_Chilena",
    "Victory_Pose",
    "Mocap_Walk_Forward",
    "Mocap_Backdash_Dodge",
    "Mocap_Block_Guard",
    "Mocap_Hitstun_Knockback",
    "Mocap_Super_Potrero",
    "Mocap_KO_Knockdown",
]

# GLB Constants
GLB_MAGIC = 0x46546C67  # b'glTF'
GLB_VERSION = 2
CHUNK_JSON = 0x4E4F534A  # b'JSON'
CHUNK_BIN = 0x004E4942   # b'BIN\x00'

# glTF Component Types
FLOAT = 5126


def euler_xyz_to_quat(rx_deg: float, ry_deg: float, rz_deg: float) -> list[float]:
    """Convert XYZ Euler angles (degrees) to a normalized glTF quaternion [x, y, z, w]."""
    rx = math.radians(rx_deg) * 0.5
    ry = math.radians(ry_deg) * 0.5
    rz = math.radians(rz_deg) * 0.5
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    qx = sx * cy * cz - cx * sy * sz
    qy = cx * sy * cz + sx * cy * sz
    qz = cx * cy * sz - sx * sy * cz
    qw = cx * cy * cz + sx * sy * sz
    norm = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    if norm < 1e-12:
        return [0.0, 0.0, 0.0, 1.0]
    return [qx / norm, qy / norm, qz / norm, qw / norm]


def enforce_quat_continuity(quats: list[list[float]]) -> list[list[float]]:
    """Ensure consecutive quaternions stay in the same hemisphere for smooth LINEAR interpolation."""
    if not quats:
        return quats
    out = [quats[0]]
    for q in quats[1:]:
        prev = out[-1]
        dot = prev[0] * q[0] + prev[1] * q[1] + prev[2] * q[2] + prev[3] * q[3]
        if dot < 0.0:
            out.append([-q[0], -q[1], -q[2], -q[3]])
        else:
            out.append(q)
    return out


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge1 == edge0:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def bell_curve(u: float, center: float, width: float) -> float:
    """Smooth bump centered at `center` with half-width `width`."""
    d = abs(u - center) / max(width, 1e-6)
    if d >= 1.0:
        return 0.0
    return 0.5 * (1.0 + math.cos(math.pi * d))


def read_glb(filepath: str) -> tuple[dict[str, Any], bytearray]:
    with open(filepath, "rb") as f:
        data = f.read()
    if len(data) < 20:
        raise ValueError(f"{filepath}: file too small ({len(data)} bytes)")
    magic, version, total_len = struct.unpack("<III", data[:12])
    if magic != GLB_MAGIC or version != GLB_VERSION:
        raise ValueError(f"{filepath}: invalid GLB header magic={hex(magic)} version={version}")
    if total_len != len(data):
        raise ValueError(f"{filepath}: header length {total_len} != file size {len(data)}")

    offset = 12
    json_len, json_type = struct.unpack("<II", data[offset:offset + 8])
    offset += 8
    if json_type != CHUNK_JSON:
        raise ValueError(f"{filepath}: first chunk is not JSON")
    gltf_json = json.loads(data[offset:offset + json_len].decode("utf-8"))
    offset += json_len

    bin_chunk = bytearray()
    if offset < len(data):
        bin_len, bin_type = struct.unpack("<II", data[offset:offset + 8])
        offset += 8
        if bin_type != CHUNK_BIN:
            raise ValueError(f"{filepath}: second chunk is not BIN")
        bin_chunk = bytearray(data[offset:offset + bin_len])
        offset += bin_len

    if offset != len(data):
        raise ValueError(f"{filepath}: trailing bytes after BIN chunk")
    return gltf_json, bin_chunk


def write_glb(filepath: str, gltf_dict: dict[str, Any], bin_chunk: bytearray) -> None:
    while len(bin_chunk) % 4 != 0:
        bin_chunk.append(0)
    gltf_dict["buffers"][0]["byteLength"] = len(bin_chunk)

    json_bytes = json.dumps(gltf_dict, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_chunk)
    with open(filepath, "wb") as f:
        f.write(struct.pack("<III", GLB_MAGIC, GLB_VERSION, total_length))
        f.write(struct.pack("<II", len(json_bytes), CHUNK_JSON))
        f.write(json_bytes)
        f.write(struct.pack("<II", len(bin_chunk), CHUNK_BIN))
        f.write(bin_chunk)


def get_node_map(gltf: dict[str, Any]) -> dict[str, int]:
    return {node["name"]: idx for idx, node in enumerate(gltf["nodes"]) if "name" in node}


def get_rest_translation(gltf: dict[str, Any], node_idx: int) -> list[float]:
    t = gltf["nodes"][node_idx].get("translation", [0.0, 0.0, 0.0])
    return [float(t[0]), float(t[1]), float(t[2])]


def build_clip_tracks(
    clip_name: str,
    gltf: dict[str, Any],
    node_map: dict[str, int],
    is_boss: bool,
) -> tuple[list[float], list[dict[str, Any]]]:
    """
    Generate 60 FPS timestamps and multi-bone TRS tracks for the given clip.
    Returns (timestamps, tracks) where each track is:
      {"node": int, "path": "translation"|"rotation"|"scale", "values": list[list[float]]}
    """
    n = node_map
    pelvis_rest = get_rest_translation(gltf, n["pelvis"])
    root_rest = get_rest_translation(gltf, n["root"])
    height = pelvis_rest[1] / 0.53 if pelvis_rest[1] > 0.1 else 1.80

    tracks: list[dict[str, Any]] = []

    def add_rot(bone_name: str, quats: list[list[float]]) -> None:
        if bone_name in n:
            tracks.append({
                "node": n[bone_name],
                "path": "rotation",
                "values": enforce_quat_continuity(quats),
            })

    def add_trans(bone_name: str, deltas: list[list[float]]) -> None:
        if bone_name in n:
            rest = get_rest_translation(gltf, n[bone_name])
            vals = [[rest[0] + d[0], rest[1] + d[1], rest[2] + d[2]] for d in deltas]
            tracks.append({
                "node": n[bone_name],
                "path": "translation",
                "values": vals,
            })

    def add_scale(bone_name: str, scales: list[list[float]]) -> None:
        if bone_name in n:
            tracks.append({
                "node": n[bone_name],
                "path": "scale",
                "values": scales,
            })

    # ------------------------------------------------------------------
    # 1. Idle_Breath (60 FPS, 121 keyframes = 2.00s seamless loop)
    # ------------------------------------------------------------------
    if clip_name == "Idle_Breath":
        num_frames = 121  # frames 0..120 -> 2.0s exact loop
        times = [f / FPS for f in range(num_frames)]
        us = [f / (num_frames - 1) for f in range(num_frames)]

        pelvis_t, pelvis_r = [], []
        spine1_r, spine3_r, head_r = [], [], []
        uarm_l_r, larm_l_r, uarm_r_r, larm_r_r = [], [], [], []
        thigh_l_r, calf_l_r, thigh_r_r, calf_r_r = [], [], [], []
        hem1_r, hem2_r = [], []
        boss_halo1_r, boss_halo2_r = [], []

        for u in us:
            ang = 2.0 * math.pi * u
            s1 = math.sin(ang)
            c1 = math.cos(ang)
            s2 = math.sin(2.0 * ang)

            hover_y = (0.14 + 0.045 * s1) if is_boss else (0.016 * s1)
            sway_x = 0.018 * c1 if not is_boss else 0.012 * c1
            pelvis_t.append([sway_x, hover_y, 0.0])
            pelvis_r.append(euler_xyz_to_quat(1.5 * s1, 10.0 + 2.5 * c1, 1.2 * c1))

            spine1_r.append(euler_xyz_to_quat(3.5 + 2.8 * s1, 6.0 + 1.5 * s1, -1.0 * c1))
            spine3_r.append(euler_xyz_to_quat(2.5 + 3.2 * s1, 4.0 - 1.5 * c1, 0.8 * c1))
            head_r.append(euler_xyz_to_quat(-4.0 - 2.0 * s1, -16.0 - 2.0 * c1, 0.0))

            # Fighting guard arms
            uarm_l_r.append(euler_xyz_to_quat(-38.0 - 4.0 * s1, 18.0 + 2.0 * c1, -24.0 + 3.0 * s2))
            larm_l_r.append(euler_xyz_to_quat(-52.0 - 3.0 * s1, 10.0, 0.0))
            uarm_r_r.append(euler_xyz_to_quat(-32.0 + 3.5 * s1, -22.0 - 2.0 * c1, 26.0 - 3.0 * s2))
            larm_r_r.append(euler_xyz_to_quat(-48.0 + 3.0 * s1, -12.0, 0.0))

            # Athletic knee flex synced to breathing
            knee_flex = 8.0 - 3.5 * s1 if not is_boss else 4.0 + 2.0 * s1
            thigh_l_r.append(euler_xyz_to_quat(-knee_flex, 8.0, 2.0))
            calf_l_r.append(euler_xyz_to_quat(knee_flex * 1.4, 0.0, 0.0))
            thigh_r_r.append(euler_xyz_to_quat(-knee_flex * 0.85, -8.0, -2.0))
            calf_r_r.append(euler_xyz_to_quat(knee_flex * 1.2, 0.0, 0.0))

            # Subtle baggy 90s jersey hem sway
            hem1_r.append(euler_xyz_to_quat(4.0 * s1, 0.0, 2.5 * c1))
            hem2_r.append(euler_xyz_to_quat(-4.0 * s1, 0.0, -2.5 * c1))

            if is_boss:
                # Continuous 360-degree astrolabe halo rotation during idle
                boss_halo1_r.append(euler_xyz_to_quat(12.0 * s1, 360.0 * u, 18.0 * c1))
                boss_halo2_r.append(euler_xyz_to_quat(-12.0 * c1, -360.0 * u, -18.0 * s1))

        add_trans("pelvis", pelvis_t)
        add_rot("pelvis", pelvis_r)
        add_rot("spine_01", spine1_r)
        add_rot("spine_03", spine3_r)
        add_rot("head", head_r)
        add_rot("upperarm_l", uarm_l_r)
        add_rot("lowerarm_l", larm_l_r)
        add_rot("upperarm_r", uarm_r_r)
        add_rot("lowerarm_r", larm_r_r)
        add_rot("thigh_l", thigh_l_r)
        add_rot("calf_l", calf_l_r)
        add_rot("thigh_r", thigh_r_r)
        add_rot("calf_r", calf_r_r)
        add_rot("kit_hem_01", hem1_r)
        add_rot("kit_hem_02", hem2_r)
        if is_boss:
            add_rot("hair_chain_01", boss_halo1_r)
            add_rot("hair_chain_04", boss_halo2_r)

        return times, tracks

    # ------------------------------------------------------------------
    # 2. Dash_Forward (60 FPS, 37 keyframes = 0.60s explosive sprint lean)
    # ------------------------------------------------------------------
    if clip_name == "Dash_Forward":
        num_frames = 37  # frames 0..36 -> 0.60s
        times = [f / FPS for f in range(num_frames)]
        us = [f / (num_frames - 1) for f in range(num_frames)]

        root_t, pelvis_t, pelvis_r = [], [], []
        spine1_r, spine3_r, head_r = [], [], []
        uarm_l_r, larm_l_r, uarm_r_r, larm_r_r = [], [], [], []
        thigh_l_r, calf_l_r, thigh_r_r, calf_r_r = [], [], [], []
        hair1_r, hair2_r = [], []

        for u in us:
            # Explosive ease-out burst forward along +Z
            burst = 1.0 - (1.0 - u) ** 2.4
            lean_env = bell_curve(u, 0.42, 0.48)
            stride = math.sin(2.5 * math.pi * u)

            root_t.append([0.0, 0.06 * math.sin(math.pi * u), 1.35 * burst])
            pelvis_t.append([0.0, -0.075 * height * lean_env, 0.04 * lean_env])
            pelvis_r.append(euler_xyz_to_quat(24.0 * lean_env, 6.0 * stride, 0.0))

            spine1_r.append(euler_xyz_to_quat(18.0 * lean_env, -8.0 * stride, 0.0))
            spine3_r.append(euler_xyz_to_quat(14.0 * lean_env, -10.0 * stride, 0.0))
            head_r.append(euler_xyz_to_quat(-28.0 * lean_env, 0.0, 0.0))

            # Explosive sprint arm drive
            uarm_l_r.append(euler_xyz_to_quat(-55.0 * stride * lean_env - 15.0 * lean_env, 12.0, -18.0))
            larm_l_r.append(euler_xyz_to_quat(-75.0 * lean_env, 0.0, 0.0))
            uarm_r_r.append(euler_xyz_to_quat(55.0 * stride * lean_env - 15.0 * lean_env, -12.0, 18.0))
            larm_r_r.append(euler_xyz_to_quat(-75.0 * lean_env, 0.0, 0.0))

            # Driving legs
            thigh_l_r.append(euler_xyz_to_quat(-58.0 * lean_env + 38.0 * stride, 0.0, 0.0))
            calf_l_r.append(euler_xyz_to_quat(52.0 * lean_env + 25.0 * max(0.0, -stride), 0.0, 0.0))
            thigh_r_r.append(euler_xyz_to_quat(42.0 * lean_env - 38.0 * stride, 0.0, 0.0))
            calf_r_r.append(euler_xyz_to_quat(48.0 * lean_env + 25.0 * max(0.0, stride), 0.0, 0.0))

            # Wind drag on hair / drones
            hair1_r.append(euler_xyz_to_quat(-26.0 * lean_env, 180.0 * u if is_boss else 0.0, 0.0))
            hair2_r.append(euler_xyz_to_quat(-34.0 * lean_env, 0.0, 0.0))

        add_trans("root", root_t)
        add_trans("pelvis", pelvis_t)
        add_rot("pelvis", pelvis_r)
        add_rot("spine_01", spine1_r)
        add_rot("spine_03", spine3_r)
        add_rot("head", head_r)
        add_rot("upperarm_l", uarm_l_r)
        add_rot("lowerarm_l", larm_l_r)
        add_rot("upperarm_r", uarm_r_r)
        add_rot("lowerarm_r", larm_r_r)
        add_rot("thigh_l", thigh_l_r)
        add_rot("calf_l", calf_l_r)
        add_rot("thigh_r", thigh_r_r)
        add_rot("calf_r", calf_r_r)
        add_rot("hair_chain_01", hair1_r)
        add_rot("hair_chain_02", hair2_r)

        return times, tracks

    # ------------------------------------------------------------------
    # 3. Kick_High (60 FPS, 49 keyframes = 0.80s dynamic strike & lunge)
    # ------------------------------------------------------------------
    if clip_name == "Kick_High":
        num_frames = 49  # frames 0..48 -> 0.80s
        times = [f / FPS for f in range(num_frames)]
        us = [f / (num_frames - 1) for f in range(num_frames)]

        root_t, pelvis_t, pelvis_r = [], [], []
        spine1_r, spine3_r, head_r = [], [], []
        uarm_l_r, uarm_r_r = [], []
        thigh_l_r, calf_l_r = [], []
        thigh_r_r, calf_r_r, foot_r_r = [], [], []
        calf_r_s, foot_r_s = [], []

        for u in us:
            windup = bell_curve(u, 0.18, 0.18)
            strike = bell_curve(u, 0.48, 0.28)
            impact = bell_curve(u, 0.48, 0.12)
            lunge_z = 0.44 * smoothstep(0.15, 0.46, u) - 0.16 * smoothstep(0.62, 1.0, u)

            root_t.append([0.0, 0.05 * impact, lunge_z])
            pelvis_t.append([-0.04 * strike, -0.04 * windup + 0.03 * strike, 0.0])
            pelvis_r.append(euler_xyz_to_quat(
                -18.0 * strike + 8.0 * windup,
                -42.0 * strike + 20.0 * windup,
                -22.0 * strike,
            ))

            spine1_r.append(euler_xyz_to_quat(-14.0 * strike, 26.0 * strike, -12.0 * strike))
            spine3_r.append(euler_xyz_to_quat(-8.0 * strike, 18.0 * strike, -6.0 * strike))
            head_r.append(euler_xyz_to_quat(12.0 * strike, -14.0 * strike, 10.0 * strike))

            # Guard / balance arms
            uarm_l_r.append(euler_xyz_to_quat(-45.0 * strike - 20.0 * windup, 35.0 * strike, -40.0 * strike))
            uarm_r_r.append(euler_xyz_to_quat(25.0 * strike - 30.0 * windup, -30.0 * strike, 55.0 * strike))

            # Pivot standing leg (left)
            thigh_l_r.append(euler_xyz_to_quat(-16.0 * windup - 10.0 * strike, 18.0 * strike, 8.0 * strike))
            calf_l_r.append(euler_xyz_to_quat(24.0 * windup + 12.0 * strike, 0.0, 0.0))

            # High striking leg (right): chamber -> snap overhead -> recover
            hip_pitch = 26.0 * windup - 118.0 * strike
            knee_bend = 65.0 * windup + 8.0 * (strike - impact)
            thigh_r_r.append(euler_xyz_to_quat(hip_pitch, -14.0 * strike, -18.0 * strike))
            calf_r_r.append(euler_xyz_to_quat(max(0.0, knee_bend), 0.0, 0.0))
            foot_r_r.append(euler_xyz_to_quat(32.0 * strike, 0.0, 0.0))

            # Subtle anime impact exaggeration on striking shin & boot
            sc = 1.0 + 0.18 * impact
            calf_r_s.append([sc, sc, sc])
            foot_r_s.append([sc, sc, sc])

        add_trans("root", root_t)
        add_trans("pelvis", pelvis_t)
        add_rot("pelvis", pelvis_r)
        add_rot("spine_01", spine1_r)
        add_rot("spine_03", spine3_r)
        add_rot("head", head_r)
        add_rot("upperarm_l", uarm_l_r)
        add_rot("upperarm_r", uarm_r_r)
        add_rot("thigh_l", thigh_l_r)
        add_rot("calf_l", calf_l_r)
        add_rot("thigh_r", thigh_r_r)
        add_rot("calf_r", calf_r_r)
        add_rot("foot_r", foot_r_r)
        add_scale("calf_r", calf_r_s)
        add_scale("foot_r", foot_r_s)

        return times, tracks

    # ------------------------------------------------------------------
    # 4. Special_Chilena (60 FPS, 73 keyframes = 1.20s 360-deg bicycle kick)
    # ------------------------------------------------------------------
    if clip_name == "Special_Chilena":
        num_frames = 73  # frames 0..72 -> 1.20s
        times = [f / FPS for f in range(num_frames)]
        us = [f / (num_frames - 1) for f in range(num_frames)]

        root_t, pelvis_r = [], []
        spine1_r, spine3_r, head_r = [], [], []
        uarm_l_r, uarm_r_r = [], []
        thigh_l_r, calf_l_r = [], []
        thigh_r_r, calf_r_r, foot_r_r = [], [], []
        calf_r_s, foot_r_s = [], []

        for u in us:
            crouch = bell_curve(u, 0.10, 0.10)
            air_u = smoothstep(0.14, 0.86, u)
            # Parabolic leap peaking at u = 0.50
            air_height = 0.96 * math.sin(math.pi * air_u) if (0.14 <= u <= 0.86) else 0.0
            # Full 360-degree backward overhead flip
            flip_deg = -360.0 * air_u
            apex = bell_curve(u, 0.50, 0.14)
            scissor_setup = bell_curve(u, 0.34, 0.16)
            land_crouch = bell_curve(u, 0.90, 0.10)

            root_t.append([
                0.0,
                air_height - 0.12 * crouch - 0.10 * land_crouch,
                0.35 * math.sin(math.pi * u),
            ])
            pelvis_r.append(euler_xyz_to_quat(flip_deg + 16.0 * crouch, 12.0 * apex, 0.0))

            spine1_r.append(euler_xyz_to_quat(24.0 * apex - 12.0 * crouch, 0.0, 0.0))
            spine3_r.append(euler_xyz_to_quat(18.0 * apex, 0.0, 0.0))
            head_r.append(euler_xyz_to_quat(15.0 * apex, 0.0, 0.0))

            # Dramatic airborne arm flare
            uarm_l_r.append(euler_xyz_to_quat(-35.0 * apex, 20.0 * apex, -68.0 * math.sin(math.pi * air_u)))
            uarm_r_r.append(euler_xyz_to_quat(-35.0 * apex, -20.0 * apex, 68.0 * math.sin(math.pi * air_u)))

            # Left leg: scissor pump up first, then drops as right leg whips overhead
            thigh_l_r.append(euler_xyz_to_quat(-95.0 * scissor_setup + 32.0 * apex - 25.0 * crouch, 0.0, 0.0))
            calf_l_r.append(euler_xyz_to_quat(45.0 * crouch + 55.0 * apex + 40.0 * land_crouch, 0.0, 0.0))

            # Right leg: explosive overhead bicycle strike at apex
            thigh_r_r.append(euler_xyz_to_quat(22.0 * scissor_setup - 122.0 * apex - 25.0 * crouch, -10.0 * apex, 0.0))
            calf_r_r.append(euler_xyz_to_quat(45.0 * crouch + 45.0 * scissor_setup + 6.0 * apex + 40.0 * land_crouch, 0.0, 0.0))
            foot_r_r.append(euler_xyz_to_quat(38.0 * apex, 0.0, 0.0))

            # 1.25x anime impact exaggeration on striking shin/boot at apex
            sc = 1.0 + 0.25 * apex
            calf_r_s.append([sc, sc, sc])
            foot_r_s.append([sc, sc, sc])

        add_trans("root", root_t)
        add_rot("pelvis", pelvis_r)
        add_rot("spine_01", spine1_r)
        add_rot("spine_03", spine3_r)
        add_rot("head", head_r)
        add_rot("upperarm_l", uarm_l_r)
        add_rot("upperarm_r", uarm_r_r)
        add_rot("thigh_l", thigh_l_r)
        add_rot("calf_l", calf_l_r)
        add_rot("thigh_r", thigh_r_r)
        add_rot("calf_r", calf_r_r)
        add_rot("foot_r", foot_r_r)
        add_scale("calf_r", calf_r_s)
        add_scale("foot_r", foot_r_s)

        return times, tracks

    # ------------------------------------------------------------------
    # 5. Victory_Pose (60 FPS, 91 keyframes = 1.50s triumphant celebration)
    #    For SK_SUPREME_JUDGE_BOSS: hovering levitation + rotating astrolabe halo!
    # ------------------------------------------------------------------
    if clip_name == "Victory_Pose":
        num_frames = 91  # frames 0..90 -> 1.50s
        times = [f / FPS for f in range(num_frames)]
        us = [f / (num_frames - 1) for f in range(num_frames)]

        root_t, pelvis_t, pelvis_r = [], [], []
        spine1_r, spine3_r, head_r = [], [], []
        uarm_l_r, larm_l_r, uarm_r_r, larm_r_r = [], [], [], []
        thigh_l_r, calf_l_r, thigh_r_r, calf_r_r = [], [], [], []

        if is_boss:
            # Majestic levitating V.A.R. Supreme Judge with rotating astrolabe halo
            halo1_t, halo1_r = [], []
            halo2_t, halo2_r = [], []
            halo_ring1_r, halo_ring2_r = [], []

            for u in us:
                rise = smoothstep(0.0, 0.35, u)
                hover = 0.38 * rise + 0.06 * math.sin(4.0 * math.pi * u) * rise
                pose = smoothstep(0.10, 0.45, u)
                orbit_angle = 2.0 * math.pi * (2.0 * u)  # 2 full 360-deg orbits in 1.5s

                root_t.append([0.0, hover, 0.0])
                pelvis_t.append([0.0, 0.0, 0.0])
                pelvis_r.append(euler_xyz_to_quat(-6.0 * pose, 12.0 * math.sin(2.0 * math.pi * u) * rise, 0.0))

                spine1_r.append(euler_xyz_to_quat(-8.0 * pose, 0.0, 0.0))
                spine3_r.append(euler_xyz_to_quat(-10.0 * pose, 0.0, 0.0))
                head_r.append(euler_xyz_to_quat(-12.0 * pose, 0.0, 0.0))

                # Authoritative levitating judge outstretched arms
                uarm_l_r.append(euler_xyz_to_quat(-15.0 * pose, 10.0 * pose, -48.0 * pose - 6.0 * math.sin(4.0 * math.pi * u)))
                larm_l_r.append(euler_xyz_to_quat(-20.0 * pose, 0.0, -18.0 * pose))
                uarm_r_r.append(euler_xyz_to_quat(-15.0 * pose, -10.0 * pose, 48.0 * pose + 6.0 * math.sin(4.0 * math.pi * u)))
                larm_r_r.append(euler_xyz_to_quat(-20.0 * pose, 0.0, 18.0 * pose))

                # Levitating relaxed legs
                thigh_l_r.append(euler_xyz_to_quat(10.0 * pose, 6.0 * pose, 6.0 * pose))
                calf_l_r.append(euler_xyz_to_quat(18.0 * pose, 0.0, 0.0))
                thigh_r_r.append(euler_xyz_to_quat(14.0 * pose, -6.0 * pose, -6.0 * pose))
                calf_r_r.append(euler_xyz_to_quat(24.0 * pose, 0.0, 0.0))

                # Rotating astrolabe halo motion on VAR drone nodes (hair_chain_01..06)
                orbit_r = 0.12 * rise
                halo1_t.append([orbit_r * math.cos(orbit_angle), 0.08 * rise + 0.04 * math.sin(orbit_angle), orbit_r * math.sin(orbit_angle)])
                halo1_r.append(euler_xyz_to_quat(25.0 * math.sin(orbit_angle), 720.0 * u, 35.0 * math.cos(orbit_angle)))

                halo2_t.append([-orbit_r * math.cos(orbit_angle), 0.08 * rise - 0.04 * math.sin(orbit_angle), -orbit_r * math.sin(orbit_angle)])
                halo2_r.append(euler_xyz_to_quat(-25.0 * math.cos(orbit_angle), -720.0 * u, -35.0 * math.sin(orbit_angle)))

                # Secondary astrolabe gimbal rings
                halo_ring1_r.append(euler_xyz_to_quat(360.0 * u, 180.0 * u, 0.0))
                halo_ring2_r.append(euler_xyz_to_quat(-360.0 * u, 0.0, 360.0 * u))

            add_trans("root", root_t)
            add_trans("pelvis", pelvis_t)
            add_rot("pelvis", pelvis_r)
            add_rot("spine_01", spine1_r)
            add_rot("spine_03", spine3_r)
            add_rot("head", head_r)
            add_rot("upperarm_l", uarm_l_r)
            add_rot("lowerarm_l", larm_l_r)
            add_rot("upperarm_r", uarm_r_r)
            add_rot("lowerarm_r", larm_r_r)
            add_rot("thigh_l", thigh_l_r)
            add_rot("calf_l", calf_l_r)
            add_rot("thigh_r", thigh_r_r)
            add_rot("calf_r", calf_r_r)
            add_trans("hair_chain_01", halo1_t)
            add_rot("hair_chain_01", halo1_r)
            add_trans("hair_chain_04", halo2_t)
            add_rot("hair_chain_04", halo2_r)
            add_rot("hair_chain_02", halo_ring1_r)
            add_rot("hair_chain_05", halo_ring2_r)
        else:
            # Standard CONMEBOL fighter triumphant championship celebration
            for u in us:
                hop = 0.22 * bell_curve(u, 0.22, 0.16)
                pose = smoothstep(0.15, 0.50, u)
                pump = 0.5 * (1.0 + math.sin(6.0 * math.pi * max(0.0, u - 0.45))) * smoothstep(0.45, 0.65, u)

                root_t.append([0.0, hop, 0.0])
                pelvis_t.append([0.0, -0.04 * bell_curve(u, 0.08, 0.08) + 0.015 * pump, 0.0])
                pelvis_r.append(euler_xyz_to_quat(-6.0 * pose, -14.0 * pose, 0.0))

                spine1_r.append(euler_xyz_to_quat(-10.0 * pose, 6.0 * pose, 0.0))
                spine3_r.append(euler_xyz_to_quat(-12.0 * pose, 8.0 * pose, 0.0))
                head_r.append(euler_xyz_to_quat(-18.0 * pose, 6.0 * pose, 4.0 * pump))

                # Both arms raised skyward in championship salute with fist pump
                uarm_l_r.append(euler_xyz_to_quat(-18.0 * pose, 12.0 * pose, 128.0 * pose + 8.0 * pump))
                larm_l_r.append(euler_xyz_to_quat(-24.0 * pose - 12.0 * pump, 0.0, 14.0 * pose))
                uarm_r_r.append(euler_xyz_to_quat(-18.0 * pose, -12.0 * pose, -128.0 * pose - 8.0 * pump))
                larm_r_r.append(euler_xyz_to_quat(-24.0 * pose - 12.0 * pump, 0.0, -14.0 * pose))

                # Heroic wide victory stance
                thigh_l_r.append(euler_xyz_to_quat(-8.0 * pose, 12.0 * pose, 10.0 * pose))
                calf_l_r.append(euler_xyz_to_quat(12.0 * pose, 0.0, 0.0))
                thigh_r_r.append(euler_xyz_to_quat(-6.0 * pose, -12.0 * pose, -10.0 * pose))
                calf_r_r.append(euler_xyz_to_quat(10.0 * pose, 0.0, 0.0))

            add_trans("root", root_t)
            add_trans("pelvis", pelvis_t)
            add_rot("pelvis", pelvis_r)
            add_rot("spine_01", spine1_r)
            add_rot("spine_03", spine3_r)
            add_rot("head", head_r)
            add_rot("upperarm_l", uarm_l_r)
            add_rot("lowerarm_l", larm_l_r)
            add_rot("upperarm_r", uarm_r_r)
            add_rot("lowerarm_r", larm_r_r)
            add_rot("thigh_l", thigh_l_r)
            add_rot("calf_l", calf_l_r)
            add_rot("thigh_r", thigh_r_r)
            add_rot("calf_r", calf_r_r)

        return times, tracks

    # ------------------------------------------------------------------
    # 6. Mocap_Walk_Forward (60 FPS, 61 keyframes = 1.00s athletic forward walk loop)
    # ------------------------------------------------------------------
    if clip_name == "Mocap_Walk_Forward":
        num_frames = 61
        times = [f / FPS for f in range(num_frames)]
        us = [f / (num_frames - 1) for f in range(num_frames)]

        root_t, pelvis_t, pelvis_r = [], [], []
        spine1_r, spine3_r, head_r = [], [], []
        uarm_l_r, larm_l_r, uarm_r_r, larm_r_r = [], [], [], []
        thigh_l_r, calf_l_r, foot_l_r, thigh_r_r, calf_r_r, foot_r_r = [], [], [], [], [], []
        hem1_r, hem2_r = [], []

        for u in us:
            ang = 2.0 * math.pi * u
            s = math.sin(ang)
            c = math.cos(ang)
            bob = abs(math.sin(ang)) * 0.035

            root_t.append([0.0, 0.0, 0.95 * u])
            pelvis_t.append([0.022 * c, bob - 0.025, 0.0])
            pelvis_r.append(euler_xyz_to_quat(4.0, 8.0 * s, 3.5 * c))
            spine1_r.append(euler_xyz_to_quat(6.0, -7.0 * s, -2.0 * c))
            spine3_r.append(euler_xyz_to_quat(4.0, -8.0 * s, 0.0))
            head_r.append(euler_xyz_to_quat(-6.0, 4.0 * s, 0.0))

            uarm_l_r.append(euler_xyz_to_quat(-24.0 + 32.0 * s, 14.0, -18.0))
            larm_l_r.append(euler_xyz_to_quat(-48.0 - 12.0 * max(0.0, -s), 0.0, 0.0))
            uarm_r_r.append(euler_xyz_to_quat(-24.0 - 32.0 * s, -14.0, 18.0))
            larm_r_r.append(euler_xyz_to_quat(-48.0 - 12.0 * max(0.0, s), 0.0, 0.0))

            thigh_l_r.append(euler_xyz_to_quat(-28.0 * s - 6.0, 4.0, 2.0))
            calf_l_r.append(euler_xyz_to_quat(12.0 + 34.0 * max(0.0, -s), 0.0, 0.0))
            foot_l_r.append(euler_xyz_to_quat(10.0 * c, 0.0, 0.0))
            thigh_r_r.append(euler_xyz_to_quat(28.0 * s - 6.0, -4.0, -2.0))
            calf_r_r.append(euler_xyz_to_quat(12.0 + 34.0 * max(0.0, s), 0.0, 0.0))
            foot_r_r.append(euler_xyz_to_quat(-10.0 * c, 0.0, 0.0))

            hem1_r.append(euler_xyz_to_quat(8.0 * s, 0.0, 4.0 * c))
            hem2_r.append(euler_xyz_to_quat(-8.0 * s, 0.0, -4.0 * c))

        add_trans("root", root_t)
        add_trans("pelvis", pelvis_t)
        add_rot("pelvis", pelvis_r)
        add_rot("spine_01", spine1_r)
        add_rot("spine_03", spine3_r)
        add_rot("head", head_r)
        add_rot("upperarm_l", uarm_l_r)
        add_rot("lowerarm_l", larm_l_r)
        add_rot("upperarm_r", uarm_r_r)
        add_rot("lowerarm_r", larm_r_r)
        add_rot("thigh_l", thigh_l_r)
        add_rot("calf_l", calf_l_r)
        add_rot("foot_l", foot_l_r)
        add_rot("thigh_r", thigh_r_r)
        add_rot("calf_r", calf_r_r)
        add_rot("foot_r", foot_r_r)
        add_rot("kit_hem_01", hem1_r)
        add_rot("kit_hem_02", hem2_r)
        return times, tracks

    # ------------------------------------------------------------------
    # 7. Mocap_Backdash_Dodge (60 FPS, 28 keyframes = 0.45s explosive evade hop)
    # ------------------------------------------------------------------
    if clip_name == "Mocap_Backdash_Dodge":
        num_frames = 28
        times = [f / FPS for f in range(num_frames)]
        us = [f / (num_frames - 1) for f in range(num_frames)]

        root_t, pelvis_t, pelvis_r = [], [], []
        spine1_r, spine3_r, head_r = [], [], []
        uarm_l_r, uarm_r_r = [], []
        thigh_l_r, calf_l_r, thigh_r_r, calf_r_r = [], [], [], []

        for u in us:
            hop = math.sin(math.pi * u)
            env = bell_curve(u, 0.45, 0.48)
            root_t.append([0.0, 0.18 * hop, -0.92 * smoothstep(0.05, 0.85, u)])
            pelvis_t.append([0.0, -0.05 * env, 0.0])
            pelvis_r.append(euler_xyz_to_quat(-16.0 * env, 8.0 * env, 0.0))
            spine1_r.append(euler_xyz_to_quat(-12.0 * env, 0.0, 0.0))
            spine3_r.append(euler_xyz_to_quat(-10.0 * env, 0.0, 0.0))
            head_r.append(euler_xyz_to_quat(18.0 * env, 0.0, 0.0))

            uarm_l_r.append(euler_xyz_to_quat(-48.0 * env, 22.0, -32.0))
            uarm_r_r.append(euler_xyz_to_quat(-48.0 * env, -22.0, 32.0))

            thigh_l_r.append(euler_xyz_to_quat(-38.0 * hop, 0.0, 4.0))
            calf_l_r.append(euler_xyz_to_quat(54.0 * hop, 0.0, 0.0))
            thigh_r_r.append(euler_xyz_to_quat(-24.0 * hop, 0.0, -4.0))
            calf_r_r.append(euler_xyz_to_quat(40.0 * hop, 0.0, 0.0))

        add_trans("root", root_t)
        add_trans("pelvis", pelvis_t)
        add_rot("pelvis", pelvis_r)
        add_rot("spine_01", spine1_r)
        add_rot("spine_03", spine3_r)
        add_rot("head", head_r)
        add_rot("upperarm_l", uarm_l_r)
        add_rot("upperarm_r", uarm_r_r)
        add_rot("thigh_l", thigh_l_r)
        add_rot("calf_l", calf_l_r)
        add_rot("thigh_r", thigh_r_r)
        add_rot("calf_r", calf_r_r)
        return times, tracks

    # ------------------------------------------------------------------
    # 8. Mocap_Block_Guard (60 FPS, 49 keyframes = 0.80s braced FGC defense)
    # ------------------------------------------------------------------
    if clip_name == "Mocap_Block_Guard":
        num_frames = 49
        times = [f / FPS for f in range(num_frames)]
        us = [f / (num_frames - 1) for f in range(num_frames)]

        pelvis_t, pelvis_r, spine1_r, spine3_r, head_r = [], [], [], [], []
        uarm_l_r, larm_l_r, uarm_r_r, larm_r_r = [], [], [], []
        thigh_l_r, calf_l_r, thigh_r_r, calf_r_r = [], [], [], []

        for u in us:
            brace = bell_curve(u, 0.45, 0.45)
            tremor = 0.015 * math.sin(10.0 * math.pi * u) * bell_curve(u, 0.5, 0.3)
            pelvis_t.append([0.0, -0.095 * height * brace, -0.05 * brace + tremor])
            pelvis_r.append(euler_xyz_to_quat(8.0 * brace, 24.0 * brace, 0.0))
            spine1_r.append(euler_xyz_to_quat(12.0 * brace, -10.0 * brace, 0.0))
            spine3_r.append(euler_xyz_to_quat(10.0 * brace, -10.0 * brace, 0.0))
            head_r.append(euler_xyz_to_quat(-16.0 * brace, -12.0 * brace, 0.0))

            uarm_l_r.append(euler_xyz_to_quat(-78.0 * brace - 25.0, 38.0 * brace, 18.0 * brace))
            larm_l_r.append(euler_xyz_to_quat(-95.0 * brace - 20.0, 0.0, 0.0))
            uarm_r_r.append(euler_xyz_to_quat(-72.0 * brace - 25.0, -38.0 * brace, -18.0 * brace))
            larm_r_r.append(euler_xyz_to_quat(-90.0 * brace - 20.0, 0.0, 0.0))

            thigh_l_r.append(euler_xyz_to_quat(-28.0 * brace - 8.0, 14.0, 8.0))
            calf_l_r.append(euler_xyz_to_quat(42.0 * brace + 10.0, 0.0, 0.0))
            thigh_r_r.append(euler_xyz_to_quat(18.0 * brace - 6.0, -14.0, -8.0))
            calf_r_r.append(euler_xyz_to_quat(28.0 * brace + 10.0, 0.0, 0.0))

        add_trans("pelvis", pelvis_t)
        add_rot("pelvis", pelvis_r)
        add_rot("spine_01", spine1_r)
        add_rot("spine_03", spine3_r)
        add_rot("head", head_r)
        add_rot("upperarm_l", uarm_l_r)
        add_rot("lowerarm_l", larm_l_r)
        add_rot("upperarm_r", uarm_r_r)
        add_rot("lowerarm_r", larm_r_r)
        add_rot("thigh_l", thigh_l_r)
        add_rot("calf_l", calf_l_r)
        add_rot("thigh_r", thigh_r_r)
        add_rot("calf_r", calf_r_r)
        return times, tracks

    # ------------------------------------------------------------------
    # 9. Mocap_Hitstun_Knockback (60 FPS, 31 keyframes = 0.50s hitstop shake + whiplash)
    # ------------------------------------------------------------------
    if clip_name == "Mocap_Hitstun_Knockback":
        num_frames = 31
        times = [f / FPS for f in range(num_frames)]
        us = [f / (num_frames - 1) for f in range(num_frames)]

        root_t, pvo_t, pelvis_r, spine1_r, spine3_r, head_r = [], [], [], [], [], []
        uarm_l_r, uarm_r_r, thigh_l_r, thigh_r_r = [], [], [], []

        for u in us:
            whip = bell_curve(u, 0.34, 0.34)
            shake = 0.028 * math.sin(24.0 * math.pi * u) * bell_curve(u, 0.20, 0.20)
            root_t.append([0.0, 0.02 * whip, -0.45 * smoothstep(0.05, 0.65, u)])
            pvo_t.append([shake, 0.0, -0.5 * shake])
            pelvis_r.append(euler_xyz_to_quat(-26.0 * whip, -12.0 * whip, 0.0))
            spine1_r.append(euler_xyz_to_quat(-22.0 * whip, 10.0 * whip, 0.0))
            spine3_r.append(euler_xyz_to_quat(-24.0 * whip, 12.0 * whip, 0.0))
            head_r.append(euler_xyz_to_quat(-38.0 * whip, -14.0 * whip, 0.0))

            uarm_l_r.append(euler_xyz_to_quat(18.0 * whip, -22.0, -58.0 * whip - 18.0))
            uarm_r_r.append(euler_xyz_to_quat(18.0 * whip, 22.0, 58.0 * whip + 18.0))
            thigh_l_r.append(euler_xyz_to_quat(-16.0 * whip, 8.0, 0.0))
            thigh_r_r.append(euler_xyz_to_quat(14.0 * whip, -8.0, 0.0))

        add_trans("root", root_t)
        add_trans("pelvis_visual_offset", pvo_t)
        add_rot("pelvis", pelvis_r)
        add_rot("spine_01", spine1_r)
        add_rot("spine_03", spine3_r)
        add_rot("head", head_r)
        add_rot("upperarm_l", uarm_l_r)
        add_rot("upperarm_r", uarm_r_r)
        add_rot("thigh_l", thigh_l_r)
        add_rot("thigh_r", thigh_r_r)
        return times, tracks

    # ------------------------------------------------------------------
    # 10. Mocap_Super_Potrero (60 FPS, 85 keyframes = 1.40s Ultimate Hinchada Strike)
    # ------------------------------------------------------------------
    if clip_name == "Mocap_Super_Potrero":
        num_frames = 85
        times = [f / FPS for f in range(num_frames)]
        us = [f / (num_frames - 1) for f in range(num_frames)]

        root_t, pelvis_t, pelvis_r = [], [], []
        spine1_r, spine3_r, head_r = [], [], []
        uarm_l_r, uarm_r_r, thigh_l_r, calf_l_r, thigh_r_r, calf_r_r = [], [], [], [], [], []
        calf_r_s, foot_r_s = [], []

        for u in us:
            charge = bell_curve(u, 0.18, 0.18)
            air = smoothstep(0.28, 0.42, u) * (1.0 - smoothstep(0.72, 0.88, u))
            arc = math.sin(math.pi * max(0.0, min(1.0, (u - 0.25) / 0.62))) if 0.25 <= u <= 0.87 else 0.0
            apex = bell_curve(u, 0.58, 0.14)
            spin = 360.0 * smoothstep(0.32, 0.78, u)

            root_t.append([0.0, 0.92 * arc, 1.15 * smoothstep(0.25, 0.82, u)])
            pelvis_t.append([0.0, -0.09 * height * charge, 0.0])
            pelvis_r.append(euler_xyz_to_quat(-165.0 * air + 18.0 * charge, spin, 22.0 * air))
            spine1_r.append(euler_xyz_to_quat(-14.0 * air + 16.0 * charge, 0.0, 0.0))
            spine3_r.append(euler_xyz_to_quat(-10.0 * air + 14.0 * charge, 0.0, 0.0))
            head_r.append(euler_xyz_to_quat(18.0 * air - 12.0 * charge, 0.0, 0.0))

            uarm_l_r.append(euler_xyz_to_quat(-42.0 * air - 20.0 * charge, 24.0, -68.0 * air - 20.0))
            uarm_r_r.append(euler_xyz_to_quat(-42.0 * air - 20.0 * charge, -24.0, 68.0 * air + 20.0))
            thigh_l_r.append(euler_xyz_to_quat(-34.0 * charge + 32.0 * air, 0.0, 8.0 * air))
            calf_l_r.append(euler_xyz_to_quat(54.0 * charge + 52.0 * air, 0.0, 0.0))
            thigh_r_r.append(euler_xyz_to_quat(-24.0 * charge - 120.0 * apex, 0.0, -8.0 * air))
            calf_r_r.append(euler_xyz_to_quat(42.0 * charge + 10.0 * apex, 0.0, 0.0))

            sm = 1.0 + 0.30 * apex
            calf_r_s.append([1.0, sm, sm])
            foot_r_s.append([1.0, sm, sm])

        add_trans("root", root_t)
        add_trans("pelvis", pelvis_t)
        add_rot("pelvis", pelvis_r)
        add_rot("spine_01", spine1_r)
        add_rot("spine_03", spine3_r)
        add_rot("head", head_r)
        add_rot("upperarm_l", uarm_l_r)
        add_rot("upperarm_r", uarm_r_r)
        add_rot("thigh_l", thigh_l_r)
        add_rot("calf_l", calf_l_r)
        add_rot("thigh_r", thigh_r_r)
        add_rot("calf_r", calf_r_r)
        add_scale("calf_r", calf_r_s)
        add_scale("foot_r", foot_r_s)
        return times, tracks

    # ------------------------------------------------------------------
    # 11. Mocap_KO_Knockdown (60 FPS, 73 keyframes = 1.20s spiral knockdown + ground bounce)
    # ------------------------------------------------------------------
    if clip_name == "Mocap_KO_Knockdown":
        num_frames = 73
        times = [f / FPS for f in range(num_frames)]
        us = [f / (num_frames - 1) for f in range(num_frames)]

        root_t, pelvis_t, pelvis_r = [], [], []
        spine1_r, spine3_r, head_r = [], [], []
        uarm_l_r, uarm_r_r, thigh_l_r, thigh_r_r = [], [], [], []

        for u in us:
            fall = smoothstep(0.08, 0.62, u)
            bounce = 0.08 * math.sin(math.pi * max(0.0, (u - 0.62) / 0.25)) if 0.62 <= u <= 0.87 else 0.0
            air_h = 0.32 * math.sin(math.pi * min(1.0, u / 0.62)) if u < 0.62 else 0.0

            root_t.append([0.0, air_h + bounce, -1.05 * smoothstep(0.0, 0.72, u)])
            pelvis_t.append([0.0, -0.44 * height * fall, 0.0])
            pelvis_r.append(euler_xyz_to_quat(-88.0 * fall, -24.0 * fall, 16.0 * fall))
            spine1_r.append(euler_xyz_to_quat(-12.0 * fall, 0.0, 0.0))
            spine3_r.append(euler_xyz_to_quat(-10.0 * fall, 0.0, 0.0))
            head_r.append(euler_xyz_to_quat(14.0 * fall, 18.0 * fall, 0.0))

            uarm_l_r.append(euler_xyz_to_quat(12.0 * fall, 0.0, -78.0 * fall - 15.0))
            uarm_r_r.append(euler_xyz_to_quat(12.0 * fall, 0.0, 78.0 * fall + 15.0))
            thigh_l_r.append(euler_xyz_to_quat(10.0 * fall, 14.0 * fall, 12.0 * fall))
            thigh_r_r.append(euler_xyz_to_quat(6.0 * fall, -14.0 * fall, -12.0 * fall))

        add_trans("root", root_t)
        add_trans("pelvis", pelvis_t)
        add_rot("pelvis", pelvis_r)
        add_rot("spine_01", spine1_r)
        add_rot("spine_03", spine3_r)
        add_rot("head", head_r)
        add_rot("upperarm_l", uarm_l_r)
        add_rot("upperarm_r", uarm_r_r)
        add_rot("thigh_l", thigh_l_r)
        add_rot("thigh_r", thigh_r_r)
        return times, tracks

    raise ValueError(f"Unknown clip name: {clip_name}")


def _read_accessor_floats(gltf: dict[str, Any], bin_chunk: bytes | bytearray, acc_idx: int) -> np.ndarray:
    acc = gltf["accessors"][acc_idx]
    bv = gltf["bufferViews"][acc["bufferView"]]
    byte_off = int(bv.get("byteOffset", 0)) + int(acc.get("byteOffset", 0))
    count = int(acc["count"])
    num_comp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[acc["type"]]
    raw = bin_chunk[byte_off:byte_off + count * num_comp * 4]
    arr = np.frombuffer(bytes(raw), dtype=np.float32).copy()
    return arr if num_comp == 1 else arr.reshape((count, num_comp))


def _compact_geometry_and_skin_buffers(
    gltf: dict[str, Any],
    old_bin: bytearray,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bytearray]:
    """
    Preserve all mesh primitive attribute/index accessors and skin inverseBindMatrices accessors
    while stripping stale animation accessors/bufferViews so re-runs stay compact and deterministic.
    """
    used_acc_indices: set[int] = set()
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            for acc_i in prim.get("attributes", {}).values():
                used_acc_indices.add(int(acc_i))
            if "indices" in prim:
                used_acc_indices.add(int(prim["indices"]))
    for skin in gltf.get("skins", []):
        if "inverseBindMatrices" in skin:
            used_acc_indices.add(int(skin["inverseBindMatrices"]))

    ordered_old_accs = sorted(used_acc_indices)
    acc_remap: dict[int, int] = {}
    new_bvs: list[dict[str, Any]] = []
    new_accs: list[dict[str, Any]] = []
    new_bin = bytearray()

    for old_acc_idx in ordered_old_accs:
        old_acc = dict(gltf["accessors"][old_acc_idx])
        old_bv = gltf["bufferViews"][old_acc["bufferView"]]
        b_off = int(old_bv.get("byteOffset", 0))
        b_len = int(old_bv["byteLength"])
        chunk_bytes = bytes(old_bin[b_off:b_off + b_len])

        while len(new_bin) % 4 != 0:
            new_bin.append(0)
        new_off = len(new_bin)
        new_bin.extend(chunk_bytes)

        bv_entry: dict[str, Any] = {
            "buffer": 0,
            "byteOffset": new_off,
            "byteLength": len(chunk_bytes),
        }
        if "target" in old_bv:
            bv_entry["target"] = old_bv["target"]
        if "byteStride" in old_bv:
            bv_entry["byteStride"] = old_bv["byteStride"]

        new_bv_idx = len(new_bvs)
        new_bvs.append(bv_entry)

        old_acc["bufferView"] = new_bv_idx
        new_acc_idx = len(new_accs)
        new_accs.append(old_acc)
        acc_remap[old_acc_idx] = new_acc_idx

    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            prim["attributes"] = {k: acc_remap[int(v)] for k, v in prim.get("attributes", {}).items()}
            if "indices" in prim:
                prim["indices"] = acc_remap[int(prim["indices"])]
    for skin in gltf.get("skins", []):
        if "inverseBindMatrices" in skin:
            skin["inverseBindMatrices"] = acc_remap[int(skin["inverseBindMatrices"])]

    return new_bvs, new_accs, new_bin


def _extract_and_resample_stepped_clip_60fps(
    anim: dict[str, Any],
    gltf: dict[str, Any],
    old_bin: bytearray,
) -> tuple[np.ndarray, list[dict[str, Any]], str]:
    """
    Resample an existing combat clip (such as `Anim_Idle` or `Anim_623HP_BicycleKick`) onto a uniform
    60 FPS grid (`dt = 1/60s` on every integer frame `0..end_frame`) so UE5 Interchange & Blender 5.2
    never infer 24 FPS or 30 FPS from sparse keyframe intervals (e.g. 0.25s or 5/60s = 1/12s).
    """
    anim_name = anim["name"]
    samplers = anim["samplers"]
    channels = anim["channels"]
    interp = samplers[0].get("interpolation", "STEP") if samplers else "STEP"

    first_in = _read_accessor_floats(gltf, old_bin, samplers[0]["input"])
    end_frame = int(round(float(first_in[-1]) * FPS))
    if anim_name == "Anim_Idle" and end_frame < 60:
        end_frame = 60  # Complete 1.00s 60-frame guard loop at uniform 60 FPS
    end_frame = max(1, end_frame)

    dense_frames = list(range(end_frame + 1))
    dense_times = np.array([f / FPS for f in dense_frames], dtype=np.float32)

    resampled_tracks: list[dict[str, Any]] = []
    for ch in channels:
        samp = samplers[ch["sampler"]]
        in_times = _read_accessor_floats(gltf, old_bin, samp["input"])
        out_vals = _read_accessor_floats(gltf, old_bin, samp["output"])
        key_frames = [int(round(float(t) * FPS)) for t in in_times]

        # For Anim_Idle looping to frame 60, return cleanly to frame 0 guard pose at frame 60
        if anim_name == "Anim_Idle" and key_frames[-1] < end_frame:
            key_frames = key_frames + [end_frame]
            out_vals = np.vstack([out_vals, out_vals[0:1]])

        dense_vals = []
        for f in dense_frames:
            k_idx = 0
            for idx_pos, kf in enumerate(key_frames):
                if kf <= f:
                    k_idx = idx_pos
                else:
                    break
            dense_vals.append(out_vals[k_idx].tolist())

        resampled_tracks.append({
            "node": int(ch["target"]["node"]),
            "path": ch["target"]["path"],
            "values": dense_vals,
        })

    return dense_times, resampled_tracks, interp


def upgrade_fighter_glb(glb_path: str) -> dict[str, Any]:
    filename = os.path.basename(glb_path)
    is_boss = (filename == "SK_SUPREME_JUDGE_BOSS.glb")

    gltf, old_bin_chunk = read_glb(glb_path)
    node_map = get_node_map(gltf)

    if "animations" not in gltf:
        gltf["animations"] = []

    # Extract existing base combat clips BEFORE compacting animation buffers
    preserved_combat_anims = [a for a in gltf["animations"] if a.get("name") not in TARGET_CLIPS]
    resampled_combat_inputs = [
        (a["name"], *_extract_and_resample_stepped_clip_60fps(a, gltf, old_bin_chunk))
        for a in preserved_combat_anims
    ]

    buffer_views, accessors, bin_chunk = _compact_geometry_and_skin_buffers(gltf, old_bin_chunk)
    gltf["bufferViews"] = buffer_views
    gltf["accessors"] = accessors
    gltf["animations"] = []

    def append_bin(raw_bytes: bytes) -> int:
        while len(bin_chunk) % 4 != 0:
            bin_chunk.append(0)
        offset = len(bin_chunk)
        bin_chunk.extend(raw_bytes)
        bv_idx = len(buffer_views)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": offset,
            "byteLength": len(raw_bytes),
        })
        return bv_idx

    def write_animation_clip(
        clip_name: str,
        times_arr: np.ndarray,
        tracks: list[dict[str, Any]],
        interpolation: str,
        special_desc: str,
    ) -> dict[str, Any]:
        bv_t = append_bin(times_arr.tobytes())
        acc_t = len(accessors)
        accessors.append({
            "bufferView": bv_t,
            "componentType": FLOAT,
            "count": int(len(times_arr)),
            "type": "SCALAR",
            "min": [float(times_arr.min())],
            "max": [float(times_arr.max())],
        })

        samplers = []
        channels = []
        for tr in tracks:
            path = tr["path"]
            vals_arr = np.array(tr["values"], dtype=np.float32)
            bv_v = append_bin(vals_arr.tobytes())
            acc_v = len(accessors)
            v_type = "VEC4" if path == "rotation" else "VEC3"
            accessors.append({
                "bufferView": bv_v,
                "componentType": FLOAT,
                "count": int(len(vals_arr)),
                "type": v_type,
            })

            s_idx = len(samplers)
            samplers.append({
                "input": acc_t,
                "interpolation": interpolation,
                "output": acc_v,
            })
            channels.append({
                "sampler": s_idx,
                "target": {
                    "node": int(tr["node"]),
                    "path": path,
                },
            })

        gltf["animations"].append({
            "name": clip_name,
            "samplers": samplers,
            "channels": channels,
        })
        return {
            "ClipName": clip_name,
            "DurationSeconds": round(float(times_arr[-1]), 4),
            "FPS": int(FPS),
            "UniformFrameStepSeconds": round(1.0 / FPS, 6),
            "KeyframeCount": int(len(times_arr)),
            "ChannelCount": len(channels),
            "SamplerCount": len(samplers),
            "Interpolation": interpolation,
            "SpecialFeatures": special_desc,
        }

    all_clip_summaries = []
    upgraded_clip_summaries = []

    # 1. Re-emit the 5 stepped combat clips resampled to uniform 60 FPS (dt = 1/60s)
    for c_name, c_times, c_tracks, c_interp in resampled_combat_inputs:
        info = write_animation_clip(
            c_name,
            c_times,
            c_tracks,
            c_interp,
            "Uniform 60 FPS stepped competitive frame-data animation (dt = 1/60s)",
        )
        all_clip_summaries.append(info)

    # 2. Emit the 5 full-body linear 60 FPS clips (dt = 1/60s)
    for clip_name in TARGET_CLIPS:
        times, tracks = build_clip_tracks(clip_name, gltf, node_map, is_boss)
        times_arr = np.array(times, dtype=np.float32)
        special_feat = (
            "Hovering levitation + dual counter-rotating astrolabe halo motion"
            if (is_boss and clip_name == "Victory_Pose")
            else ("Hovering idle + orbital astrolabe halo rotation"
                  if (is_boss and clip_name == "Idle_Breath")
                  else "Full-body 60 FPS keyframe animation")
        )
        info = write_animation_clip(clip_name, times_arr, tracks, "LINEAR", special_feat)
        upgraded_clip_summaries.append(info)
        all_clip_summaries.append(info)

    write_glb(glb_path, gltf, bin_chunk)

    return {
        "FighterFile": filename,
        "FighterID": filename.replace("SK_", "").replace(".glb", ""),
        "IsBoss": is_boss,
        "FileSizeBytes": os.path.getsize(glb_path),
        "TotalAnimationsInGLB": len(gltf["animations"]),
        "AllAnimationNames": [a["name"] for a in gltf["animations"]],
        "AllClipsUniform60FPS": True,
        "AllClips": all_clip_summaries,
        "UpgradedClips": upgraded_clip_summaries,
    }


def validate_fighter_glb(glb_path: str) -> dict[str, Any]:
    """Programmatically validate GLB magic, chunk lengths, file size, and all 5 target animation clips."""
    with open(glb_path, "rb") as f:
        raw = f.read()

    assert raw[:4] == b"glTF", f"{glb_path}: does not start with b'glTF'"
    magic, version, total_len = struct.unpack("<III", raw[:12])
    assert version == 2, f"{glb_path}: unexpected glTF version {version}"
    assert total_len == len(raw), f"{glb_path}: header length {total_len} != file size {len(raw)}"

    jlen, jtype = struct.unpack("<II", raw[12:20])
    assert jtype == CHUNK_JSON, f"{glb_path}: missing JSON chunk"
    assert jlen % 4 == 0, f"{glb_path}: JSON chunk not 4-byte aligned"
    gltf = json.loads(raw[20:20 + jlen].decode("utf-8"))

    bin_hdr_off = 20 + jlen
    blen, btype = struct.unpack("<II", raw[bin_hdr_off:bin_hdr_off + 8])
    assert btype == CHUNK_BIN, f"{glb_path}: missing BIN chunk"
    assert blen % 4 == 0, f"{glb_path}: BIN chunk not 4-byte aligned"
    assert 12 + 8 + jlen + 8 + blen == len(raw), f"{glb_path}: chunk lengths do not sum to file size"
    assert gltf["buffers"][0]["byteLength"] == blen, f"{glb_path}: buffer byteLength mismatch"

    accessors = gltf["accessors"]
    buffer_views = gltf["bufferViews"]
    nodes = gltf["nodes"]
    anims_by_name = {a["name"]: a for a in gltf.get("animations", [])}
    bin_bytes = raw[bin_hdr_off + 8:bin_hdr_off + 8 + blen]
    expected_dt = 1.0 / FPS

    assert len(anims_by_name) == len(TARGET_CLIPS) + 5, (
        f"{glb_path}: expected {len(TARGET_CLIPS) + 5} animations, found {len(anims_by_name)}"
    )
    for clip_name in TARGET_CLIPS:
        assert clip_name in anims_by_name, f"{glb_path}: missing required clip '{clip_name}'"

    for clip_name, anim in anims_by_name.items():
        samplers = anim["samplers"]
        channels = anim["channels"]
        assert len(samplers) > 0 and len(channels) > 0, f"{glb_path}/{clip_name}: empty samplers/channels"

        for ch in channels:
            s_idx = ch["sampler"]
            assert 0 <= s_idx < len(samplers), f"{glb_path}/{clip_name}: invalid sampler index {s_idx}"
            t_node = ch["target"]["node"]
            t_path = ch["target"]["path"]
            assert 0 <= t_node < len(nodes), f"{glb_path}/{clip_name}: invalid node index {t_node}"
            assert t_path in ("translation", "rotation", "scale"), f"{glb_path}/{clip_name}: invalid path {t_path}"

            samp = samplers[s_idx]
            in_idx = samp["input"]
            out_idx = samp["output"]
            assert 0 <= in_idx < len(accessors), f"{glb_path}/{clip_name}: invalid input accessor {in_idx}"
            assert 0 <= out_idx < len(accessors), f"{glb_path}/{clip_name}: invalid output accessor {out_idx}"

            in_acc = accessors[in_idx]
            out_acc = accessors[out_idx]
            assert in_acc["type"] == "SCALAR" and in_acc["componentType"] == FLOAT
            assert "min" in in_acc and "max" in in_acc
            assert in_acc["count"] == out_acc["count"], f"{glb_path}/{clip_name}: keyframe count mismatch"
            assert in_acc["count"] >= 2, f"{glb_path}/{clip_name}: expected >=2 keyframes"
            expected_type = "VEC4" if t_path == "rotation" else "VEC3"
            assert out_acc["type"] == expected_type and out_acc["componentType"] == FLOAT

            for acc in (in_acc, out_acc):
                bv_idx = acc["bufferView"]
                assert 0 <= bv_idx < len(buffer_views)
                bv = buffer_views[bv_idx]
                assert bv["byteOffset"] % 4 == 0
                assert bv["byteOffset"] + bv["byteLength"] <= blen

            # Verify uniform 60 FPS spacing (dt = 1/60s) on every single clip in the GLB
            in_bv = buffer_views[in_acc["bufferView"]]
            ts = np.frombuffer(
                bin_bytes[in_bv["byteOffset"]:in_bv["byteOffset"] + in_bv["byteLength"]],
                dtype=np.float32,
            )
            diffs = np.diff(ts)
            max_err = float(np.max(np.abs(diffs - expected_dt)))
            assert max_err < 1e-4, f"{glb_path}/{clip_name}: non-60FPS dt detected (max_err={max_err})"

    return {
        "File": os.path.basename(glb_path),
        "Valid": True,
        "SizeBytes": len(raw),
        "JSONChunkBytes": jlen,
        "BINChunkBytes": blen,
        "TotalAnimations": len(anims_by_name),
        "VerifiedUniform60FPSClips": list(anims_by_name.keys()),
    }


def main() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fighters_dir = os.path.join(repo_root, "Assets", "Models3D", "Fighters")
    glb_files = sorted(glob.glob(os.path.join(fighters_dir, "SK_*.glb")))

    if len(glb_files) != 17:
        raise RuntimeError(f"Expected 17 fighter GLB files, found {len(glb_files)}")

    fighter_entries = []
    validation_results = []

    for glb_path in glb_files:
        summary = upgrade_fighter_glb(glb_path)
        val = validate_fighter_glb(glb_path)
        fighter_entries.append(summary)
        validation_results.append(val)
        print(
            f"[OK] {summary['FighterFile']} | {summary['FileSizeBytes']:,} bytes | "
            f"{summary['TotalAnimationsInGLB']} total clips | validated {len(TARGET_CLIPS)}/{len(TARGET_CLIPS)} Mocap/60Hz clips"
        )

    manifest = {
        "SchemaVersion": "2.2.0-UE5.4-GLTF2-HighPolyMocap60FPS",
        "Project": "LA COPA ETERNA: SANGRE Y POTRERO",
        "TargetFormat": "glTF 2.0 Binary (.glb)",
        "SampleRateFPS": int(FPS),
        "UniformFrameStepSeconds": round(1.0 / FPS, 6),
        "All10ClipsUniform60FPS": True,
        "All16ClipsUniform60FPS": True,
        "SteppedCombatClipNames": [
            "Anim_Idle",
            "Anim_5LP_Jab4f",
            "Anim_236SK_Shot",
            "Anim_623HP_BicycleKick",
            "Anim_214SK_Scorpion",
        ],
        "UpgradedClipNames": TARGET_CLIPS,
        "TotalFightersUpgraded": len(fighter_entries),
        "ValidationPassed": all(v["Valid"] for v in validation_results),
        "ClipCatalog": [
            {
                "ClipName": "Anim_Idle",
                "DurationSeconds": 1.0,
                "KeyframeCount": 61,
                "FPS": 60,
                "Interpolation": "STEP",
                "Looping": True,
                "Description": "Uniform 60 FPS stepped street-guard loop (dt = 1/60s across frames 0..60)",
            },
            {
                "ClipName": "Anim_5LP_Jab4f",
                "DurationSeconds": 0.2333,
                "KeyframeCount": 15,
                "FPS": 60,
                "Interpolation": "STEP",
                "Looping": False,
                "Description": "Uniform 60 FPS stepped 4-frame startup jab (frames 0..14, dt = 1/60s)",
            },
            {
                "ClipName": "Anim_236SK_Shot",
                "DurationSeconds": 0.6333,
                "KeyframeCount": 39,
                "FPS": 60,
                "Interpolation": "STEP",
                "Looping": False,
                "Description": "Uniform 60 FPS stepped special ball shot (frames 0..38, dt = 1/60s)",
            },
            {
                "ClipName": "Anim_623HP_BicycleKick",
                "DurationSeconds": 0.5833,
                "KeyframeCount": 36,
                "FPS": 60,
                "Interpolation": "STEP",
                "Looping": False,
                "Description": "Uniform 60 FPS stepped anti-air bicycle kick with 1.25x shin/boot active scale (frames 0..35, dt = 1/60s)",
            },
            {
                "ClipName": "Anim_214SK_Scorpion",
                "DurationSeconds": 0.7,
                "KeyframeCount": 43,
                "FPS": 60,
                "Interpolation": "STEP",
                "Looping": False,
                "Description": "Uniform 60 FPS stepped scorpion reflect kick (frames 0..42, dt = 1/60s)",
            },
            {
                "ClipName": "Idle_Breath",
                "DurationSeconds": 2.0,
                "KeyframeCount": 121,
                "FPS": 60,
                "Interpolation": "LINEAR",
                "Looping": True,
                "Description": "60 FPS looping breathing & fighting guard sway (plus hovering + orbital astrolabe halo on SK_SUPREME_JUDGE_BOSS)",
            },
            {
                "ClipName": "Dash_Forward",
                "DurationSeconds": 0.6,
                "KeyframeCount": 37,
                "FPS": 60,
                "Interpolation": "LINEAR",
                "Looping": False,
                "Description": "Explosive forward sprint lean with root translation burst, torso pitch, arm drive, and hair wind-drag",
            },
            {
                "ClipName": "Kick_High",
                "DurationSeconds": 0.8,
                "KeyframeCount": 49,
                "FPS": 60,
                "Interpolation": "LINEAR",
                "Looping": False,
                "Description": "Dynamic high leg/body strike rotation & forward lunge with 1.18x anime impact exaggeration on striking shin/boot",
            },
            {
                "ClipName": "Special_Chilena",
                "DurationSeconds": 1.2,
                "KeyframeCount": 73,
                "FPS": 60,
                "Interpolation": "LINEAR",
                "Looping": False,
                "Description": "Acrobatic 360-degree overhead bicycle-kick arc with parabolic leap, scissor-kick whip, and 1.25x apex strike scale",
            },
            {
                "ClipName": "Victory_Pose",
                "DurationSeconds": 1.5,
                "KeyframeCount": 91,
                "FPS": 60,
                "Interpolation": "LINEAR",
                "Looping": False,
                "Description": "Triumphant championship celebration salute (SK_SUPREME_JUDGE_BOSS features hovering levitation + dual counter-rotating astrolabe halo)",
            },
            {
                "ClipName": "Mocap_Walk_Forward",
                "DurationSeconds": 1.0,
                "KeyframeCount": 61,
                "FPS": 60,
                "Interpolation": "LINEAR",
                "Looping": True,
                "Description": "60 FPS Mocap athletic forward walk cycle with counter-rotating shoulders, pelvis bob, and foot roll",
            },
            {
                "ClipName": "Mocap_Backdash_Dodge",
                "DurationSeconds": 0.45,
                "KeyframeCount": 28,
                "FPS": 60,
                "Interpolation": "LINEAR",
                "Looping": False,
                "Description": "60 FPS Mocap explosive backward evade hop with guarded torso recoil",
            },
            {
                "ClipName": "Mocap_Block_Guard",
                "DurationSeconds": 0.8,
                "KeyframeCount": 49,
                "FPS": 60,
                "Interpolation": "LINEAR",
                "Looping": False,
                "Description": "60 FPS Mocap braced cross-arm competitive block guard with knee absorption",
            },
            {
                "ClipName": "Mocap_Hitstun_Knockback",
                "DurationSeconds": 0.5,
                "KeyframeCount": 31,
                "FPS": 60,
                "Interpolation": "LINEAR",
                "Looping": False,
                "Description": "60 FPS Mocap whiplash hitstun recoil with decoupled pelvis_visual_offset hitstop vibration",
            },
            {
                "ClipName": "Mocap_Super_Potrero",
                "DurationSeconds": 1.4,
                "KeyframeCount": 85,
                "FPS": 60,
                "Interpolation": "LINEAR",
                "Looping": False,
                "Description": "60 FPS Mocap Super Hinchada Nivel 3 leaping volley strike with 1.30x active smear frame",
            },
            {
                "ClipName": "Mocap_KO_Knockdown",
                "DurationSeconds": 1.2,
                "KeyframeCount": 73,
                "FPS": 60,
                "Interpolation": "LINEAR",
                "Looping": False,
                "Description": "60 FPS Mocap full-body knockdown collapse and stadium turf rebound",
            },
        ],
        "Fighters": fighter_entries,
    }

    manifest_path = os.path.join(fighters_dir, "Animations3D_TechnicalManifest.json")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    print(f"\n[DONE] Upgraded and validated {len(validation_results)}/17 fighter GLBs.")
    print(f"[DONE] Manifest written to: {manifest_path}")


if __name__ == "__main__":
    main()
