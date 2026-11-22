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

    raise ValueError(f"Unknown clip name: {clip_name}")


def upgrade_fighter_glb(glb_path: str) -> dict[str, Any]:
    filename = os.path.basename(glb_path)
    is_boss = (filename == "SK_SUPREME_JUDGE_BOSS.glb")

    gltf, bin_chunk = read_glb(glb_path)
    node_map = get_node_map(gltf)

    if "animations" not in gltf:
        gltf["animations"] = []

    # Remove any previous versions of TARGET_CLIPS to keep reruns clean
    existing_anims = [a for a in gltf["animations"] if a.get("name") not in TARGET_CLIPS]
    gltf["animations"] = existing_anims

    buffer_views = gltf["bufferViews"]
    accessors = gltf["accessors"]

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

    clip_summaries = []

    for clip_name in TARGET_CLIPS:
        times, tracks = build_clip_tracks(clip_name, gltf, node_map, is_boss)
        times_arr = np.array(times, dtype=np.float32)

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
                "interpolation": "LINEAR",
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

        clip_summaries.append({
            "ClipName": clip_name,
            "DurationSeconds": round(float(times_arr[-1]), 4),
            "FPS": int(FPS),
            "KeyframeCount": int(len(times_arr)),
            "ChannelCount": len(channels),
            "SamplerCount": len(samplers),
            "Interpolation": "LINEAR",
            "SpecialFeatures": (
                "Hovering levitation + dual counter-rotating astrolabe halo motion"
                if (is_boss and clip_name == "Victory_Pose")
                else ("Hovering idle + orbital astrolabe halo rotation"
                      if (is_boss and clip_name == "Idle_Breath")
                      else "Full-body 60 FPS keyframe animation")
            ),
        })

    write_glb(glb_path, gltf, bin_chunk)

    return {
        "FighterFile": filename,
        "FighterID": filename.replace("SK_", "").replace(".glb", ""),
        "IsBoss": is_boss,
        "FileSizeBytes": os.path.getsize(glb_path),
        "TotalAnimationsInGLB": len(gltf["animations"]),
        "AllAnimationNames": [a["name"] for a in gltf["animations"]],
        "UpgradedClips": clip_summaries,
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

    for clip_name in TARGET_CLIPS:
        assert clip_name in anims_by_name, f"{glb_path}: missing required clip '{clip_name}'"
        anim = anims_by_name[clip_name]
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
            expected_type = "VEC4" if t_path == "rotation" else "VEC3"
            assert out_acc["type"] == expected_type and out_acc["componentType"] == FLOAT

            for acc in (in_acc, out_acc):
                bv_idx = acc["bufferView"]
                assert 0 <= bv_idx < len(buffer_views)
                bv = buffer_views[bv_idx]
                assert bv["byteOffset"] % 4 == 0
                assert bv["byteOffset"] + bv["byteLength"] <= blen

    return {
        "File": os.path.basename(glb_path),
        "Valid": True,
        "SizeBytes": len(raw),
        "JSONChunkBytes": jlen,
        "BINChunkBytes": blen,
        "TotalAnimations": len(anims_by_name),
        "VerifiedClips": TARGET_CLIPS,
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
            f"{summary['TotalAnimationsInGLB']} total clips | validated 5/5 new clips"
        )

    manifest = {
        "SchemaVersion": "2.0.0-UE5.4-GLTF2-Animations",
        "Project": "LA COPA ETERNA: SANGRE Y POTRERO",
        "TargetFormat": "glTF 2.0 Binary (.glb)",
        "SampleRateFPS": int(FPS),
        "UpgradedClipNames": TARGET_CLIPS,
        "TotalFightersUpgraded": len(fighter_entries),
        "ValidationPassed": all(v["Valid"] for v in validation_results),
        "ClipCatalog": [
            {
                "ClipName": "Idle_Breath",
                "DurationSeconds": 2.0,
                "KeyframeCount": 121,
                "Looping": True,
                "Description": "60 FPS looping breathing & fighting guard sway (plus hovering + orbital astrolabe halo on SK_SUPREME_JUDGE_BOSS)",
            },
            {
                "ClipName": "Dash_Forward",
                "DurationSeconds": 0.6,
                "KeyframeCount": 37,
                "Looping": False,
                "Description": "Explosive forward sprint lean with root translation burst, torso pitch, arm drive, and hair wind-drag",
            },
            {
                "ClipName": "Kick_High",
                "DurationSeconds": 0.8,
                "KeyframeCount": 49,
                "Looping": False,
                "Description": "Dynamic high leg/body strike rotation & forward lunge with 1.18x anime impact exaggeration on striking shin/boot",
            },
            {
                "ClipName": "Special_Chilena",
                "DurationSeconds": 1.2,
                "KeyframeCount": 73,
                "Looping": False,
                "Description": "Acrobatic 360-degree overhead bicycle-kick arc with parabolic leap, scissor-kick whip, and 1.25x apex strike scale",
            },
            {
                "ClipName": "Victory_Pose",
                "DurationSeconds": 1.5,
                "KeyframeCount": 91,
                "Looping": False,
                "Description": "Triumphant championship celebration salute (SK_SUPREME_JUDGE_BOSS features hovering levitation + dual counter-rotating astrolabe halo)",
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
