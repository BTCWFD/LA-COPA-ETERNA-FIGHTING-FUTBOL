#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_conmebol_stages_gltf.py
3D Stages Architect for LA COPA ETERNA: SANGRE Y POTRERO.

Generates all 10 distinct CONMEBOL 3D Stadium glTF 2.0 binary (.glb) models
in Assets/Models3D/Stages/ plus Assets/Models3D/Stages/Stages3D_TechnicalManifest.json,
and validates every generated .glb binary header and JSON chunk.

Coordinate convention (glTF 2.0 right-handed Y-up, meters):
  - X: Fighting plane left (-X) to right (+X).
       Zone A pitch: [-12.5, +12.5], Destructible Wall Break panels at x = +/-12.5,
       Zone B extended outer arena: [-18.5, -12.5] and [+12.5, +18.5].
  - Y: Vertical up (+Y). Playable pitch surface at y = 0.0.
  - Z: Depth. Camera looks from +Z toward -Z; grandstands, towers, canopies,
       and mountain/volcano backdrops occupy -Z and flanking sides so the
       2.5D fighting foreground remains unobstructed.
"""

import os
import json
import math
import struct
import numpy as np


# ============================================================================
# GEOMETRY PRIMITIVE BUILDERS (Right-Handed Y-Up, Clean Normals & UVs)
# ============================================================================

def _rot_matrix(rx_deg: float = 0.0, ry_deg: float = 0.0, rz_deg: float = 0.0) -> np.ndarray:
    rx, ry, rz = math.radians(rx_deg), math.radians(ry_deg), math.radians(rz_deg)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=np.float32)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float32)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], dtype=np.float32)
    return (Ry @ Rx @ Rz).astype(np.float32)


def make_box(
    center: list[float],
    half_extents: list[float],
    rot_x: float = 0.0,
    rot_y: float = 0.0,
    rot_z: float = 0.0,
) -> dict:
    hx, hy, hz = half_extents
    faces = [
        ([-hx, -hy, hz], [hx, -hy, hz], [hx, hy, hz], [-hx, hy, hz], [0, 0, 1]),
        ([hx, -hy, -hz], [-hx, -hy, -hz], [-hx, hy, -hz], [hx, hy, -hz], [0, 0, -1]),
        ([hx, -hy, hz], [hx, -hy, -hz], [hx, hy, -hz], [hx, hy, hz], [1, 0, 0]),
        ([-hx, -hy, -hz], [-hx, -hy, hz], [-hx, hy, hz], [-hx, hy, -hz], [-1, 0, 0]),
        ([-hx, hy, hz], [hx, hy, hz], [hx, hy, -hz], [-hx, hy, -hz], [0, 1, 0]),
        ([-hx, -hy, -hz], [hx, -hy, -hz], [hx, -hy, hz], [-hx, -hy, hz], [0, -1, 0]),
    ]
    positions, normals, uvs, indices = [], [], [], []
    for f_idx, (v0, v1, v2, v3, nrm) in enumerate(faces):
        base = f_idx * 4
        for vi, v in enumerate((v0, v1, v2, v3)):
            positions.append(v)
            normals.append(nrm)
            uvs.append([1.0 if vi in (1, 2) else 0.0, 1.0 if vi in (2, 3) else 0.0])
        indices.extend([base, base + 1, base + 2, base, base + 2, base + 3])

    pos = np.array(positions, dtype=np.float32)
    nrm = np.array(normals, dtype=np.float32)
    if rot_x != 0.0 or rot_y != 0.0 or rot_z != 0.0:
        R = _rot_matrix(rot_x, rot_y, rot_z)
        pos = pos @ R.T
        nrm = nrm @ R.T
    pos += np.array(center, dtype=np.float32)

    return {
        "positions": pos,
        "normals": nrm,
        "uvs": np.array(uvs, dtype=np.float32),
        "indices": np.array(indices, dtype=np.uint32),
    }


def make_cylinder(
    center: list[float],
    radius_bottom: float,
    radius_top: float,
    height: float,
    segments: int = 16,
    rot_x: float = 0.0,
    rot_y: float = 0.0,
    rot_z: float = 0.0,
    cap_top: bool = True,
    cap_bottom: bool = True,
) -> dict:
    half_h = height * 0.5
    positions, normals, uvs, indices = [], [], [], []

    slope = (radius_bottom - radius_top) / max(height, 1e-5)
    n_len = math.sqrt(1.0 + slope * slope)

    # Side wall
    for i in range(segments + 1):
        u = i / segments
        theta = u * 2.0 * math.pi
        ct, st = math.cos(theta), math.sin(theta)
        nx, ny, nz = ct / n_len, slope / n_len, st / n_len
        positions.append([radius_bottom * ct, -half_h, radius_bottom * st])
        normals.append([nx, ny, nz])
        uvs.append([u, 0.0])
        positions.append([radius_top * ct, half_h, radius_top * st])
        normals.append([nx, ny, nz])
        uvs.append([u, 1.0])

    for i in range(segments):
        b0 = i * 2
        b1 = b0 + 2
        t0 = b0 + 1
        t1 = b1 + 1
        indices.extend([b0, t0, b1, b1, t0, t1])

    # Top cap
    if cap_top and radius_top > 1e-4:
        c_idx = len(positions)
        positions.append([0.0, half_h, 0.0])
        normals.append([0.0, 1.0, 0.0])
        uvs.append([0.5, 0.5])
        ring_start = len(positions)
        for i in range(segments + 1):
            theta = (i / segments) * 2.0 * math.pi
            ct, st = math.cos(theta), math.sin(theta)
            positions.append([radius_top * ct, half_h, radius_top * st])
            normals.append([0.0, 1.0, 0.0])
            uvs.append([0.5 + 0.5 * ct, 0.5 + 0.5 * st])
        for i in range(segments):
            indices.extend([c_idx, ring_start + i + 1, ring_start + i])

    # Bottom cap
    if cap_bottom and radius_bottom > 1e-4:
        c_idx = len(positions)
        positions.append([0.0, -half_h, 0.0])
        normals.append([0.0, -1.0, 0.0])
        uvs.append([0.5, 0.5])
        ring_start = len(positions)
        for i in range(segments + 1):
            theta = (i / segments) * 2.0 * math.pi
            ct, st = math.cos(theta), math.sin(theta)
            positions.append([radius_bottom * ct, -half_h, radius_bottom * st])
            normals.append([0.0, -1.0, 0.0])
            uvs.append([0.5 + 0.5 * ct, 0.5 + 0.5 * st])
        for i in range(segments):
            indices.extend([c_idx, ring_start + i, ring_start + i + 1])

    pos = np.array(positions, dtype=np.float32)
    nrm = np.array(normals, dtype=np.float32)
    if rot_x != 0.0 or rot_y != 0.0 or rot_z != 0.0:
        R = _rot_matrix(rot_x, rot_y, rot_z)
        pos = pos @ R.T
        nrm = nrm @ R.T
    pos += np.array(center, dtype=np.float32)

    return {
        "positions": pos,
        "normals": nrm,
        "uvs": np.array(uvs, dtype=np.float32),
        "indices": np.array(indices, dtype=np.uint32),
    }


def make_arc_ring_segment(
    center_xz: tuple[float, float],
    rx_inner: float,
    rz_inner: float,
    rx_outer: float,
    rz_outer: float,
    y_bottom: float,
    y_top: float,
    angle_start_deg: float,
    angle_end_deg: float,
    segments: int = 24,
) -> dict:
    """Elliptical arc ring block (for stadium bowls, roofs, and running tracks)."""
    cx, cz = center_xz
    parts = []
    a0 = math.radians(angle_start_deg)
    a1 = math.radians(angle_end_deg)
    for i in range(segments):
        t0 = a0 + (a1 - a0) * (i / segments)
        t1 = a0 + (a1 - a0) * ((i + 1) / segments)
        tm = 0.5 * (t0 + t1)

        p0_in = (cx + rx_inner * math.cos(t0), cz + rz_inner * math.sin(t0))
        p1_in = (cx + rx_inner * math.cos(t1), cz + rz_inner * math.sin(t1))
        p0_out = (cx + rx_outer * math.cos(t0), cz + rz_outer * math.sin(t0))
        p1_out = (cx + rx_outer * math.cos(t1), cz + rz_outer * math.sin(t1))

        # Approximate each wedge with a cleanly oriented box matching chord & radial depth
        mid_x = 0.25 * (p0_in[0] + p1_in[0] + p0_out[0] + p1_out[0])
        mid_z = 0.25 * (p0_in[1] + p1_in[1] + p0_out[1] + p1_out[1])
        chord = math.hypot(p1_out[0] - p0_out[0], p1_out[1] - p0_out[1])
        depth = math.hypot(
            0.5 * (p0_out[0] + p1_out[0]) - 0.5 * (p0_in[0] + p1_in[0]),
            0.5 * (p0_out[1] + p1_out[1]) - 0.5 * (p0_in[1] + p1_in[1]),
        )
        tangent_angle = math.degrees(math.atan2(-(p1_out[1] - p0_out[1]), p1_out[0] - p0_out[0]))
        h = max(0.05, y_top - y_bottom)
        parts.append(
            make_box(
                [mid_x, 0.5 * (y_bottom + y_top), mid_z],
                [max(0.1, chord * 0.54), h * 0.5, max(0.1, depth * 0.52)],
                rot_y=tangent_angle,
            )
        )
    return merge_meshes(parts)


def make_mountain_peak(
    center_xz: tuple[float, float],
    base_y: float,
    radius_x: float,
    radius_z: float,
    height: float,
    facets: int = 8,
    seed: int = 0,
    snow_cap_ratio: float = 0.0,
) -> tuple[dict, dict | None]:
    """Builds a jagged faceted mountain peak and optional snow cap mesh."""
    cx, cz = center_xz
    rng_angles = []
    for i in range(facets):
        a = (i / facets) * 2.0 * math.pi
        jitter = 0.82 + 0.34 * abs(math.sin((i + 1) * 2.7 + seed * 1.9))
        rng_angles.append((a, jitter))

    def _build_cone_band(y0: float, y1: float, s0: float, s1: float) -> dict:
        positions, normals, uvs, indices = [], [], [], []
        for i in range(facets):
            a0, j0 = rng_angles[i]
            a1, j1 = rng_angles[(i + 1) % facets]
            v00 = np.array([cx + math.cos(a0) * radius_x * j0 * s0, y0, cz + math.sin(a0) * radius_z * j0 * s0], dtype=np.float32)
            v10 = np.array([cx + math.cos(a1) * radius_x * j1 * s0, y0, cz + math.sin(a1) * radius_z * j1 * s0], dtype=np.float32)
            v11 = np.array([cx + math.cos(a1) * radius_x * j1 * s1, y1, cz + math.sin(a1) * radius_z * j1 * s1], dtype=np.float32)
            v01 = np.array([cx + math.cos(a0) * radius_x * j0 * s1, y1, cz + math.sin(a0) * radius_z * j0 * s1], dtype=np.float32)
            e1 = v10 - v00
            e2 = v01 - v00
            n = np.cross(e2, e1)
            n_norm = float(np.linalg.norm(n))
            n = (n / n_norm) if n_norm > 1e-6 else np.array([0.0, 1.0, 0.0], dtype=np.float32)
            base = len(positions)
            for v, uv in ((v00, [0.0, 0.0]), (v10, [1.0, 0.0]), (v11, [1.0, 1.0]), (v01, [0.0, 1.0])):
                positions.append(v)
                normals.append(n)
                uvs.append(uv)
            indices.extend([base, base + 2, base + 1, base, base + 3, base + 2])
        return {
            "positions": np.array(positions, dtype=np.float32),
            "normals": np.array(normals, dtype=np.float32),
            "uvs": np.array(uvs, dtype=np.float32),
            "indices": np.array(indices, dtype=np.uint32),
        }

    if snow_cap_ratio > 0.05:
        split_y = base_y + height * (1.0 - snow_cap_ratio)
        rock = _build_cone_band(base_y, split_y, 1.0, snow_cap_ratio)
        snow = _build_cone_band(split_y, base_y + height, snow_cap_ratio, 0.02)
        return rock, snow
    else:
        rock = _build_cone_band(base_y, base_y + height, 1.0, 0.03)
        return rock, None


def merge_meshes(meshes: list[dict]) -> dict:
    pos_l, nrm_l, uv_l, idx_l = [], [], [], []
    offset = 0
    for m in meshes:
        if m is None or len(m["positions"]) == 0:
            continue
        pos_l.append(m["positions"])
        nrm_l.append(m["normals"])
        uv_l.append(m["uvs"])
        idx_l.append(m["indices"].astype(np.uint32) + offset)
        offset += len(m["positions"])
    if not pos_l:
        return {
            "positions": np.zeros((0, 3), dtype=np.float32),
            "normals": np.zeros((0, 3), dtype=np.float32),
            "uvs": np.zeros((0, 2), dtype=np.float32),
            "indices": np.zeros((0,), dtype=np.uint32),
        }
    return {
        "positions": np.vstack(pos_l).astype(np.float32),
        "normals": np.vstack(nrm_l).astype(np.float32),
        "uvs": np.vstack(uv_l).astype(np.float32),
        "indices": np.concatenate(idx_l).astype(np.uint32),
    }


# ============================================================================
# SHARED 2.5D FIGHTING ARENA CORE (PITCH, MARKINGS, WALL-BREAK, ZONE B)
# ============================================================================

def add_common_arena_core(
    buckets: dict[str, list[dict]],
    pitch_mat: str = "M_PitchGrass",
    line_mat: str = "M_PitchLines",
    wall_mat: str = "M_DestructibleWall",
    zone_b_mat: str = "M_ZoneB_Concourse",
    wall_height: float = 1.35,
) -> None:
    # Zone A Pitch (-12.5m to +12.5m in X, -8.0m to +8.0m in Z, top at y = 0.0)
    buckets[pitch_mat].append(make_box([0.0, -0.15, 0.0], [12.5, 0.15, 8.0]))

    # Crisp white pitch lines (slightly raised +0.015m to avoid Z-fighting)
    # Center line
    buckets[line_mat].append(make_box([0.0, 0.015, 0.0], [0.08, 0.015, 7.6]))
    # Touchlines (back & front)
    buckets[line_mat].append(make_box([0.0, 0.015, -7.6], [12.1, 0.015, 0.08]))
    buckets[line_mat].append(make_box([0.0, 0.015,  7.6], [12.1, 0.015, 0.08]))
    # Goal lines (left & right)
    buckets[line_mat].append(make_box([-12.1, 0.015, 0.0], [0.08, 0.015, 7.6]))
    buckets[line_mat].append(make_box([ 12.1, 0.015, 0.0], [0.08, 0.015, 7.6]))
    # Center circle (16 segments, radius 2.8m)
    buckets[line_mat].append(
        make_arc_ring_segment((0.0, 0.0), 2.72, 2.72, 2.88, 2.88, 0.002, 0.03, 0.0, 360.0, segments=24)
    )
    # Penalty boxes (left & right)
    for sx in (-1.0, 1.0):
        buckets[line_mat].append(make_box([sx * 9.5, 0.015, 0.0], [0.07, 0.015, 4.2]))
        buckets[line_mat].append(make_box([sx * 10.8, 0.015, -4.2], [1.3, 0.015, 0.07]))
        buckets[line_mat].append(make_box([sx * 10.8, 0.015,  4.2], [1.3, 0.015, 0.07]))

    # Pre-Fractured Destructible Side Walls (6 segments per side at x = +/-12.5m)
    hy = wall_height * 0.5
    for sx in (-1.0, 1.0):
        for z_pos in (-5.0, -3.0, -1.0, 1.0, 3.0, 5.0):
            buckets[wall_mat].append(make_box([sx * 12.55, hy, z_pos], [0.18, hy, 0.92]))

    # Zone B Extended Outer Arena ([-18.5, -12.5] and [+12.5, +18.5])
    buckets[zone_b_mat].append(make_box([-15.5, -0.18, 0.0], [3.0, 0.15, 8.5]))
    buckets[zone_b_mat].append(make_box([ 15.5, -0.18, 0.0], [3.0, 0.15, 8.5]))


# ============================================================================
# GLTF 2.0 BINARY (.GLB) EXPORTER
# ============================================================================

def pbr_mat(
    name: str,
    color: list[float],
    roughness: float = 0.75,
    metallic: float = 0.05,
    emissive: list[float] | None = None,
    alpha_mode: str | None = None,
    double_sided: bool = False,
) -> dict:
    m = {
        "name": name,
        "pbrMetallicRoughness": {
            "baseColorFactor": color,
            "metallicFactor": metallic,
            "roughnessFactor": roughness,
        },
    }
    if emissive is not None:
        m["emissiveFactor"] = emissive
    if alpha_mode is not None:
        m["alphaMode"] = alpha_mode
    if double_sided:
        m["doubleSided"] = True
    return m


def export_stage_glb(
    output_path: str,
    stage_node_name: str,
    materials_spec: list[dict],
    buckets: dict[str, list[dict]],
    extras: dict,
) -> dict:
    blob = bytearray()
    buffer_views = []
    accessors = []
    primitives = []

    def add_bv(data: bytes, target: int) -> int:
        while len(blob) % 4 != 0:
            blob.append(0)
        off = len(blob)
        blob.extend(data)
        buffer_views.append({"buffer": 0, "byteOffset": off, "byteLength": len(data), "target": target})
        return len(buffer_views) - 1

    total_verts = 0
    total_tris = 0
    g_min = np.array([1e9, 1e9, 1e9], dtype=np.float32)
    g_max = np.array([-1e9, -1e9, -1e9], dtype=np.float32)

    used_materials = []
    for mat_def in materials_spec:
        mat_name = mat_def["name"]
        mesh_list = buckets.get(mat_name, [])
        merged = merge_meshes(mesh_list)
        if len(merged["positions"]) == 0:
            continue

        mat_idx = len(used_materials)
        used_materials.append(mat_def)

        pos = merged["positions"]
        nrm = merged["normals"]
        uv = merged["uvs"]
        idx_u32 = merged["indices"]

        total_verts += len(pos)
        total_tris += len(idx_u32) // 3

        p_min = pos.min(axis=0)
        p_max = pos.max(axis=0)
        g_min = np.minimum(g_min, p_min)
        g_max = np.maximum(g_max, p_max)

        bv_p = add_bv(pos.tobytes(), 34962)
        acc_p = len(accessors)
        accessors.append({
            "bufferView": bv_p,
            "componentType": 5126,
            "count": int(len(pos)),
            "type": "VEC3",
            "min": [float(x) for x in p_min],
            "max": [float(x) for x in p_max],
        })

        bv_n = add_bv(nrm.tobytes(), 34962)
        acc_n = len(accessors)
        accessors.append({
            "bufferView": bv_n,
            "componentType": 5126,
            "count": int(len(nrm)),
            "type": "VEC3",
        })

        bv_u = add_bv(uv.tobytes(), 34962)
        acc_u = len(accessors)
        accessors.append({
            "bufferView": bv_u,
            "componentType": 5126,
            "count": int(len(uv)),
            "type": "VEC2",
        })

        if len(pos) < 65535:
            idx_arr = idx_u32.astype(np.uint16)
            comp_type = 5123
        else:
            idx_arr = idx_u32.astype(np.uint32)
            comp_type = 5125

        bv_i = add_bv(idx_arr.tobytes(), 34963)
        acc_i = len(accessors)
        accessors.append({
            "bufferView": bv_i,
            "componentType": comp_type,
            "count": int(len(idx_arr)),
            "type": "SCALAR",
        })

        primitives.append({
            "attributes": {"POSITION": acc_p, "NORMAL": acc_n, "TEXCOORD_0": acc_u},
            "indices": acc_i,
            "material": mat_idx,
            "mode": 4,
        })

    while len(blob) % 4 != 0:
        blob.append(0)

    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "LA COPA ETERNA CONMEBOL 3D Stages Architect (UE 5.4+ glTF 2.0)",
        },
        "scene": 0,
        "scenes": [{"name": f"Scene_{stage_node_name}", "nodes": [0]}],
        "nodes": [{"name": stage_node_name, "mesh": 0}],
        "materials": used_materials,
        "meshes": [{
            "name": f"Mesh_{stage_node_name}",
            "primitives": primitives,
            "extras": extras,
        }],
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(blob)}],
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_length = 12 + 8 + len(json_bytes) + 8 + len(blob)
    with open(output_path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total_length))
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        f.write(struct.pack("<II", len(blob), 0x004E4942))
        f.write(blob)

    dims = (g_max - g_min).tolist()
    return {
        "File": os.path.basename(output_path),
        "FileSizeBytes": os.path.getsize(output_path),
        "Vertices": int(total_verts),
        "Triangles": int(total_tris),
        "MaterialCount": len(used_materials),
        "BoundingBoxMin": [round(float(v), 2) for v in g_min],
        "BoundingBoxMax": [round(float(v), 2) for v in g_max],
        "BoundingDimensionsMeters": {
            "WidthX": round(float(dims[0]), 2),
            "HeightY": round(float(dims[1]), 2),
            "DepthZ": round(float(dims[2]), 2),
        },
    }


# ============================================================================
# 10 DISTINCT CONMEBOL STADIUM BUILDERS
# ============================================================================

def build_maracana_br(out_path: str) -> dict:
    """1. Estádio do Maracanã (Brazil): curved concrete ring, floodlight towers, destructible LED side walls."""
    mats = [
        pbr_mat("M_PitchGrass", [0.10, 0.48, 0.14, 1.0], roughness=0.85),
        pbr_mat("M_PitchLines", [0.96, 0.96, 0.96, 1.0], roughness=0.7),
        pbr_mat("M_ZoneB_Concourse", [0.58, 0.56, 0.52, 1.0], roughness=0.82),
        pbr_mat("M_DestructibleLED", [0.05, 0.88, 0.42, 1.0], roughness=0.25, metallic=0.2, emissive=[0.08, 0.65, 0.25]),
        pbr_mat("M_MaracanaConcrete", [0.76, 0.75, 0.72, 1.0], roughness=0.88),
        pbr_mat("M_MaracanaSeatsYellow", [0.96, 0.80, 0.08, 1.0], roughness=0.6),
        pbr_mat("M_MaracanaSeatsBlue", [0.08, 0.32, 0.78, 1.0], roughness=0.6),
        pbr_mat("M_RoofCanopy", [0.92, 0.93, 0.95, 1.0], roughness=0.45, metallic=0.15),
        pbr_mat("M_FloodlightSteel", [0.30, 0.33, 0.36, 1.0], roughness=0.4, metallic=0.75),
        pbr_mat("M_FloodlightGlow", [1.0, 0.97, 0.88, 1.0], roughness=0.1, emissive=[1.0, 0.95, 0.82]),
    ]
    b = {m["name"]: [] for m in mats}
    add_common_arena_core(b, wall_mat="M_DestructibleLED", wall_height=1.3)

    # Curved concrete ring bowl (-200 deg to +20 deg covers background -Z & flanks)
    for tier in range(4):
        r_in_x = 20.5 + tier * 2.8
        r_in_z = 11.5 + tier * 2.4
        y0 = tier * 2.4
        y1 = y0 + 2.2
        seat_mat = "M_MaracanaSeatsYellow" if tier % 2 == 0 else "M_MaracanaSeatsBlue"
        b[seat_mat].append(make_arc_ring_segment((0.0, 0.0), r_in_x, r_in_z, r_in_x + 2.6, r_in_z + 2.2, y0, y1, 185, 355, segments=28))
        b["M_MaracanaConcrete"].append(make_arc_ring_segment((0.0, 0.0), r_in_x + 2.4, r_in_z + 2.0, r_in_x + 3.2, r_in_z + 2.8, y0 - 0.2, y1 + 0.3, 185, 355, segments=28))

    # Iconic continuous elliptical concrete outer wall & cantilevered roof ring
    b["M_MaracanaConcrete"].append(make_arc_ring_segment((0.0, 0.0), 33.5, 22.5, 35.0, 24.0, 0.0, 14.5, 180, 360, segments=32))
    b["M_RoofCanopy"].append(make_arc_ring_segment((0.0, 0.0), 23.0, 13.5, 35.5, 24.5, 14.2, 15.2, 180, 360, segments=32))

    # Radial tensioned roof ribs
    for i in range(15):
        ang = math.radians(188 + i * 11.8)
        x_mid = 29.0 * math.cos(ang)
        z_mid = 19.0 * math.sin(ang)
        b["M_FloodlightSteel"].append(make_box([x_mid, 15.35, z_mid], [5.8, 0.22, 0.28], rot_y=-math.degrees(ang)))

    # 4 Towering Floodlight Towers with glowing light banks
    for fx, fz, yaw in [(-28.0, -16.0, -35), (-13.0, -24.5, -15), (13.0, -24.5, 15), (28.0, -16.0, 35)]:
        b["M_FloodlightSteel"].append(make_cylinder([fx, 13.5, fz], 0.9, 0.45, 27.0, segments=10))
        b["M_FloodlightSteel"].append(make_box([fx, 26.8, fz], [3.0, 1.7, 0.45], rot_y=yaw))
        b["M_FloodlightGlow"].append(make_box([fx, 26.8, fz + 0.45], [2.7, 1.4, 0.15], rot_y=yaw))

    info = export_stage_glb(out_path, "SM_Stage_Maracana_BR", mats, b, {
        "Country": "Brazil", "City": "Rio de Janeiro",
        "Landmarks": ["Curved Concrete Ring", "Tensioned Roof Canopy", "4 Floodlight Towers", "Destructible LED Side Walls"],
    })
    info["StageID"] = "STAGE_MARACANA_BR"
    info["DisplayName"] = "Estádio do Maracanã (Brasil)"
    info["Landmarks"] = ["Curved concrete elliptical ring & roof canopy", "4 towering floodlight towers with emissive banks", "Pre-fractured destructible LED side walls"]
    return info


def build_bombonera_ar(out_path: str) -> dict:
    """2. La Bombonera (Argentina): steep vertical 3-tier D-shaped stands, Caminito colorful side facade, destructible walls."""
    mats = [
        pbr_mat("M_PitchGrass", [0.11, 0.46, 0.15, 1.0], roughness=0.85),
        pbr_mat("M_PitchLines", [0.96, 0.96, 0.96, 1.0], roughness=0.7),
        pbr_mat("M_ZoneB_CaminitoCobble", [0.42, 0.40, 0.39, 1.0], roughness=0.9),
        pbr_mat("M_DestructibleBocaWall", [0.06, 0.22, 0.62, 1.0], roughness=0.65),
        pbr_mat("M_BocaBlue", [0.05, 0.18, 0.56, 1.0], roughness=0.72),
        pbr_mat("M_BocaGold", [0.98, 0.78, 0.04, 1.0], roughness=0.55),
        pbr_mat("M_Concrete", [0.68, 0.68, 0.66, 1.0], roughness=0.88),
        pbr_mat("M_CaminitoRed", [0.85, 0.16, 0.18, 1.0], roughness=0.68),
        pbr_mat("M_CaminitoCyan", [0.10, 0.68, 0.80, 1.0], roughness=0.68),
        pbr_mat("M_CaminitoMagenta", [0.78, 0.15, 0.48, 1.0], roughness=0.68),
        pbr_mat("M_CaminitoYellow", [0.95, 0.76, 0.12, 1.0], roughness=0.68),
    ]
    b = {m["name"]: [] for m in mats}
    add_common_arena_core(b, wall_mat="M_DestructibleBocaWall", zone_b_mat="M_ZoneB_CaminitoCobble", wall_height=1.45)

    # Steep vertical 3-tier D-shaped stands rising almost vertically behind the pitch (-Z)
    for tier in range(3):
        y_base = 1.2 + tier * 5.8
        z_front = -10.5 - tier * 1.4  # Extremely steep vertical stack!
        # Main straight back wall of the D-shape
        b["M_BocaBlue"].append(make_box([0.0, y_base + 2.2, z_front - 3.0], [18.5, 2.2, 3.0]))
        # Gold balcony fascia stripe
        b["M_BocaGold"].append(make_box([0.0, y_base + 0.5, z_front + 0.15], [18.7, 0.55, 0.25]))
        # Concrete overhang slab
        b["M_Concrete"].append(make_box([0.0, y_base - 0.1, z_front - 2.8], [18.8, 0.35, 3.3]))
        # Steep curved D-wing corners on left & right
        b["M_BocaBlue"].append(make_arc_ring_segment((-18.0, -5.0), 4.5 + tier * 0.8, 5.0 + tier * 0.8, 7.5 + tier * 0.8, 8.0 + tier * 0.8, y_base, y_base + 4.4, 145, 250, segments=10))
        b["M_BocaBlue"].append(make_arc_ring_segment(( 18.0, -5.0), 4.5 + tier * 0.8, 5.0 + tier * 0.8, 7.5 + tier * 0.8, 8.0 + tier * 0.8, y_base, y_base + 4.4, 290, 395, segments=10))

    # Flat vertical VIP Palcos tower on right flank
    b["M_Concrete"].append(make_box([23.5, 11.0, -2.5], [2.4, 11.0, 10.0]))
    for floor in range(4):
        b["M_BocaGold"].append(make_box([21.0, 3.5 + floor * 4.2, -2.5], [0.2, 0.35, 9.6]))

    # Caminito colorful side facade in Zone B (left side, x = -19m to -24m)
    caminito_houses = [
        (-21.0, -6.0, 3.4, 2.4, "M_CaminitoRed"),
        (-21.2, -1.2, 4.2, 2.3, "M_CaminitoYellow"),
        (-20.8,  3.4, 3.6, 2.2, "M_CaminitoCyan"),
        (-21.4,  7.6, 4.0, 2.1, "M_CaminitoMagenta"),
    ]
    for hx, hz, hh, half_z, mat_name in caminito_houses:
        b[mat_name].append(make_box([hx, hh, hz], [2.2, hh, half_z]))
        # Balcony rail & roof trim
        b["M_Concrete"].append(make_box([hx + 2.3, hh * 1.15, hz], [0.35, 0.15, half_z * 0.85]))
        b["M_BocaBlue"].append(make_box([hx, hh * 2.0 + 0.25, hz], [2.4, 0.25, half_z + 0.1]))

    info = export_stage_glb(out_path, "SM_Stage_Bombonera_AR", mats, b, {
        "Country": "Argentina", "City": "Buenos Aires",
        "Landmarks": ["3-Tier Vertical D-Shaped Stands", "VIP Palcos Wall", "Caminito Colorful Facade", "Destructible Boca Walls"],
    })
    info["StageID"] = "STAGE_BOMBONERA_AR"
    info["DisplayName"] = "La Bombonera (Argentina)"
    info["Landmarks"] = ["Steep vertical 3-tier D-shaped stands with gold fascia", "VIP Palcos vertical wall", "Caminito colorful corrugated-style side facade", "Pre-fractured destructible walls"]
    return info


def build_centenario_uy(out_path: str) -> dict:
    """3. Estadio Centenario (Uruguay): Art Deco Torre de los Homenajes spire + heritage arches."""
    mats = [
        pbr_mat("M_PitchGrass", [0.12, 0.47, 0.16, 1.0], roughness=0.85),
        pbr_mat("M_PitchLines", [0.96, 0.96, 0.96, 1.0], roughness=0.7),
        pbr_mat("M_ZoneB_Stone", [0.64, 0.62, 0.56, 1.0], roughness=0.88),
        pbr_mat("M_DestructibleWall", [0.32, 0.65, 0.88, 1.0], roughness=0.65),
        pbr_mat("M_LimestoneArtDeco", [0.84, 0.80, 0.72, 1.0], roughness=0.82),
        pbr_mat("M_CelesteTrim", [0.35, 0.72, 0.94, 1.0], roughness=0.55),
        pbr_mat("M_DarkBronze", [0.24, 0.20, 0.16, 1.0], roughness=0.4, metallic=0.7),
        pbr_mat("M_GoldBeacon", [0.98, 0.84, 0.25, 1.0], roughness=0.25, metallic=0.8, emissive=[0.5, 0.4, 0.1]),
    ]
    b = {m["name"]: [] for m in mats}
    add_common_arena_core(b, wall_mat="M_DestructibleWall", zone_b_mat="M_ZoneB_Stone")

    # Classic open heritage concrete bowl (Tribuna Olímpica)
    for tier in range(3):
        b["M_LimestoneArtDeco"].append(
            make_arc_ring_segment((0.0, 0.0), 20.0 + tier * 3.0, 11.5 + tier * 2.5, 22.8 + tier * 3.0, 14.0 + tier * 2.5, tier * 2.2, (tier + 1) * 2.2, 190, 350, segments=24)
        )

    # Heritage Arches colonnade along upper Tribuna Olímpica (-Z)
    for i in range(9):
        ax = -16.0 + i * 4.0
        az = -20.5
        # Arch pillars
        b["M_LimestoneArtDeco"].append(make_box([ax - 1.5, 8.8, az], [0.45, 2.6, 0.8]))
        b["M_LimestoneArtDeco"].append(make_box([ax + 1.5, 8.8, az], [0.45, 2.6, 0.8]))
        # Stepped Art Deco arch lintel
        b["M_LimestoneArtDeco"].append(make_box([ax, 11.6, az], [1.95, 0.55, 0.85]))
        b["M_CelesteTrim"].append(make_box([ax, 10.9, az + 0.3], [1.1, 0.28, 0.35]))

    # Iconic Art Deco Torre de los Homenajes (centered at x = 0, z = -24.5)
    tz = -24.5
    # Stepped base podium
    b["M_LimestoneArtDeco"].append(make_box([0.0, 4.5, tz], [4.2, 4.5, 3.2]))
    # Main vertical Art Deco shaft (ship-prow silhouette)
    b["M_LimestoneArtDeco"].append(make_box([0.0, 18.0, tz], [2.4, 13.5, 2.2]))
    b["M_LimestoneArtDeco"].append(make_box([0.0, 18.0, tz + 1.6], [1.1, 13.0, 1.0]))
    # 9 horizontal cantilevered observation balconies (symbolizing Uruguay's 9 stripes)
    for deck in range(9):
        dy = 10.5 + deck * 2.1
        b["M_CelesteTrim"].append(make_box([0.0, dy, tz + 1.4], [2.9 - deck * 0.08, 0.25, 1.8]))
    # Crown & flagpole spire
    b["M_LimestoneArtDeco"].append(make_box([0.0, 33.0, tz], [1.5, 2.2, 1.5]))
    b["M_DarkBronze"].append(make_cylinder([0.0, 39.5, tz], 0.22, 0.06, 11.0, segments=10))
    b["M_GoldBeacon"].append(make_cylinder([0.0, 45.2, tz], 0.35, 0.05, 0.9, segments=10))

    info = export_stage_glb(out_path, "SM_Stage_Centenario_UY", mats, b, {
        "Country": "Uruguay", "City": "Montevideo",
        "Landmarks": ["Torre de los Homenajes Art Deco Spire", "9-Deck Ship-Prow Tower", "Heritage Colonnade Arches"],
    })
    info["StageID"] = "STAGE_CENTENARIO_UY"
    info["DisplayName"] = "Estadio Centenario (Uruguay)"
    info["Landmarks"] = ["Art Deco Torre de los Homenajes with 9 balconies & spire", "Heritage concrete colonnade arches", "Pre-fractured celeste side walls"]
    return info


def build_metropolitano_co(out_path: str) -> dict:
    """4. Estadio Metropolitano (Colombia): curved tropical canopy ribs + stadium bowl."""
    mats = [
        pbr_mat("M_PitchGrass", [0.10, 0.52, 0.14, 1.0], roughness=0.84),
        pbr_mat("M_PitchLines", [0.97, 0.97, 0.97, 1.0], roughness=0.7),
        pbr_mat("M_ZoneB_Plaza", [0.76, 0.70, 0.58, 1.0], roughness=0.85),
        pbr_mat("M_DestructibleWall", [0.96, 0.80, 0.06, 1.0], roughness=0.55),
        pbr_mat("M_BowlYellow", [0.96, 0.80, 0.06, 1.0], roughness=0.65),
        pbr_mat("M_BowlBlue", [0.08, 0.24, 0.66, 1.0], roughness=0.65),
        pbr_mat("M_BowlRed", [0.82, 0.12, 0.16, 1.0], roughness=0.65),
        pbr_mat("M_CanopyWhite", [0.95, 0.96, 0.98, 1.0], roughness=0.35, metallic=0.15),
        pbr_mat("M_CanopyRibSteel", [0.85, 0.88, 0.92, 1.0], roughness=0.3, metallic=0.65),
        pbr_mat("M_PalmTrunk", [0.46, 0.34, 0.22, 1.0], roughness=0.9),
        pbr_mat("M_PalmFrond", [0.12, 0.54, 0.18, 1.0], roughness=0.75),
    ]
    b = {m["name"]: [] for m in mats}
    add_common_arena_core(b, wall_mat="M_DestructibleWall", zone_b_mat="M_ZoneB_Plaza")

    # Tricolor Stadium Bowl
    tier_mats = ["M_BowlYellow", "M_BowlBlue", "M_BowlRed"]
    for t_idx, tm in enumerate(tier_mats):
        b[tm].append(
            make_arc_ring_segment((0.0, 0.0), 19.5 + t_idx * 3.2, 11.0 + t_idx * 2.6, 22.5 + t_idx * 3.2, 13.4 + t_idx * 2.6, t_idx * 2.6, (t_idx + 1) * 2.6, 182, 358, segments=26)
        )

    # Curved Tropical Canopy Ribs & Scalloped Sun-Shade Roof
    num_ribs = 13
    for i in range(num_ribs):
        ang_deg = 192.0 + i * (156.0 / (num_ribs - 1))
        ang = math.radians(ang_deg)
        ca, sa = math.cos(ang), math.sin(ang)
        # Rear support mast
        rx, rz = 31.5 * ca, 21.5 * sa
        b["M_CanopyRibSteel"].append(make_cylinder([rx, 8.0, rz], 0.45, 0.35, 16.0, segments=8))
        # Sweeping arched canopy rib in 3 angled segments
        for seg, (r_frac, y_h, pitch) in enumerate([(0.95, 15.8, 18), (0.78, 17.2, 6), (0.62, 16.8, -12)]):
            px = (31.5 * r_frac) * ca
            pz = (21.5 * r_frac) * sa
            b["M_CanopyRibSteel"].append(make_box([px, y_h, pz], [3.2, 0.32, 0.36], rot_y=-ang_deg, rot_z=pitch))
            # White tropical tensioned membrane panel between ribs
            b["M_CanopyWhite"].append(make_box([px, y_h - 0.25, pz], [3.1, 0.14, 2.35], rot_y=-ang_deg, rot_z=pitch))

    # Caribbean Palm Trees flanking Zone B concourse
    for px, pz in [(-17.5, -7.2), (-17.8, 6.8), (17.5, -7.2), (17.8, 6.8)]:
        b["M_PalmTrunk"].append(make_cylinder([px, 3.2, pz], 0.32, 0.20, 6.4, segments=8))
        for f_ang in range(0, 360, 60):
            rad = math.radians(f_ang)
            b["M_PalmFrond"].append(make_box([px + math.cos(rad) * 1.1, 6.5, pz + math.sin(rad) * 1.1], [1.2, 0.08, 0.35], rot_y=-f_ang, rot_z=-18))

    info = export_stage_glb(out_path, "SM_Stage_Metropolitano_CO", mats, b, {
        "Country": "Colombia", "City": "Barranquilla",
        "Landmarks": ["Curved Tropical Canopy Ribs", "Tricolor Stadium Bowl", "Caribbean Palm Concourse"],
    })
    info["StageID"] = "STAGE_METROPOLITANO_CO"
    info["DisplayName"] = "Estadio Metropolitano (Colombia)"
    info["Landmarks"] = ["Sweeping curved tropical canopy ribs & white shade membranes", "Yellow/Blue/Red stadium bowl", "Caribbean palm-lined Zone B concourse"]
    return info


def build_nunoa_cl(out_path: str) -> dict:
    """5. Estadio Nacional de Ñuñoa (Chile): elliptical athletic track + snow-capped Andes mountain backdrop."""
    mats = [
        pbr_mat("M_PitchGrass", [0.11, 0.48, 0.15, 1.0], roughness=0.85),
        pbr_mat("M_PitchLines", [0.97, 0.97, 0.97, 1.0], roughness=0.7),
        pbr_mat("M_AthleticTrack", [0.74, 0.26, 0.18, 1.0], roughness=0.78),
        pbr_mat("M_DestructibleWall", [0.85, 0.12, 0.16, 1.0], roughness=0.6),
        pbr_mat("M_StadiumConcrete", [0.75, 0.75, 0.74, 1.0], roughness=0.86),
        pbr_mat("M_ChileRed", [0.82, 0.10, 0.14, 1.0], roughness=0.65),
        pbr_mat("M_AndesGranite", [0.36, 0.38, 0.44, 1.0], roughness=0.92),
        pbr_mat("M_AndesSnow", [0.94, 0.96, 1.00, 1.0], roughness=0.45),
    ]
    b = {m["name"]: [] for m in mats}
    add_common_arena_core(b, wall_mat="M_DestructibleWall", zone_b_mat="M_AthleticTrack")

    # Prominent Elliptical Athletic Running Track surrounding the pitch
    b["M_AthleticTrack"].append(make_arc_ring_segment((0.0, 0.0), 15.5, 8.2, 20.5, 12.2, -0.25, -0.02, 0, 360, segments=40))
    # White running track lane rings
    for r_off in (0.0, 1.5, 3.0, 4.5):
        b["M_PitchLines"].append(make_arc_ring_segment((0.0, 0.0), 15.8 + r_off, 8.4 + r_off * 0.78, 15.95 + r_off, 8.55 + r_off * 0.78, -0.02, 0.02, 0, 360, segments=40))

    # Low-profile open concrete bowl (preserving sweeping view of the Cordillera)
    for tier in range(3):
        mat_t = "M_ChileRed" if tier == 1 else "M_StadiumConcrete"
        b[mat_t].append(
            make_arc_ring_segment((0.0, 0.0), 21.5 + tier * 2.6, 12.8 + tier * 2.2, 23.9 + tier * 2.6, 14.8 + tier * 2.2, tier * 1.8, (tier + 1) * 1.8, 185, 355, segments=28)
        )

    # Majestic Snow-Capped Andes Mountain Backdrop (Cordillera de los Andes)
    andes_peaks = [
        (-42.0, -48.0, 18.0, 14.0, 34.0, 1, 0.42),
        (-22.0, -52.0, 20.0, 15.0, 42.0, 2, 0.46),
        (  0.0, -56.0, 22.0, 16.0, 48.0, 3, 0.50),
        ( 22.0, -51.0, 19.0, 15.0, 40.0, 4, 0.45),
        ( 43.0, -47.0, 18.0, 14.0, 32.0, 5, 0.40),
    ]
    for px, pz, rx, rz, h, seed, snow_r in andes_peaks:
        rock, snow = make_mountain_peak((px, pz), -2.0, rx, rz, h, facets=9, seed=seed, snow_cap_ratio=snow_r)
        b["M_AndesGranite"].append(rock)
        if snow is not None:
            b["M_AndesSnow"].append(snow)

    info = export_stage_glb(out_path, "SM_Stage_Nunoa_CL", mats, b, {
        "Country": "Chile", "City": "Santiago (Ñuñoa)",
        "Landmarks": ["Elliptical Athletic Track", "Open Concrete Bowl", "Snow-Capped Andes Mountain Backdrop"],
    })
    info["StageID"] = "STAGE_NUNOA_CL"
    info["DisplayName"] = "Estadio Nacional de Ñuñoa (Chile)"
    info["Landmarks"] = ["Elliptical terracotta athletic track with lane lines", "Low-profile open stadium bowl", "Snow-capped Cordillera de los Andes backdrop"]
    return info


def build_defensores_py(out_path: str) -> dict:
    """6. Estadio Defensores del Chaco (Paraguay): fortress concrete bastions + red/white/blue pylons."""
    mats = [
        pbr_mat("M_PitchGrass", [0.10, 0.46, 0.14, 1.0], roughness=0.85),
        pbr_mat("M_PitchLines", [0.96, 0.96, 0.96, 1.0], roughness=0.7),
        pbr_mat("M_ZoneB_Concrete", [0.52, 0.51, 0.49, 1.0], roughness=0.9),
        pbr_mat("M_DestructibleWall", [0.68, 0.12, 0.14, 1.0], roughness=0.75),
        pbr_mat("M_FortressConcrete", [0.58, 0.57, 0.54, 1.0], roughness=0.92),
        pbr_mat("M_PylonRed", [0.85, 0.10, 0.14, 1.0], roughness=0.5),
        pbr_mat("M_PylonWhite", [0.95, 0.95, 0.96, 1.0], roughness=0.5),
        pbr_mat("M_PylonBlue", [0.08, 0.22, 0.68, 1.0], roughness=0.5),
        pbr_mat("M_FloodlightGlow", [1.0, 0.96, 0.85, 1.0], roughness=0.1, emissive=[0.95, 0.90, 0.78]),
    ]
    b = {m["name"]: [] for m in mats}
    add_common_arena_core(b, wall_mat="M_DestructibleWall", zone_b_mat="M_ZoneB_Concrete", wall_height=1.5)

    # Heavy Brutalist Fortress Concrete Stands & Sloped Bastions
    b["M_FortressConcrete"].append(make_box([0.0, 4.5, -15.5], [22.0, 4.5, 5.0]))
    b["M_FortressConcrete"].append(make_box([0.0, 9.2, -19.0], [23.0, 2.2, 2.5]))

    # Crenellated Fortress Concrete Bastion Buttresses along the rear wall
    for bx in (-20.0, -12.0, -4.0, 4.0, 12.0, 20.0):
        # Heavy sloped bastion tower
        b["M_FortressConcrete"].append(make_box([bx, 6.8, -19.8], [2.2, 6.8, 2.4]))
        b["M_FortressConcrete"].append(make_box([bx, 14.2, -20.0], [2.5, 0.9, 2.6]))
        # Bastion corner battlements
        b["M_FortressConcrete"].append(make_box([bx - 1.6, 15.4, -18.8], [0.6, 0.7, 0.6]))
        b["M_FortressConcrete"].append(make_box([bx + 1.6, 15.4, -18.8], [0.6, 0.7, 0.6]))

    # Flanking fortress walls
    for sx in (-1.0, 1.0):
        b["M_FortressConcrete"].append(make_box([sx * 22.5, 5.5, -5.0], [2.5, 5.5, 11.0]))

    # Iconic Tall Red / White / Blue Tricolor Pylons (stacked bands)
    pylon_coords = [(-22.5, -16.5), (-10.5, -22.0), (10.5, -22.0), (22.5, -16.5)]
    for px, pz in pylon_coords:
        b["M_PylonBlue"].append(make_cylinder([px, 4.5, pz], 1.05, 0.90, 9.0, segments=8))
        b["M_PylonWhite"].append(make_cylinder([px, 13.0, pz], 0.90, 0.75, 8.0, segments=8))
        b["M_PylonRed"].append(make_cylinder([px, 21.0, pz], 0.75, 0.55, 8.0, segments=8))
        b["M_FloodlightGlow"].append(make_box([px, 25.4, pz + 0.6], [2.4, 1.1, 0.35]))

    info = export_stage_glb(out_path, "SM_Stage_Defensores_PY", mats, b, {
        "Country": "Paraguay", "City": "Asunción",
        "Landmarks": ["Fortress Concrete Bastions", "Red/White/Blue Tricolor Pylons", "Brutalist Buttress Wall"],
    })
    info["StageID"] = "STAGE_DEFENSORES_PY"
    info["DisplayName"] = "Estadio Defensores del Chaco (Paraguay)"
    info["Landmarks"] = ["Fortress concrete bastions with battlements", "4 towering red/white/blue tricolor pylons", "Pre-fractured concrete side walls"]
    return info


def build_nacional_lima_pe(out_path: str) -> dict:
    """7. Estadio Nacional de Lima (Peru): illuminated vertical architectural fins + tower spire."""
    mats = [
        pbr_mat("M_PitchGrass", [0.10, 0.49, 0.15, 1.0], roughness=0.84),
        pbr_mat("M_PitchLines", [0.97, 0.97, 0.97, 1.0], roughness=0.7),
        pbr_mat("M_ZoneB_Plaza", [0.66, 0.66, 0.68, 1.0], roughness=0.8),
        pbr_mat("M_DestructibleLED", [0.92, 0.10, 0.16, 1.0], roughness=0.25, emissive=[0.65, 0.06, 0.10]),
        pbr_mat("M_BowlConcrete", [0.78, 0.78, 0.80, 1.0], roughness=0.82),
        pbr_mat("M_IlluminatedFinRed", [0.95, 0.12, 0.16, 1.0], roughness=0.3, emissive=[0.78, 0.08, 0.12]),
        pbr_mat("M_IlluminatedFinWhite", [0.98, 0.98, 1.0, 1.0], roughness=0.3, emissive=[0.55, 0.55, 0.62]),
        pbr_mat("M_TowerGlass", [0.16, 0.24, 0.34, 1.0], roughness=0.15, metallic=0.8),
        pbr_mat("M_SpireMetal", [0.85, 0.86, 0.90, 1.0], roughness=0.25, metallic=0.85),
    ]
    b = {m["name"]: [] for m in mats}
    add_common_arena_core(b, wall_mat="M_DestructibleLED", zone_b_mat="M_ZoneB_Plaza")

    # Modern Stadium Bowl
    for tier in range(3):
        b["M_BowlConcrete"].append(
            make_arc_ring_segment((0.0, 0.0), 19.5 + tier * 2.8, 11.2 + tier * 2.4, 22.1 + tier * 2.8, 13.4 + tier * 2.4, tier * 2.5, (tier + 1) * 2.5, 182, 358, segments=26)
        )

    # Signature Illuminated Vertical Architectural Fins wrapping the stadium facade
    num_fins = 29
    for i in range(num_fins):
        ang_deg = 186.0 + i * (168.0 / (num_fins - 1))
        ang = math.radians(ang_deg)
        fx = 31.0 * math.cos(ang)
        fz = 20.5 * math.sin(ang)
        fin_mat = "M_IlluminatedFinRed" if (i % 3 != 1) else "M_IlluminatedFinWhite"
        # Tall vertical curved architectural louver fin
        b[fin_mat].append(make_box([fx, 8.8, fz], [0.35, 8.8, 1.45], rot_y=-ang_deg))
        # Upper cantilevered crown segment
        b[fin_mat].append(make_box([fx * 0.94, 17.6, fz * 0.94], [0.32, 1.6, 2.2], rot_y=-ang_deg, rot_x=16))

    # Iconic North Tower & Broadcast Spire (Torre Norte)
    tx, tz = 0.0, -24.5
    b["M_BowlConcrete"].append(make_box([tx, 14.0, tz], [3.6, 14.0, 2.6]))
    b["M_TowerGlass"].append(make_box([tx, 16.0, tz + 1.4], [2.8, 11.0, 1.4]))
    b["M_IlluminatedFinRed"].append(make_box([tx - 3.7, 15.0, tz + 0.5], [0.35, 13.5, 1.2]))
    b["M_IlluminatedFinRed"].append(make_box([tx + 3.7, 15.0, tz + 0.5], [0.35, 13.5, 1.2]))
    b["M_SpireMetal"].append(make_cylinder([tx, 34.5, tz], 0.55, 0.08, 13.0, segments=12))
    b["M_IlluminatedFinRed"].append(make_cylinder([tx, 41.2, tz], 0.35, 0.10, 1.0, segments=10))

    info = export_stage_glb(out_path, "SM_Stage_NacionalLima_PE", mats, b, {
        "Country": "Peru", "City": "Lima",
        "Landmarks": ["Illuminated Vertical Architectural Fins", "Torre Norte Glass Tower & Spire", "Destructible Red LED Walls"],
    })
    info["StageID"] = "STAGE_NACIONAL_LIMA_PE"
    info["DisplayName"] = "Estadio Nacional de Lima (Perú)"
    info["Landmarks"] = ["29 illuminated red & white vertical architectural fins", "Torre Norte glass tower with metallic spire", "Pre-fractured red LED side walls"]
    return info


def build_atahualpa_ec(out_path: str) -> dict:
    """8. Estadio Olímpico Atahualpa (Ecuador): equatorial center line + towering volcanic cone with ember crater."""
    mats = [
        pbr_mat("M_PitchGrass", [0.11, 0.49, 0.16, 1.0], roughness=0.85),
        pbr_mat("M_PitchLines", [0.96, 0.96, 0.96, 1.0], roughness=0.7),
        pbr_mat("M_EquatorialGold", [1.0, 0.82, 0.06, 1.0], roughness=0.25, metallic=0.7, emissive=[0.55, 0.42, 0.02]),
        pbr_mat("M_ZoneB_Basalt", [0.34, 0.33, 0.35, 1.0], roughness=0.92),
        pbr_mat("M_DestructibleWall", [0.96, 0.78, 0.06, 1.0], roughness=0.6),
        pbr_mat("M_EcuadorBlue", [0.06, 0.24, 0.68, 1.0], roughness=0.65),
        pbr_mat("M_EcuadorRed", [0.80, 0.12, 0.14, 1.0], roughness=0.65),
        pbr_mat("M_VolcanoBasalt", [0.22, 0.20, 0.21, 1.0], roughness=0.95),
        pbr_mat("M_EmberCrater", [1.0, 0.28, 0.04, 1.0], roughness=0.2, emissive=[1.0, 0.32, 0.05]),
    ]
    b = {m["name"]: [] for m in mats}
    add_common_arena_core(b, wall_mat="M_DestructibleWall", zone_b_mat="M_ZoneB_Basalt")

    # Prominent Equatorial Center Line (0°00'00" Mitad del Mundo golden meridian strip + marker plinth)
    b["M_EquatorialGold"].append(make_box([0.0, 0.028, 0.0], [0.24, 0.028, 8.2]))
    b["M_EquatorialGold"].append(make_arc_ring_segment((0.0, 0.0), 2.55, 2.55, 3.05, 3.05, 0.005, 0.045, 0, 360, segments=28))
    # Equatorial monument obelisk behind center line
    b["M_ZoneB_Basalt"].append(make_box([0.0, 2.4, -10.5], [1.1, 2.4, 1.1]))
    b["M_EquatorialGold"].append(make_cylinder([0.0, 5.4, -10.5], 0.85, 0.85, 0.35, segments=16))

    # Open Andean Stadium Bowl (tricolor)
    for tier, tm in enumerate(["M_DestructibleWall", "M_EcuadorBlue", "M_EcuadorRed"]):
        b[tm].append(
            make_arc_ring_segment((0.0, 0.0), 19.5 + tier * 2.8, 11.8 + tier * 2.2, 22.1 + tier * 2.8, 13.8 + tier * 2.2, tier * 2.0, (tier + 1) * 2.0, 185, 355, segments=24)
        )

    # Towering Volcanic Cone with Glowing Ember Crater (centered dramatically in -Z backdrop)
    vx, vz = 0.0, -52.0
    b["M_VolcanoBasalt"].append(make_cylinder([vx, 21.0, vz], 28.0, 7.2, 46.0, segments=20, cap_top=False))
    # Flanking volcanic ridges
    r_left, _ = make_mountain_peak((-32.0, -50.0), -2.0, 18.0, 14.0, 26.0, facets=8, seed=11)
    r_right, _ = make_mountain_peak(( 32.0, -50.0), -2.0, 18.0, 14.0, 28.0, facets=8, seed=17)
    b["M_VolcanoBasalt"].extend([r_left, r_right])
    # Glowing Ember Crater Rim & Lava Pool
    b["M_EmberCrater"].append(make_arc_ring_segment((vx, vz), 5.6, 5.6, 7.6, 7.6, 43.2, 44.6, 0, 360, segments=20))
    b["M_EmberCrater"].append(make_cylinder([vx, 43.4, vz], 5.7, 5.7, 0.6, segments=18))
    # Lava fissures radiating down the volcanic cone
    for f_ang in (-35, 0, 35):
        rad = math.radians(f_ang)
        b["M_EmberCrater"].append(make_box([vx + math.sin(rad) * 11.5, 34.0, vz + math.cos(rad) * 11.5], [0.45, 9.5, 0.45], rot_x=-26, rot_y=f_ang))

    info = export_stage_glb(out_path, "SM_Stage_Atahualpa_EC", mats, b, {
        "Country": "Ecuador", "City": "Quito",
        "Landmarks": ["Equatorial Center Line (0°00'00\")", "Towering Volcanic Cone", "Glowing Ember Crater & Lava Fissures"],
    })
    info["StageID"] = "STAGE_ATAHUALPA_EC"
    info["DisplayName"] = "Estadio Olímpico Atahualpa (Ecuador)"
    info["Landmarks"] = ["Golden equatorial center line & Mitad del Mundo marker", "Towering volcanic cone backdrop", "Glowing emissive ember crater & lava fissures"]
    return info


def build_avila_ve(out_path: str) -> dict:
    """9. Estadio del Ávila (Venezuela): modern curved roof + Cerro El Ávila mountain ridge + VIP helipad."""
    mats = [
        pbr_mat("M_PitchGrass", [0.10, 0.50, 0.16, 1.0], roughness=0.84),
        pbr_mat("M_PitchLines", [0.97, 0.97, 0.97, 1.0], roughness=0.7),
        pbr_mat("M_ZoneB_Deck", [0.45, 0.46, 0.48, 1.0], roughness=0.75),
        pbr_mat("M_DestructibleWall", [0.52, 0.08, 0.18, 1.0], roughness=0.45, metallic=0.2),
        pbr_mat("M_Vinotinto", [0.48, 0.06, 0.16, 1.0], roughness=0.55),
        pbr_mat("M_ModernRoofSilver", [0.84, 0.87, 0.92, 1.0], roughness=0.28, metallic=0.7),
        pbr_mat("M_AvilaMountainGreen", [0.16, 0.34, 0.18, 1.0], roughness=0.92),
        pbr_mat("M_AvilaRidgeSlate", [0.28, 0.32, 0.30, 1.0], roughness=0.94),
        pbr_mat("M_HelipadDeck", [0.24, 0.26, 0.30, 1.0], roughness=0.7),
        pbr_mat("M_HelipadGlow", [1.0, 0.85, 0.12, 1.0], roughness=0.2, emissive=[0.95, 0.78, 0.08]),
    ]
    b = {m["name"]: [] for m in mats}
    add_common_arena_core(b, wall_mat="M_DestructibleWall", zone_b_mat="M_ZoneB_Deck")

    # Vinotinto Modern Stadium Bowl
    for tier in range(3):
        tm = "M_Vinotinto" if tier != 1 else "M_ModernRoofSilver"
        b[tm].append(
            make_arc_ring_segment((0.0, 0.0), 19.5 + tier * 2.8, 11.2 + tier * 2.3, 22.1 + tier * 2.8, 13.3 + tier * 2.3, tier * 2.3, (tier + 1) * 2.3, 185, 355, segments=26)
        )

    # Modern Cantilevered Curved Roof Shell (sweeping wave profile)
    b["M_ModernRoofSilver"].append(make_arc_ring_segment((0.0, 0.0), 21.0, 12.2, 32.5, 21.0, 11.8, 12.8, 195, 345, segments=28))
    b["M_Vinotinto"].append(make_arc_ring_segment((0.0, 0.0), 20.6, 11.9, 21.6, 12.6, 11.5, 12.9, 195, 345, segments=28))
    # Roof structural arch struts
    for sx in (-18.0, -9.0, 0.0, 9.0, 18.0):
        b["M_ModernRoofSilver"].append(make_cylinder([sx, 6.2, -20.5], 0.55, 0.40, 12.4, segments=8))

    # Elevated VIP Helipad cantilevered on the right flank (x = +21.5, y = 10.5, z = -6.0)
    hx, hy, hz = 22.5, 10.2, -6.5
    b["M_ModernRoofSilver"].append(make_cylinder([hx, hy * 0.5, hz], 1.4, 1.1, hy, segments=12))
    b["M_HelipadDeck"].append(make_cylinder([hx, hy + 0.3, hz], 5.2, 5.2, 0.6, segments=20))
    # Glowing Helipad circle & "H" marking
    b["M_HelipadGlow"].append(make_arc_ring_segment((hx, hz), 4.1, 4.1, 4.5, 4.5, hy + 0.61, hy + 0.68, 0, 360, segments=24))
    b["M_HelipadGlow"].append(make_box([hx - 1.3, hy + 0.65, hz], [0.28, 0.05, 2.0]))
    b["M_HelipadGlow"].append(make_box([hx + 1.3, hy + 0.65, hz], [0.28, 0.05, 2.0]))
    b["M_HelipadGlow"].append(make_box([hx, hy + 0.65, hz], [1.3, 0.05, 0.28]))

    # Cerro El Ávila Mountain Ridge backdrop (broad verdant coastal massif)
    avila_peaks = [
        (-40.0, -46.0, 22.0, 14.0, 26.0, 21),
        (-16.0, -50.0, 24.0, 15.0, 33.0, 22),
        ( 10.0, -52.0, 26.0, 16.0, 36.0, 23),
        ( 36.0, -47.0, 22.0, 14.0, 28.0, 24),
    ]
    for idx, (px, pz, rx, rz, h, seed) in enumerate(avila_peaks):
        rock, _ = make_mountain_peak((px, pz), -2.0, rx, rz, h, facets=9, seed=seed)
        b["M_AvilaMountainGreen" if idx % 2 == 0 else "M_AvilaRidgeSlate"].append(rock)

    info = export_stage_glb(out_path, "SM_Stage_Avila_VE", mats, b, {
        "Country": "Venezuela", "City": "Caracas",
        "Landmarks": ["Modern Curved Roof", "Cerro El Ávila Mountain Ridge", "Cantilevered VIP Helipad"],
    })
    info["StageID"] = "STAGE_AVILA_VE"
    info["DisplayName"] = "Estadio del Ávila (Venezuela)"
    info["Landmarks"] = ["Modern cantilevered silver & vinotinto curved roof", "Cerro El Ávila lush coastal mountain ridge", "Elevated VIP helipad with glowing H & perimeter ring"]
    return info


def build_hernando_siles_bo(out_path: str) -> dict:
    """10. Estadio Hernando Siles (Bolivia - 3600m): above-the-clouds floating planes + carved Andean stone monolith + Illimani peaks."""
    mats = [
        pbr_mat("M_PitchGrass", [0.12, 0.50, 0.16, 1.0], roughness=0.84),
        pbr_mat("M_PitchLines", [0.97, 0.97, 0.97, 1.0], roughness=0.7),
        pbr_mat("M_ZoneB_AndeanStone", [0.62, 0.54, 0.44, 1.0], roughness=0.92),
        pbr_mat("M_DestructibleStoneWall", [0.58, 0.48, 0.36, 1.0], roughness=0.9),
        pbr_mat("M_BoliviaGreen", [0.08, 0.52, 0.22, 1.0], roughness=0.68),
        pbr_mat("M_BoliviaRed", [0.80, 0.14, 0.14, 1.0], roughness=0.68),
        pbr_mat("M_BoliviaYellow", [0.95, 0.80, 0.10, 1.0], roughness=0.68),
        pbr_mat("M_MonolithSandstone", [0.68, 0.56, 0.40, 1.0], roughness=0.9),
        pbr_mat("M_IllimaniRock", [0.34, 0.36, 0.42, 1.0], roughness=0.92),
        pbr_mat("M_IllimaniSnow", [0.96, 0.98, 1.00, 1.0], roughness=0.4),
        pbr_mat("M_CloudDeck", [0.96, 0.97, 1.00, 0.72], roughness=0.95, alpha_mode="BLEND", double_sided=True),
    ]
    b = {m["name"]: [] for m in mats}
    add_common_arena_core(b, wall_mat="M_DestructibleStoneWall", zone_b_mat="M_ZoneB_AndeanStone")

    # Bolivian High-Altitude Stadium Bowl (Red / Yellow / Green)
    for tier, tm in enumerate(["M_BoliviaGreen", "M_BoliviaYellow", "M_BoliviaRed"]):
        b[tm].append(
            make_arc_ring_segment((0.0, 0.0), 19.5 + tier * 2.7, 11.5 + tier * 2.2, 22.0 + tier * 2.7, 13.5 + tier * 2.2, tier * 2.1, (tier + 1) * 2.1, 185, 355, segments=24)
        )

    # Carved Andean Stone Monolith & Puerta del Sol Gateway (centered behind upper concourse)
    mx, mz = 0.0, -21.5
    # Stepped Tiwanaku pedestal
    b["M_MonolithSandstone"].append(make_box([mx, 1.2, mz], [5.8, 1.2, 2.2]))
    b["M_MonolithSandstone"].append(make_box([mx, 3.0, mz], [4.6, 0.9, 1.8]))
    # Twin carved pillars & massive sun-gate lintel
    b["M_MonolithSandstone"].append(make_box([mx - 2.6, 7.8, mz], [1.1, 4.0, 1.2]))
    b["M_MonolithSandstone"].append(make_box([mx + 2.6, 7.8, mz], [1.1, 4.0, 1.2]))
    b["M_MonolithSandstone"].append(make_box([mx, 12.6, mz], [4.4, 1.4, 1.35]))
    # Carved central solar relief & stepped crown
    b["M_BoliviaYellow"].append(make_box([mx, 12.6, mz + 0.72], [1.2, 0.95, 0.15]))
    b["M_MonolithSandstone"].append(make_box([mx, 14.6, mz], [2.4, 0.75, 1.1]))

    # Iconic Triple-Peaked Nevado Illimani Backdrop
    illimani_peaks = [
        (-28.0, -52.0, 20.0, 15.0, 40.0, 31, 0.52),
        (  0.0, -56.0, 24.0, 17.0, 52.0, 32, 0.58),  # Central highest peak
        ( 28.0, -51.0, 20.0, 15.0, 42.0, 33, 0.52),
    ]
    for px, pz, rx, rz, h, seed, snow_r in illimani_peaks:
        rock, snow = make_mountain_peak((px, pz), -3.0, rx, rz, h, facets=9, seed=seed, snow_cap_ratio=snow_r)
        b["M_IllimaniRock"].append(rock)
        if snow is not None:
            b["M_IllimaniSnow"].append(snow)

    # 3,600m Above-the-Clouds Floating Cloud Planes (layered volumetric slabs around the stadium & below peaks)
    cloud_planes = [
        (-28.0, -2.5, -26.0, 14.0, 0.45, 7.0),
        ( 28.0, -2.2, -26.0, 14.0, 0.45, 7.0),
        (  0.0, -3.2, -34.0, 32.0, 0.55, 9.0),
        (-22.0, 11.5, -36.0, 11.0, 0.40, 5.5),
        ( 24.0, 13.0, -38.0, 12.0, 0.40, 5.5),
        (  0.0, 17.5, -42.0, 18.0, 0.45, 6.0),
    ]
    for cx, cy, cz, hx, hy, hz in cloud_planes:
        b["M_CloudDeck"].append(make_box([cx, cy, cz], [hx, hy, hz]))

    info = export_stage_glb(out_path, "SM_Stage_HernandoSiles_BO", mats, b, {
        "Country": "Bolivia", "City": "La Paz (3,600m)",
        "Landmarks": ["3600m Floating Cloud Planes", "Carved Andean Stone Monolith", "Nevado Illimani Triple Peaks"],
    })
    info["StageID"] = "STAGE_HERNANDO_SILES_BO"
    info["DisplayName"] = "Estadio Hernando Siles (Bolivia - 3,600m)"
    info["Landmarks"] = ["3,600m above-the-clouds semi-transparent floating cloud planes", "Carved Tiwanaku-inspired Andean stone monolith", "Triple-peaked snow-capped Illimani backdrop"]
    return info


# ============================================================================
# PROGRAMMATIC GLB VALIDATION
# ============================================================================

def validate_glb(filepath: str) -> dict:
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Missing GLB: {filepath}")
    size = os.path.getsize(filepath)
    with open(filepath, "rb") as f:
        header = f.read(12)
        if len(header) != 12:
            raise ValueError(f"Truncated GLB header in {filepath}")
        magic_bytes = header[:4]
        magic, version, total_len = struct.unpack("<III", header)
        if magic_bytes != b"glTF" or version != 2 or total_len != size:
            raise ValueError(
                f"Invalid GLB header in {filepath}: magic={magic_bytes!r}, version={version}, "
                f"declared_len={total_len}, actual_size={size}"
            )
        json_len, json_type = struct.unpack("<II", f.read(8))
        if json_type != 0x4E4F534A:
            raise ValueError(f"First chunk is not JSON in {filepath}")
        json_raw = f.read(json_len).decode("utf-8")
        gltf_obj = json.loads(json_raw)
        if gltf_obj.get("asset", {}).get("version") != "2.0":
            raise ValueError(f"Invalid glTF asset.version in {filepath}")

        bin_len, bin_type = struct.unpack("<II", f.read(8))
        if bin_type != 0x004E4942:
            raise ValueError(f"Second chunk is not BIN in {filepath}")
        actual_bin = len(f.read(bin_len))
        if actual_bin != bin_len:
            raise ValueError(f"Truncated BIN chunk in {filepath}")

    return {
        "ValidGLTF2Binary": True,
        "HeaderMagic": "glTF",
        "Version": version,
        "JSONChunkBytes": json_len,
        "BINChunkBytes": bin_len,
        "Primitives": len(gltf_obj["meshes"][0]["primitives"]),
    }


def main() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stages_dir = os.path.join(repo_root, "Assets", "Models3D", "Stages")
    os.makedirs(stages_dir, exist_ok=True)

    stage_builders = [
        ("SM_Stage_Maracana_BR.glb",      build_maracana_br),
        ("SM_Stage_Bombonera_AR.glb",     build_bombonera_ar),
        ("SM_Stage_Centenario_UY.glb",    build_centenario_uy),
        ("SM_Stage_Metropolitano_CO.glb", build_metropolitano_co),
        ("SM_Stage_Nunoa_CL.glb",         build_nunoa_cl),
        ("SM_Stage_Defensores_PY.glb",    build_defensores_py),
        ("SM_Stage_NacionalLima_PE.glb",  build_nacional_lima_pe),
        ("SM_Stage_Atahualpa_EC.glb",     build_atahualpa_ec),
        ("SM_Stage_Avila_VE.glb",         build_avila_ve),
        ("SM_Stage_HernandoSiles_BO.glb", build_hernando_siles_bo),
    ]

    stage_reports = []
    for filename, builder_fn in stage_builders:
        glb_path = os.path.join(stages_dir, filename)
        info = builder_fn(glb_path)
        validation = validate_glb(glb_path)
        info["Validation"] = validation
        stage_reports.append(info)
        dims = info["BoundingDimensionsMeters"]
        print(
            f"[OK] {filename:32s} | {info['FileSizeBytes']:7d} B | "
            f"Verts: {info['Vertices']:5d} | Tris: {info['Triangles']:5d} | "
            f"Dims(m): {dims['WidthX']}x{dims['HeightY']}x{dims['DepthZ']} | "
            f"glTF 2.0 VALID"
        )

    manifest_path = os.path.join(stages_dir, "Stages3D_TechnicalManifest.json")
    manifest = {
        "SchemaVersion": "1.0.0-CONMEBOL-STAGES-GLTF2",
        "Project": "LA COPA ETERNA: SANGRE Y POTRERO",
        "TargetEngine": "Unreal Engine 5.4+ (2.5D Fighting Arena & Chaos Wall-Break Pipeline)",
        "CoordinateConvention": {
            "UpAxis": "+Y",
            "FightingPlaneX": {"ZoneA_Meters": [-12.5, 12.5], "WallBreakX": [-12.55, 12.55], "ZoneB_Meters": [-18.5, 18.5]},
            "CameraViewDirection": "+Z looking toward -Z (unobstructed foreground)",
        },
        "TotalStagesGenerated": len(stage_reports),
        "AllStagesValidated": all(s["Validation"]["ValidGLTF2Binary"] for s in stage_reports),
        "Stages": stage_reports,
    }
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    print(f"\n[OK] Manifest written to: {manifest_path}")
    print(f"[OK] All {len(stage_reports)} CONMEBOL 3D Stadium .glb files generated and validated.")


if __name__ == "__main__":
    main()
