#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_3d_models_gltf.py
Generador Procedural de Modelos 3D glTF 2.0 Binarios (.glb) y Wavefront (.obj) para Unreal Engine 5.8+.
Construye:
1. 17 Skeletal Meshes Anatómicos (16 Luchadores CONMEBOL + El Juez Supremo V.A.R. - ZERO) con:
   - Mallas base orgánicas multi-anillo (cápsulas/lofts anatómicos para cráneo, rostro, orejas,
     cuello, torso con cuello en V y faldón holgado 90s, brazos, manos/guantes, shorts, rodillas,
     calcetas altas con puño, botines con tapones, ojos y peinados/accesorios por arquetipo).
   - Contrato exacto de Atlas UV (`TEXCOORD_0` con convención glTF top-left, invertido desde
     coordenadas bottom-left para coincidir al 100% con Blender, UE5 FBX y WebGL2).
   - 3 Slots de Material Maestro (`M_FighterSkin_SSS`, `M_FighterKit_Retro90s_Cloth`, `M_FighterHairCards_And_Eyes`)
     con incrustación automática de texturas `Assets/TexturesPBR/Fighters/T_<ID>_{Skin,Kit,Hair}_Albedo.png`
     cuando existan.
   - Esqueleto UE5 de 38 huesos (`BONE_DEFS`), pesos suaves de skinning, `COLOR_0` para Chaos Cloth,
     y 5 Clips de Animación Stepped a 60 FPS (`"interpolation": "STEP"`).
2. Balón Oficial de 32 Paneles (Icosaedro Truncado) en .glb y .obj.
3. Escenario Modular 2.5D con Zona A, Vallas Pre-Fracturadas para Wall Break y Zona B.
4. Manifiesto Técnico JSON (`Models3D_TechnicalManifest.json`).
"""

import json
import math
import os
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

GOALKEEPER_IDS = {"LOCO_CO", "BULLDOG_PY"}
CAPTAIN_ARMBAND_IDS = {"TREN_EC"}

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


def uv_bl_to_gltf(u: float, v_bl: float) -> list[float]:
    """Convierte UV bottom-left (Blender/OpenGL/PIL upright) a top-left glTF 2.0 (`v_gltf = 1 - v_bl`)."""
    return [float(max(0.0, min(1.0, u))), float(max(0.0, min(1.0, 1.0 - v_bl)))]


def _normalize_weights(joint_weights: list[tuple[int, float]]) -> tuple[list[int], list[float]]:
    jw = [(int(j), float(w)) for j, w in joint_weights if w > 1e-5]
    if not jw:
        return [1, 0, 0, 0], [1.0, 0.0, 0.0, 0.0]
    jw.sort(key=lambda pair: pair[1], reverse=True)
    jw = jw[:4]
    total = sum(w for _, w in jw)
    j4 = [0, 0, 0, 0]
    w4 = [0.0, 0.0, 0.0, 0.0]
    for k, (j, w) in enumerate(jw):
        j4[k] = j
        w4[k] = w / total
    return j4, w4


def _compute_smooth_normals(positions: np.ndarray, indices: np.ndarray) -> np.ndarray:
    normals = np.zeros_like(positions, dtype=np.float32)
    tris = indices.reshape(-1, 3)
    p0 = positions[tris[:, 0]]
    p1 = positions[tris[:, 1]]
    p2 = positions[tris[:, 2]]
    fn = np.cross(p1 - p0, p2 - p0)
    for k in range(3):
        np.add.at(normals, tris[:, k], fn)
    lens = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.where(lens > 1e-8, normals / np.maximum(lens, 1e-8), np.array([0.0, 1.0, 0.0], dtype=np.float32))
    return normals.astype(np.float32)


def _pack_submesh(
    positions: list[list[float]],
    uvs: list[list[float]],
    colors: list[list[float]],
    joints: list[list[int]],
    weights: list[list[float]],
    indices: list[int],
) -> dict:
    pos_arr = np.array(positions, dtype=np.float32)
    idx_arr = np.array(indices, dtype=np.uint16)
    nrm_arr = _compute_smooth_normals(pos_arr, idx_arr)
    return {
        "positions": pos_arr,
        "normals": nrm_arr,
        "uvs": np.array(uvs, dtype=np.float32),
        "colors": np.array(colors, dtype=np.float32),
        "joints": np.array(joints, dtype=np.uint8),
        "weights": np.array(weights, dtype=np.float32),
        "indices": idx_arr,
    }


def _ortho_basis(axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve dos vectores unitarios ortogonales a `axis` para secciones transversales consistentes."""
    ax = axis / max(float(np.linalg.norm(axis)), 1e-8)
    # Preferimos +Z adelante o +Y arriba como referencia estable
    ref = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    if abs(float(np.dot(ax, ref))) > 0.90:
        ref = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    u_vec = np.cross(ref, ax)
    u_vec = u_vec / max(float(np.linalg.norm(u_vec)), 1e-8)
    v_vec = np.cross(ax, u_vec)
    v_vec = v_vec / max(float(np.linalg.norm(v_vec)), 1e-8)
    return u_vec, v_vec


def build_lofted_prism(
    rings: list[dict],
    n_seg: int = 12,
    basis_u: np.ndarray | None = None,
    basis_v: np.ndarray | None = None,
    cap_start: bool = True,
    cap_end: bool = True,
    split_front_back_uv: bool = False,
    uv_front_box: tuple[float, float, float, float] = (0.02, 0.48, 0.52, 0.98),
    uv_back_box: tuple[float, float, float, float] = (0.52, 0.98, 0.52, 0.98),
    uv_full_box: tuple[float, float, float, float] = (0.02, 0.98, 0.02, 0.48),
    reverse_back_u: bool = False,
) -> dict:
    """
    Construye un prisma/cápsula orgánica multi-anillo con secciones elípticas modulables,
    pesos suaves de huesos y UVs exactas sin estiramientos.

    Cada anillo en `rings` contiene:
      - center: [x, y, z]
      - rx: float (eje basis_u)
      - ry: float (eje basis_v)
      - joints: list[(joint_idx, weight)]
      - cloth: float (peso Chaos Cloth COLOR_0.R)
      - v_t: float in [0..1] (0 = primer anillo/arriba o inicio, 1 = final)
      - deform: opcional callable(theta, pos) -> (dx, dy, dz) en mundo
    """
    if basis_u is None or basis_v is None:
        c0 = np.array(rings[0]["center"], dtype=np.float32)
        c1 = np.array(rings[-1]["center"], dtype=np.float32)
        axis = c1 - c0
        if float(np.linalg.norm(axis)) < 1e-6:
            axis = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        basis_u, basis_v = _ortho_basis(axis)

    positions: list[list[float]] = []
    uvs: list[list[float]] = []
    colors: list[list[float]] = []
    joints: list[list[int]] = []
    weights: list[list[float]] = []
    indices: list[int] = []

    if split_front_back_uv:
        # Asegurar número par de segmentos para dividir limpiamente frente (z >= 0) y espalda (z <= 0)
        half = max(4, n_seg // 2)
        # Frente: ángulos donde el vector apunta hacia +Z (theta de -pi/2 a +pi/2 alrededor de +Z/+X)
        # Construimos explicitamente dos mitades que comparten borde en x = ±rx, z = 0
        # Mitad Frente: phi in [0 .. pi] -> cos(phi) va de +1 (-X? no, +X a -X) o x = -rx*cos(phi), z = +ry*sin(phi)
        # De modo que phi=0 -> (-rx, 0) [viewer left], phi=pi/2 -> (0, +ry) [front], phi=pi -> (+rx, 0) [viewer right]
        shells = [
            ("front", [math.pi * (s / half) for s in range(half + 1)]),
            ("back",  [math.pi + math.pi * (s / half) for s in range(half + 1)]),
        ]
        # Nota: en shell "back", phi va de pi (+rx, 0) -> 1.5*pi (0, -ry) -> 2*pi (-rx, 0)
        for shell_name, phis in shells:
            u0, u1, v0, v1 = uv_front_box if shell_name == "front" else uv_back_box
            ring_cols = len(phis)
            base_v_idx = len(positions)
            for r in rings:
                cx, cy, cz = r["center"]
                rx, ry = r["rx"], r["ry"]
                cw = float(r.get("cloth", 0.0))
                v_t = float(r.get("v_t", 0.5))
                v_bl = v1 - v_t * (v1 - v0)  # v_t=0 -> v1 (top), v_t=1 -> v0 (bottom)
                j4, w4 = _normalize_weights(r["joints"])
                deform_fn = r.get("deform")

                for s_idx, phi in enumerate(phis):
                    # Convención consistente de frente (+Z): x = -cos(phi)*rx, z = sin(phi)*ry
                    # Para shell "front" (phi 0..pi): x va de -rx (izq cámara, u0) a +rx (der cámara, u1)
                    # Para shell "back" (phi pi..2pi): x va de +rx a -rx
                    u_frac = s_idx / float(half)
                    if shell_name == "back" and reverse_back_u:
                        # Mirando desde atrás (-Z), izq es +rx (u0) y der es -rx (u1), así que u_frac=0..1 ya va de +rx -> -rx!
                        pass
                    elif shell_name == "back" and not reverse_back_u:
                        u_frac = 1.0 - u_frac
                    u_val = u0 + u_frac * (u1 - u0)

                    lx = -math.cos(phi) * rx
                    lz = math.sin(phi) * ry
                    px = cx + lx * float(basis_u[0]) + lz * float(basis_v[0])
                    py = cy + lx * float(basis_u[1]) + lz * float(basis_v[1])
                    pz = cz + lx * float(basis_u[2]) + lz * float(basis_v[2])
                    if deform_fn is not None:
                        dx, dy, dz = deform_fn(phi, (px, py, pz))
                        px += dx
                        py += dy
                        pz += dz

                    positions.append([px, py, pz])
                    uvs.append(uv_bl_to_gltf(u_val, v_bl))
                    colors.append([cw, 0.85, 0.15, 1.0])
                    joints.append(j4)
                    weights.append(w4)

            # Verificar orientación de winding para que las normales apunten hacia afuera
            # Si rings[0].center[1] > rings[-1].center[1] (de arriba hacia abajo) y basis_u=+X, basis_v=+Z:
            # Con x=-cos(phi), z=sin(phi): d/dphi = (+sin, +cos), d/dring = (0, -1, 0)
            # cross(d_phi, d_ring) = (+sin, 0, +cos) x (0, -1, 0) = (+cos, 0, -sin) -> INWARD si cross(c_next, c_phi)!
            # Comprobamos orden de triángulos dinámicamente con el primer quad
            for ri in range(len(rings) - 1):
                for si in range(ring_cols - 1):
                    i00 = base_v_idx + ri * ring_cols + si
                    i01 = i00 + 1
                    i10 = i00 + ring_cols
                    i11 = i10 + 1
                    if ri == 0 and si == 0:
                        p00 = np.array(positions[i00])
                        p01 = np.array(positions[i01])
                        p10 = np.array(positions[i10])
                        c_ring = np.array(rings[0]["center"])
                        n_test = np.cross(p01 - p00, p10 - p00)
                        flip_winding = float(np.dot(n_test, p00 - c_ring)) < 0.0
                    if flip_winding:
                        indices.extend([i00, i10, i01, i01, i10, i11])
                    else:
                        indices.extend([i00, i01, i10, i01, i11, i10])

        # Tapas opcionales usando un centro por anillo extremo
        if cap_start:
            r0 = rings[0]
            c_idx = len(positions)
            j4, w4 = _normalize_weights(r0["joints"])
            u_mid = 0.5 * (uv_front_box[0] + uv_front_box[1])
            positions.append(list(r0["center"]))
            uvs.append(uv_bl_to_gltf(u_mid, uv_front_box[3]))
            colors.append([float(r0.get("cloth", 0.0)), 0.85, 0.15, 1.0])
            joints.append(j4)
            weights.append(w4)
            # Triángulos desde shell front y back en ri=0
            ring_cols = half + 1
            for s_offset, box_start in [(0, 0), (len(rings) * ring_cols, 1)]:
                for si in range(half):
                    a = s_offset + si
                    b = a + 1
                    if si == 0 and s_offset == 0:
                        n_cap = np.cross(np.array(positions[b]) - np.array(positions[c_idx]),
                                         np.array(positions[a]) - np.array(positions[c_idx]))
                        axis_out = np.array(rings[0]["center"]) - np.array(rings[1]["center"])
                        cap_flip = float(np.dot(n_cap, axis_out)) < 0.0
                    if cap_flip:
                        indices.extend([c_idx, a, b])
                    else:
                        indices.extend([c_idx, b, a])

        if cap_end:
            rn = rings[-1]
            c_idx = len(positions)
            j4, w4 = _normalize_weights(rn["joints"])
            u_mid = 0.5 * (uv_front_box[0] + uv_front_box[1])
            positions.append(list(rn["center"]))
            uvs.append(uv_bl_to_gltf(u_mid, uv_front_box[2]))
            colors.append([float(rn.get("cloth", 0.0)), 0.85, 0.15, 1.0])
            joints.append(j4)
            weights.append(w4)
            ring_cols = half + 1
            last_row = (len(rings) - 1) * ring_cols
            shell2_last_row = len(rings) * ring_cols + last_row
            for s_base in (last_row, shell2_last_row):
                for si in range(half):
                    a = s_base + si
                    b = a + 1
                    if si == 0 and s_base == last_row:
                        n_cap = np.cross(np.array(positions[a]) - np.array(positions[c_idx]),
                                         np.array(positions[b]) - np.array(positions[c_idx]))
                        axis_out = np.array(rings[-1]["center"]) - np.array(rings[-2]["center"])
                        cap_flip_end = float(np.dot(n_cap, axis_out)) < 0.0
                    if cap_flip_end:
                        indices.extend([c_idx, b, a])
                    else:
                        indices.extend([c_idx, a, b])

    else:
        u0, u1, v0, v1 = uv_full_box
        ring_cols = n_seg + 1
        for r in rings:
            cx, cy, cz = r["center"]
            rx, ry = r["rx"], r["ry"]
            cw = float(r.get("cloth", 0.0))
            v_t = float(r.get("v_t", 0.5))
            v_bl = v1 - v_t * (v1 - v0)
            j4, w4 = _normalize_weights(r["joints"])
            deform_fn = r.get("deform")

            for si in range(ring_cols):
                frac = si / float(n_seg)
                phi = 2.0 * math.pi * frac
                u_val = u0 + frac * (u1 - u0)
                lx = math.cos(phi) * rx
                lz = math.sin(phi) * ry
                px = cx + lx * float(basis_u[0]) + lz * float(basis_v[0])
                py = cy + lx * float(basis_u[1]) + lz * float(basis_v[1])
                pz = cz + lx * float(basis_u[2]) + lz * float(basis_v[2])
                if deform_fn is not None:
                    dx, dy, dz = deform_fn(phi, (px, py, pz))
                    px += dx
                    py += dy
                    pz += dz
                positions.append([px, py, pz])
                uvs.append(uv_bl_to_gltf(u_val, v_bl))
                colors.append([cw, 0.85, 0.15, 1.0])
                joints.append(j4)
                weights.append(w4)

        flip_winding = False
        for ri in range(len(rings) - 1):
            for si in range(n_seg):
                i00 = ri * ring_cols + si
                i01 = i00 + 1
                i10 = i00 + ring_cols
                i11 = i10 + 1
                if ri == 0 and si == 0:
                    p00 = np.array(positions[i00])
                    p01 = np.array(positions[i01])
                    p10 = np.array(positions[i10])
                    c_ring = np.array(rings[0]["center"])
                    n_test = np.cross(p01 - p00, p10 - p00)
                    flip_winding = float(np.dot(n_test, p00 - c_ring)) < 0.0
                if flip_winding:
                    indices.extend([i00, i10, i01, i01, i10, i11])
                else:
                    indices.extend([i00, i01, i10, i01, i11, i10])

        if cap_start:
            r0 = rings[0]
            c_idx = len(positions)
            j4, w4 = _normalize_weights(r0["joints"])
            positions.append(list(r0["center"]))
            uvs.append(uv_bl_to_gltf(0.5 * (u0 + u1), v1))
            colors.append([float(r0.get("cloth", 0.0)), 0.85, 0.15, 1.0])
            joints.append(j4)
            weights.append(w4)
            cap_flip = False
            for si in range(n_seg):
                a = si
                b = si + 1
                if si == 0 and len(rings) > 1:
                    n_cap = np.cross(np.array(positions[b]) - np.array(positions[c_idx]),
                                     np.array(positions[a]) - np.array(positions[c_idx]))
                    axis_out = np.array(rings[0]["center"]) - np.array(rings[1]["center"])
                    cap_flip = float(np.dot(n_cap, axis_out)) < 0.0
                if cap_flip:
                    indices.extend([c_idx, a, b])
                else:
                    indices.extend([c_idx, b, a])

        if cap_end:
            rn = rings[-1]
            c_idx = len(positions)
            j4, w4 = _normalize_weights(rn["joints"])
            positions.append(list(rn["center"]))
            uvs.append(uv_bl_to_gltf(0.5 * (u0 + u1), v0))
            colors.append([float(rn.get("cloth", 0.0)), 0.85, 0.15, 1.0])
            joints.append(j4)
            weights.append(w4)
            last_row = (len(rings) - 1) * ring_cols
            cap_flip_end = False
            for si in range(n_seg):
                a = last_row + si
                b = last_row + si + 1
                if si == 0 and len(rings) > 1:
                    n_cap = np.cross(np.array(positions[a]) - np.array(positions[c_idx]),
                                     np.array(positions[b]) - np.array(positions[c_idx]))
                    axis_out = np.array(rings[-1]["center"]) - np.array(rings[-2]["center"])
                    cap_flip_end = float(np.dot(n_cap, axis_out)) < 0.0
                if cap_flip_end:
                    indices.extend([c_idx, b, a])
                else:
                    indices.extend([c_idx, a, b])

    return _pack_submesh(positions, uvs, colors, joints, weights, indices)


def build_ellipsoid(
    center: list[float],
    radii: list[float],
    joint_weights: list[tuple[int, float]],
    n_lat: int = 8,
    n_lon: int = 12,
    uv_box: tuple[float, float, float, float] = (0.52, 0.98, 0.02, 0.98),
    cloth_weight: float = 0.0,
    deform: callable = None,
) -> dict:
    """Construye un elipsoide orgánico cerrado (para globos oculares, orejas, lóbulos afro, etc.)."""
    cx, cy, cz = center
    rx, ry, rz = radii
    u0, u1, v0, v1 = uv_box
    j4, w4 = _normalize_weights(joint_weights)

    positions, uvs, colors, joints, weights, indices = [], [], [], [], [], []
    cols = n_lon + 1
    for i in range(n_lat + 1):
        lat_t = i / float(n_lat)
        theta = math.pi * lat_t  # 0 (polo +Y) -> pi (polo -Y)
        sin_t, cos_t = math.sin(theta), math.cos(theta)
        v_bl = v1 - lat_t * (v1 - v0)
        for j in range(cols):
            lon_t = j / float(n_lon)
            phi = 2.0 * math.pi * lon_t
            # phi=0 -> +Z para que los ojos proyecten su pupila justo al frente (+Z)
            px = cx + rx * sin_t * math.sin(phi)
            py = cy + ry * cos_t
            pz = cz + rz * sin_t * math.cos(phi)
            if deform is not None:
                dx, dy, dz = deform(theta, phi, (px, py, pz))
                px += dx
                py += dy
                pz += dz
            # Para los ojos: lon_t centrado en +Z (phi=0 o 2pi), mapeamos frente [0..pi/2, 3pi/2..2pi]
            u_val = u0 + ((math.sin(phi) * 0.5 + 0.5) if (u1 - u0) < 0.45 else lon_t) * (u1 - u0)
            positions.append([px, py, pz])
            uvs.append(uv_bl_to_gltf(u_val, v_bl))
            colors.append([cloth_weight, 0.85, 0.15, 1.0])
            joints.append(j4)
            weights.append(w4)

    for i in range(n_lat):
        for j in range(n_lon):
            p0 = i * cols + j
            p1 = p0 + 1
            p2 = p0 + cols
            p3 = p2 + 1
            indices.extend([p0, p1, p2, p1, p3, p2])

    return _pack_submesh(positions, uvs, colors, joints, weights, indices)


def build_torus_ring(
    center: list[float],
    major_r: float,
    minor_r: float,
    normal_axis: list[float],
    joint_weights: list[tuple[int, float]],
    n_major: int = 18,
    n_minor: int = 6,
    uv_box: tuple[float, float, float, float] = (0.54, 0.96, 0.04, 0.96),
    cloth_weight: float = 0.0,
) -> dict:
    """Construye un anillo toro 3D orientado perpendicularmente a `normal_axis` (para los drones astrolabio de V.A.R.-ZERO)."""
    cx, cy, cz = center
    u_vec, v_vec = _ortho_basis(np.array(normal_axis, dtype=np.float32))
    n_vec = np.array(normal_axis, dtype=np.float32)
    n_vec = n_vec / max(float(np.linalg.norm(n_vec)), 1e-8)

    u0, u1, v0, v1 = uv_box
    j4, w4 = _normalize_weights(joint_weights)

    positions, uvs, colors, joints, weights, indices = [], [], [], [], [], []
    cols = n_minor + 1
    for i in range(n_major + 1):
        maj_t = i / float(n_major)
        theta = 2.0 * math.pi * maj_t
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        rad_dir = u_vec * cos_t + v_vec * sin_t
        ring_center = np.array([cx, cy, cz], dtype=np.float32) + rad_dir * major_r
        u_val = u0 + maj_t * (u1 - u0)

        for j in range(cols):
            min_t = j / float(n_minor)
            phi = 2.0 * math.pi * min_t
            offset = (rad_dir * math.cos(phi) + n_vec * math.sin(phi)) * minor_r
            pos = ring_center + offset
            v_bl = v1 - min_t * (v1 - v0)
            positions.append([float(pos[0]), float(pos[1]), float(pos[2])])
            uvs.append(uv_bl_to_gltf(u_val, v_bl))
            colors.append([cloth_weight, 0.85, 0.15, 1.0])
            joints.append(j4)
            weights.append(w4)

    for i in range(n_major):
        for j in range(n_minor):
            p0 = i * cols + j
            p1 = p0 + 1
            p2 = p0 + cols
            p3 = p2 + 1
            indices.extend([p0, p2, p1, p1, p2, p3])

    return _pack_submesh(positions, uvs, colors, joints, weights, indices)


def build_box_submesh(
    center: list[float],
    half_extents: list[float],
    joint_idx: int,
    cloth_weight_top: float,
    cloth_weight_bottom: float,
) -> dict:
    """Usado por el escenario modular (`generate_stage_pitch_and_walls`)."""
    cx, cy, cz = center
    hx, hy, hz = half_extents

    faces = [
        ([cx - hx, cy - hy, cz + hz], [cx + hx, cy - hy, cz + hz], [cx + hx, cy + hy, cz + hz], [cx - hx, cy + hy, cz + hz], [0, 0, 1]),
        ([cx + hx, cy - hy, cz - hz], [cx - hx, cy - hy, cz - hz], [cx - hx, cy + hy, cz - hz], [cx + hx, cy + hy, cz - hz], [0, 0, -1]),
        ([cx + hx, cy - hy, cz + hz], [cx + hx, cy - hy, cz - hz], [cx + hx, cy + hy, cz - hz], [cx + hx, cy + hy, cz + hz], [1, 0, 0]),
        ([cx - hx, cy - hy, cz - hz], [cx - hx, cy - hy, cz + hz], [cx - hx, cy + hy, cz + hz], [cx - hx, cy + hy, cz - hz], [-1, 0, 0]),
        ([cx - hx, cy + hy, cz + hz], [cx + hx, cy + hy, cz + hz], [cx + hx, cy + hy, cz - hz], [cx - hx, cy + hy, cz - hz], [0, 1, 0]),
        ([cx - hx, cy - hy, cz - hz], [cx + hx, cy - hy, cz - hz], [cx - hx, cy - hy, cz + hz], [cx + hx, cy - hy, cz + hz], [0, -1, 0]),
    ]

    positions, normals, uvs, colors, joints, weights, indices = [], [], [], [], [], [], []
    for f_idx, (v0, v1, v2, v3, nrm) in enumerate(faces):
        base = f_idx * 4
        for v_local, v in enumerate([v0, v1, v2, v3]):
            positions.append(v)
            normals.append(nrm)
            u = 1.0 if v_local in (1, 2) else 0.0
            vv = 1.0 if v_local in (2, 3) else 0.0
            uvs.append([u, vv])
            cw = cloth_weight_top if v[1] >= cy else cloth_weight_bottom
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
        idx_list.append(sm["indices"].astype(np.uint32) + vertex_offset)
        vertex_offset += len(sm["positions"])

    idx_cat = np.concatenate(idx_list)
    idx_dtype = np.uint32 if vertex_offset > 65535 else np.uint16
    return {
        "positions": np.vstack(pos_list),
        "normals": np.vstack(nrm_list),
        "uvs": np.vstack(uv_list),
        "colors": np.vstack(col_list),
        "joints": np.vstack(jnt_list),
        "weights": np.vstack(wgt_list),
        "indices": idx_cat.astype(idx_dtype),
    }


# ============================================================================
# CONSTRUCTORES ANATÓMICOS POR PARTE CORPORAL Y ARQUETIPO
# ============================================================================

def _build_head_and_neck(spec: dict) -> list[dict]:
    h = float(spec["height"])
    b = float(spec["bulk"])
    hb = 0.55 + 0.45 * b  # Proporción craneal atlética sin cabezas gigantes
    is_boss = (spec["id"] == "SUPREME_JUDGE_BOSS")

    # Eje vertical estándar: basis_u = +X, basis_v = +Z
    bu = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    bv = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    def head_deform(phi: float, pos: tuple[float, float, float]) -> tuple[float, float, float]:
        px, py, pz = pos
        if pz <= 0.0:
            return (0.0, 0.0, 0.0)
        # Normalizamos altura facial dentro del cráneo
        fy = (py - 0.870 * h) / (0.126 * h)  # ~0 chin -> ~0.54 eyes -> ~1.0 crown
        fx = abs(px) / max(0.068 * hb, 0.02)

        # Arco superciliar (brow ridge) a fy ~ 0.62
        brow = math.exp(-((fy - 0.62) / 0.08) ** 2) * math.exp(-(fx / 0.72) ** 2)
        # Cuencas oculares a fy ~ 0.53, fx ~ 0.38
        eye_sock = math.exp(-(((fx - 0.38) / 0.24) ** 2 + ((fy - 0.53) / 0.08) ** 2))
        # Tabique nasal y punta de nariz (fy ~ 0.36..0.58)
        nose = math.exp(-((fx / 0.16) ** 2)) * math.exp(-((fy - 0.43) / 0.11) ** 2)
        nostrils = math.exp(-(((fx - 0.14) / 0.10) ** 2 + ((fy - 0.36) / 0.05) ** 2))
        # Pómulos
        cheek = math.exp(-(((fx - 0.58) / 0.26) ** 2 + ((fy - 0.38) / 0.10) ** 2))
        # Labios y mentón
        lips = math.exp(-((fx / 0.28) ** 2)) * math.exp(-((fy - 0.22) / 0.06) ** 2)
        chin = math.exp(-((fx / 0.26) ** 2)) * math.exp(-((fy - 0.08) / 0.07) ** 2)

        dz = (
            0.0065 * brow
            - 0.0070 * eye_sock
            + 0.0175 * nose
            + 0.0045 * nostrils
            + 0.0055 * cheek
            + 0.0060 * lips
            + 0.0085 * chin
        )
        if is_boss:
            dz += 0.005 * math.exp(-((fy - 0.55) / 0.07) ** 2)
        dx = 0.0040 * cheek * (1.0 if px >= 0 else -1.0)
        return (dx, 0.0, dz)

    # Cráneo atlético más ancho (+16% X/Z) y mandíbula más llena desde coronilla (0.996*h) hasta mentón (0.870*h)
    head_profile = [
        (0.996, 0.030 * hb, 0.034 * hb, 0.00, [(7, 1.0)]),
        (0.986, 0.053 * hb, 0.062 * hb, 0.08, [(7, 1.0)]),
        (0.970, 0.064 * hb, 0.074 * hb, 0.21, [(7, 1.0)]),
        (0.952, 0.068 * hb, 0.078 * hb, 0.36, [(7, 1.0)]),
        (0.938, 0.068 * hb, 0.078 * hb, 0.47, [(7, 1.0)]),  # Nivel ojos -> v_bl ~ 0.77..0.79
        (0.923, 0.066 * hb, 0.076 * hb, 0.59, [(7, 1.0)]),  # Pómulos / puente nasal
        (0.908, 0.062 * hb, 0.072 * hb, 0.71, [(7, 1.0)]),  # Punta nariz / bigote
        (0.895, 0.058 * hb, 0.068 * hb, 0.82, [(7, 0.92), (6, 0.08)]),  # Boca
        (0.882, 0.052 * hb, 0.060 * hb, 0.92, [(7, 0.85), (6, 0.15)]),  # Mandíbula atlética llena
        (0.870, 0.033 * hb, 0.042 * hb, 0.99, [(7, 0.75), (6, 0.25)]),  # Mentón
    ]
    head_rings = [
        {
            "center": [0.0, y_f * h, 0.002],
            "rx": rx,
            "ry": rz,
            "joints": jnts,
            "cloth": 0.0,
            "v_t": vt,
            "deform": head_deform,
        }
        for y_f, rx, rz, vt, jnts in head_profile
    ]
    head_mesh = build_lofted_prism(
        head_rings,
        n_seg=20,
        basis_u=bu,
        basis_v=bv,
        cap_start=True,
        cap_end=True,
        split_front_back_uv=True,
        uv_front_box=(0.02, 0.48, 0.52, 0.98),
        uv_back_box=(0.52, 0.98, 0.52, 0.98),
        reverse_back_u=True,
    )

    # Orejas esculpidas (Slot 0) ajustadas al cráneo ensanchado
    ear_l = build_ellipsoid(
        [0.068 * hb, 0.930 * h, -0.004],
        [0.010 * hb, 0.020 * h, 0.014 * hb],
        [(7, 1.0)],
        n_lat=4,
        n_lon=6,
        uv_box=(0.54, 0.74, 0.65, 0.85),
    )
    ear_r = build_ellipsoid(
        [-0.068 * hb, 0.930 * h, -0.004],
        [0.010 * hb, 0.020 * h, 0.014 * hb],
        [(7, 1.0)],
        n_lat=4,
        n_lon=6,
        uv_box=(0.76, 0.96, 0.65, 0.85),
    )

    # Cuello atlético más ancho (+24%) y compacto, conectando suavemente con el trapecio del torso
    neck_rings = [
        {"center": [0.0, 0.880 * h, -0.005], "rx": 0.047 * hb, "ry": 0.048 * hb, "joints": [(7, 0.55), (6, 0.45)], "cloth": 0.0, "v_t": 0.0},
        {"center": [0.0, 0.860 * h, -0.005], "rx": 0.049 * hb, "ry": 0.050 * hb, "joints": [(6, 0.85), (7, 0.15)], "cloth": 0.0, "v_t": 0.35},
        {"center": [0.0, 0.840 * h, -0.003], "rx": 0.058 * hb, "ry": 0.055 * hb, "joints": [(6, 0.60), (5, 0.40)], "cloth": 0.0, "v_t": 0.70},
        {"center": [0.0, 0.818 * h,  0.000], "rx": 0.072 * hb, "ry": 0.060 * hb, "joints": [(5, 0.75), (6, 0.25)], "cloth": 0.0, "v_t": 1.0},
    ]
    neck_mesh = build_lofted_prism(
        neck_rings,
        n_seg=12,
        basis_u=bu,
        basis_v=bv,
        cap_start=True,
        cap_end=True,
        split_front_back_uv=False,
        uv_full_box=(0.54, 0.96, 0.54, 0.72),
    )
    return [head_mesh, ear_l, ear_r, neck_mesh]


def _build_torso_jersey(spec: dict) -> list[dict]:
    h = float(spec["height"])
    b = float(spec["bulk"])
    is_boss = (spec["id"] == "SUPREME_JUDGE_BOSS")
    bu = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    bv = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    tb = 0.45 + 0.55 * b
    shoulder_w = 0.138 * h * (0.55 + 0.45 * b)
    chest_d = 0.080 * h * tb

    def torso_deform(phi: float, pos: tuple[float, float, float]) -> tuple[float, float, float]:
        px, py, pz = pos
        ax = abs(px) / max(shoulder_w, 0.05)
        # Escote en V limpio al frente del cuello (y >= 0.80*h)
        if pz > 0.0 and py > 0.80 * h:
            v_notch = math.exp(-((ax / 0.24) ** 2))
            return (0.0, -0.016 * h * v_notch, 0.0)
        # Relieve pectoral suave en frente
        if pz > 0.0 and 0.67 * h <= py <= 0.78 * h:
            pec = math.exp(-((ax - 0.36) / 0.30) ** 2) * math.exp(-(((py - 0.73 * h) / (0.048 * h)) ** 2))
            return (0.0, 0.0, 0.008 * pec * tb)
        # Caída vertical sutil exclusivamente en el borde inferior del faldón (sin ondas horizontales)
        if 0.51 * h <= py <= 0.56 * h:
            hem_env = max(0.0, (0.56 * h - py) / (0.05 * h))
            drape = math.sin(phi * 7.0) * 0.0022 * hem_env
            return (math.cos(phi) * drape, 0.0, math.sin(phi) * drape)
        return (0.0, 0.0, 0.0)

    # Cuello en V / Polo rim conectado a pendiente de trapecio
    collar_rings = [
        {"center": [0.0, 0.844 * h, 0.0], "rx": 0.062 * tb, "ry": 0.056 * tb, "joints": [(5, 0.75), (6, 0.25)], "cloth": 0.0416, "v_t": 0.00},
        {"center": [0.0, 0.828 * h, 0.0], "rx": 0.076 * tb, "ry": 0.064 * tb, "joints": [(5, 0.90), (6, 0.10)], "cloth": 0.0416, "v_t": 0.05, "deform": torso_deform},
    ]

    # Torso completo desde pendiente de hombros (0.834*h) hasta faldón holgado (0.520*h)
    torso_profile = [
        (0.834, shoulder_w * 0.76, chest_d * 0.78, 0.04, 0.0416, [(5, 0.95), (6, 0.05)]),
        (0.805, shoulder_w * 0.98, chest_d * 0.96, 0.12, 0.07,   [(5, 0.85), (8, 0.075), (13, 0.075)]),
        (0.755, shoulder_w * 1.00, chest_d * 1.04, 0.27, 0.15,   [(5, 0.75), (4, 0.25)]),
        (0.700, shoulder_w * 0.90, chest_d * 0.95, 0.44, 0.28,   [(4, 0.75), (5, 0.15), (3, 0.10)]),
        (0.648, shoulder_w * 0.85, chest_d * 0.90, 0.61, 0.46,   [(4, 0.40), (3, 0.60)]),
        (0.595, shoulder_w * 0.88, chest_d * 0.94, 0.78, 0.72,   [(3, 0.80), (34, 0.05), (35, 0.05), (36, 0.05), (37, 0.05)]),
        (0.550, shoulder_w * 0.93, chest_d * 0.99, 0.92, 0.92,   [(3, 0.65), (34, 0.09), (35, 0.09), (36, 0.085), (37, 0.085)]),
        (0.520, shoulder_w * 0.90, chest_d * 0.95, 1.00, 1.00,   [(3, 0.55), (34, 0.1125), (35, 0.1125), (36, 0.1125), (37, 0.1125)]),
    ]
    torso_rings = collar_rings + [
        {
            "center": [0.0, yf * h, 0.0],
            "rx": rx,
            "ry": rz,
            "joints": jnts,
            "cloth": cw,
            "v_t": vt,
            "deform": torso_deform,
        }
        for yf, rx, rz, vt, cw, jnts in torso_profile
    ]
    jersey_mesh = build_lofted_prism(
        torso_rings,
        n_seg=22,
        basis_u=bu,
        basis_v=bv,
        cap_start=False,
        cap_end=True,
        split_front_back_uv=True,
        uv_front_box=(0.02, 0.48, 0.52, 0.98),
        uv_back_box=(0.52, 0.98, 0.52, 0.98),
        reverse_back_u=True,
    )
    parts = [jersey_mesh]

    # Tapas anatómicas redondeadas de hombro/trapecio/deltoides conectando spine_03 -> upperarm_l/r
    for side, j_clav, j_uarm in [(1.0, 8, 9), (-1.0, 13, 14)]:
        parts.append(build_ellipsoid(
            [side * 0.128 * h, 0.835 * h, 0.0],
            [0.052 * h, 0.044 * h, 0.060 * tb],
            [(5, 0.35), (j_clav, 0.40), (j_uarm, 0.25)],
            n_lat=5,
            n_lon=8,
            uv_box=(0.04, 0.46, 0.28, 0.46),
            cloth_weight=0.05,
        ))

    if is_boss:
        # Hombreras blindadas adicionales para V.A.R.-ZERO
        for side, j_clav, j_uarm in [(1.0, 8, 9), (-1.0, 13, 14)]:
            pauldron = build_ellipsoid(
                [side * 0.155 * h, 0.858 * h, 0.0],
                [0.054 * h, 0.038 * h, 0.070 * tb],
                [(j_clav, 0.65), (j_uarm, 0.35)],
                n_lat=5,
                n_lon=8,
                uv_box=(0.04, 0.46, 0.28, 0.46),
                cloth_weight=0.0,
            )
            parts.append(pauldron)
        coat_rings = [
            {"center": [0.0, 0.535 * h, -0.005], "rx": shoulder_w * 0.94, "ry": chest_d * 0.98, "joints": [(2, 0.70), (3, 0.30)], "cloth": 0.20, "v_t": 0.0},
            {"center": [0.0, 0.420 * h, -0.015], "rx": shoulder_w * 1.06, "ry": chest_d * 1.08, "joints": [(2, 0.60), (18, 0.20), (23, 0.20)], "cloth": 0.65, "v_t": 0.5},
            {"center": [0.0, 0.300 * h, -0.022], "rx": shoulder_w * 1.12, "ry": chest_d * 1.14, "joints": [(2, 0.40), (18, 0.30), (23, 0.30)], "cloth": 1.00, "v_t": 1.0},
        ]
        parts.append(build_lofted_prism(
            coat_rings, n_seg=14, basis_u=bu, basis_v=bv,
            cap_start=False, cap_end=False, split_front_back_uv=True,
            uv_front_box=(0.52, 0.98, 0.27, 0.48), uv_back_box=(0.52, 0.98, 0.27, 0.48), reverse_back_u=True,
        ))
    return parts


def _build_arms_and_hands(spec: dict) -> tuple[list[dict], list[dict]]:
    """
    Construye Mangas + Bandas/Guantes (Slot 1) y Antebrazos/Manos (Slot 0) alineados
    con los pivotes exactos de `BONE_DEFS` (`upperarm` 0.14*h, `lowerarm` 0.29*h, `hand` 0.43*h, y=0.86*h).
    Retorna `(skin_parts, kit_parts)`.
    """
    h = float(spec["height"])
    b = float(spec["bulk"])
    tb = 0.50 + 0.50 * b
    is_keeper = spec["id"] in GOALKEEPER_IDS
    is_boss = (spec["id"] == "SUPREME_JUDGE_BOSS")
    has_armband = spec["id"] in CAPTAIN_ARMBAND_IDS

    skin_parts: list[dict] = []
    kit_parts: list[dict] = []

    for is_left in (True, False):
        s = 1.0 if is_left else -1.0
        j_clav = 8 if is_left else 13
        j_uarm = 9 if is_left else 14
        j_larm = 10 if is_left else 15
        j_twist = 11 if is_left else 16
        j_hand = 12 if is_left else 17

        # Eje de brazo a lo largo de ±X: basis_u = +Z (adelante), basis_v = +Y (arriba)
        axis_arm = np.array([s, 0.0, 0.0], dtype=np.float32)
        au, av = _ortho_basis(axis_arm)
        y_arm = 0.855 * h  # Conectado limpio al hombro superior

        # 1. Manga de Camiseta conectada suavemente del hombro/deltoides (0.095*h) hacia el brazo (y=0.850*h)
        if is_keeper or is_boss:
            sleeve_profile = [
                (0.098, 0.062 * tb, 0.056 * tb, 0.00, 0.05, [(5, 0.35), (j_clav, 0.40), (j_uarm, 0.25)]),
                (0.145, 0.060 * tb, 0.056 * tb, 0.18, 0.12, [(j_uarm, 0.80), (j_clav, 0.20)]),
                (0.215, 0.050 * tb, 0.048 * tb, 0.40, 0.25, [(j_uarm, 0.85), (j_larm, 0.15)]),
                (0.290, 0.043 * tb, 0.041 * tb, 0.62, 0.30, [(j_uarm, 0.45), (j_larm, 0.55)]),
                (0.360, 0.040 * tb, 0.038 * tb, 0.82, 0.35, [(j_larm, 0.50), (j_twist, 0.50)]),
                (0.418, 0.033 * tb, 0.031 * tb, 1.00, 0.15, [(j_twist, 0.45), (j_hand, 0.55)]),
            ]
        else:
            sleeve_profile = [
                (0.098, 0.064 * tb, 0.058 * tb, 0.00, 0.06, [(5, 0.35), (j_clav, 0.40), (j_uarm, 0.25)]),
                (0.145, 0.060 * tb, 0.056 * tb, 0.32, 0.22, [(j_uarm, 0.82), (j_clav, 0.18)]),
                (0.200, 0.054 * tb, 0.051 * tb, 0.68, 0.55, [(j_uarm, 0.95), (j_larm, 0.05)]),
                (0.246, 0.050 * tb, 0.048 * tb, 1.00, 0.85, [(j_uarm, 0.85), (j_larm, 0.15)]),
            ]
        sleeve_rings = [
            {
                "center": [s * xf * h, (0.830 if idx_r == 0 else (0.848 if idx_r == 1 else y_arm)) * (1.0 if idx_r > 1 else h), 0.0],
                "rx": rx, "ry": ry, "joints": jnts, "cloth": cw, "v_t": vt,
            }
            for idx_r, (xf, rx, ry, vt, cw, jnts) in enumerate(sleeve_profile)
        ]
        kit_parts.append(build_lofted_prism(
            sleeve_rings, n_seg=12, basis_u=au, basis_v=av,
            cap_start=True, cap_end=True, split_front_back_uv=False,
            uv_full_box=(0.02, 0.48, 0.27, 0.48),
        ))

        # Brazalete de Capitán en brazo izquierdo (TREN_EC)
        if has_armband and is_left:
            band_rings = [
                {"center": [s * 0.195 * h, y_arm, 0.0], "rx": 0.056 * tb, "ry": 0.054 * tb, "joints": [(j_uarm, 1.0)], "cloth": 0.0, "v_t": 0.0},
                {"center": [s * 0.232 * h, y_arm, 0.0], "rx": 0.055 * tb, "ry": 0.053 * tb, "joints": [(j_uarm, 1.0)], "cloth": 0.0, "v_t": 1.0},
            ]
            kit_parts.append(build_lofted_prism(
                band_rings, n_seg=12, basis_u=au, basis_v=av,
                cap_start=True, cap_end=True, split_front_back_uv=False,
                uv_full_box=(0.06, 0.44, 0.29, 0.46),
            ))

        # 2. Brazo inferior + Antebrazo (Slot 0 Skin, excepto arqueros/boss que llevan manga larga)
        if not (is_keeper or is_boss):
            arm_skin_profile = [
                (0.228, 0.040 * tb, 0.039 * tb, 0.00, [(j_uarm, 0.90), (j_larm, 0.10)]),
                (0.265, 0.037 * tb, 0.036 * tb, 0.20, [(j_uarm, 0.65), (j_larm, 0.35)]),
                (0.295, 0.035 * tb, 0.035 * tb, 0.36, [(j_uarm, 0.30), (j_larm, 0.70)]),  # Codo
                (0.335, 0.039 * tb, 0.038 * tb, 0.56, [(j_larm, 0.65), (j_twist, 0.35)]), # Vientre antebrazo
                (0.382, 0.031 * tb, 0.029 * tb, 0.80, [(j_twist, 0.70), (j_larm, 0.30)]),
                (0.425, 0.025 * tb, 0.022 * tb, 1.00, [(j_twist, 0.40), (j_hand, 0.60)]),  # Muñeca
            ]
            arm_rings = [
                {"center": [s * xf * h, y_arm, 0.0], "rx": rx, "ry": ry, "joints": jnts, "cloth": 0.0, "v_t": vt}
                for xf, rx, ry, vt, jnts in arm_skin_profile
            ]
            skin_parts.append(build_lofted_prism(
                arm_rings, n_seg=12, basis_u=au, basis_v=av,
                cap_start=True, cap_end=True, split_front_back_uv=False,
                uv_full_box=(0.03, 0.47, 0.26, 0.47),
            ))

        # 3. Mano esculpida o Guante de Arquero / Guantelete Boss
        glove_scale = 1.32 if (is_keeper or is_boss) else 1.0
        hand_profile = [
            (0.420, 0.026 * tb * glove_scale, 0.020 * tb * glove_scale, 0.00, [(j_hand, 0.75), (j_twist, 0.25)]),
            (0.445, 0.038 * tb * glove_scale, 0.017 * tb * glove_scale, 0.35, [(j_hand, 1.0)]),
            (0.478, 0.036 * tb * glove_scale, 0.014 * tb * glove_scale, 0.70, [(j_hand, 1.0)]),
            (0.506, 0.024 * tb * glove_scale, 0.009 * tb * glove_scale, 1.00, [(j_hand, 1.0)]),
        ]
        hand_rings = [
            {"center": [s * xf * h, y_arm - 0.004 * h, 0.003], "rx": rx, "ry": ry, "joints": jnts, "cloth": 0.0, "v_t": vt}
            for xf, rx, ry, vt, jnts in hand_profile
        ]
        # Pulgar apuntando adelante (+Z)
        thumb = build_ellipsoid(
            [s * 0.448 * h, y_arm - 0.004 * h, 0.034 * tb * glove_scale],
            [0.019 * h * glove_scale, 0.010 * tb * glove_scale, 0.014 * tb * glove_scale],
            [(j_hand, 1.0)],
            n_lat=4,
            n_lon=6,
            uv_box=(0.54, 0.96, 0.04, 0.21) if (is_keeper or is_boss) else (0.04, 0.46, 0.04, 0.23),
        )
        hand_mesh = build_lofted_prism(
            hand_rings, n_seg=10, basis_u=au, basis_v=av,
            cap_start=True, cap_end=True, split_front_back_uv=False,
            uv_full_box=(0.54, 0.96, 0.04, 0.21) if (is_keeper or is_boss) else (0.04, 0.46, 0.04, 0.23),
        )
        if is_keeper or is_boss:
            kit_parts.extend([hand_mesh, thumb])
        else:
            skin_parts.extend([hand_mesh, thumb])

    return skin_parts, kit_parts


def _build_legs_and_boots(spec: dict) -> tuple[list[dict], list[dict]]:
    """
    Construye Shorts, Calcetas Altas con puño y Botines con tapones (Slot 1) +
    Rodillas/Muslo inferior/Pantorrilla superior descubierta (Slot 0).
    """
    h = float(spec["height"])
    b = float(spec["bulk"])
    lb = 0.50 + 0.50 * b
    bu = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    bv = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    skin_parts: list[dict] = []
    kit_parts: list[dict] = []

    # Puente continuo de Pelvis/Cadera/Entrepierna de Shorts (Slot 1, 0.555*h -> 0.425*h)
    pelvis_rings = [
        {"center": [0.0, 0.555 * h, 0.0], "rx": 0.122 * h * lb, "ry": 0.082 * h * lb, "joints": [(2, 0.85), (3, 0.15)], "cloth": 0.08, "v_t": 0.00},
        {"center": [0.0, 0.515 * h, 0.0], "rx": 0.136 * h * lb, "ry": 0.088 * h * lb, "joints": [(2, 0.80), (18, 0.10), (23, 0.10)], "cloth": 0.15, "v_t": 0.30},
        {"center": [0.0, 0.475 * h, 0.0], "rx": 0.142 * h * lb, "ry": 0.088 * h * lb, "joints": [(2, 0.68), (18, 0.16), (23, 0.16)], "cloth": 0.22, "v_t": 0.65},
        {"center": [0.0, 0.432 * h, 0.0], "rx": 0.118 * h * lb, "ry": 0.072 * h * lb, "joints": [(2, 0.50), (18, 0.25), (23, 0.25)], "cloth": 0.28, "v_t": 1.00},
    ]
    kit_parts.append(build_lofted_prism(
        pelvis_rings, n_seg=16, basis_u=bu, basis_v=bv,
        cap_start=True, cap_end=True, split_front_back_uv=False,
        uv_full_box=(0.52, 0.98, 0.34, 0.48),
    ))

    for is_left in (True, False):
        s = 1.0 if is_left else -1.0
        lx = s * 0.09 * h
        j_thigh = 18 if is_left else 23
        j_calf = 19 if is_left else 24
        j_ctwist = 20 if is_left else 25
        j_foot = 21 if is_left else 26
        j_ball = 22 if is_left else 27

        # 1. Pierna de Shorts (Slot 1, emergiendo suavemente de la pelvis desde 0.515*h -> 0.345*h)
        shorts_leg_rings = [
            {"center": [lx * 0.92, 0.515 * h, 0.0], "rx": 0.078 * lb, "ry": 0.078 * lb, "joints": [(2, 0.45), (j_thigh, 0.55)], "cloth": 0.10, "v_t": 0.00},
            {"center": [lx,        0.460 * h, 0.0], "rx": 0.074 * lb, "ry": 0.074 * lb, "joints": [(j_thigh, 0.88), (2, 0.12)], "cloth": 0.28, "v_t": 0.35},
            {"center": [lx,        0.400 * h, 0.0], "rx": 0.068 * lb, "ry": 0.068 * lb, "joints": [(j_thigh, 1.0)],              "cloth": 0.48, "v_t": 0.70},
            {"center": [lx,        0.345 * h, 0.0], "rx": 0.064 * lb, "ry": 0.066 * lb, "joints": [(j_thigh, 0.90), (j_calf, 0.10)], "cloth": 0.65, "v_t": 1.00},
        ]
        kit_parts.append(build_lofted_prism(
            shorts_leg_rings, n_seg=12, basis_u=bu, basis_v=bv,
            cap_start=True, cap_end=True, split_front_back_uv=False,
            uv_full_box=(0.52, 0.98, 0.27, 0.46),
        ))

        # 2. Muslo inferior + Rodilla esculpida + Pantorrilla alta descubierta (Slot 0)
        def knee_deform(phi: float, pos: tuple[float, float, float]) -> tuple[float, float, float]:
            px, py, pz = pos
            if pz > 0.0 and 0.245 * h <= py <= 0.285 * h:
                # Rótula (patella) adelante
                pat = math.exp(-(((py - 0.265 * h) / (0.016 * h)) ** 2))
                return (0.0, 0.0, 0.007 * pat)
            return (0.0, 0.0, 0.0)

        bare_leg_rings = [
            {"center": [lx, 0.365 * h, 0.000], "rx": 0.050 * lb, "ry": 0.054 * lb, "joints": [(j_thigh, 1.0)], "cloth": 0.0, "v_t": 0.00},
            {"center": [lx, 0.320 * h, 0.003], "rx": 0.046 * lb, "ry": 0.049 * lb, "joints": [(j_thigh, 0.85), (j_calf, 0.15)], "cloth": 0.0, "v_t": 0.30},
            {"center": [lx, 0.282 * h, 0.004], "rx": 0.041 * lb, "ry": 0.043 * lb, "joints": [(j_thigh, 0.60), (j_calf, 0.40)], "cloth": 0.0, "v_t": 0.56, "deform": knee_deform},
            {"center": [lx, 0.260 * h, 0.004], "rx": 0.039 * lb, "ry": 0.041 * lb, "joints": [(j_thigh, 0.35), (j_calf, 0.65)], "cloth": 0.0, "v_t": 0.72, "deform": knee_deform}, # Rodilla
            {"center": [lx, 0.235 * h, 0.000], "rx": 0.038 * lb, "ry": 0.040 * lb, "joints": [(j_calf, 0.90), (j_thigh, 0.10)], "cloth": 0.0, "v_t": 0.90},
            {"center": [lx, 0.215 * h, 0.000], "rx": 0.038 * lb, "ry": 0.040 * lb, "joints": [(j_calf, 1.0)], "cloth": 0.0, "v_t": 1.00},
        ]
        skin_parts.append(build_lofted_prism(
            bare_leg_rings, n_seg=12, basis_u=bu, basis_v=bv,
            cap_start=True, cap_end=True, split_front_back_uv=False,
            uv_full_box=(0.52, 0.98, 0.03, 0.46),
        ))

        # 3. Calceta Alta de Fútbol con Puño Doble y Gemelos anatómicos (Slot 1)
        sock_rings = [
            {"center": [lx, 0.232 * h,  0.000], "rx": 0.042 * lb, "ry": 0.044 * lb, "joints": [(j_calf, 0.95), (j_thigh, 0.05)], "cloth": 0.0, "v_t": 0.00}, # Puño superior
            {"center": [lx, 0.220 * h,  0.000], "rx": 0.044 * lb, "ry": 0.046 * lb, "joints": [(j_calf, 1.0)], "cloth": 0.0, "v_t": 0.08}, # Relieve puño doblado
            {"center": [lx, 0.205 * h, -0.002], "rx": 0.041 * lb, "ry": 0.043 * lb, "joints": [(j_calf, 1.0)], "cloth": 0.0, "v_t": 0.18},
            {"center": [lx, 0.172 * h, -0.008], "rx": 0.044 * lb, "ry": 0.049 * lb, "joints": [(j_calf, 0.65), (j_ctwist, 0.35)], "cloth": 0.0, "v_t": 0.38}, # Vientre gemelos
            {"center": [lx, 0.132 * h, -0.005], "rx": 0.037 * lb, "ry": 0.041 * lb, "joints": [(j_ctwist, 0.70), (j_calf, 0.30)], "cloth": 0.0, "v_t": 0.60},
            {"center": [lx, 0.085 * h, -0.002], "rx": 0.031 * lb, "ry": 0.034 * lb, "joints": [(j_ctwist, 0.55), (j_foot, 0.45)], "cloth": 0.0, "v_t": 0.82},
            {"center": [lx, 0.046 * h,  0.000], "rx": 0.031 * lb, "ry": 0.035 * lb, "joints": [(j_foot, 0.85), (j_ctwist, 0.15)], "cloth": 0.0, "v_t": 1.00},
        ]
        kit_parts.append(build_lofted_prism(
            sock_rings, n_seg=12, basis_u=bu, basis_v=bv,
            cap_start=True, cap_end=True, split_front_back_uv=False,
            uv_full_box=(0.02, 0.48, 0.02, 0.23),
        ))

        # 4. Botín de Fútbol Contorneado (Slot 1) desde talón (-0.042*h) hasta puntera (+0.128*h)
        axis_foot = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        fu, fv = _ortho_basis(axis_foot)  # fu = +X, fv = +Y (approx)

        def boot_deform(phi: float, pos: tuple[float, float, float]) -> tuple[float, float, float]:
            px, py, pz = pos
            # Aplanar la suela en y ~ 0.008*h
            if py < 0.010 * h:
                return (0.0, 0.008 * h - py, 0.0)
            return (0.0, 0.0, 0.0)

        boot_rings = [
            {"center": [lx, 0.026 * h, -0.042 * h], "rx": 0.026 * lb, "ry": 0.020 * h, "joints": [(j_foot, 1.0)], "cloth": 0.0, "v_t": 0.00, "deform": boot_deform},
            {"center": [lx, 0.032 * h, -0.015 * h], "rx": 0.035 * lb, "ry": 0.028 * h, "joints": [(j_foot, 1.0)], "cloth": 0.0, "v_t": 0.20, "deform": boot_deform}, # Cuello tobillo
            {"center": [lx, 0.028 * h,  0.022 * h], "rx": 0.037 * lb, "ry": 0.024 * h, "joints": [(j_foot, 0.75), (j_ball, 0.25)], "cloth": 0.0, "v_t": 0.45, "deform": boot_deform}, # Empeine
            {"center": [lx, 0.022 * h,  0.065 * h], "rx": 0.038 * lb, "ry": 0.018 * h, "joints": [(j_ball, 0.70), (j_foot, 0.30)], "cloth": 0.0, "v_t": 0.70, "deform": boot_deform}, # Metatarso
            {"center": [lx, 0.017 * h,  0.104 * h], "rx": 0.032 * lb, "ry": 0.013 * h, "joints": [(j_ball, 0.95), (j_foot, 0.05)], "cloth": 0.0, "v_t": 0.88, "deform": boot_deform}, # Puntera
            {"center": [lx, 0.013 * h,  0.128 * h], "rx": 0.018 * lb, "ry": 0.008 * h, "joints": [(j_ball, 1.0)], "cloth": 0.0, "v_t": 1.00, "deform": boot_deform}, # Punta
        ]
        kit_parts.append(build_lofted_prism(
            boot_rings, n_seg=12, basis_u=fu, basis_v=fv,
            cap_start=True, cap_end=True, split_front_back_uv=False,
            uv_full_box=(0.52, 0.98, 0.02, 0.23),
        ))

        # Tapones (studs) en la suela del botín
        for stud_z, stud_x_off, j_st in [
            (-0.020 * h, -0.016 * lb, j_foot),
            (-0.020 * h,  0.016 * lb, j_foot),
            ( 0.085 * h, -0.018 * lb, j_ball),
            ( 0.085 * h,  0.018 * lb, j_ball),
        ]:
            kit_parts.append(build_ellipsoid(
                [lx + stud_x_off, 0.004 * h, stud_z],
                [0.006 * lb, 0.005 * h, 0.006 * lb],
                [(j_st, 1.0)],
                n_lat=3,
                n_lon=6,
                uv_box=(0.54, 0.96, 0.02, 0.10),
            ))

    return skin_parts, kit_parts


def _build_eyes_and_hair(spec: dict) -> list[dict]:
    """
    Slot 2: Ojos gemelos esféricos/biselados + Cejas / Visor + Cabello / Drones V.A.R. por arquetipo.
    """
    h = float(spec["height"])
    b = float(spec["bulk"])
    hb = 0.55 + 0.45 * b
    hair_style = str(spec["hair_style"])
    is_boss = (spec["id"] == "SUPREME_JUDGE_BOSS")
    bu = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    bv = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    parts: list[dict] = []

    if is_boss:
        # Visor cibernético luminoso sobre las cuencas oculares (Turnaround VAR_ZERO_BOSS)
        visor_rings = [
            {"center": [0.0, 0.946 * h, 0.022], "rx": 0.070 * hb, "ry": 0.066 * hb, "joints": [(7, 1.0)], "cloth": 0.0, "v_t": 0.0},
            {"center": [0.0, 0.930 * h, 0.022], "rx": 0.068 * hb, "ry": 0.064 * hb, "joints": [(7, 1.0)], "cloth": 0.0, "v_t": 1.0},
        ]
        parts.append(build_lofted_prism(
            visor_rings, n_seg=12, basis_u=bu, basis_v=bv,
            cap_start=True, cap_end=True, split_front_back_uv=False,
            uv_full_box=(0.08, 0.42, 0.58, 0.92),
        ))
        # Dos Drones Astrolabio Simétricos verticales mirando hacia la cámara sobre ambos hombros (±0.26*h, y=0.88*h)
        for j_drone, sx in [(28, 0.26 * h), (31, -0.26 * h)]:
            # Aro astrolabio exterior orientado al frente (+Z)
            parts.append(build_torus_ring(
                [sx, 0.88 * h, -0.02 * h],
                major_r=0.062 * h,
                minor_r=0.007 * h,
                normal_axis=[0.0, 0.12, 1.0],
                joint_weights=[(j_drone, 1.0)],
                n_major=18,
                n_minor=6,
                uv_box=(0.54, 0.96, 0.04, 0.96),
            ))
            # Aro gimbal interior inclinado
            parts.append(build_torus_ring(
                [sx, 0.88 * h, -0.02 * h],
                major_r=0.044 * h,
                minor_r=0.005 * h,
                normal_axis=[0.42 if sx > 0 else -0.42, 0.22, 0.88],
                joint_weights=[(j_drone, 1.0)],
                n_major=14,
                n_minor=5,
                uv_box=(0.54, 0.96, 0.04, 0.96),
            ))
            # Núcleo holográfico central
            parts.append(build_ellipsoid(
                [sx, 0.88 * h, -0.02 * h],
                [0.018 * h, 0.018 * h, 0.018 * h],
                [(j_drone, 1.0)],
                n_lat=5, n_lon=8, uv_box=(0.56, 0.94, 0.10, 0.90),
            ))
        return parts

    # Ojos esféricos en sus cuencas (Slot 2: u in [0.05, 0.45], v_bl in [0.55, 0.95])
    for side in (1.0, -1.0):
        parts.append(build_ellipsoid(
            [side * 0.025 * hb, 0.938 * h, 0.066 * hb],
            [0.009 * hb, 0.0075 * h, 0.009 * hb],
            [(7, 1.0)],
            n_lat=5,
            n_lon=8,
            uv_box=(0.05, 0.45, 0.55, 0.95),
        ))

    # Cabello por arquetipo (Slot 2: u in [0.52, 0.98], v_bl in [0.02, 0.98])
    hair_uv = (0.52, 0.98, 0.02, 0.98)

    if hair_style == "r9_crest":
        # FENOMENO_BR: Base rapada pegada al cráneo + icónica cresta media luna frontal en la frente
        crest_rings = [
            {"center": [0.0, 0.992 * h, 0.030 * hb], "rx": 0.042 * hb, "ry": 0.024 * hb, "joints": [(7, 0.7), (28, 0.3)], "cloth": 0.0, "v_t": 0.0},
            {"center": [0.0, 0.978 * h, 0.043 * hb], "rx": 0.050 * hb, "ry": 0.030 * hb, "joints": [(7, 0.7), (28, 0.3)], "cloth": 0.0, "v_t": 0.5},
            {"center": [0.0, 0.964 * h, 0.050 * hb], "rx": 0.046 * hb, "ry": 0.026 * hb, "joints": [(7, 0.8), (28, 0.2)], "cloth": 0.0, "v_t": 1.0},
        ]
        parts.append(build_lofted_prism(
            crest_rings, n_seg=12, basis_u=bu, basis_v=bv,
            cap_start=True, cap_end=True, split_front_back_uv=False, uv_full_box=hair_uv,
        ))
        parts.append(build_ellipsoid(
            [0.0, 0.948 * h, -0.008 * hb],
            [0.066 * hb, 0.046 * h, 0.072 * hb],
            [(7, 1.0)], n_lat=5, n_lon=10, uv_box=hair_uv,
        ))

    elif hair_style in ("golden_afro", "black_afro"):
        # PIBE_CO / LOCO_CO: Amplia corona afro redonda envolviendo sienes, orejas y nuca (sin pico cónico alto)
        parts.append(build_ellipsoid(
            [0.0, 0.972 * h, -0.014 * hb],
            [0.136 * hb, 0.074 * h, 0.126 * hb],
            [(7, 0.50), (28, 0.50)], n_lat=6, n_lon=10, uv_box=hair_uv, cloth_weight=0.25,
        ))
        lobe_offsets = [
            ( 0.000, 1.002, -0.020, 0.112, 0.054, 0.104, 28),
            ( 0.094, 0.960, -0.008, 0.076, 0.066, 0.088, 31),
            (-0.094, 0.960, -0.008, 0.076, 0.066, 0.088, 31),
            ( 0.074, 0.922, -0.062, 0.074, 0.062, 0.074, 29),
            (-0.074, 0.922, -0.062, 0.074, 0.062, 0.074, 32),
            ( 0.000, 0.906, -0.082, 0.088, 0.056, 0.066, 30),
        ]
        for ox, oy_f, oz, rx, ry_f, rz, j_id in lobe_offsets:
            parts.append(build_ellipsoid(
                [ox * hb, oy_f * h, oz * hb],
                [rx * hb, ry_f * h, rz * hb],
                [(j_id, 0.70), (7, 0.30)], n_lat=5, n_lon=7, uv_box=hair_uv, cloth_weight=0.55,
            ))
        if hair_style == "black_afro":
            casc_rings = [
                {"center": [0.0, 0.920 * h, -0.058 * hb], "rx": 0.110 * hb, "ry": 0.052 * hb, "joints": [(29, 0.6), (30, 0.4)], "cloth": 0.45, "v_t": 0.0},
                {"center": [0.0, 0.855 * h, -0.066 * hb], "rx": 0.114 * hb, "ry": 0.054 * hb, "joints": [(30, 0.8), (33, 0.2)], "cloth": 0.75, "v_t": 0.5},
                {"center": [0.0, 0.798 * h, -0.068 * hb], "rx": 0.100 * hb, "ry": 0.044 * hb, "joints": [(30, 0.9), (33, 0.1)], "cloth": 0.90, "v_t": 1.0},
            ]
            parts.append(build_lofted_prism(
                casc_rings, n_seg=12, basis_u=bu, basis_v=bv,
                cap_start=True, cap_end=True, split_front_back_uv=False, uv_full_box=hair_uv,
            ))

    elif hair_style == "king_mohawk":
        # REY_CL: Cresta punk alta de adelante hacia atrás + base rapada
        axis_mh = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        mu, mv = _ortho_basis(axis_mh)
        mh_rings = [
            {"center": [0.0, 0.988 * h,  0.052 * hb], "rx": 0.014 * hb, "ry": 0.022 * h, "joints": [(28, 0.6), (7, 0.4)], "cloth": 0.15, "v_t": 0.0},
            {"center": [0.0, 1.010 * h,  0.020 * hb], "rx": 0.017 * hb, "ry": 0.036 * h, "joints": [(28, 0.8), (7, 0.2)], "cloth": 0.30, "v_t": 0.30},
            {"center": [0.0, 1.008 * h, -0.022 * hb], "rx": 0.017 * hb, "ry": 0.036 * h, "joints": [(28, 0.8), (29, 0.2)], "cloth": 0.35, "v_t": 0.65},
            {"center": [0.0, 0.974 * h, -0.066 * hb], "rx": 0.014 * hb, "ry": 0.024 * h, "joints": [(29, 0.7), (7, 0.3)], "cloth": 0.25, "v_t": 1.00},
        ]
        parts.append(build_lofted_prism(
            mh_rings, n_seg=8, basis_u=mu, basis_v=mv,
            cap_start=True, cap_end=True, split_front_back_uv=False, uv_full_box=hair_uv,
        ))
        parts.append(build_ellipsoid(
            [0.0, 0.950 * h, -0.008 * hb],
            [0.066 * hb, 0.044 * h, 0.072 * hb],
            [(7, 1.0)], n_lat=5, n_lon=10, uv_box=hair_uv,
        ))

    elif hair_style in ("long_curls", "lion_mane", "golden_band", "diablo_mane"):
        # Cabello retro-90s largo / melena con sienes anchas enmarcando el rostro (Bruxo, Cañón, Matador, Diablo)
        crown = build_ellipsoid(
            [0.0, 0.958 * h, -0.008 * hb],
            [0.078 * hb, 0.052 * h, 0.082 * hb],
            [(7, 0.70), (28, 0.30)], n_lat=6, n_lon=12, uv_box=hair_uv, cloth_weight=0.10,
        )
        parts.append(crown)

        if hair_style in ("long_curls", "lion_mane", "golden_band"):
            band_rings = [
                {"center": [0.0, 0.964 * h, -0.002], "rx": 0.073 * hb, "ry": 0.080 * hb, "joints": [(7, 1.0)], "cloth": 0.0, "v_t": 0.0},
                {"center": [0.0, 0.952 * h, -0.002], "rx": 0.074 * hb, "ry": 0.081 * hb, "joints": [(7, 1.0)], "cloth": 0.0, "v_t": 1.0},
            ]
            parts.append(build_lofted_prism(
                band_rings, n_seg=14, basis_u=bu, basis_v=bv,
                cap_start=False, cap_end=False, split_front_back_uv=False, uv_full_box=hair_uv,
            ))

        mane_w = 0.094 if hair_style == "lion_mane" else (0.084 if hair_style in ("golden_band", "diablo_mane") else 0.076)
        mane_bot = 0.805 if hair_style in ("lion_mane", "golden_band") else 0.832
        mane_rings = [
            {"center": [0.0, 0.945 * h, -0.044 * hb], "rx": mane_w * hb,       "ry": 0.042 * hb, "joints": [(28, 0.7), (7, 0.3)],  "cloth": 0.25, "v_t": 0.0},
            {"center": [0.0, 0.895 * h, -0.058 * hb], "rx": (mane_w+0.012)*hb, "ry": 0.045 * hb, "joints": [(29, 0.7), (28, 0.3)], "cloth": 0.55, "v_t": 0.5},
            {"center": [0.0, mane_bot * h, -0.064 * hb], "rx": (mane_w+0.006)*hb, "ry": 0.036 * hb, "joints": [(30, 0.8), (29, 0.2)], "cloth": 0.85, "v_t": 1.0},
        ]
        parts.append(build_lofted_prism(
            mane_rings, n_seg=12, basis_u=bu, basis_v=bv,
            cap_start=True, cap_end=True, split_front_back_uv=False, uv_full_box=hair_uv,
        ))
        # Mechones laterales anchos enmarcando sienes y mejillas para los 4 estilos de melena (Bruxo/Cañón/Matador/Diablo)
        for side in (1.0, -1.0):
            side_rings = [
                {"center": [side * 0.072 * hb, 0.955 * h,  0.006 * hb], "rx": 0.024 * hb, "ry": 0.034 * hb, "joints": [(7, 0.5), (31, 0.5)], "cloth": 0.20, "v_t": 0.0},
                {"center": [side * 0.080 * hb, 0.902 * h, -0.002 * hb], "rx": 0.028 * hb, "ry": 0.038 * hb, "joints": [(32, 0.7), (7, 0.3)], "cloth": 0.55, "v_t": 0.5},
                {"center": [side * 0.082 * hb, 0.848 * h, -0.010 * hb], "rx": 0.022 * hb, "ry": 0.030 * hb, "joints": [(33, 0.8), (32, 0.2)], "cloth": 0.80, "v_t": 1.0},
            ]
            parts.append(build_lofted_prism(
                side_rings, n_seg=8, basis_u=bu, basis_v=bv,
                cap_start=True, cap_end=True, split_front_back_uv=False, uv_full_box=hair_uv,
            ))

    else:
        # Casquetes de pelo corto anatómicos (`short_messy`, `short_crop`, `bulldog_cut`, `classic_90s`)
        top_lift = 0.052 if hair_style in ("classic_90s", "short_messy") else 0.045
        rad_mul = 1.06 if hair_style == "classic_90s" else (1.04 if hair_style == "short_messy" else 1.01)
        parts.append(build_ellipsoid(
            [0.0, 0.955 * h, -0.010 * hb],
            [0.070 * hb * rad_mul, top_lift * h, 0.076 * hb * rad_mul],
            [(7, 0.80), (28, 0.20)], n_lat=6, n_lon=12, uv_box=hair_uv, cloth_weight=0.05,
        ))
        nape_rings = [
            {"center": [0.0, 0.946 * h, -0.040 * hb], "rx": 0.064 * hb, "ry": 0.034 * hb, "joints": [(7, 0.9), (28, 0.1)], "cloth": 0.05, "v_t": 0.0},
            {"center": [0.0, 0.902 * h, -0.048 * hb], "rx": 0.056 * hb, "ry": 0.028 * hb, "joints": [(7, 0.9), (29, 0.1)], "cloth": 0.10, "v_t": 1.0},
        ]
        parts.append(build_lofted_prism(
            nape_rings, n_seg=10, basis_u=bu, basis_v=bv,
            cap_start=True, cap_end=True, split_front_back_uv=False, uv_full_box=hair_uv,
        ))

    return parts


def build_fighter_three_slot_primitives(spec: dict) -> list[dict]:
    """
    Construye las 3 primitivas anatómicas del luchador:
      - Slot 0: M_FighterSkin_SSS
      - Slot 1: M_FighterKit_Retro90s_Cloth
      - Slot 2: M_FighterHairCards_And_Eyes
    """
    head_neck_skin = _build_head_and_neck(spec)
    torso_kit = _build_torso_jersey(spec)
    arm_skin, arm_kit = _build_arms_and_hands(spec)
    leg_skin, leg_kit = _build_legs_and_boots(spec)
    hair_and_eyes = _build_eyes_and_hair(spec)

    slot0_skin = merge_submeshes(head_neck_skin + arm_skin + leg_skin)
    slot1_kit = merge_submeshes(torso_kit + arm_kit + leg_kit)
    slot2_hair = merge_submeshes(hair_and_eyes)
    return [slot0_skin, slot1_kit, slot2_hair]


def embed_fighter_albedo_textures(gltf_json: dict, binary_blob: bytearray, fighter_id: str) -> list[str]:
    """
    Incrusta en el binario glTF las 3 texturas `Assets/TexturesPBR/Fighters/T_<ID>_{Skin,Kit,Hair}_Albedo.png`
    si existen en disco, actualizando `images`, `textures`, `samplers` y `materials[0..2]`.
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tex_dir = os.path.join(repo_root, "Assets", "TexturesPBR", "Fighters")

    # Soportar alias VAR_ZERO_BOSS además de SUPREME_JUDGE_BOSS
    id_candidates = [fighter_id]
    if fighter_id == "SUPREME_JUDGE_BOSS":
        id_candidates.append("VAR_ZERO_BOSS")

    slot_suffixes = [(0, "Skin"), (1, "Kit"), (2, "Hair")]
    images = list(gltf_json.get("images", []))
    textures = list(gltf_json.get("textures", []))
    samplers = list(gltf_json.get("samplers", []))
    buffer_views = gltf_json["bufferViews"]
    embedded_names: list[str] = []

    sampler_idx = None
    for slot_idx, suffix in slot_suffixes:
        found_path = None
        for fid in id_candidates:
            cand = os.path.join(tex_dir, f"T_{fid}_{suffix}_Albedo.png")
            if os.path.isfile(cand):
                found_path = cand
                break
        if not found_path:
            continue

        if sampler_idx is None:
            sampler_idx = len(samplers)
            samplers.append({
                "magFilter": 9729,  # LINEAR
                "minFilter": 9987,  # LINEAR_MIPMAP_LINEAR
                "wrapS": 33071,     # CLAMP_TO_EDGE
                "wrapT": 33071,     # CLAMP_TO_EDGE
            })

        with open(found_path, "rb") as tf:
            png_bytes = tf.read()

        while len(binary_blob) % 4 != 0:
            binary_blob.append(0)
        off = len(binary_blob)
        binary_blob.extend(png_bytes)
        bv_idx = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": off, "byteLength": len(png_bytes)})

        img_idx = len(images)
        images.append({
            "name": os.path.basename(found_path),
            "bufferView": bv_idx,
            "mimeType": "image/png",
        })
        tex_idx = len(textures)
        textures.append({
            "name": os.path.splitext(os.path.basename(found_path))[0],
            "sampler": sampler_idx,
            "source": img_idx,
        })

        pbr = gltf_json["materials"][slot_idx].setdefault("pbrMetallicRoughness", {})
        pbr["baseColorTexture"] = {"index": tex_idx, "texCoord": 0}
        pbr["baseColorFactor"] = [1.0, 1.0, 1.0, 1.0]
        embedded_names.append(os.path.basename(found_path))

    if images:
        gltf_json["images"] = images
    if textures:
        gltf_json["textures"] = textures
    if samplers:
        gltf_json["samplers"] = samplers
    return embedded_names


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

        idx_comp = 5125 if idx_arr.dtype == np.uint32 else 5123
        bv_idx = append_to_blob(idx_arr.tobytes(), 34963)
        acc_idx = len(accessors)
        accessors.append({"bufferView": bv_idx, "componentType": idx_comp, "count": len(idx_arr), "type": "SCALAR"})

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
    fps = 60.0
    animations = []

    def add_stepped_animation(anim_name: str, frame_indices: list[int], tracks: list[dict]) -> None:
        end_frame = int(frame_indices[-1])
        dense_frames = list(range(end_frame + 1))
        times = np.array([f / fps for f in dense_frames], dtype=np.float32)
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
            sparse_vals = tr["values"]
            dense_vals = []
            for f in dense_frames:
                k_idx = 0
                for idx_pos, kf in enumerate(frame_indices):
                    if kf <= f:
                        k_idx = idx_pos
                    else:
                        break
                dense_vals.append(sparse_vals[k_idx])

            vals = np.array(dense_vals, dtype=np.float32)
            bv_v = append_to_blob(vals.tobytes())
            acc_v = len(accessors)
            v_type = "VEC4" if path == "rotation" else "VEC3"
            accessors.append({"bufferView": bv_v, "componentType": 5126, "count": len(vals), "type": v_type})

            s_idx = len(samplers)
            samplers.append({"input": acc_t, "interpolation": "STEP", "output": acc_v})
            channels.append({"sampler": s_idx, "target": {"node": bone_id + 1, "path": path}})

        animations.append({"name": anim_name, "samplers": samplers, "channels": channels})

    # Clip 1: Anim_Idle (Guardia de potrero a 60Hz uniforme, 61 keyframes = 1.00s)
    add_stepped_animation("Anim_Idle", [0, 15, 30, 45, 60], [
        {"bone": 3, "path": "rotation", "values": [
            euler_xyz_to_quat(4.0, 12.0, 0.0),
            euler_xyz_to_quat(7.0, 12.0, 0.0),
            euler_xyz_to_quat(4.0, 12.0, 0.0),
            euler_xyz_to_quat(2.0, 12.0, 0.0),
            euler_xyz_to_quat(4.0, 12.0, 0.0),
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

    # Clip 4: Anim_623HP_BicycleKick (Chilena Antiaérea con exageración anime 1.25x en tibia/botín)
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

    # Clip 5: Anim_214SK_Scorpion (El Escorpión: arqueo dorsal y rechazo con ambos talones)
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
            "generator": "SouthAmericaFighters AAA Anatomical glTF 2.0 Pipeline (UE 5.8 + Chaos Cloth)"
        },
        "scene": 0,
        "scenes": [{"name": "FighterScene", "nodes": [0]}],
        "nodes": nodes,
        "skins": [{
            "name": f"Skeleton_{spec['id']}",
            "inverseBindMatrices": acc_ibm,
            "skeleton": 1,
            "joints": list(range(1, num_bones + 1))
        }],
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

    embedded_textures = embed_fighter_albedo_textures(gltf_json, binary_blob, spec["id"])
    write_glb_file(output_path, gltf_json, binary_blob)
    return {
        "FighterID": spec["id"],
        "DisplayName": spec["name"],
        "File": os.path.basename(output_path),
        "HeightMeters": height,
        "SkeletonJoints": num_bones,
        "Vertices": total_verts,
        "Triangles": total_tris,
        "EmbeddedAlbedoTextures": embedded_textures,
        "MaterialSlots": ["M_FighterSkin_SSS", "M_FighterKit_Retro90s_Cloth", "M_FighterHairCards_And_Eyes"],
        "SteppedAnimations60Hz": ["Anim_Idle", "Anim_5LP_Jab4f", "Anim_236SK_Shot", "Anim_623HP_BicycleKick", "Anim_214SK_Scorpion"]
    }


def write_glb_file(filepath: str, gltf_dict: dict, bin_chunk: bytearray) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    while len(bin_chunk) % 4 != 0:
        bin_chunk.append(0)

    gltf_dict["buffers"][0]["byteLength"] = len(bin_chunk)
    json_bytes = json.dumps(gltf_dict, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_chunk)
    with open(filepath, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total_length))
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        f.write(struct.pack("<II", len(bin_chunk), 0x004E4942))
        f.write(bin_chunk)


def generate_truncated_icosahedron_ball(glb_path: str, obj_path: str) -> dict:
    """Genera el balón clásico de 32 paneles (Icosaedro Truncado esférico de radio 0.22m) en .glb y .obj."""
    radius = 0.22
    lat_steps = 16
    lon_steps = 32

    positions, normals, uvs, colors, indices = [], [], [], [], []

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

    blob = bytearray()
    bvs, accs = [], []

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
        build_box_submesh([0.0, -0.10, 0.0], [12.5, 0.10, 8.0], 0, 0.0, 0.0),
        build_box_submesh([-12.5, 0.60, -1.5], [0.15, 0.60, 0.7], 0, 0.0, 0.0),
        build_box_submesh([-12.5, 0.60,  0.0], [0.15, 0.60, 0.7], 0, 0.0, 0.0),
        build_box_submesh([-12.5, 0.60,  1.5], [0.15, 0.60, 0.7], 0, 0.0, 0.0),
        build_box_submesh([12.5, 0.60, -1.5], [0.15, 0.60, 0.7], 0, 0.0, 0.0),
        build_box_submesh([12.5, 0.60,  0.0], [0.15, 0.60, 0.7], 0, 0.0, 0.0),
        build_box_submesh([12.5, 0.60,  1.5], [0.15, 0.60, 0.7], 0, 0.0, 0.0),
        build_box_submesh([-15.5, -0.12, 0.0], [3.0, 0.10, 8.0], 0, 0.0, 0.0),
        build_box_submesh([ 15.5, -0.12, 0.0], [3.0, 0.10, 8.0], 0, 0.0, 0.0),
    ]
    merged = merge_submeshes(submeshes)
    pos_arr = merged["positions"]
    nrm_arr = merged["normals"]
    uv_arr = merged["uvs"]
    idx_arr = merged["indices"]

    blob = bytearray()
    bvs, accs = [], []

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
        print(
            f"[OK] Luchador 3D glTF: SK_{spec['id']}.glb "
            f"({info['Vertices']}v/{info['Triangles']}t, {os.path.getsize(glb_file)} bytes)"
        )

    ball_glb = os.path.join(props_dir, "SM_Ball_TruncatedIcosahedron_32Panels.glb")
    ball_obj = os.path.join(props_dir, "SM_Ball_TruncatedIcosahedron_32Panels.obj")
    ball_info = generate_truncated_icosahedron_ball(ball_glb, ball_obj)
    print(f"[OK] Balón 32 Paneles: {os.path.basename(ball_glb)} & {os.path.basename(ball_obj)}")

    stage_glb = os.path.join(stages_dir, "SM_Stage_PitchAndDestructibleWalls.glb")
    stage_info = generate_stage_pitch_and_walls(stage_glb)
    print(f"[OK] Escenario Modular Wall-Break: {os.path.basename(stage_glb)}")

    manifest = {
        "SchemaVersion": "2.0.0-UE5.8-Anatomical-GLTF2",
        "TargetEngine": "Unreal Engine 5.8+ (Skinned Cloth & Stepped FGC Pipeline)",
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
            "LOD0_CloseUpAndGameplay": {"TargetTriangles": 16000, "MaxMorphTargets": 32, "ClothSimulation": True},
            "LOD1_MidRange": {"TargetTriangles": 8000, "MaxMorphTargets": 16, "ClothSimulation": True},
            "LOD2_WideCamera": {"TargetTriangles": 4000, "MaxMorphTargets": 0, "ClothSimulation": False},
            "LOD3_LowSpecFallback": {"TargetTriangles": 2000, "MaxMorphTargets": 0, "ClothSimulation": False},
            "UVChannels": {
                "UV0": "Contracted 3-Slot Atlas (Skin / Retro90s Kit / Hair & Eyes) upright glTF top-left",
                "UV1": "Non-overlapping Cycles Sculpt Bake (Normal & AO)"
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
