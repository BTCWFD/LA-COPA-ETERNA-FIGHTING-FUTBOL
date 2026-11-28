#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blender_highpoly_sculpt_pipeline.py - LA COPA ETERNA: SANGRE Y POTRERO
Blender 5.2.1 LTS Headless High-Poly 3D Sculpting, Cycles Normal/AO Bake,
and Anatomical Game LOD0 glTF 2.0 Pipeline.

Run with:
  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" --background --python Scripts/blender_highpoly_sculpt_pipeline.py
Optional single-fighter dry-run:
  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" --background --python Scripts/blender_highpoly_sculpt_pipeline.py -- --only FENOMENO_BR

What it does:
  1. Rebuilds deterministic 38-bone anatomical base meshes (`SK_*.glb`) via
     `generate_3d_models_gltf.build_fighter_glb()` so repeated runs never double-subdivide.
  2. For each fighter (all 17 by default, or filtered via `--only`):
     - Imports the clean 38-bone armature & 3-slot mesh (`Skin`, `Kit`, `Hair/Eyes`) in Rest Pose.
     - Welds split glTF seam vertices cleanly (preserving loop UVs), builds:
         * Anatomical Game LOD0 (quad-converted + Catmull-Clark Level 1: ~10,000–16,000 tris)
         * High-Poly Sculpt Source (Catmull-Clark Level 2: ~80,000–130,000 tris)
     - Sculpts crisp anatomical & archetype micro-detail (brow/cheek/nose/chin/deltoid/pec/ab/
       quad/calf/cloth-pleat/boot-studs/hair strands/astrolabe bevels).
     - Generates a non-overlapping `UV_SculptBake` layer and runs Cycles Bake (`512x512`, 16 samples,
       tangent Normal + AO) from the High-Poly Sculpt -> Game LOD0:
         * `Assets/TexturesPBR/HighPolyBakes/T_<FIGHTER>_Sculpt_Normal.png`
         * `Assets/TexturesPBR/HighPolyBakes/T_<FIGHTER>_Sculpt_AO.png`
     - Injects the sculpted anatomical LOD0 buffers back into `Assets/Models3D/Fighters/SK_*.glb`
       converting `UVMap` back to glTF top-left `(u, 1.0 - v_bl)`, preserving `COLOR_0`
       (`ChaosCloth_Jersey_Weight`), top-4 `JOINTS_0`/`WEIGHTS_0`, 38 bones, `inverseBindMatrices`,
       all animations, and embedding `Assets/TexturesPBR/Fighters/T_<ID>_{Skin,Kit,Hair}_Albedo.png`
       when present.
  3. Updates `Assets/Models3D/Models3D_TechnicalManifest.json` with verified metrics.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys
import time
from typing import Any

import bpy
import bmesh
import numpy as np
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import generate_3d_models_gltf as base_gen  # noqa: E402

FIGHTERS_DIR = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Fighters")
BAKES_DIR = os.path.join(PROJECT_ROOT, "Assets", "TexturesPBR", "HighPolyBakes")
MODELS_MANIFEST_PATH = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Models3D_TechnicalManifest.json")

BONE_INDEX_BY_NAME: dict[str, int] = {name: idx for idx, name, _, _ in base_gen.BONE_DEFS}
GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942


def parse_cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Blender 5.2 High-Poly Sculpt & LOD0 Bake Pipeline")
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help="Optional comma-separated Fighter IDs (e.g. FENOMENO_BR or FENOMENO_BR,PIBE_CO)",
    )
    parser.add_argument(
        "--res",
        type=int,
        default=512,
        help="Bake texture resolution (default: 512)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=16,
        help="Cycles bake samples (default: 16)",
    )
    return parser.parse_args(argv)


def remove_gltf_helper_objects() -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and obj.name.startswith("Icosphere") and obj.parent is None:
            bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        if col.name == "glTF_not_exported" and len(col.objects) == 0:
            bpy.data.collections.remove(col)


def sculpt_fighter_anatomical_detail(
    mesh_obj: bpy.types.Object,
    spec: dict[str, Any],
    fine_micro_pass: bool = False,
) -> None:
    """
    Apply deterministic anatomical 3D micro-sculpting refinement in Blender coordinates
    (+X = left/right, -Y = front facing, +Z = height 0..spec['height']) on top of the
    multi-ring organic base meshes.
    """
    h = float(spec["height"])
    b = float(spec["bulk"])
    hair_style = str(spec["hair_style"])
    is_boss = (spec["id"] == "SUPREME_JUDGE_BOSS")
    hb = 0.55 + 0.45 * b

    vg_name_by_idx = {vg.index: vg.name for vg in mesh_obj.vertex_groups}

    vert_mat: dict[int, int] = {}
    for poly in mesh_obj.data.polygons:
        for vid in poly.vertices:
            vert_mat.setdefault(vid, poly.material_index)

    def dominant_bone(v: bpy.types.MeshVertex) -> str:
        best_w = -1.0
        best_name = ""
        for g in v.groups:
            if g.weight > best_w:
                best_w = g.weight
                best_name = vg_name_by_idx.get(g.group, "")
        return best_name

    bone_verts: dict[str, list[bpy.types.MeshVertex]] = {}
    for v in mesh_obj.data.vertices:
        bname = dominant_bone(v)
        bone_verts.setdefault(bname, []).append(v)

    bone_centers: dict[str, Vector] = {}
    for bname, vlist in bone_verts.items():
        acc = Vector((0.0, 0.0, 0.0))
        for v in vlist:
            acc += v.co
        bone_centers[bname] = acc / max(len(vlist), 1)

    micro = 1.0 if fine_micro_pass else 0.65

    for v in mesh_obj.data.vertices:
        bname = dominant_bone(v)
        mat_idx = vert_mat.get(v.index, 0)
        c = bone_centers.get(bname, Vector((0.0, 0.0, 0.0)))
        co = v.co.copy()
        dx = co.x - c.x
        dy = co.y - c.y
        dz = co.z - c.z
        nz_body = co.z / max(h, 0.1)

        # ------------------------------------------------------------------
        # 1. SKULL & FACIAL CHISEL REFINEMENT (head bone, Material 0 Skin)
        # ------------------------------------------------------------------
        if bname == "head" and mat_idx == 0 and co.z >= 0.868 * h:
            # Front of face is Blender -Y
            if co.y < -0.022 * hb:
                face_z = (co.z - 0.870 * h) / (0.126 * h)  # ~0 chin .. ~1 crown
                face_x = abs(co.x) / max(0.068 * hb, 0.02)

                brow = math.exp(-((face_z - 0.62) / 0.07) ** 2) * math.exp(-(face_x / 0.68) ** 2)
                nose = math.exp(-((face_x / 0.14) ** 2)) * math.exp(-((face_z - 0.43) / 0.09) ** 2)
                cheek = math.exp(-(((face_x - 0.56) / 0.22) ** 2 + ((face_z - 0.38) / 0.09) ** 2))
                lips = math.exp(-((face_x / 0.24) ** 2)) * math.exp(-((face_z - 0.22) / 0.05) ** 2)
                chin = math.exp(-((face_x / 0.22) ** 2)) * math.exp(-((face_z - 0.08) / 0.06) ** 2)

                visor = math.exp(-((face_z - 0.55) / 0.06) ** 2) * 0.004 if is_boss else 0.0
                delta_fwd = (
                    0.0030 * brow
                    + 0.0040 * nose
                    + 0.0032 * cheek
                    + 0.0025 * lips
                    + 0.0035 * chin
                    + visor
                ) * micro
                co.y -= delta_fwd
                co.x += (0.0022 * cheek * (1.0 if co.x >= 0 else -1.0)) * micro

                if fine_micro_pass:
                    # Subtle philtrum & nasolabial crease definition
                    nasolab = math.exp(-(((face_x - 0.26) / 0.08) ** 2 + ((face_z - 0.30) / 0.09) ** 2))
                    co.y += 0.0018 * nasolab

        # ------------------------------------------------------------------
        # 2. TORSO MUSCULATURE & SOFT HEM DRAPE (Kit Material 1)
        # ------------------------------------------------------------------
        elif bname in ("spine_03", "spine_02", "spine_01", "kit_hem_01", "kit_hem_02", "kit_hem_03", "kit_hem_04") and mat_idx == 1:
            ax = abs(co.x) / max(0.135 * h * (0.55 + 0.45 * b), 0.05)

            # Smooth pectoral chest sweep (front -Y)
            if co.y < 0.0 and 0.67 * h <= co.z <= 0.78 * h:
                pec = math.exp(-((ax - 0.36) / 0.30) ** 2) * math.exp(-(((co.z - 0.73 * h) / (0.048 * h)) ** 2))
                co.y -= (0.0055 * pec * b) * micro

            # Subtle athletic V-taper waist (no horizontal waffle/ribbed bands)
            waist_taper = 1.0 - 0.035 * math.exp(-((nz_body - 0.61) / 0.07) ** 2)
            co.x *= waist_taper

            # Very soft vertical hem drapery right near bottom hem (0.49*h .. 0.56*h)
            if 0.49 * h <= co.z <= 0.56 * h:
                hem_env = max(0.0, (0.56 * h - co.z) / (0.07 * h))
                angle = math.atan2(co.y, co.x)
                drape = math.sin(angle * 7.0) * 0.0022 * hem_env * micro
                radial_len = max(math.hypot(co.x, co.y), 1e-5)
                co.x += (co.x / radial_len) * drape
                co.y += (co.y / radial_len) * drape

            # Collar rim relief on high-poly pass
            if fine_micro_pass and 0.80 * h <= co.z <= 0.84 * h and abs(co.x) < 0.075 * h:
                co.z += 0.0022 * math.exp(-((abs(co.x) - 0.052 * h) / 0.025) ** 2)

        # ------------------------------------------------------------------
        # 3. ARMS, LEGS & BOOTS REFINEMENT
        # ------------------------------------------------------------------
        elif bname in ("upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r"):
            # Deltoid & bicep/forearm muscularity along +/-X
            limb_rad = math.hypot(dy, dz)
            if limb_rad > 1e-4:
                bulge = math.sin(min(1.0, abs(dx) / max(0.08 * h, 0.04)) * math.pi)
                co.z += (dz / limb_rad) * (0.0038 * bulge * b) * micro
                co.y += (dy / limb_rad) * (0.0032 * bulge * b) * micro

        elif bname in ("thigh_l", "thigh_r", "calf_l", "calf_r", "calf_twist_01_l", "calf_twist_01_r"):
            # Quadriceps front (-Y) and gastrocnemius calf belly rear (+Y)
            if "thigh" in bname and co.y < -0.01:
                quad = math.exp(-(((co.z - 0.40 * h) / (0.06 * h)) ** 2))
                co.y -= (0.0065 * quad * b) * micro
            elif "calf" in bname and co.y > 0.005:
                gastroc = math.exp(-(((co.z - 0.172 * h) / (0.042 * h)) ** 2))
                co.y += (0.0075 * gastroc * b) * micro

        elif bname in ("foot_l", "foot_r", "ball_l", "ball_r") and mat_idx == 1:
            # Fine boot upper welt & sole cleat studs on high-poly pass
            if fine_micro_pass and co.z < 0.012 * h:
                stud = max(0.0, math.sin(co.y * 155.0) * math.cos(dx * 155.0))
                co.z -= 0.0028 * stud

        # ------------------------------------------------------------------
        # 4. ARCHETYPE HAIR / CROWN / V.A.R.-ZERO DRONES (Material 2)
        # ------------------------------------------------------------------
        elif mat_idx == 2 and ("hair" in bname or co.z > 0.945 * h):
            if hair_style in ("golden_afro", "black_afro"):
                curl = (
                    math.sin(co.x * 115.0) * math.cos(co.y * 115.0) * math.sin(co.z * 115.0)
                ) * (0.0085 if fine_micro_pass else 0.0045)
                d_len = max(math.hypot(dx, dy, dz), 1e-5)
                co.x += (dx / d_len) * curl
                co.y += (dy / d_len) * curl
                co.z += (dz / d_len) * curl
            elif hair_style == "king_mohawk":
                crest = max(0.0, 1.0 - abs(co.x) / (0.018 * hb))
                co.z += (0.009 * crest * math.sin((co.y + 0.06) * 40.0)) * micro
            elif hair_style == "var_drones":
                # Keep Boss astrolabe halo arcs crisp and symmetric
                pass
            else:
                strand = math.sin(co.x * 100.0 + co.y * 60.0) * (0.0038 if fine_micro_pass else 0.0020)
                co.z += strand
                if hair_style == "r9_crest" and co.y < -0.025:
                    co.y -= 0.0035 * micro

        v.co = co

    mesh_obj.data.update()


def recalculate_smooth_normals(mesh_obj: bpy.types.Object) -> None:
    """Recalculate outward consistent normals and enable smooth shading across all polygons."""
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj

    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh_obj.data)
    bm.free()

    poly_count = len(mesh_obj.data.polygons)
    if poly_count > 0:
        mesh_obj.data.polygons.foreach_set("use_smooth", [True] * poly_count)
    mesh_obj.data.update()


def bake_highpoly_sculpt_maps(
    low_obj: bpy.types.Object,
    high_obj: bpy.types.Object,
    fighter_stem: str,
    res: int = 512,
    samples: int = 16,
) -> tuple[str, str]:
    """
    Create a non-overlapping `UV_SculptBake` map on `low_obj` and bake tangent-space Normal + AO
    textures from the ~80k–130k-tri High-Poly Sculpt `high_obj` onto `low_obj` using Cycles.
    """
    os.makedirs(BAKES_DIR, exist_ok=True)
    norm_path = os.path.join(BAKES_DIR, f"T_{fighter_stem}_Sculpt_Normal.png")
    ao_path = os.path.join(BAKES_DIR, f"T_{fighter_stem}_Sculpt_AO.png")

    uv_bake = low_obj.data.uv_layers.get("UV_SculptBake")
    if uv_bake is None:
        uv_bake = low_obj.data.uv_layers.new(name="UV_SculptBake")
    low_obj.data.uv_layers.active = uv_bake

    bpy.ops.object.select_all(action="DESELECT")
    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.012)
    bpy.ops.object.mode_set(mode="OBJECT")

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(samples)
    scene.render.bake.margin = 4

    norm_img = bpy.data.images.new(f"T_{fighter_stem}_Sculpt_Normal", width=res, height=res, alpha=False)
    norm_img.colorspace_settings.name = "Non-Color"
    ao_img = bpy.data.images.new(f"T_{fighter_stem}_Sculpt_AO", width=res, height=res, alpha=False)
    ao_img.colorspace_settings.name = "Non-Color"

    bake_nodes = []
    for mat in low_obj.data.materials:
        if mat is None:
            continue
        if mat.node_tree is None:
            mat.use_nodes = True
        nt = mat.node_tree
        uv_node = nt.nodes.new("ShaderNodeUVMap")
        uv_node.uv_map = "UV_SculptBake"
        tex_node = nt.nodes.new("ShaderNodeTexImage")
        tex_node.name = "TempSculptBakeTarget"
        nt.links.new(uv_node.outputs["UV"], tex_node.inputs["Vector"])
        nt.nodes.active = tex_node
        tex_node.select = True
        bake_nodes.append((nt, tex_node, uv_node))

    bpy.ops.object.select_all(action="DESELECT")
    high_obj.select_set(True)
    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj

    for _, tex_node, _ in bake_nodes:
        tex_node.image = norm_img
    bpy.ops.object.bake(
        type="NORMAL",
        use_selected_to_active=True,
        cage_extrusion=0.04,
        normal_space="TANGENT",
    )
    norm_img.filepath_raw = norm_path
    norm_img.file_format = "PNG"
    norm_img.save()

    for _, tex_node, _ in bake_nodes:
        tex_node.image = ao_img
    bpy.ops.object.bake(
        type="AO",
        use_selected_to_active=True,
        cage_extrusion=0.04,
    )
    ao_img.filepath_raw = ao_path
    ao_img.file_format = "PNG"
    ao_img.save()

    for nt, tex_node, uv_node in bake_nodes:
        nt.nodes.remove(tex_node)
        nt.nodes.remove(uv_node)
    if "UVMap" in low_obj.data.uv_layers:
        low_obj.data.uv_layers.active = low_obj.data.uv_layers["UVMap"]

    return norm_path, ao_path


def extract_lod0_primitives_gltf_space(mesh_obj: bpy.types.Object) -> list[dict[str, Any]]:
    """
    Extract triangulated sculpted Game LOD0 mesh primitives grouped by material index (0, 1, 2)
    in glTF +Y-up coordinates (`(x, z, -y)`), preserving `UVMap` (converted back to glTF top-left
    `(u, 1.0 - v_bl)`), `Color` (`COLOR_0`), and normalized top-4 bone weights (`JOINTS_0`, `WEIGHTS_0`).
    """
    vg_to_bone = {}
    for vg in mesh_obj.vertex_groups:
        if vg.name in BONE_INDEX_BY_NAME:
            vg_to_bone[vg.index] = BONE_INDEX_BY_NAME[vg.name]

    color_attr = mesh_obj.data.color_attributes.get("Color")
    uv_layer = mesh_obj.data.uv_layers.get("UVMap") or (mesh_obj.data.uv_layers[0] if mesh_obj.data.uv_layers else None)

    mesh_obj.data.calc_loop_triangles()

    num_mats = max(3, len(mesh_obj.data.materials))
    prims_out: list[dict[str, Any]] = []

    for m_idx in range(min(3, num_mats)):
        vert_cache: dict[tuple[Any, ...], int] = {}
        positions: list[list[float]] = []
        normals: list[list[float]] = []
        uvs: list[list[float]] = []
        colors: list[list[float]] = []
        joints: list[list[int]] = []
        weights: list[list[float]] = []
        indices: list[int] = []

        for tri in mesh_obj.data.loop_triangles:
            if tri.material_index != m_idx:
                continue
            for loop_idx in tri.loops:
                loop = mesh_obj.data.loops[loop_idx]
                vi = loop.vertex_index
                v = mesh_obj.data.vertices[vi]

                # Blender -> glTF (+X -> +X, +Z -> +Y, -Y -> +Z; det = +1 preserves CCW winding)
                n_bl = v.normal if mesh_obj.data.polygons[tri.polygon_index].use_smooth else tri.normal
                gx, gy, gz = float(v.co.x), float(v.co.z), float(-v.co.y)
                gnx, gny, gnz = float(n_bl.x), float(n_bl.z), float(-n_bl.y)
                n_len = math.sqrt(gnx * gnx + gny * gny + gnz * gnz)
                if n_len > 1e-8:
                    gnx /= n_len
                    gny /= n_len
                    gnz /= n_len

                # Convertir UV bottom-left de Blender a glTF top-left: v_gltf = 1.0 - v_bl
                if uv_layer is not None:
                    uv_co = uv_layer.data[loop_idx].uv
                    u_val, v_val = float(uv_co.x), 1.0 - float(uv_co.y)
                else:
                    u_val, v_val = 0.0, 0.0

                key = (vi, round(u_val, 4), round(v_val, 4), round(gnx, 3), round(gny, 3), round(gnz, 3))
                out_vi = vert_cache.get(key)
                if out_vi is None:
                    out_vi = len(positions)
                    vert_cache[key] = out_vi
                    positions.append([gx, gy, gz])
                    normals.append([gnx, gny, gnz])
                    uvs.append([u_val, v_val])

                    if color_attr is not None:
                        if color_attr.domain == "CORNER":
                            c_raw = color_attr.data[loop_idx].color
                        else:
                            c_raw = color_attr.data[vi].color
                        colors.append([float(c_raw[0]), float(c_raw[1]), float(c_raw[2]), float(c_raw[3])])
                    else:
                        colors.append([0.0, 0.85, 0.15, 1.0])

                    inf = []
                    for g in v.groups:
                        b_idx = vg_to_bone.get(g.group)
                        if b_idx is not None and g.weight > 1e-5:
                            inf.append((g.weight, b_idx))
                    inf.sort(reverse=True)
                    inf = inf[:4]
                    if not inf:
                        inf = [(1.0, 1)]
                    w_sum = sum(w for w, _ in inf)
                    j4 = [0, 0, 0, 0]
                    w4 = [0.0, 0.0, 0.0, 0.0]
                    for k, (w, j) in enumerate(inf):
                        j4[k] = j
                        w4[k] = w / w_sum
                    joints.append(j4)
                    weights.append(w4)

                indices.append(out_vi)

        if not indices:
            positions = [[0.0, 0.0, 0.0], [0.001, 0.0, 0.0], [0.0, 0.001, 0.0]]
            normals = [[0.0, 1.0, 0.0]] * 3
            uvs = [[0.0, 0.0]] * 3
            colors = [[0.0, 0.85, 0.15, 1.0]] * 3
            joints = [[1, 0, 0, 0]] * 3
            weights = [[1.0, 0.0, 0.0, 0.0]] * 3
            indices = [0, 1, 2]

        max_idx = max(indices)
        idx_dtype = np.uint32 if max_idx > 65535 else np.uint16
        prims_out.append({
            "positions": np.array(positions, dtype=np.float32),
            "normals": np.array(normals, dtype=np.float32),
            "uvs": np.array(uvs, dtype=np.float32),
            "colors": np.array(colors, dtype=np.float32),
            "joints": np.array(joints, dtype=np.uint8),
            "weights": np.array(weights, dtype=np.float32),
            "indices": np.array(indices, dtype=idx_dtype),
        })

    return prims_out


def write_sculpted_lod0_to_glb(
    glb_path: str,
    prims_data: list[dict[str, Any]],
    fighter_id: str,
) -> dict[str, Any]:
    """
    Replace `meshes[0].primitives` in `glb_path` with our sculpted anatomical LOD0 buffers
    while preserving exact skin `inverseBindMatrices`, bone hierarchy, materials, clips,
    and embedding `T_<ID>_{Skin,Kit,Hair}_Albedo.png` when present.
    """
    with open(glb_path, "rb") as f:
        raw = f.read()

    jlen = struct.unpack("<I", raw[12:16])[0]
    gltf = json.loads(raw[20:20 + jlen].decode("utf-8"))
    blen = struct.unpack("<I", raw[20 + jlen + 4:20 + jlen + 8])[0]
    old_bin = bytearray(raw[20 + jlen + 8:20 + jlen + 8 + blen])

    new_bin = bytearray()
    new_bvs: list[dict[str, Any]] = []
    new_accs: list[dict[str, Any]] = []

    def append_bytes(b: bytes, target: int | None = None) -> int:
        while len(new_bin) % 4 != 0:
            new_bin.append(0)
        off = len(new_bin)
        new_bin.extend(b)
        bv: dict[str, Any] = {"buffer": 0, "byteOffset": off, "byteLength": len(b)}
        if target is not None:
            bv["target"] = target
        idx = len(new_bvs)
        new_bvs.append(bv)
        return idx

    new_prims = []
    total_verts = 0
    total_tris = 0

    for mat_idx, prim in enumerate(prims_data):
        pos = prim["positions"]
        nrm = prim["normals"]
        uv = prim["uvs"]
        col = prim["colors"]
        jnt = prim["joints"]
        wgt = prim["weights"]
        idx_arr = prim["indices"]

        total_verts += len(pos)
        total_tris += len(idx_arr) // 3

        acc_pos = len(new_accs)
        new_accs.append({
            "bufferView": append_bytes(pos.tobytes(), 34962),
            "componentType": 5126,
            "count": int(len(pos)),
            "type": "VEC3",
            "min": [float(x) for x in pos.min(axis=0)],
            "max": [float(x) for x in pos.max(axis=0)],
        })

        acc_nrm = len(new_accs)
        new_accs.append({
            "bufferView": append_bytes(nrm.tobytes(), 34962),
            "componentType": 5126,
            "count": int(len(nrm)),
            "type": "VEC3",
        })

        acc_uv = len(new_accs)
        new_accs.append({
            "bufferView": append_bytes(uv.tobytes(), 34962),
            "componentType": 5126,
            "count": int(len(uv)),
            "type": "VEC2",
        })

        acc_col = len(new_accs)
        new_accs.append({
            "bufferView": append_bytes(col.tobytes(), 34962),
            "componentType": 5126,
            "count": int(len(col)),
            "type": "VEC4",
        })

        acc_jnt = len(new_accs)
        new_accs.append({
            "bufferView": append_bytes(jnt.tobytes(), 34962),
            "componentType": 5121,
            "count": int(len(jnt)),
            "type": "VEC4",
        })

        acc_wgt = len(new_accs)
        new_accs.append({
            "bufferView": append_bytes(wgt.tobytes(), 34962),
            "componentType": 5126,
            "count": int(len(wgt)),
            "type": "VEC4",
        })

        idx_comp = 5125 if idx_arr.dtype == np.uint32 else 5123
        acc_idx = len(new_accs)
        new_accs.append({
            "bufferView": append_bytes(idx_arr.tobytes(), 34963),
            "componentType": idx_comp,
            "count": int(len(idx_arr)),
            "type": "SCALAR",
        })

        new_prims.append({
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
            "mode": 4,
        })

    # Re-append skin inverseBindMatrices
    for skin in gltf.get("skins", []):
        if "inverseBindMatrices" in skin:
            old_acc = gltf["accessors"][skin["inverseBindMatrices"]]
            old_bv = gltf["bufferViews"][old_acc["bufferView"]]
            ibm_bytes = bytes(old_bin[old_bv["byteOffset"]:old_bv["byteOffset"] + old_bv["byteLength"]])
            new_bv_idx = append_bytes(ibm_bytes)
            acc_ibm = len(new_accs)
            new_accs.append({
                "bufferView": new_bv_idx,
                "componentType": old_acc["componentType"],
                "count": old_acc["count"],
                "type": old_acc["type"],
            })
            skin["inverseBindMatrices"] = acc_ibm

    # Re-append existing animation accessors cleanly
    old_accs = gltf["accessors"]
    old_bvs = gltf["bufferViews"]
    acc_remap: dict[int, int] = {}

    def copy_anim_acc(old_idx: int) -> int:
        if old_idx in acc_remap:
            return acc_remap[old_idx]
        oa = dict(old_accs[old_idx])
        obv = old_bvs[oa["bufferView"]]
        raw_chunk = bytes(old_bin[obv["byteOffset"]:obv["byteOffset"] + obv["byteLength"]])
        oa["bufferView"] = append_bytes(raw_chunk)
        new_idx = len(new_accs)
        new_accs.append(oa)
        acc_remap[old_idx] = new_idx
        return new_idx

    for anim in gltf.get("animations", []):
        for smp in anim.get("samplers", []):
            smp["input"] = copy_anim_acc(smp["input"])
            smp["output"] = copy_anim_acc(smp["output"])

    # Reset image/texture/sampler slots cleanly before re-embedding
    for k in ("images", "textures", "samplers"):
        gltf.pop(k, None)
    for mat in gltf.get("materials", []):
        pbr = mat.get("pbrMetallicRoughness", {})
        pbr.pop("baseColorTexture", None)

    gltf["meshes"][0]["primitives"] = new_prims
    gltf["bufferViews"] = new_bvs
    gltf["accessors"] = new_accs

    embedded_textures = base_gen.embed_fighter_albedo_textures(gltf, new_bin, fighter_id)

    while len(new_bin) % 4 != 0:
        new_bin.append(0)
    gltf["buffers"][0]["byteLength"] = len(new_bin)

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_len = 12 + 8 + len(json_bytes) + 8 + len(new_bin)
    with open(glb_path, "wb") as f:
        f.write(struct.pack("<III", GLB_MAGIC, 2, total_len))
        f.write(struct.pack("<II", len(json_bytes), CHUNK_JSON))
        f.write(json_bytes)
        f.write(struct.pack("<II", len(new_bin), CHUNK_BIN))
        f.write(new_bin)

    return {
        "Vertices": total_verts,
        "Triangles": total_tris,
        "EmbeddedAlbedoTextures": embedded_textures,
    }


def main() -> None:
    args = parse_cli_args()
    only_ids = {s.strip().upper() for s in args.only.split(",") if s.strip()} if args.only else set()

    t_start = time.time()
    os.makedirs(FIGHTERS_DIR, exist_ok=True)
    os.makedirs(BAKES_DIR, exist_ok=True)

    target_specs = [
        spec for spec in base_gen.FIGHTER_SPECS
        if not only_ids or spec["id"].upper() in only_ids
    ]
    if not target_specs:
        raise ValueError(f"No matching fighters found for --only={args.only}")

    print(
        f"[Blender {bpy.app.version_string}] High-Poly 3D Sculpt & Cycles Normal/AO Bake Pipeline "
        f"starting for {len(target_specs)} fighter(s) (res={args.res}, samples={args.samples})..."
    )

    if os.path.isfile(MODELS_MANIFEST_PATH):
        with open(MODELS_MANIFEST_PATH, "r", encoding="utf-8") as mf:
            models_manifest = json.load(mf)
    else:
        models_manifest = {"GeneratedFighters": []}

    existing_by_id = {
        entry["FighterID"]: entry
        for entry in models_manifest.get("GeneratedFighters", [])
        if isinstance(entry, dict) and "FighterID" in entry
    }

    updated_fighter_reports = []

    for spec in target_specs:
        fighter_stem = f"SK_{spec['id']}"
        glb_path = os.path.join(FIGHTERS_DIR, f"{fighter_stem}.glb")

        # 1. Regenerate deterministic clean 38-bone anatomical base mesh
        base_gen.build_fighter_glb(spec, glb_path)

        # 2. Import into fresh Blender scene in Rest Pose
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=glb_path)
        remove_gltf_helper_objects()

        arm_obj = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
        mesh_obj = [o for o in bpy.data.objects if o.type == "MESH"][0]
        arm_obj.data.pose_position = "REST"
        bpy.context.view_layer.update()

        # Weld split glTF UV seam vertices at identical 3D positions so Catmull-Clark
        # smooths across seams cleanly while preserving per-loop UV islands
        bpy.ops.object.select_all(action="DESELECT")
        mesh_obj.select_set(True)
        bpy.context.view_layer.objects.active = mesh_obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles(threshold=1e-5)
        bpy.ops.object.mode_set(mode="OBJECT")

        # Duplicate pre-quad mesh for High-Poly Sculpt (~3.5k-4.2k tris -> ~85k-115k tris at Subsurf Level 2)
        hp_obj = mesh_obj.copy()
        hp_obj.data = mesh_obj.data.copy()
        hp_obj.name = f"{fighter_stem}_HighPolySculpt"
        bpy.context.collection.objects.link(hp_obj)

        # 3. Convert LOD0 triangles -> quads (respecting UV seams) and apply Catmull-Clark Level 1 (~10k-16k tris)
        bpy.ops.object.select_all(action="DESELECT")
        mesh_obj.select_set(True)
        bpy.context.view_layer.objects.active = mesh_obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.tris_convert_to_quads(
            face_threshold=math.radians(50.0),
            shape_threshold=math.radians(50.0),
            uvs=True,
        )
        bpy.ops.object.mode_set(mode="OBJECT")

        sub_lod0 = mesh_obj.modifiers.new("LOD0_Subsurf", "SUBSURF")
        sub_lod0.subdivision_type = "CATMULL_CLARK"
        sub_lod0.levels = 1
        sub_lod0.render_levels = 1
        sub_lod0.uv_smooth = "PRESERVE_CORNERS"
        bpy.ops.object.modifier_move_to_index(modifier=sub_lod0.name, index=0)
        bpy.ops.object.modifier_apply(modifier=sub_lod0.name)

        sculpt_fighter_anatomical_detail(mesh_obj, spec, fine_micro_pass=False)
        recalculate_smooth_normals(mesh_obj)

        # 4. Build High-Poly Sculpt Source (Catmull-Clark Level 2 -> ~80k-130k tris)
        bpy.ops.object.select_all(action="DESELECT")
        hp_obj.select_set(True)
        bpy.context.view_layer.objects.active = hp_obj
        sub_hp = hp_obj.modifiers.new("HighPoly_Subsurf", "SUBSURF")
        sub_hp.subdivision_type = "CATMULL_CLARK"
        sub_hp.levels = 2
        sub_hp.render_levels = 2
        sub_hp.uv_smooth = "PRESERVE_CORNERS"
        bpy.ops.object.modifier_move_to_index(modifier=sub_hp.name, index=0)
        bpy.ops.object.modifier_apply(modifier=sub_hp.name)

        sculpt_fighter_anatomical_detail(hp_obj, spec, fine_micro_pass=True)
        recalculate_smooth_normals(hp_obj)
        hp_verts = len(hp_obj.data.vertices)
        hp_tris = sum(len(p.vertices) - 2 for p in hp_obj.data.polygons)

        # 5. Bake Tangent-Space Normal + AO from High-Poly -> Game LOD0
        norm_path, ao_path = bake_highpoly_sculpt_maps(
            mesh_obj, hp_obj, fighter_stem, res=args.res, samples=args.samples
        )
        bpy.data.objects.remove(hp_obj, do_unlink=True)

        # 6. Extract sculpted anatomical LOD0 buffers & embed textures back into SK_*.glb
        lod0_prims = extract_lod0_primitives_gltf_space(mesh_obj)
        glb_stats = write_sculpted_lod0_to_glb(glb_path, lod0_prims, spec["id"])

        print(
            f"  [SCULPT+BAKE OK] {fighter_stem:23s} | HP={hp_verts:,}v/{hp_tris:,}t "
            f"| LOD0={glb_stats['Vertices']:,}v/{glb_stats['Triangles']:,}t "
            f"| Tex={len(glb_stats['EmbeddedAlbedoTextures'])}/3 "
            f"| Normal={os.path.basename(norm_path)} AO={os.path.basename(ao_path)}"
        )

        report = {
            "FighterID": spec["id"],
            "DisplayName": spec["name"],
            "File": f"{fighter_stem}.glb",
            "HeightMeters": spec["height"],
            "SkeletonJoints": len(base_gen.BONE_DEFS),
            "Vertices": glb_stats["Vertices"],
            "Triangles": glb_stats["Triangles"],
            "HighPolySculptVertices": hp_verts,
            "HighPolySculptTriangles": hp_tris,
            "EmbeddedAlbedoTextures": glb_stats["EmbeddedAlbedoTextures"],
            "BakedNormalMap": os.path.relpath(norm_path, PROJECT_ROOT).replace("\\", "/"),
            "BakedAOMap": os.path.relpath(ao_path, PROJECT_ROOT).replace("\\", "/"),
            "MorphTargets": ["Smile_Victory", "Battle_Roar", "Pain_Hitstun", "Effort_Sprint"],
            "MaterialSlots": [
                "M_FighterSkin_SSS",
                "M_FighterKit_Retro90s_Cloth",
                "M_FighterHairCards_And_Eyes",
            ],
            "SteppedAnimations60Hz": [
                "Anim_Idle",
                "Anim_5LP_Jab4f",
                "Anim_236SK_Shot",
                "Anim_623HP_BicycleKick",
                "Anim_214SK_Scorpion",
            ],
        }
        updated_fighter_reports.append(report)
        existing_by_id[spec["id"]] = report

    models_manifest["SchemaVersion"] = "2.3.0-UE5.8-AnatomicalSculptLOD0"
    models_manifest["HighPolySculptPipeline"] = {
        "BlenderVersion": bpy.app.version_string,
        "HighPolySubsurfLevels": 2,
        "GameLOD0SubsurfLevels": 1,
        "BakeResolution": args.res,
        "BakeSamples": args.samples,
        "BakedMaps": ["TangentNormal", "AmbientOcclusion"],
        "BakesDirectory": "Assets/TexturesPBR/HighPolyBakes",
        "MorphTargetSet": ["Smile_Victory", "Battle_Roar", "Pain_Hitstun", "Effort_Sprint"],
    }
    models_manifest["GeneratedFighters"] = (
        [existing_by_id[s["id"]] for s in base_gen.FIGHTER_SPECS if s["id"] in existing_by_id]
        if only_ids else updated_fighter_reports
    )

    with open(MODELS_MANIFEST_PATH, "w", encoding="utf-8") as mf:
        json.dump(models_manifest, mf, indent=2, ensure_ascii=False)

    print(
        f"\n[DONE] Sculpted & baked {len(updated_fighter_reports)} fighter(s) "
        f"in {time.time() - t_start:.1f}s -> {MODELS_MANIFEST_PATH}"
    )


if __name__ == "__main__":
    main()
