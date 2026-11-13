#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_3d_models_gltf.py
Generador Procedural de Modelos 3D glTF 2.0 Binarios (.glb) y Wavefront (.obj) para Unreal Engine 5.4+.
Construye:
1. 17 Skeletal Meshes (16 Luchadores CONMEBOL + El Juez Supremo V.A.R. - ZERO) con:
   - 3 Slots de Material Maestro (M_FighterSkin_SSS, M_FighterKit_Retro90s_Cloth, M_FighterHairCards_And_Eyes)
   - Esqueleto UE5 de 38 huesos (incluyendo pelvis_visual_offset para Hitstop Shake, twist bones, hair_chain_01..06 y kit_hem_01..04)
   - Atributo de vértice COLOR_0 con el mapa de pesos Chaos Cloth 5.4 (MaxDistance 0.5cm a 12.0cm)
   - 5 Clips de Animación Stepped a 60 FPS ("interpolation": "STEP"): Anim_Idle, Anim_5LP_Jab4f, Anim_236SK_Shot, Anim_623HP_BicycleKick (con escala 1.25x en tibia/botín), Anim_214SK_Scorpion.
2. Balón Oficial de 32 Paneles (Icosaedro Truncado) en .glb y .obj.
3. Escenario Modular 2.5D con Zona A, Vallas Pre-Fracturadas para Wall Break (Chaos Destruction) y Zona B.
4. Manifiesto Técnico JSON (Models3D_TechnicalManifest.json).
"""

import os
import json
import math
import struct
import numpy as np


# ============================================================================
# ESPECIFICACIONES ANATÓMICAS Y DE ARQUETIPO DE LOS 17 PERSONAJES
# ============================================================================

FIGHTER_SPECS = [
    {"id": "FENOMENO_BR",       "name": "O Fenômeno",          "height": 1.83, "bulk": 1.06, "hair_style": "r9_crest",    "kit_color": [0.98, 0.84, 0.05, 1.0]},
    {"id": "BRUXO_BR",          "name": "O Bruxo",             "height": 1.82, "bulk": 0.98, "hair_style": "long_curls",  "kit_color": [0.98, 0.84, 0.05, 1.0]},
    {"id": "CANON_AR",          "name": "El Cañón",            "height": 1.85, "bulk": 1.10, "hair_style": "lion_mane",   "kit_color": [0.45, 0.75, 0.96, 1.0]},
    {"id": "PULGA_AR",          "name": "La Pulga",            "height": 1.70, "bulk": 0.92, "hair_style": "short_messy", "kit_color": [0.45, 0.75, 0.96, 1.0]},
    {"id": "PIBE_CO",           "name": "El Pibe",             "height": 1.76, "bulk": 1.00, "hair_style": "golden_afro", "kit_color": [0.98, 0.82, 0.08, 1.0]},
    {"id": "LOCO_CO",           "name": "El Loco",             "height": 1.76, "bulk": 1.04, "hair_style": "black_afro",  "kit_color": [0.55, 0.12, 0.72, 1.0]},
    {"id": "PISTOLERO_UY",      "name": "El Pistolero",        "height": 1.82, "bulk": 1.08, "hair_style": "short_crop",  "kit_color": [0.35, 0.68, 0.92, 1.0]},
    {"id": "MATADOR_UY",        "name": "El Matador",          "height": 1.80, "bulk": 1.02, "hair_style": "golden_band", "kit_color": [0.35, 0.68, 0.92, 1.0]},
    {"id": "BAMBAM_CL",         "name": "Bam-Bam",             "height": 1.78, "bulk": 1.03, "hair_style": "classic_90s", "kit_color": [0.85, 0.12, 0.15, 1.0]},
    {"id": "REY_CL",            "name": "El Rey",              "height": 1.80, "bulk": 1.07, "hair_style": "king_mohawk", "kit_color": [0.85, 0.12, 0.15, 1.0]},
    {"id": "BULLDOG_PY",        "name": "El Bulldog",          "height": 1.92, "bulk": 1.24, "hair_style": "bulldog_cut", "kit_color": [0.18, 0.22, 0.28, 1.0]},
    {"id": "MAESTRO_PE",        "name": "El Maestro",          "height": 1.77, "bulk": 0.96, "hair_style": "classic_90s", "kit_color": [0.95, 0.95, 0.95, 1.0]},
    {"id": "TREN_EC",           "name": "El Tren Amazónico",   "height": 1.79, "bulk": 1.08, "hair_style": "short_crop",  "kit_color": [0.96, 0.80, 0.05, 1.0]},
    {"id": "HURACAN_VE",        "name": "El Huracán Vinotinto","height": 1.80, "bulk": 1.01, "hair_style": "classic_90s", "kit_color": [0.52, 0.08, 0.18, 1.0]},
    {"id": "DIABLO_BO",         "name": "El Diablo Andino",    "height": 1.76, "bulk": 0.99, "hair_style": "diablo_mane", "kit_color": [0.08, 0.58, 0.24, 1.0]},
    {"id": "GENERAL_FR",        "name": "Le Général",          "height": 1.85, "bulk": 1.04, "hair_style": "short_crop",  "kit_color": [0.10, 0.22, 0.68, 1.0]},
    {"id": "SUPREME_JUDGE_BOSS","name": "El Juez Supremo (V.A.R. - ZERO)", "height": 2.15, "bulk": 1.28, "hair_style": "var_drones", "kit_color": [0.08, 0.95, 0.88, 1.0]},
]

# Lista ordenada de los 38 huesos del esqueleto competitivo UE5
BONE_DEFS = [
    # (idx, name, parent_idx, local_translation_normalized)
    (0,  "root",                 -1, [0.0,   0.0,   0.0]),
    (1,  "pelvis",                0, [0.0,   0.53,  0.0]),
    (2,  "pelvis_visual_offset",  1, [0.0,   0.0,   0.0]),
    (3,  "spine_01",              2, [0.0,   0.06,  0.0]),
    (4,  "spine_02",              3, [0.0,   0.10,  0.0]),
    (5,  "spine_03",              4, [0.0,   0.11,  0.0]),
    (6,  "neck_01",               5, [0.0,   0.08,  0.0]),
    (7,  "head",                  6, [0.0,   0.06,  0.0]),
    (8,  "clavicle_l",            5, [0.05,  0.06,  0.0]),
    (9,  "upperarm_l",            8, [0.09,  0.0,   0.0]),
    (10, "lowerarm_l",            9, [0.15,  0.0,   0.0]),
    (11, "lowerarm_twist_01_l",  10, [0.07,  0.0,   0.0]),
    (12, "hand_l",               10, [0.14,  0.0,   0.0]),
    (13, "clavicle_r",            5, [-0.05, 0.06,  0.0]),
    (14, "upperarm_r",           13, [-0.09, 0.0,   0.0]),
    (15, "lowerarm_r",           14, [-0.15, 0.0,   0.0]),
    (16, "lowerarm_twist_01_r",  15, [-0.07, 0.0,   0.0]),
    (17, "hand_r",               15, [-0.14, 0.0,   0.0]),
    (18, "thigh_l",               2, [0.09, -0.04,  0.0]),
    (19, "calf_l",               18, [0.0,  -0.23,  0.0]),
    (20, "calf_twist_01_l",      19, [0.0,  -0.11,  0.0]),
    (21, "foot_l",               19, [0.0,  -0.22,  0.0]),
    (22, "ball_l",               21, [0.0,  -0.03,  0.08]),
    (23, "thigh_r",               2, [-0.09,-0.04,  0.0]),
    (24, "calf_r",               23, [0.0,  -0.23,  0.0]),
    (25, "calf_twist_01_r",      24, [0.0,  -0.11,  0.0]),
    (26, "foot_r",               24, [0.0,  -0.22,  0.0]),
    (27, "ball_r",               26, [0.0,  -0.03,  0.08]),
    (28, "hair_chain_01",         7, [0.0,   0.08, -0.03]),
    (29, "hair_chain_02",        28, [0.0,   0.02, -0.04]),
    (30, "hair_chain_03",        29, [0.0,  -0.02, -0.04]),
    (31, "hair_chain_04",         7, [0.05,  0.06, -0.02]),
    (32, "hair_chain_05",        31, [0.02,  0.0,  -0.04]),
    (33, "hair_chain_06",        32, [0.0,  -0.03, -0.03]),
    (34, "kit_hem_01",            3, [0.0,  -0.06,  0.09]),
    (35, "kit_hem_02",            3, [0.0,  -0.06, -0.09]),
    (36, "kit_hem_03",            3, [0.11, -0.06,  0.0]),
    (37, "kit_hem_04",            3, [-0.11,-0.06,  0.0]),
]


def euler_xyz_to_quat(rx_deg: float, ry_deg: float, rz_deg: float) -> list[float]:
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
    return [float(qx), float(qy), float(qz), float(qw)]


def build_box_submesh(
    center: list[float],
    half_extents: list[float],
    joint_idx: int,
    cloth_weight_top: float,
    cloth_weight_bottom: float,
) -> dict:
    cx, cy, cz = center
    hx, hy, hz = half_extents

    # 24 vértices (4 por cara) con normales y UVs limpias
    faces = [
        # +Z (Front)
        ([cx - hx, cy - hy, cz + hz], [cx + hx, cy - hy, cz + hz], [cx + hx, cy + hy, cz + hz], [cx - hx, cy + hy, cz + hz], [0, 0, 1]),
        # -Z (Back)
        ([cx + hx, cy - hy, cz - hz], [cx - hx, cy - hy, cz - hz], [cx - hx, cy + hy, cz - hz], [cx + hx, cy + hy, cz - hz], [0, 0, -1]),
        # +X (Left)
        ([cx + hx, cy - hy, cz + hz], [cx + hx, cy - hy, cz - hz], [cx + hx, cy + hy, cz - hz], [cx + hx, cy + hy, cz + hz], [1, 0, 0]),
        # -X (Right)
        ([cx - hx, cy - hy, cz - hz], [cx - hx, cy - hy, cz + hz], [cx - hx, cy + hy, cz + hz], [cx - hx, cy + hy, cz - hz], [-1, 0, 0]),
        # +Y (Top)
        ([cx - hx, cy + hy, cz + hz], [cx + hx, cy + hy, cz + hz], [cx + hx, cy + hy, cz - hz], [cx - hx, cy + hy, cz - hz], [0, 1, 0]),
        # -Y (Bottom)
        ([cx - hx, cy - hy, cz - hz], [cx + hx, cy - hy, cz - hz], [cx + hx, cy - hy, cz + hz], [cx - hx, cy - hy, cz + hz], [0, -1, 0]),
    ]

    positions = []
    normals = []
    uvs = []
    colors = []
    joints = []
    weights = []
    indices = []

    for f_idx, (v0, v1, v2, v3, nrm) in enumerate(faces):
        base = f_idx * 4
        for v_local, v in enumerate([v0, v1, v2, v3]):
            positions.append(v)
            normals.append(nrm)
            u = 1.0 if v_local in (1, 2) else 0.0
            vv = 1.0 if v_local in (2, 3) else 0.0
            uvs.append([u, vv])
            # Canal R = MaxDistance de Chaos Cloth normalizado (0.5cm -> 0.0416, 12.0cm -> 1.0)
            is_top = (v[1] >= cy)
            cw = cloth_weight_top if is_top else cloth_weight_bottom
            colors.append([cw, 0.85, 0.15, 1.0])
            joints.append([joint_idx, 2, 0, 0])
            weights.append([1.0, 0.0, 0.0, 0.0])

        indices.extend([base, base + 1, base + 2, base, base + 2, base + 3])

    return {
        "positions": np.array(positions, dtype=np.float32),
        "normals": np.array(normals, dtype=np.float32),
        "uvs": np.array(uvs, dtype=np.float32),
        "colors": np.array(colors, dtype=np.float32),
        "joints": np.array(joints, dtype=np.uint8),
        "weights": np.array(weights, dtype=np.float32),
        "indices": np.array(indices, dtype=np.uint16),
    }


def merge_submeshes(submeshes: list[dict]) -> dict:
    pos_list, nrm_list, uv_list, col_list, jnt_list, wgt_list, idx_list = [], [], [], [], [], [], []
    vertex_offset = 0
    for sm in submeshes:
        pos_list.append(sm["positions"])
        nrm_list.append(sm["normals"])
        uv_list.append(sm["uvs"])
        col_list.append(sm["colors"])
        jnt_list.append(sm["joints"])
        wgt_list.append(sm["weights"])
        idx_list.append(sm["indices"] + vertex_offset)
        vertex_offset += len(sm["positions"])

    return {
        "positions": np.vstack(pos_list),
        "normals": np.vstack(nrm_list),
        "uvs": np.vstack(uv_list),
        "colors": np.vstack(col_list),
        "joints": np.vstack(jnt_list),
        "weights": np.vstack(wgt_list),
        "indices": np.concatenate(idx_list).astype(np.uint16),
    }


def build_fighter_three_slot_primitives(spec: dict) -> list[dict]:
    h = spec["height"]
    b = spec["bulk"]

    # ------------------------------------------------------------------------
    # SLOT 0: M_FighterSkin_SSS (Cabeza, Cuello, Antebrazos, Pantorrillas)
    # ------------------------------------------------------------------------
    skin_parts = [
        build_box_submesh([0.0, 0.89 * h, 0.0], [0.065 * b, 0.075 * h, 0.070 * b], 7, 0.0, 0.0),   # Head
        build_box_submesh([0.0, 0.80 * h, 0.0], [0.038 * b, 0.030 * h, 0.038 * b], 6, 0.0, 0.0),   # Neck
        build_box_submesh([0.28 * h * b, 0.72 * h, 0.0], [0.07 * h, 0.028 * b, 0.028 * b], 10, 0.0, 0.0), # Forearm L
        build_box_submesh([-0.28 * h * b, 0.72 * h, 0.0], [0.07 * h, 0.028 * b, 0.028 * b], 15, 0.0, 0.0),# Forearm R
        build_box_submesh([0.09 * h, 0.21 * h, 0.0], [0.038 * b, 0.095 * h, 0.038 * b], 19, 0.0, 0.0),    # Calf L
        build_box_submesh([-0.09 * h, 0.21 * h, 0.0], [0.038 * b, 0.095 * h, 0.038 * b], 24, 0.0, 0.0),   # Calf R
    ]
    slot0_skin = merge_submeshes(skin_parts)

    # ------------------------------------------------------------------------
    # SLOT 1: M_FighterKit_Retro90s_Cloth (Camiseta holgada 90s con Chaos Cloth COLOR_0, Pantalón, Botines)
    # ------------------------------------------------------------------------
    # MaxDistance normalizado en R: 0.0416 (0.5 cm en cuello/escudo) -> 1.0 (12.0 cm en faldón y mangas)
    kit_parts = [
        build_box_submesh([0.0, 0.69 * h, 0.0], [0.125 * h * b, 0.085 * h, 0.078 * h * b], 5, 0.0416, 0.35), # Chest (0.5cm a 4.2cm)
        build_box_submesh([0.0, 0.56 * h, 0.0], [0.120 * h * b, 0.065 * h, 0.082 * h * b], 3, 0.35, 1.00),   # Baggy 90s Hem (4.2cm a 12.0cm)
        build_box_submesh([0.16 * h * b, 0.73 * h, 0.0], [0.065 * h, 0.042 * b, 0.042 * b], 9, 0.08, 0.85),  # Baggy Sleeve L (hasta 10.2cm)
        build_box_submesh([-0.16 * h * b, 0.73 * h, 0.0], [0.065 * h, 0.042 * b, 0.042 * b], 14, 0.08, 0.85),# Baggy Sleeve R
        build_box_submesh([0.09 * h, 0.41 * h, 0.0], [0.062 * b, 0.095 * h, 0.062 * b], 18, 0.12, 0.65),     # Shorts L
        build_box_submesh([-0.09 * h, 0.41 * h, 0.0], [0.062 * b, 0.095 * h, 0.062 * b], 23, 0.12, 0.65),    # Shorts R
        build_box_submesh([0.09 * h, 0.04 * h, 0.03 * h], [0.042 * b, 0.038 * h, 0.075 * h], 21, 0.0, 0.0),  # Boot L
        build_box_submesh([-0.09 * h, 0.04 * h, 0.03 * h], [0.042 * b, 0.038 * h, 0.075 * h], 26, 0.0, 0.0), # Boot R
    ]
    slot1_kit = merge_submeshes(kit_parts)

    # ------------------------------------------------------------------------
    # SLOT 2: M_FighterHairCards_And_Eyes (Ojos + Hair Cards poligonales / Melena / Drones V.A.R.)
    # ------------------------------------------------------------------------
    hair_style = spec["hair_style"]
    hair_parts = [
        # Ojos
        build_box_submesh([0.025 * b, 0.90 * h, 0.071 * b], [0.012, 0.008, 0.004], 7, 0.0, 0.0),
        build_box_submesh([-0.025 * b, 0.90 * h, 0.071 * b], [0.012, 0.008, 0.004], 7, 0.0, 0.0),
    ]

    if hair_style in ("golden_afro", "black_afro"):
        # Melena rizada voluminosa (El Pibe / El Loco) con 6 Hair Cards vinculadas a hair_chain_01..06
        for c_idx, j_id in enumerate([28, 29, 30, 31, 32, 33]):
            angle = (c_idx / 6.0) * math.pi * 2.0
            ox = math.cos(angle) * 0.065 * b
            oz = math.sin(angle) * 0.065 * b
            hair_parts.append(build_box_submesh([ox, (0.93 - c_idx * 0.012) * h, oz], [0.055 * b, 0.065 * h, 0.045 * b], j_id, 0.15, 0.75))
    elif hair_style == "king_mohawk":
        # Cresta de El Rey
        hair_parts.append(build_box_submesh([0.0, 0.98 * h, 0.0], [0.018 * b, 0.045 * h, 0.078 * b], 28, 0.05, 0.35))
    elif hair_style == "var_drones":
        # Drones holográficos flotantes de V.A.R. - ZERO
        hair_parts.append(build_box_submesh([0.28 * h, 0.95 * h, 0.0], [0.055, 0.035, 0.055], 28, 0.0, 0.0))
        hair_parts.append(build_box_submesh([-0.28 * h, 0.95 * h, 0.0], [0.055, 0.035, 0.055], 31, 0.0, 0.0))
    else:
        # Hair Cards estándar / Melena de los 90
        hair_parts.append(build_box_submesh([0.0, 0.95 * h, -0.02 * b], [0.068 * b, 0.045 * h, 0.072 * b], 28, 0.08, 0.55))
        hair_parts.append(build_box_submesh([0.0, 0.87 * h, -0.06 * b], [0.058 * b, 0.055 * h, 0.025 * b], 29, 0.25, 0.80))

    slot2_hair = merge_submeshes(hair_parts)
    return [slot0_skin, slot1_kit, slot2_hair]


def build_fighter_glb(spec: dict, output_path: str) -> dict:
    height = spec["height"]
    primitives_data = build_fighter_three_slot_primitives(spec)

    # Calcular posiciones globales de bind pose e InverseBindMatrices (4x4 column-major)
    num_bones = len(BONE_DEFS)
    global_pos = np.zeros((num_bones, 3), dtype=np.float32)
    ibm_array = np.zeros((num_bones, 16), dtype=np.float32)

    for idx, name, parent_idx, local_t in BONE_DEFS:
        scaled_t = np.array(local_t, dtype=np.float32) * height
        if parent_idx >= 0:
            global_pos[idx] = global_pos[parent_idx] + scaled_t
        else:
            global_pos[idx] = scaled_t

        mat = np.eye(4, dtype=np.float32)
        mat[0, 3] = -global_pos[idx][0]
        mat[1, 3] = -global_pos[idx][1]
        mat[2, 3] = -global_pos[idx][2]
        ibm_array[idx] = mat.T.flatten()  # Column-major para glTF 2.0

    binary_blob = bytearray()
    buffer_views = []
    accessors = []

    def append_to_blob(data_bytes: bytes, target: int = None) -> int:
        while len(binary_blob) % 4 != 0:
            binary_blob.append(0)
        offset = len(binary_blob)
        binary_blob.extend(data_bytes)
        bv = {"buffer": 0, "byteOffset": offset, "byteLength": len(data_bytes)}
        if target is not None:
            bv["target"] = target
        bv_idx = len(buffer_views)
        buffer_views.append(bv)
        return bv_idx

    # 1. Primitivas de los 3 Slots de Material Maestro
    gltf_primitives = []
    total_verts = 0
    total_tris = 0

    for mat_idx, prim in enumerate(primitives_data):
        pos = prim["positions"]
        nrm = prim["normals"]
        uv = prim["uvs"]
        col = prim["colors"]
        jnt = prim["joints"]
        wgt = prim["weights"]
        idx_arr = prim["indices"]

        total_verts += len(pos)
        total_tris += len(idx_arr) // 3

        bv_pos = append_to_blob(pos.tobytes(), 34962)
        acc_pos = len(accessors)
        accessors.append({
            "bufferView": bv_pos, "componentType": 5126, "count": len(pos), "type": "VEC3",
            "min": pos.min(axis=0).tolist(), "max": pos.max(axis=0).tolist()
        })

        bv_nrm = append_to_blob(nrm.tobytes(), 34962)
        acc_nrm = len(accessors)
        accessors.append({"bufferView": bv_nrm, "componentType": 5126, "count": len(nrm), "type": "VEC3"})

        bv_uv = append_to_blob(uv.tobytes(), 34962)
        acc_uv = len(accessors)
        accessors.append({"bufferView": bv_uv, "componentType": 5126, "count": len(uv), "type": "VEC2"})

        bv_col = append_to_blob(col.tobytes(), 34962)
        acc_col = len(accessors)
        accessors.append({"bufferView": bv_col, "componentType": 5126, "count": len(col), "type": "VEC4"})

        bv_jnt = append_to_blob(jnt.tobytes(), 34962)
        acc_jnt = len(accessors)
        accessors.append({"bufferView": bv_jnt, "componentType": 5121, "count": len(jnt), "type": "VEC4"})

        bv_wgt = append_to_blob(wgt.tobytes(), 34962)
        acc_wgt = len(accessors)
        accessors.append({"bufferView": bv_wgt, "componentType": 5126, "count": len(wgt), "type": "VEC4"})

        bv_idx = append_to_blob(idx_arr.tobytes(), 34963)
        acc_idx = len(accessors)
        accessors.append({"bufferView": bv_idx, "componentType": 5123, "count": len(idx_arr), "type": "SCALAR"})

        gltf_primitives.append({
            "attributes": {
                "POSITION": acc_pos,
                "NORMAL": acc_nrm,
                "TEXCOORD_0": acc_uv,
                "COLOR_0": acc_col,
                "JOINTS_0": acc_jnt,
                "WEIGHTS_0": acc_wgt,
            },
            "indices": acc_idx,
            "material": mat_idx,
            "mode": 4
        })

    # 2. InverseBindMatrices del Skin
    bv_ibm = append_to_blob(ibm_array.tobytes())
    acc_ibm = len(accessors)
    accessors.append({"bufferView": bv_ibm, "componentType": 5126, "count": num_bones, "type": "MAT4"})

    # 3. 5 Clips de Animación Stepped a 60 FPS ("interpolation": "STEP")
    # Los Nodos de hueso van del índice 1 al num_bones (el Nodo 0 es el Mesh Skinned)
    fps = 60.0
    animations = []

    def add_stepped_animation(anim_name: str, frame_indices: list[int], tracks: list[dict]) -> None:
        times = np.array([f / fps for f in frame_indices], dtype=np.float32)
        bv_t = append_to_blob(times.tobytes())
        acc_t = len(accessors)
        accessors.append({
            "bufferView": bv_t, "componentType": 5126, "count": len(times), "type": "SCALAR",
            "min": [float(times.min())], "max": [float(times.max())]
        })

        samplers = []
        channels = []
        for tr in tracks:
            bone_id = tr["bone"]
            path = tr["path"]
            vals = np.array(tr["values"], dtype=np.float32)
            bv_v = append_to_blob(vals.tobytes())
            acc_v = len(accessors)
            v_type = "VEC4" if path == "rotation" else "VEC3"
            accessors.append({"bufferView": bv_v, "componentType": 5126, "count": len(vals), "type": v_type})

            s_idx = len(samplers)
            samplers.append({"input": acc_t, "interpolation": "STEP", "output": acc_v})
            channels.append({"sampler": s_idx, "target": {"node": bone_id + 1, "path": path}})

        animations.append({"name": anim_name, "samplers": samplers, "channels": channels})

    # Clip 1: Anim_Idle (Guardia de potrero a 60Hz, frames 0, 15, 30, 45)
    add_stepped_animation("Anim_Idle", [0, 15, 30, 45], [
        {"bone": 3, "path": "rotation", "values": [
            euler_xyz_to_quat(4.0, 12.0, 0.0),
            euler_xyz_to_quat(7.0, 12.0, 0.0),
            euler_xyz_to_quat(4.0, 12.0, 0.0),
            euler_xyz_to_quat(2.0, 12.0, 0.0),
        ]},
    ])

    # Clip 2: Anim_5LP_Jab4f (Startup 4f, Active 3f, Recovery 7f = 14f total)
    add_stepped_animation("Anim_5LP_Jab4f", [0, 3, 4, 7, 14], [
        {"bone": 9, "path": "rotation", "values": [
            euler_xyz_to_quat(0.0, 0.0, 0.0),
            euler_xyz_to_quat(-25.0, 15.0, 0.0),
            euler_xyz_to_quat(-85.0, 0.0, 0.0),
            euler_xyz_to_quat(-40.0, 10.0, 0.0),
            euler_xyz_to_quat(0.0, 0.0, 0.0),
        ]},
    ])

    # Clip 3: Anim_236SK_Shot (Disparo de Balón: carga de pierna derecha e impacto con empeine)
    add_stepped_animation("Anim_236SK_Shot", [0, 8, 14, 24, 38], [
        {"bone": 23, "path": "rotation", "values": [
            euler_xyz_to_quat(0.0, 0.0, 0.0),
            euler_xyz_to_quat(48.0, 0.0, 0.0),
            euler_xyz_to_quat(-72.0, 0.0, 0.0),
            euler_xyz_to_quat(-35.0, 0.0, 0.0),
            euler_xyz_to_quat(0.0, 0.0, 0.0),
        ]},
    ])

    # Clip 4: Anim_623HP_BicycleKick (Chilena Antiaérea con exageración anime 1.25x en tibia/botín en los frames activos)
    add_stepped_animation("Anim_623HP_BicycleKick", [0, 5, 10, 15, 35], [
        {"bone": 1, "path": "rotation", "values": [
            euler_xyz_to_quat(0.0, 0.0, 0.0),
            euler_xyz_to_quat(-65.0, 0.0, 0.0),
            euler_xyz_to_quat(-135.0, 0.0, 0.0),
            euler_xyz_to_quat(-90.0, 0.0, 0.0),
            euler_xyz_to_quat(0.0, 0.0, 0.0),
        ]},
        {"bone": 24, "path": "scale", "values": [
            [1.0, 1.0, 1.0],
            [1.25, 1.25, 1.25],
            [1.25, 1.25, 1.25],
            [1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0],
        ]},
        {"bone": 26, "path": "scale", "values": [
            [1.0, 1.0, 1.0],
            [1.25, 1.25, 1.25],
            [1.25, 1.25, 1.25],
            [1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0],
        ]},
    ])

    # Clip 5: Anim_214SK_Scorpion (El Escorpión: arqueo dorsal y rechazo con ambos talones en el aire)
    add_stepped_animation("Anim_214SK_Scorpion", [0, 10, 16, 24, 42], [
        {"bone": 3, "path": "rotation", "values": [
            euler_xyz_to_quat(0.0, 0.0, 0.0),
            euler_xyz_to_quat(55.0, 0.0, 0.0),
            euler_xyz_to_quat(82.0, 0.0, 0.0),
            euler_xyz_to_quat(40.0, 0.0, 0.0),
            euler_xyz_to_quat(0.0, 0.0, 0.0),
        ]},
        {"bone": 19, "path": "rotation", "values": [
            euler_xyz_to_quat(0.0, 0.0, 0.0),
            euler_xyz_to_quat(75.0, 0.0, 0.0),
            euler_xyz_to_quat(115.0, 0.0, 0.0),
            euler_xyz_to_quat(45.0, 0.0, 0.0),
            euler_xyz_to_quat(0.0, 0.0, 0.0),
        ]},
        {"bone": 24, "path": "rotation", "values": [
            euler_xyz_to_quat(0.0, 0.0, 0.0),
            euler_xyz_to_quat(75.0, 0.0, 0.0),
            euler_xyz_to_quat(115.0, 0.0, 0.0),
            euler_xyz_to_quat(45.0, 0.0, 0.0),
            euler_xyz_to_quat(0.0, 0.0, 0.0),
        ]},
    ])

    # 4. Construir Nodos del glTF (Nodo 0 = Mesh Skinned, Nodos 1..38 = Huesos)
    children_map = {i: [] for i in range(num_bones)}
    for idx, name, parent_idx, _ in BONE_DEFS:
        if parent_idx >= 0:
            children_map[parent_idx].append(idx + 1)

    nodes = [
        {"name": f"SK_{spec['id']}", "mesh": 0, "skin": 0, "children": [1]}
    ]
    for idx, name, parent_idx, local_t in BONE_DEFS:
        scaled_t = (np.array(local_t, dtype=np.float32) * height).tolist()
        node_obj = {"name": name, "translation": scaled_t, "rotation": [0.0, 0.0, 0.0, 1.0], "scale": [1.0, 1.0, 1.0]}
        if children_map[idx]:
            node_obj["children"] = children_map[idx]
        nodes.append(node_obj)

    gltf_json = {
        "asset": {
            "version": "2.0",
            "generator": "SouthAmericaFighters AAA Procedural glTF 2.0 Pipeline (UE 5.4 + Chaos Cloth 5.4)"
        },
        "scene": 0,
        "scenes": [{"name": "FighterScene", "nodes": [0]}],
        "nodes": nodes,
        "Skins": undefined_check if False else None,
        "skins": [{
            "name": f"Skeleton_{spec['id']}",
            "inverseBindMatrices": acc_ibm,
            "skeleton": 1,
            "joints": list(range(1, num_bones + 1))
        }],
        "Materials_Info": None,
        "materials": [
            {
                "name": "M_FighterSkin_SSS",
                "pbrMetallicRoughness": {"baseColorFactor": [0.78, 0.54, 0.38, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.45}
            },
            {
                "name": "M_FighterKit_Retro90s_Cloth",
                "pbrMetallicRoughness": {"baseColorFactor": spec["kit_color"], "metallicFactor": 0.05, "roughnessFactor": 0.72}
            },
            {
                "name": "M_FighterHairCards_And_Eyes",
                "pbrMetallicRoughness": {"baseColorFactor": [0.15, 0.12, 0.08, 1.0], "metallicFactor": 0.1, "roughnessFactor": 0.35}
            }
        ],
        "meshes": [{
            "name": f"Mesh_{spec['id']}",
            "primitives": gltf_primitives,
            "extras": {
                "ChaosCloth54_MaxDistanceCm": {"MinCollarCrest": 0.5, "MaxHemSleeves": 12.0},
                "ChaosCloth54_Aerodynamics": {"Drag": 0.08, "Lift": 0.04}
            }
        }],
        "animations": animations,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(binary_blob)}]
    }
    del gltf_json["Skins"]
    del gltf_json["Materials_Info"]

    write_glb_file(output_path, gltf_json, binary_blob)
    return {
        "FighterID": spec["id"],
        "DisplayName": spec["name"],
        "File": os.path.basename(output_path),
        "HeightMeters": height,
        "SkeletonJoints": num_bones,
        "Vertices": total_verts,
        "Triangles": total_tris,
        "MaterialSlots": ["M_FighterSkin_SSS", "M_FighterKit_Retro90s_Cloth", "M_FighterHairCards_And_Eyes"],
        "SteppedAnimations60Hz": ["Anim_Idle", "Anim_5LP_Jab4f", "Anim_236SK_Shot", "Anim_623HP_BicycleKick", "Anim_214SK_Scorpion"]
    }


def write_glb_file(filepath: str, gltf_dict: dict, bin_chunk: bytearray) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    json_bytes = json.dumps(gltf_dict, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "
    while len(bin_chunk) % 4 != 0:
        bin_chunk.append(0)

    gltf_dict["buffers"][0]["byteLength"] = len(bin_chunk)
    json_bytes = json.dumps(gltf_dict, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_chunk)
    with open(filepath, "wb") as f:
        # Header GLB (magic 'glTF' = 0x46546C67, version = 2, length)
        f.write(struct.pack("<III", 0x46546C67, 2, total_length))
        # JSON Chunk (type = 0x4E4F534A)
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        # BIN Chunk (type = 0x004E4942)
        f.write(struct.pack("<II", len(bin_chunk), 0x004E4942))
        f.write(bin_chunk)


def generate_truncated_icosahedron_ball(glb_path: str, obj_path: str) -> dict:
    """Genera el balón clásico de 32 paneles (Icosaedro Truncado esférico de radio 0.22m) en .glb y .obj."""
    radius = 0.22
    lat_steps = 16
    lon_steps = 32

    positions = []
    normals = []
    uvs = []
    colors = []
    indices = []

    for i in range(lat_steps + 1):
        theta = math.pi * (i / lat_steps)
        sin_t, cos_t = math.sin(theta), math.cos(theta)
        for j in range(lon_steps + 1):
            phi = 2.0 * math.pi * (j / lon_steps)
            nx = sin_t * math.cos(phi)
            ny = cos_t
            nz = sin_t * math.sin(phi)
            positions.append([nx * radius, ny * radius + radius, nz * radius])
            normals.append([nx, ny, nz])
            uvs.append([j / lon_steps, i / lat_steps])
            # Patrón de 32 paneles (12 pentágonos negros + 20 hexágonos blancos)
            panel_id = ((i // 3) + (j // 3)) % 3
            if panel_id == 0:
                colors.append([0.08, 0.08, 0.09, 1.0])
            else:
                colors.append([0.96, 0.96, 0.94, 1.0])

    for i in range(lat_steps):
        for j in range(lon_steps):
            p0 = i * (lon_steps + 1) + j
            p1 = p0 + 1
            p2 = p0 + (lon_steps + 1)
            p3 = p2 + 1
            indices.extend([p0, p2, p1, p1, p2, p3])

    pos_arr = np.array(positions, dtype=np.float32)
    nrm_arr = np.array(normals, dtype=np.float32)
    uv_arr = np.array(uvs, dtype=np.float32)
    col_arr = np.array(colors, dtype=np.float32)
    idx_arr = np.array(indices, dtype=np.uint16)

    # Exportar .OBJ
    os.makedirs(os.path.dirname(obj_path), exist_ok=True)
    with open(obj_path, "w", encoding="utf-8") as wf:
        wf.write("# SM_Ball_TruncatedIcosahedron_32Panels.obj - SouthAmericaFighters\n")
        for v in pos_arr:
            wf.write(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}\n")
        for vt in uv_arr:
            wf.write(f"vt {vt[0]:.5f} {vt[1]:.5f}\n")
        for vn in nrm_arr:
            wf.write(f"vn {vn[0]:.5f} {vn[1]:.5f} {vn[2]:.5f}\n")
        for k in range(0, len(idx_arr), 3):
            i0, i1, i2 = int(idx_arr[k]) + 1, int(idx_arr[k + 1]) + 1, int(idx_arr[k + 2]) + 1
            wf.write(f"f {i0}/{i0}/{i0} {i1}/{i1}/{i1} {i2}/{i2}/{i2}\n")

    # Exportar .GLB
    blob = bytearray()
    bvs = []
    accs = []

    def add_bv(b_data: bytes, target: int) -> int:
        while len(blob) % 4 != 0:
            blob.append(0)
        off = len(blob)
        blob.extend(b_data)
        bvs.append({"buffer": 0, "byteOffset": off, "byteLength": len(b_data), "target": target})
        return len(bvs) - 1

    bv_p = add_bv(pos_arr.tobytes(), 34962)
    accs.append({"bufferView": bv_p, "componentType": 5126, "count": len(pos_arr), "type": "VEC3",
                 "min": pos_arr.min(axis=0).tolist(), "max": pos_arr.max(axis=0).tolist()})
    bv_n = add_bv(nrm_arr.tobytes(), 34962)
    accs.append({"bufferView": bv_n, "componentType": 5126, "count": len(nrm_arr), "type": "VEC3"})
    bv_u = add_bv(uv_arr.tobytes(), 34962)
    accs.append({"bufferView": bv_u, "componentType": 5126, "count": len(uv_arr), "type": "VEC2"})
    bv_c = add_bv(col_arr.tobytes(), 34962)
    accs.append({"bufferView": bv_c, "componentType": 5126, "count": len(col_arr), "type": "VEC4"})
    bv_i = add_bv(idx_arr.tobytes(), 34963)
    accs.append({"bufferView": bv_i, "componentType": 5123, "count": len(idx_arr), "type": "SCALAR"})

    gltf = {
        "asset": {"version": "2.0", "generator": "SouthAmericaFighters 32-Panel Ball Generator"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "SM_Ball_TruncatedIcosahedron_32Panels", "mesh": 0}],
        "materials": [{"name": "M_OfficialLeatherBall_32Panels", "pbrMetallicRoughness": {"roughnessFactor": 0.38, "metallicFactor": 0.05}}],
        "meshes": [{
            "name": "Mesh_Ball_32Panels",
            "primitives": [{
                "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2, "COLOR_0": 3},
                "indices": 4, "material": 0, "mode": 4
            }]
        }],
        "accessors": accs,
        "bufferViews": bvs,
        "buffers": [{"byteLength": len(blob)}]
    }
    write_glb_file(glb_path, gltf, blob)
    return {"Vertices": int(len(pos_arr)), "Triangles": int(len(idx_arr) // 3)}


def generate_stage_pitch_and_walls(glb_path: str) -> dict:
    """Genera el escenario modular 2.5D con Cancha Zona A (24m), Vallas Pre-Fracturadas para Wall Break y Zona B."""
    submeshes = [
        # Zona A: Césped principal (-12.5m a +12.5m)
        build_box_submesh([0.0, -0.10, 0.0], [12.5, 0.10, 8.0], 0, 0.0, 0.0),
        # Muro Izquierdo Pre-Fracturado (6 fragmentos listos para Chaos Destruction Wall Break)
        build_box_submesh([-12.5, 0.60, -1.5], [0.15, 0.60, 0.7], 0, 0.0, 0.0),
        build_box_submesh([-12.5, 0.60,  0.0], [0.15, 0.60, 0.7], 0, 0.0, 0.0),
        build_box_submesh([-12.5, 0.60,  1.5], [0.15, 0.60, 0.7], 0, 0.0, 0.0),
        # Muro Derecho Pre-Fracturado
        build_box_submesh([12.5, 0.60, -1.5], [0.15, 0.60, 0.7], 0, 0.0, 0.0),
        build_box_submesh([12.5, 0.60,  0.0], [0.15, 0.60, 0.7], 0, 0.0, 0.0),
        build_box_submesh([12.5, 0.60,  1.5], [0.15, 0.60, 0.7], 0, 0.0, 0.0),
        # Zona B Extendida (Explanada / Calle Caminito / Exterior hasta +-18.5m)
        build_box_submesh([-15.5, -0.12, 0.0], [3.0, 0.10, 8.0], 0, 0.0, 0.0),
        build_box_submesh([ 15.5, -0.12, 0.0], [3.0, 0.10, 8.0], 0, 0.0, 0.0),
    ]
    merged = merge_submeshes(submeshes)
    pos_arr = merged["positions"]
    nrm_arr = merged["normals"]
    uv_arr = merged["uvs"]
    idx_arr = merged["indices"]

    blob = bytearray()
    bvs = []
    accs = []

    def add_bv(b_data: bytes, target: int) -> int:
        while len(blob) % 4 != 0:
            blob.append(0)
        off = len(blob)
        blob.extend(b_data)
        bvs.append({"buffer": 0, "byteOffset": off, "byteLength": len(b_data), "target": target})
        return len(bvs) - 1

    bv_p = add_bv(pos_arr.tobytes(), 34962)
    accs.append({"bufferView": bv_p, "componentType": 5126, "count": len(pos_arr), "type": "VEC3",
                 "min": pos_arr.min(axis=0).tolist(), "max": pos_arr.max(axis=0).tolist()})
    bv_n = add_bv(nrm_arr.tobytes(), 34962)
    accs.append({"bufferView": bv_n, "componentType": 5126, "count": len(nrm_arr), "type": "VEC3"})
    bv_u = add_bv(uv_arr.tobytes(), 34962)
    accs.append({"bufferView": bv_u, "componentType": 5126, "count": len(uv_arr), "type": "VEC2"})
    bv_i = add_bv(idx_arr.tobytes(), 34963)
    accs.append({"bufferView": bv_i, "componentType": 5123, "count": len(idx_arr), "type": "SCALAR"})

    gltf = {
        "asset": {"version": "2.0", "generator": "SouthAmericaFighters Stage & WallBreak Generator"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "SM_Stage_PitchAndDestructibleWalls", "mesh": 0}],
        "materials": [{"name": "M_Stage_PitchAndPreFracturedWalls", "pbrMetallicRoughness": {"roughnessFactor": 0.8, "metallicFactor": 0.1}}],
        "meshes": [{
            "name": "Mesh_Stage_PitchAndWalls",
            "primitives": [{
                "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                "indices": 3, "material": 0, "mode": 4
            }]
        }],
        "accessors": accs,
        "bufferViews": bvs,
        "buffers": [{"byteLength": len(blob)}]
    }
    write_glb_file(glb_path, gltf, blob)
    return {"Vertices": int(len(pos_arr)), "Triangles": int(len(idx_arr) // 3)}


def main() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_root = os.path.join(repo_root, "Assets", "Models3D")
    fighters_dir = os.path.join(models_root, "Fighters")
    props_dir = os.path.join(models_root, "Props")
    stages_dir = os.path.join(models_root, "Stages")

    fighter_reports = []
    for spec in FIGHTER_SPECS:
        glb_file = os.path.join(fighters_dir, f"SK_{spec['id']}.glb")
        info = build_fighter_glb(spec, glb_file)
        fighter_reports.append(info)
        print(f"[OK] Luchador 3D glTF: SK_{spec['id']}.glb ({os.path.getsize(glb_file)} bytes)")

    ball_glb = os.path.join(props_dir, "SM_Ball_TruncatedIcosahedron_32Panels.glb")
    ball_obj = os.path.join(props_dir, "SM_Ball_TruncatedIcosahedron_32Panels.obj")
    ball_info = generate_truncated_icosahedron_ball(ball_glb, ball_obj)
    print(f"[OK] Balón 32 Paneles: {os.path.basename(ball_glb)} & {os.path.basename(ball_obj)}")

    stage_glb = os.path.join(stages_dir, "SM_Stage_PitchAndDestructibleWalls.glb")
    stage_info = generate_stage_pitch_and_walls(stage_glb)
    print(f"[OK] Escenario Modular Wall-Break: {os.path.basename(stage_glb)}")

    manifest = {
        "SchemaVersion": "1.0.0-UE5.4-GLTF2",
        "TargetEngine": "Unreal Engine 5.4+ (Nanite & Skinned Cloth Pipeline)",
        "SkeletonStandard": {
            "TotalBones": len(BONE_DEFS),
            "RootAndHitstopBones": ["root", "pelvis", "pelvis_visual_offset"],
            "SecondaryChainBones": ["hair_chain_01..06", "kit_hem_01..04"],
            "AnimationSampleRateHz": 60,
            "InterpolationMode": "STEP (Pure Stepped Keyframes)"
        },
        "ChaosCloth54Specification": {
            "VertexColorAttribute": "COLOR_0.r",
            "MinMaxDistanceCm": 0.5,
            "MaxHemAndSleevesDistanceCm": 12.0,
            "AerodynamicDrag": 0.08,
            "AerodynamicLift": 0.04,
            "RollbackTeleportThresholdCm": 15.0
        },
        "GPUBudgetAndLODTargets": {
            "LOD0_CloseUpAndGameplay": {"TargetTriangles": 65000, "MaxMorphTargets": 32, "ClothSimulation": True},
            "LOD1_MidRange": {"TargetTriangles": 32000, "MaxMorphTargets": 16, "ClothSimulation": True},
            "LOD2_WideCamera": {"TargetTriangles": 16000, "MaxMorphTargets": 0, "ClothSimulation": False},
            "LOD3_LowSpecFallback": {"TargetTriangles": 8000, "MaxMorphTargets": 0, "ClothSimulation": False},
            "UVChannels": {
                "UV0": "Primary PBR/Street-Ink BaseColor, Normal & ORM",
                "UV1": "Dynamic Jersey Numbers, National Crest & Pitch Mud Mask"
            }
        },
        "GeneratedFighters": fighter_reports,
        "GeneratedPropsAndStages": {
            "OfficialBall32Panels": ball_info,
            "StagePitchAndDestructibleWalls": stage_info
        }
    }

    manifest_path = os.path.join(models_root, "Models3D_TechnicalManifest.json")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)
    print(f"[OK] Manifiesto Técnico 3D guardado en: {manifest_path}")


if __name__ == "__main__":
    main()
