#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blender_fighters_ue5_pipeline.py - LA COPA ETERNA: SANGRE Y POTRERO
Blender 5.2+ headless UE 5.4+ Fighters Production Pipeline (`bpy`).

Run with:
  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" --background --python Scripts/blender_fighters_ue5_pipeline.py

What it does:
  1. Discovers all 17 fighter `.glb` files in `Assets/Models3D/Fighters/SK_*.glb`.
  2. For each fighter (in a clean scene to guarantee zero cross-contamination):
     - Imports the `.glb` (Armature, Mesh, UV maps, skin weights, and all 10 embedded 60 FPS animations).
     - Removes glTF helper objects (e.g., `Icosphere` bone custom-shape artifacts).
     - Applies Subdivision Surface (`levels=1`, Catmull-Clark, `PRESERVE_CORNERS` UV smoothing)
       in Rest Pose above the Armature modifier so skin weights and UVs are preserved cleanly.
     - Enforces smooth shading (`use_smooth = True`) on all faces and verifies clean UV maps.
     - Binds matching PBR textures from `Assets/TexturesPBR/`:
         * `T_Kit_<Country>_Albedo.png` (sRGB) -> Base Color
         * `T_FighterKit_ORM.png` (Non-Color) -> Roughness (G) & Metallic (B)
         * `T_Retro90s_Jacquard_Normal.png` (Non-Color) -> Normal Map (Kit)
         * `T_Skin_MicroPores_Normal.png` (Non-Color) -> Normal Map (Skin)
     - Paints the UE5 Chaos Cloth Vertex Group `ChaosCloth_Jersey_Weight`:
         * `0.0` pinned on shoulders / collar (`z >= z_collar`)
         * Smooth linear gradient down to `1.0` free hem (`12.0 cm` max distance at `z <= z_hem`)
     - Exports UE 5.4+-ready `.fbx` (`FBX_SCALE_ALL`, `add_leaf_bones=False`, `bake_anim=True`)
       into `Assets/BlenderProduction/Fighters/SK_*.fbx`.
  3. Assembles all 17 enhanced fighters into a lit 2-row showcase scene and saves
     `Assets/BlenderProduction/Fighters/Master_17Fighters_Showcase.blend`.
  4. Writes `Assets/BlenderProduction/Fighters/BlenderFighters_Manifest.json` with exact
     file sizes, vertex/face/bone/action counts, `ChaosCloth_Jersey_Weight` verification,
     bound texture paths, and Blender version.
"""

from __future__ import annotations

import glob
import json
import math
import os
import sys
from datetime import datetime, timezone
from typing import Any

import bpy
from mathutils import Vector

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_FIGHTERS_DIR = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Fighters")
TEXTURES_DIR = os.path.join(PROJECT_ROOT, "Assets", "TexturesPBR")
OUTPUT_FIGHTERS_DIR = os.path.join(PROJECT_ROOT, "Assets", "BlenderProduction", "Fighters")
SHOWCASE_BLEND_PATH = os.path.join(OUTPUT_FIGHTERS_DIR, "Master_17Fighters_Showcase.blend")
MANIFEST_PATH = os.path.join(OUTPUT_FIGHTERS_DIR, "BlenderFighters_Manifest.json")

CHAOS_CLOTH_VG_NAME = "ChaosCloth_Jersey_Weight"
CHAOS_CLOTH_MAX_DISTANCE_CM = 12.0

COUNTRY_CODE_TO_KIT_ALBEDO: dict[str, str] = {
    "AR": "T_Kit_Argentina_Albedo.png",
    "BO": "T_Kit_Bolivia_Albedo.png",
    "BR": "T_Kit_Brazil_Albedo.png",
    "CL": "T_Kit_Chile_Albedo.png",
    "CO": "T_Kit_Colombia_Albedo.png",
    "EC": "T_Kit_Ecuador_Albedo.png",
    "FR": "T_Kit_France_Albedo.png",
    "PE": "T_Kit_Peru_Albedo.png",
    "PY": "T_Kit_Paraguay_Albedo.png",
    "UY": "T_Kit_Uruguay_Albedo.png",
    "VE": "T_Kit_Venezuela_Albedo.png",
    "BOSS": "T_Kit_VARBoss_Albedo.png",
}


def resolve_texture_path(*candidates: str) -> str | None:
    """Return the first existing texture path in `Assets/TexturesPBR/`."""
    for name in candidates:
        full_path = os.path.join(TEXTURES_DIR, name)
        if os.path.isfile(full_path):
            return full_path
    return None


def resolve_kit_albedo_for_fighter(fighter_stem: str) -> str | None:
    """Map fighter stem (e.g. `SK_PIBE_CO`, `SK_SUPREME_JUDGE_BOSS`) to its country kit albedo."""
    suffix = fighter_stem.rsplit("_", 1)[-1].upper()
    filename = COUNTRY_CODE_TO_KIT_ALBEDO.get(suffix)
    if filename:
        return resolve_texture_path(filename)
    return None


def load_image_cached(filepath: str, colorspace: str) -> bpy.types.Image:
    """Load an image into Blender and configure its color space cleanly."""
    img = bpy.data.images.load(filepath, check_existing=True)
    try:
        img.colorspace_settings.name = colorspace
    except Exception:
        pass
    return img


def get_material_node_tree(mat: bpy.types.Material) -> bpy.types.NodeTree:
    """Return a material's node tree without triggering Blender 5.2+ `use_nodes` deprecation warnings."""
    nt = mat.node_tree
    if nt is None:
        mat.use_nodes = True
        nt = mat.node_tree
    return nt


def ensure_principled_bsdf(nt: bpy.types.NodeTree) -> tuple[bpy.types.Node, bpy.types.Node]:
    """Find or create a Principled BSDF and Material Output node in the given node tree."""
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    output = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if output is None:
        output = nt.nodes.new("ShaderNodeOutputMaterial")
        output.location = (400, 0)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (100, 0)
        nt.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return bsdf, output


def bind_pbr_materials(
    mesh_obj: bpy.types.Object,
    fighter_stem: str,
    unique_suffix: str | None = None,
) -> dict[str, str]:
    """
    Bind country kit albedo, retro 90s jacquard normal, ORM, and skin micro-pores normal
    textures from `Assets/TexturesPBR/` onto the fighter's materials.
    Returns a dict of bound texture names for the manifest.
    """
    kit_albedo_path = resolve_kit_albedo_for_fighter(fighter_stem)
    kit_normal_path = resolve_texture_path("T_Kit_Jacquard_Normal.png", "T_Retro90s_Jacquard_Normal.png")
    kit_orm_path = resolve_texture_path("T_FighterKit_ORM.png")
    skin_normal_path = resolve_texture_path("T_Skin_MicroPores_Normal.png")

    bound_textures: dict[str, str] = {}

    for slot in mesh_obj.material_slots:
        mat = slot.material
        if mat is None:
            continue

        if unique_suffix:
            mat = mat.copy()
            mat.name = f"{slot.material.name}_{unique_suffix}"
            slot.material = mat

        mat_name_lower = mat.name.lower()
        nt = get_material_node_tree(mat)
        bsdf, _ = ensure_principled_bsdf(nt)

        if "kit" in mat_name_lower or "cloth" in mat_name_lower:
            # Base Color: Country Kit Albedo
            if kit_albedo_path:
                tex_albedo = nt.nodes.new("ShaderNodeTexImage")
                tex_albedo.label = "Kit_Albedo"
                tex_albedo.location = (-500, 260)
                tex_albedo.image = load_image_cached(kit_albedo_path, "sRGB")
                nt.links.new(tex_albedo.outputs["Color"], bsdf.inputs["Base Color"])
                bound_textures["kit_albedo"] = os.path.basename(kit_albedo_path)

            # ORM: Roughness (G) and Metallic (B)
            if kit_orm_path:
                tex_orm = nt.nodes.new("ShaderNodeTexImage")
                tex_orm.label = "Kit_ORM"
                tex_orm.location = (-500, 0)
                tex_orm.image = load_image_cached(kit_orm_path, "Non-Color")
                sep = nt.nodes.new("ShaderNodeSeparateColor")
                sep.location = (-220, 0)
                nt.links.new(tex_orm.outputs["Color"], sep.inputs["Color"])
                if "Roughness" in bsdf.inputs:
                    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
                if "Metallic" in bsdf.inputs:
                    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
                bound_textures["kit_orm"] = os.path.basename(kit_orm_path)

            # Normal: Retro 90s Jacquard Normal
            if kit_normal_path:
                tex_norm = nt.nodes.new("ShaderNodeTexImage")
                tex_norm.label = "Kit_Jacquard_Normal"
                tex_norm.location = (-500, -260)
                tex_norm.image = load_image_cached(kit_normal_path, "Non-Color")
                norm_map = nt.nodes.new("ShaderNodeNormalMap")
                norm_map.location = (-200, -260)
                norm_map.inputs["Strength"].default_value = 0.65
                nt.links.new(tex_norm.outputs["Color"], norm_map.inputs["Color"])
                nt.links.new(norm_map.outputs["Normal"], bsdf.inputs["Normal"])
                bound_textures["kit_normal"] = os.path.basename(kit_normal_path)

        elif "skin" in mat_name_lower:
            # Normal: Skin Micro-Pores Normal
            if skin_normal_path:
                tex_skin_norm = nt.nodes.new("ShaderNodeTexImage")
                tex_skin_norm.label = "Skin_MicroPores_Normal"
                tex_skin_norm.location = (-500, -220)
                tex_skin_norm.image = load_image_cached(skin_normal_path, "Non-Color")
                norm_map = nt.nodes.new("ShaderNodeNormalMap")
                norm_map.location = (-200, -220)
                norm_map.inputs["Strength"].default_value = 0.35
                nt.links.new(tex_skin_norm.outputs["Color"], norm_map.inputs["Color"])
                nt.links.new(norm_map.outputs["Normal"], bsdf.inputs["Normal"])
                bound_textures["skin_normal"] = os.path.basename(skin_normal_path)

            if "Subsurface Weight" in bsdf.inputs:
                bsdf.inputs["Subsurface Weight"].default_value = 0.15
            if "Roughness" in bsdf.inputs and not bsdf.inputs["Roughness"].is_linked:
                bsdf.inputs["Roughness"].default_value = 0.45

    return bound_textures


def remove_gltf_helper_objects() -> None:
    """Remove glTF importer utility meshes such as `Icosphere` bone shapes."""
    to_remove = [
        obj for obj in list(bpy.data.objects)
        if obj.type == "MESH" and obj.name.startswith("Icosphere") and obj.parent is None
    ]
    for obj in to_remove:
        bpy.data.objects.remove(obj, do_unlink=True)

    for col in list(bpy.data.collections):
        if col.name == "glTF_not_exported" and len(col.objects) == 0:
            bpy.data.collections.remove(col)


def apply_subsurf_and_smooth(mesh_obj: bpy.types.Object, arm_obj: bpy.types.Object) -> None:
    """
    Apply Catmull-Clark Subdivision Surface (`levels=1`) cleanly in Rest Pose above the
    Armature modifier, enforce smooth shading on all faces, and verify clean UV maps.
    """
    prev_pose_pos = arm_obj.data.pose_position
    arm_obj.data.pose_position = "REST"
    bpy.context.view_layer.update()

    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj

    subsurf = mesh_obj.modifiers.new(name="Subdivision_UE5", type="SUBSURF")
    subsurf.subdivision_type = "CATMULL_CLARK"
    subsurf.levels = 1
    subsurf.render_levels = 1
    subsurf.uv_smooth = "PRESERVE_CORNERS"

    # Place Subsurf before Armature so skinning weights subdivide cleanly in rest pose
    bpy.ops.object.modifier_move_to_index(modifier=subsurf.name, index=0)
    bpy.ops.object.modifier_apply(modifier=subsurf.name)

    # Smooth shading on all polygons (Blender 5.2 safe, no deprecated auto_smooth calls)
    poly_count = len(mesh_obj.data.polygons)
    if poly_count > 0:
        mesh_obj.data.polygons.foreach_set("use_smooth", [True] * poly_count)
    mesh_obj.data.update()

    # Ensure at least one clean UV map exists
    if len(mesh_obj.data.uv_layers) == 0:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.02)
        bpy.ops.object.mode_set(mode="OBJECT")

    arm_obj.data.pose_position = prev_pose_pos
    bpy.context.view_layer.update()


def paint_chaos_cloth_jersey_weight(mesh_obj: bpy.types.Object) -> dict[str, Any]:
    """
    Paint the `ChaosCloth_Jersey_Weight` vertex group on the fighter mesh:
      - Shoulders / collar of jersey (`z >= z_collar`): `0.0` (pinned)
      - Free jersey hem (`z <= z_hem`): `1.0` (`12.0 cm` Chaos Cloth max distance)
      - Smooth linear gradient across torso jersey vertices.
    Returns verification metrics for the manifest.
    """
    existing = mesh_obj.vertex_groups.get(CHAOS_CLOTH_VG_NAME)
    if existing is not None:
        mesh_obj.vertex_groups.remove(existing)
    vg = mesh_obj.vertex_groups.new(name=CHAOS_CLOTH_VG_NAME)

    # Identify Kit / Cloth material slot indices
    kit_mat_indices = {
        idx for idx, mat in enumerate(mesh_obj.data.materials)
        if mat is not None and ("kit" in mat.name.lower() or "cloth" in mat.name.lower())
    }

    # Collect vertices belonging to kit polygons in the jersey torso height band (z >= 0.85m)
    jersey_vert_indices: set[int] = set()
    for poly in mesh_obj.data.polygons:
        if poly.material_index in kit_mat_indices:
            for vid in poly.vertices:
                if mesh_obj.data.vertices[vid].co.z >= 0.85:
                    jersey_vert_indices.add(vid)

    # Fallback if a fighter mesh uses different Z bounds
    if not jersey_vert_indices:
        jersey_vert_indices = {v.index for v in mesh_obj.data.vertices if 0.85 <= v.co.z <= 1.45}

    jersey_zs = [mesh_obj.data.vertices[vid].co.z for vid in jersey_vert_indices]
    z_min = min(jersey_zs)
    z_max = max(jersey_zs)
    z_span = max(z_max - z_min, 1e-4)

    # Top 15% of jersey = pinned shoulders/collar (0.0); bottom 15% = free hem (1.0 -> 12.0 cm)
    z_collar = z_max - 0.15 * z_span
    z_hem = z_min + 0.15 * z_span
    grad_span = max(z_collar - z_hem, 1e-4)

    pinned_count = 0
    free_hem_count = 0
    gradient_count = 0
    min_w = 1.0
    max_w = 0.0

    for vid in sorted(jersey_vert_indices):
        z = mesh_obj.data.vertices[vid].co.z
        if z >= z_collar:
            w = 0.0
            pinned_count += 1
        elif z <= z_hem:
            w = 1.0
            free_hem_count += 1
        else:
            w = (z_collar - z) / grad_span
            w = max(0.0, min(1.0, w))
            gradient_count += 1

        vg.add([vid], float(w), "REPLACE")
        if w < min_w:
            min_w = w
        if w > max_w:
            max_w = w

    return {
        "vertex_group": CHAOS_CLOTH_VG_NAME,
        "max_distance_cm": CHAOS_CLOTH_MAX_DISTANCE_CM,
        "jersey_vertex_count": len(jersey_vert_indices),
        "pinned_collar_vertices": pinned_count,
        "gradient_vertices": gradient_count,
        "free_hem_vertices": free_hem_count,
        "min_weight": round(min_w, 4),
        "max_weight": round(max_w, 4),
        "jersey_z_range_m": [round(z_min, 4), round(z_max, 4)],
    }


def configure_scene_60fps() -> None:
    """Configure scene frame rate to 60 FPS for competitive fighting-game animation export."""
    scene = bpy.context.scene
    scene.render.fps = 60
    scene.render.fps_base = 1.0


def enhance_imported_fighter(
    glb_path: str,
    unique_material_suffix: str | None = None,
) -> tuple[bpy.types.Object, bpy.types.Object, dict[str, Any]]:
    """
    Import a single fighter `.glb` and run the full geometry/material/Chaos Cloth pipeline.
    Returns `(arm_obj, mesh_obj, stats_dict)`.
    """
    fighter_stem = os.path.splitext(os.path.basename(glb_path))[0]
    existing_objs = set(bpy.data.objects)

    bpy.ops.import_scene.gltf(filepath=glb_path)
    remove_gltf_helper_objects()

    new_objs = [o for o in bpy.data.objects if o not in existing_objs]
    arm_objs = [o for o in new_objs if o.type == "ARMATURE"]
    mesh_objs = [o for o in new_objs if o.type == "MESH"]

    if not arm_objs or not mesh_objs:
        raise RuntimeError(
            f"Expected armature and mesh in {glb_path}, found "
            f"{len(arm_objs)} armatures and {len(mesh_objs)} meshes."
        )

    arm_obj = arm_objs[0]
    mesh_obj = mesh_objs[0]

    pre_verts = len(mesh_obj.data.vertices)
    pre_faces = len(mesh_obj.data.polygons)

    apply_subsurf_and_smooth(mesh_obj, arm_obj)
    bound_textures = bind_pbr_materials(mesh_obj, fighter_stem, unique_suffix=unique_material_suffix)
    cloth_info = paint_chaos_cloth_jersey_weight(mesh_obj)

    post_verts = len(mesh_obj.data.vertices)
    post_faces = len(mesh_obj.data.polygons)
    uv_layers = [uv.name for uv in mesh_obj.data.uv_layers]

    stats = {
        "fighter": fighter_stem,
        "source_glb": os.path.relpath(glb_path, PROJECT_ROOT).replace("\\", "/"),
        "armature_name": arm_obj.name,
        "mesh_name": mesh_obj.name,
        "bone_count": len(arm_obj.data.bones),
        "action_count": len(bpy.data.actions),
        "actions": sorted(a.name for a in bpy.data.actions),
        "pre_subsurf_vertices": pre_verts,
        "pre_subsurf_faces": pre_faces,
        "vertices": post_verts,
        "faces": post_faces,
        "uv_layers": uv_layers,
        "smooth_shaded": all(p.use_smooth for p in mesh_obj.data.polygons),
        "materials": [m.name for m in mesh_obj.data.materials if m is not None],
        "bound_textures": bound_textures,
        "chaos_cloth": cloth_info,
    }
    return arm_obj, mesh_obj, stats


def export_fighter_fbx(arm_obj: bpy.types.Object, mesh_obj: bpy.types.Object, fbx_path: str) -> int:
    """Export the enhanced fighter armature + mesh + all baked 60 FPS animations as UE 5.4+ FBX."""
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj

    os.makedirs(os.path.dirname(fbx_path), exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=fbx_path,
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        use_space_transform=True,
        bake_space_transform=False,
        mesh_smooth_type="FACE",
        use_mesh_modifiers=True,
        use_tspace=True,
        add_leaf_bones=False,
        primary_bone_axis="Y",
        secondary_bone_axis="X",
        armature_nodetype="NULL",
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=True,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,
        path_mode="COPY",
        embed_textures=True,
        axis_forward="-Z",
        axis_up="Y",
    )
    return os.path.getsize(fbx_path)


def build_master_showcase_blend(glb_files: list[str], output_blend_path: str) -> int:
    """
    Build `Master_17Fighters_Showcase.blend` containing all 17 enhanced fighters arranged
    in a clean 2-row stadium lineup with studio 3-point lighting and camera.
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    configure_scene_60fps()

    scene = bpy.context.scene
    root_col = scene.collection

    # Pitch Showcase Floor
    bpy.ops.mesh.primitive_plane_add(size=32.0, location=(0.0, 1.0, 0.0))
    floor_obj = bpy.context.active_object
    floor_obj.name = "Showcase_Pitch_Floor"
    floor_mat = bpy.data.materials.new(name="M_Showcase_PitchFloor")
    nt = get_material_node_tree(floor_mat)
    bsdf, _ = ensure_principled_bsdf(nt)
    bsdf.inputs["Base Color"].default_value = (0.045, 0.14, 0.055, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.72
    floor_obj.data.materials.append(floor_mat)

    # 3-Point Stadium Studio Lighting
    def add_light(name: str, light_type: str, energy: float, color: tuple[float, float, float], loc: tuple[float, float, float], rot_deg: tuple[float, float, float], size: float = 4.0) -> None:
        ldata = bpy.data.lights.new(name=name, type=light_type)
        ldata.energy = energy
        ldata.color = color
        if light_type == "AREA":
            ldata.size = size
        lobj = bpy.data.objects.new(name=name, object_data=ldata)
        lobj.location = loc
        lobj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
        root_col.objects.link(lobj)

    add_light("Key_Stadium_Light", "AREA", 4500.0, (1.0, 0.96, 0.88), (6.0, -9.0, 8.5), (52.0, 0.0, 28.0), size=6.0)
    add_light("Fill_Cool_Light", "AREA", 2200.0, (0.75, 0.86, 1.0), (-7.5, -7.5, 6.0), (58.0, 0.0, -35.0), size=6.0)
    add_light("Rim_Floodlight", "AREA", 3500.0, (1.0, 0.92, 0.78), (0.0, 8.0, 7.5), (-55.0, 0.0, 180.0), size=8.0)

    # Showcase Camera framing both rows
    cam_data = bpy.data.cameras.new(name="Showcase_Camera")
    cam_data.lens = 35.0
    cam_obj = bpy.data.objects.new(name="Showcase_Camera", object_data=cam_data)
    cam_obj.location = (0.0, -13.5, 2.8)
    cam_obj.rotation_euler = (math.radians(82.0), 0.0, 0.0)
    root_col.objects.link(cam_obj)
    scene.camera = cam_obj

    # Place 17 fighters in 2 rows: Front Row = 9 fighters, Back Row = 8 fighters
    front_count = 9
    spacing_x = 1.65
    for idx, glb_path in enumerate(glb_files):
        fighter_stem = os.path.splitext(os.path.basename(glb_path))[0]
        arm_obj, mesh_obj, _ = enhance_imported_fighter(glb_path, unique_material_suffix=fighter_stem)

        # Put fighter into its own named collection for easy inspection
        f_col = bpy.data.collections.new(name=fighter_stem)
        root_col.children.link(f_col)
        for obj in (arm_obj, mesh_obj):
            for c in list(obj.users_collection):
                c.objects.unlink(obj)
            f_col.objects.link(obj)

        if idx < front_count:
            row_idx = idx
            row_len = front_count
            y_pos = 0.0
        else:
            row_idx = idx - front_count
            row_len = len(glb_files) - front_count
            y_pos = 2.2

        x_pos = (row_idx - (row_len - 1) * 0.5) * spacing_x
        arm_obj.location = Vector((x_pos, y_pos, 0.0))

    # Pack external PBR textures so Master_17Fighters_Showcase.blend is portable
    bpy.ops.file.pack_all()
    os.makedirs(os.path.dirname(output_blend_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_blend_path, compress=True)
    return os.path.getsize(output_blend_path)


def main() -> None:
    os.makedirs(OUTPUT_FIGHTERS_DIR, exist_ok=True)
    glb_files = sorted(glob.glob(os.path.join(SOURCE_FIGHTERS_DIR, "SK_*.glb")))

    if not glb_files:
        raise FileNotFoundError(f"No SK_*.glb fighter files found in {SOURCE_FIGHTERS_DIR}")

    print(f"[Blender {bpy.app.version_string}] Fighters UE5 Pipeline starting for {len(glb_files)} fighters...")

    fighter_entries: list[dict[str, Any]] = []

    for glb_path in glb_files:
        fighter_stem = os.path.splitext(os.path.basename(glb_path))[0]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        configure_scene_60fps()

        arm_obj, mesh_obj, stats = enhance_imported_fighter(glb_path, unique_material_suffix=None)

        fbx_path = os.path.join(OUTPUT_FIGHTERS_DIR, f"{fighter_stem}.fbx")
        fbx_size = export_fighter_fbx(arm_obj, mesh_obj, fbx_path)

        stats["output_fbx"] = os.path.relpath(fbx_path, PROJECT_ROOT).replace("\\", "/")
        stats["fbx_size_bytes"] = fbx_size
        fighter_entries.append(stats)

        print(
            f"  [OK] {fighter_stem:24s} | verts={stats['vertices']:4d} faces={stats['faces']:4d} "
            f"| bones={stats['bone_count']} anims={stats['action_count']} "
            f"| cloth_vg={stats['chaos_cloth']['jersey_vertex_count']}v "
            f"[{stats['chaos_cloth']['min_weight']}..{stats['chaos_cloth']['max_weight']}] "
            f"| fbx={fbx_size:,} B"
        )

    print("[Showcase] Building Master_17Fighters_Showcase.blend...")
    showcase_size = build_master_showcase_blend(glb_files, SHOWCASE_BLEND_PATH)
    print(f"  [OK] Master_17Fighters_Showcase.blend ({showcase_size:,} B)")

    manifest = {
        "project": "LA COPA ETERNA: SANGRE Y POTRERO",
        "pipeline": "blender_fighters_ue5_pipeline.py",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "blender_version": bpy.app.version_string,
        "blender_version_tuple": list(bpy.app.version),
        "target_engine": "Unreal Engine 5.4+",
        "fbx_export_settings": {
            "apply_scale_options": "FBX_SCALE_ALL",
            "add_leaf_bones": False,
            "bake_anim": True,
            "bake_anim_use_all_actions": True,
            "fps": 60,
            "embed_textures": True,
            "mesh_smooth_type": "FACE",
            "subsurf_levels": 1,
        },
        "total_fighters": len(fighter_entries),
        "all_fbx_nonzero": all(e["fbx_size_bytes"] > 0 for e in fighter_entries),
        "all_chaos_cloth_verified": all(
            e["chaos_cloth"]["vertex_group"] == CHAOS_CLOTH_VG_NAME
            and e["chaos_cloth"]["min_weight"] == 0.0
            and e["chaos_cloth"]["max_weight"] == 1.0
            and e["chaos_cloth"]["jersey_vertex_count"] > 0
            for e in fighter_entries
        ),
        "showcase_blend": {
            "path": os.path.relpath(SHOWCASE_BLEND_PATH, PROJECT_ROOT).replace("\\", "/"),
            "size_bytes": showcase_size,
        },
        "fighters": fighter_entries,
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    print(f"[DONE] Manifest written to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
