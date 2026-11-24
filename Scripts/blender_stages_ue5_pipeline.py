#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blender_stages_ue5_pipeline.py
Blender 5.2 Headless Stages Pipeline for LA COPA ETERNA: SANGRE Y POTRERO.

Usage:
    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" --background --python Scripts/blender_stages_ue5_pipeline.py

Pipeline Steps:
  1. Loads the 10 CONMEBOL 3D Stadium .glb models from Assets/Models3D/Stages/SM_Stage_*.glb.
  2. Applies clean smooth shading + angle-based sharp edge marking + Weighted Normal modifier
     (Blender 5.2 compatible — no deprecated mesh.use_auto_smooth).
  3. Verifies UV maps (validates active UV layer & finite coordinates; generates fallback UVs if absent).
  4. Adds UE 5.4+ standard convex collision hulls matching Zone A [-12.5m, +12.5m]:
       - UCX_PitchFloor  (X: [-12.5, +12.5], Y: [-8.5, +8.5], Z: [-0.5, 0.0])
       - UCX_WallLeft    (X: [-13.0, -12.5], Y: [-8.5, +8.5], Z: [0.0, 12.0])
       - UCX_WallRight   (X: [+12.5, +13.0], Y: [-8.5, +8.5], Z: [0.0, 12.0])
  5. Exports UE 5.4+-ready FBX files to Assets/BlenderProduction/Stages/SM_Stage_*.fbx (10 files).
  6. Builds & saves the flagship master .blend scene with Renacimiento Sfumato golden-amber
     three-point studio lighting + 2.5D broadcast camera:
       Assets/BlenderProduction/Stages/Master_Maracana_And_Centenario.blend
  7. Writes Assets/BlenderProduction/Stages/BlenderStages_Manifest.json with exact file sizes,
     mesh/collision counts, UV verification, and Blender version metadata.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import bmesh
import bpy
import mathutils


# ============================================================================
# CONFIGURATION & PATHS
# ============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
INPUT_STAGES_DIR = PROJECT_ROOT / "Assets" / "Models3D" / "Stages"
INPUT_MANIFEST_PATH = INPUT_STAGES_DIR / "Stages3D_TechnicalManifest.json"
OUTPUT_STAGES_DIR = PROJECT_ROOT / "Assets" / "BlenderProduction" / "Stages"
MASTER_BLEND_PATH = OUTPUT_STAGES_DIR / "Master_Maracana_And_Centenario.blend"
OUTPUT_MANIFEST_PATH = OUTPUT_STAGES_DIR / "BlenderStages_Manifest.json"

# Canonical 10 CONMEBOL Stadium GLBs (used as fallback if manifest is absent)
CANONICAL_CONMEBOL_STAGES = [
    ("SM_Stage_Maracana_BR.glb", "STAGE_MARACANA_BR", "Estádio do Maracanã (Brasil)"),
    ("SM_Stage_Bombonera_AR.glb", "STAGE_BOMBONERA_AR", "La Bombonera (Argentina)"),
    ("SM_Stage_Centenario_UY.glb", "STAGE_CENTENARIO_UY", "Estadio Centenario (Uruguay)"),
    ("SM_Stage_Metropolitano_CO.glb", "STAGE_METROPOLITANO_CO", "Estadio Metropolitano (Colombia)"),
    ("SM_Stage_Nunoa_CL.glb", "STAGE_NUNOA_CL", "Estadio Nacional de Ñuñoa (Chile)"),
    ("SM_Stage_Defensores_PY.glb", "STAGE_DEFENSORES_PY", "Estadio Defensores del Chaco (Paraguay)"),
    ("SM_Stage_NacionalLima_PE.glb", "STAGE_NACIONAL_LIMA_PE", "Estadio Nacional de Lima (Perú)"),
    ("SM_Stage_Atahualpa_EC.glb", "STAGE_ATAHUALPA_EC", "Estadio Olímpico Atahualpa (Ecuador)"),
    ("SM_Stage_Avila_VE.glb", "STAGE_AVILA_VE", "Estadio del Ávila (Venezuela)"),
    ("SM_Stage_HernandoSiles_BO.glb", "STAGE_HERNANDO_SILES_BO", "Estadio Hernando Siles (Bolivia - 3,600m)"),
]

FLAGSHIP_STAGES = [
    ("SM_Stage_Maracana_BR.glb", "01_Stage_Maracana_BR", True),
    ("SM_Stage_Centenario_UY.glb", "02_Stage_Centenario_UY", False),
]

# Zone A fighting bounds in Blender Z-up meters (matches glTF X fighting plane)
ZONE_A_HALF_WIDTH = 12.5   # [-12.5m, +12.5m]
ARENA_HALF_DEPTH = 8.5     # [-8.5m, +8.5m]
FLOOR_THICKNESS = 0.5      # Z: [-0.5m, 0.0m]
WALL_THICKNESS = 0.5       # Extruded outward from +/-12.5m
WALL_HEIGHT = 12.0         # Z: [0.0m, 12.0m]
SHARP_ANGLE_DEG = 35.0


# ============================================================================
# SCENE & METRIC UTILITIES
# ============================================================================

def reset_scene() -> None:
    """Reset Blender to a clean empty scene configured in metric meters."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = 'METERS'


def get_stage_catalog() -> list[dict]:
    """Load the 10 CONMEBOL stage entries from Stages3D_TechnicalManifest.json or fallback."""
    if INPUT_MANIFEST_PATH.exists():
        with open(INPUT_MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        entries = []
        for item in manifest.get("Stages", []):
            entries.append({
                "file": item["File"],
                "stage_id": item.get("StageID", Path(item["File"]).stem),
                "display_name": item.get("DisplayName", Path(item["File"]).stem),
            })
        if len(entries) == 10:
            return entries

    return [
        {"file": fname, "stage_id": sid, "display_name": dname}
        for fname, sid, dname in CANONICAL_CONMEBOL_STAGES
    ]


def ensure_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    """Create or retrieve a Blender collection linked to parent (or scene root)."""
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        target_parent = parent if parent is not None else bpy.context.scene.collection
        target_parent.children.link(col)
    return col


def move_object_to_collection(obj: bpy.types.Object, target_col: bpy.types.Collection) -> None:
    """Link object exclusively to target_col."""
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    target_col.objects.link(obj)


# ============================================================================
# MESH PROCESSING: SMOOTH / WEIGHTED NORMALS & UV VERIFICATION
# ============================================================================

def apply_clean_smooth_and_weighted_normals(obj: bpy.types.Object, sharp_angle_deg: float = SHARP_ANGLE_DEG) -> dict:
    """
    Apply smooth shading with angle-based sharp edges and bake a Weighted Normal modifier.
    Fully compatible with Blender 5.2 (avoids removed mesh.use_auto_smooth).
    """
    mesh = obj.data
    sharp_rad = math.radians(sharp_angle_deg)

    # Ensure object scale/rotation transforms are clean before normal calculation
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Mark polygons smooth and flag architectural hard edges > sharp_angle_deg as sharp
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    for face in bm.faces:
        face.smooth = True

    sharp_edges_marked = 0
    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            angle = edge.calc_face_angle(0.0)
            if angle >= sharp_rad:
                edge.smooth = False
                sharp_edges_marked += 1
            else:
                edge.smooth = True
        else:
            edge.smooth = False
            sharp_edges_marked += 1

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    # Add and apply Weighted Normal modifier (face-area weighted, preserving sharp edges)
    mod = obj.modifiers.new(name="WeightedNormal_UE5", type='WEIGHTED_NORMAL')
    mod.mode = 'FACE_AREA'
    mod.weight = 50
    mod.keep_sharp = True
    mod.use_face_influence = False

    bpy.ops.object.modifier_apply(modifier=mod.name)
    mesh.update()

    return {
        "sharp_edges_marked": sharp_edges_marked,
        "weighted_normals_applied": True,
        "has_custom_normals": bool(getattr(mesh, "has_custom_normals", True)),
    }


def verify_and_repair_uvs(obj: bpy.types.Object) -> dict:
    """
    Verify that the mesh has at least one valid UV layer with finite coordinates.
    Generates a clean Smart UV Project fallback if missing.
    """
    mesh = obj.data
    generated_fallback = False

    if len(mesh.uv_layers) == 0:
        mesh.uv_layers.new(name="UVMap")
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.02)
        bpy.ops.object.mode_set(mode='OBJECT')
        generated_fallback = True

    active_uv = mesh.uv_layers.active
    if active_uv is None and len(mesh.uv_layers) > 0:
        mesh.uv_layers.active_index = 0
        active_uv = mesh.uv_layers.active

    invalid_uv_count = 0
    total_uv_loops = len(active_uv.data) if active_uv else 0
    if active_uv:
        for uv_loop in active_uv.data:
            u, v = uv_loop.uv.x, uv_loop.uv.y
            if not (math.isfinite(u) and math.isfinite(v)):
                uv_loop.uv.x = 0.0
                uv_loop.uv.y = 0.0
                invalid_uv_count += 1

    return {
        "uv_layer_count": len(mesh.uv_layers),
        "active_uv_layer": active_uv.name if active_uv else None,
        "uv_loop_count": total_uv_loops,
        "repaired_non_finite_uvs": invalid_uv_count,
        "generated_fallback_uvs": generated_fallback,
        "uvs_valid": len(mesh.uv_layers) > 0 and total_uv_loops > 0,
    }


# ============================================================================
# UE 5.4+ CONVEX COLLISION HULLS (UCX_*)
# ============================================================================

def _create_convex_box_collision(
    name: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    """Create a clean 8-vertex, 6-face convex box mesh for UE5 UCX collision."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    sx, sy, sz = size
    cx, cy, cz = center
    scale_mat = mathutils.Matrix.Diagonal((sx, sy, sz, 1.0))
    trans_mat = mathutils.Matrix.Translation((cx, cy, cz))
    bmesh.ops.transform(bm, matrix=trans_mat @ scale_mat, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    # Keep collision hulls visible as wireframes in Blender without rendering them
    obj.display_type = 'WIRE'
    obj.hide_render = True
    obj["UE5_CollisionType"] = "UCX_ConvexHull"
    obj["ZoneA_Bounds_Meters"] = "[-12.5, +12.5]"
    return obj


def add_ue5_zone_a_collisions(collection: bpy.types.Collection, suffix: str = "") -> list[bpy.types.Object]:
    """
    Create UE 5.4+ convex collision hulls matching Zone A [-12.5m, +12.5m]:
      - UCX_PitchFloor
      - UCX_WallLeft
      - UCX_WallRight
    """
    floor = _create_convex_box_collision(
        name=f"UCX_PitchFloor{suffix}",
        center=(0.0, 0.0, -FLOOR_THICKNESS * 0.5),
        size=(ZONE_A_HALF_WIDTH * 2.0, ARENA_HALF_DEPTH * 2.0, FLOOR_THICKNESS),
        collection=collection,
    )
    wall_left = _create_convex_box_collision(
        name=f"UCX_WallLeft{suffix}",
        center=(-(ZONE_A_HALF_WIDTH + WALL_THICKNESS * 0.5), 0.0, WALL_HEIGHT * 0.5),
        size=(WALL_THICKNESS, ARENA_HALF_DEPTH * 2.0, WALL_HEIGHT),
        collection=collection,
    )
    wall_right = _create_convex_box_collision(
        name=f"UCX_WallRight{suffix}",
        center=(ZONE_A_HALF_WIDTH + WALL_THICKNESS * 0.5, 0.0, WALL_HEIGHT * 0.5),
        size=(WALL_THICKNESS, ARENA_HALF_DEPTH * 2.0, WALL_HEIGHT),
        collection=collection,
    )
    return [floor, wall_left, wall_right]


# ============================================================================
# RENACIMIENTO SFUMATO GOLDEN-AMBER 3-POINT STUDIO LIGHT RIG & CAMERA
# ============================================================================

def _aim_object_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    """Orient a light or camera (-Z forward, +Y up) toward a 3D target point."""
    direction = mathutils.Vector(target) - obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    obj.rotation_euler = rot_quat.to_euler()


def setup_renacimiento_sfumato_lighting(collection: bpy.types.Collection) -> dict:
    """
    Build the Renacimiento Sfumato golden-amber three-point studio light rig,
    warm atmospheric world shader, and 2.5D fighting broadcast camera.
    """
    scene = bpy.context.scene

    # 1. Key Light: Warm Golden-Amber Renaissance Chiaroscuro Sun/Area
    key_data = bpy.data.lights.new(name="Renacimiento_Key_GoldenAmber", type='SUN')
    key_data.color = (1.0, 0.78, 0.46)
    key_data.energy = 4.2
    key_data.angle = math.radians(4.5)  # Soft sfumato penumbra
    key_obj = bpy.data.objects.new(name="Renacimiento_Key_GoldenAmber", object_data=key_data)
    key_obj.location = (-28.0, -22.0, 32.0)
    _aim_object_at(key_obj, (0.0, 2.0, 2.0))
    collection.objects.link(key_obj)

    # 2. Fill Light: Soft Sfumato Warm Ochre-Twilight Area Fill
    fill_data = bpy.data.lights.new(name="Renacimiento_Fill_Sfumato", type='AREA')
    fill_data.shape = 'RECTANGLE'
    fill_data.size = 24.0
    fill_data.size_y = 14.0
    fill_data.color = (0.76, 0.68, 0.60)
    fill_data.energy = 18000.0
    fill_obj = bpy.data.objects.new(name="Renacimiento_Fill_Sfumato", object_data=fill_data)
    fill_obj.location = (26.0, -24.0, 14.0)
    _aim_object_at(fill_obj, (0.0, 0.0, 3.0))
    collection.objects.link(fill_obj)

    # 3. Rim / Back Light: Molten Sunset Amber Silhouette Rim
    rim_data = bpy.data.lights.new(name="Renacimiento_Rim_MoltenGold", type='AREA')
    rim_data.shape = 'RECTANGLE'
    rim_data.size = 32.0
    rim_data.size_y = 10.0
    rim_data.color = (1.0, 0.56, 0.22)
    rim_data.energy = 32000.0
    rim_obj = bpy.data.objects.new(name="Renacimiento_Rim_MoltenGold", object_data=rim_data)
    rim_obj.location = (0.0, 32.0, 26.0)
    _aim_object_at(rim_obj, (0.0, 0.0, 2.5))
    collection.objects.link(rim_obj)

    # 4. World Shader: Deep Umber to Golden-Amber Twilight Backdrop
    world = bpy.data.worlds.new("World_Renacimiento_Sfumato")
    scene.world = world
    if world.node_tree is None:
        world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()

    out_node = nt.nodes.new("ShaderNodeOutputWorld")
    bg_node = nt.nodes.new("ShaderNodeBackground")
    bg_node.inputs["Color"].default_value = (0.14, 0.085, 0.045, 1.0)
    bg_node.inputs["Strength"].default_value = 0.65
    nt.links.new(bg_node.outputs["Background"], out_node.inputs["Surface"])

    # 5. 2.5D Fighting Broadcast Camera
    cam_data = bpy.data.cameras.new(name="Camera_25D_Broadcast")
    cam_data.lens = 35.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 500.0
    cam_obj = bpy.data.objects.new(name="Camera_25D_Broadcast", object_data=cam_data)
    cam_obj.location = (0.0, -24.0, 5.2)
    _aim_object_at(cam_obj, (0.0, 0.0, 3.2))
    collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # AgX / Filmic color management for golden-amber dynamic range
    try:
        scene.view_settings.view_transform = 'AgX'
    except Exception:
        scene.view_settings.view_transform = 'Filmic'
    scene.view_settings.exposure = 0.0

    return {
        "rig_name": "Renacimiento Sfumato Golden-Amber Three-Point Studio Rig",
        "lights": [key_obj.name, fill_obj.name, rim_obj.name],
        "camera": cam_obj.name,
        "world": world.name,
    }


# ============================================================================
# STAGE IMPORT & FBX EXPORT
# ============================================================================

def import_and_process_stage(
    glb_path: Path,
    stage_col: bpy.types.Collection,
    collision_col: bpy.types.Collection,
    collision_suffix: str = "",
) -> tuple[list[bpy.types.Object], list[bpy.types.Object], dict]:
    """Import a stage .glb, apply smooth/weighted normals, verify UVs, and add UCX hulls."""
    before_objs = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    imported_objs = [o for o in bpy.data.objects if o not in before_objs]

    mesh_objs = [o for o in imported_objs if o.type == 'MESH']
    for obj in imported_objs:
        move_object_to_collection(obj, stage_col)

    total_verts = 0
    total_polys = 0
    total_tris = 0
    total_materials = set()
    uv_reports = []
    normal_reports = []

    for obj in mesh_objs:
        normal_rep = apply_clean_smooth_and_weighted_normals(obj)
        uv_rep = verify_and_repair_uvs(obj)
        normal_reports.append(normal_rep)
        uv_reports.append(uv_rep)

        mesh = obj.data
        total_verts += len(mesh.vertices)
        total_polys += len(mesh.polygons)
        mesh.calc_loop_triangles()
        total_tris += len(mesh.loop_triangles)
        for mat in mesh.materials:
            if mat is not None:
                total_materials.add(mat.name)

    collision_objs = add_ue5_zone_a_collisions(collision_col, suffix=collision_suffix)

    stats = {
        "mesh_object_count": len(mesh_objs),
        "collision_object_count": len(collision_objs),
        "collision_names": [c.name for c in collision_objs],
        "vertex_count": total_verts,
        "polygon_count": total_polys,
        "triangle_count": total_tris,
        "material_count": len(total_materials),
        "uvs_verified": all(r["uvs_valid"] for r in uv_reports) and len(uv_reports) > 0,
        "weighted_normals_applied": all(r["weighted_normals_applied"] for r in normal_reports) and len(normal_reports) > 0,
        "sharp_edges_marked": sum(r["sharp_edges_marked"] for r in normal_reports),
    }
    return mesh_objs, collision_objs, stats


def export_ue5_fbx(mesh_objs: list[bpy.types.Object], collision_objs: list[bpy.types.Object], fbx_path: Path) -> None:
    """Export selected stage meshes and UCX collision hulls as UE 5.4+-ready FBX."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs + collision_objs:
        obj.select_set(True)
    if mesh_objs:
        bpy.context.view_layer.objects.active = mesh_objs[0]

    bpy.ops.export_scene.fbx(
        filepath=str(fbx_path),
        use_selection=True,
        object_types={'MESH'},
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',
        use_space_transform=True,
        bake_space_transform=False,
        axis_forward='-Y',
        axis_up='Z',
        use_mesh_modifiers=True,
        mesh_smooth_type='FACE',
        use_tspace=True,
        use_triangles=False,
        bake_anim=False,
        add_leaf_bones=False,
        path_mode='COPY',
        embed_textures=True,
    )


# ============================================================================
# MASTER .BLEND ASSEMBLY
# ============================================================================

def build_master_blend(master_blend_path: Path) -> dict:
    """
    Build Master_Maracana_And_Centenario.blend containing:
      - 00_Lighting_Renacimiento_Sfumato (3-point golden-amber rig + 2.5D camera)
      - 01_Stage_Maracana_BR (active flagship stadium + UCX collisions)
      - 02_Stage_Centenario_UY (secondary flagship stadium + UCX collisions, hidden in viewport for toggle)
    """
    reset_scene()
    light_col = ensure_collection("00_Lighting_Renacimiento_Sfumato")
    lighting_info = setup_renacimiento_sfumato_lighting(light_col)

    included_stages = []
    total_meshes = 0
    total_collisions = 0

    for glb_name, col_name, visible_by_default in FLAGSHIP_STAGES:
        glb_path = INPUT_STAGES_DIR / glb_name
        if not glb_path.exists():
            raise FileNotFoundError(f"Missing flagship GLB: {glb_path}")

        stage_col = ensure_collection(col_name)
        coll_col = ensure_collection(f"{col_name}_Collision", parent=stage_col)
        suffix = "" if visible_by_default else "_Centenario"

        mesh_objs, coll_objs, stats = import_and_process_stage(
            glb_path=glb_path,
            stage_col=stage_col,
            collision_col=coll_col,
            collision_suffix=suffix,
        )
        total_meshes += len(mesh_objs)
        total_collisions += len(coll_objs)

        if not visible_by_default:
            stage_col.hide_viewport = True
            stage_col.hide_render = True

        included_stages.append({
            "source_glb": glb_name,
            "collection": col_name,
            "visible_by_default": visible_by_default,
            "mesh_count": len(mesh_objs),
            "collision_count": len(coll_objs),
        })

    bpy.ops.wm.save_as_mainfile(filepath=str(master_blend_path), compress=True)
    file_size = master_blend_path.stat().st_size

    return {
        "file": master_blend_path.name,
        "relative_path": str(master_blend_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "file_size_bytes": file_size,
        "included_stages": included_stages,
        "total_mesh_objects": total_meshes,
        "total_collision_objects": total_collisions,
        "lighting_rig": lighting_info,
    }


# ============================================================================
# MAIN PIPELINE ENTRYPOINT
# ============================================================================

def main() -> int:
    print("=" * 78)
    print("LA COPA ETERNA: SANGRE Y POTRERO — Blender 5.2 Stages UE5 Pipeline")
    print(f"Blender Version : {bpy.app.version_string}")
    print(f"Input Directory : {INPUT_STAGES_DIR}")
    print(f"Output Directory: {OUTPUT_STAGES_DIR}")
    print("=" * 78)

    OUTPUT_STAGES_DIR.mkdir(parents=True, exist_ok=True)
    stage_catalog = get_stage_catalog()

    exported_stages = []

    for idx, entry in enumerate(stage_catalog, start=1):
        glb_name = entry["file"]
        glb_path = INPUT_STAGES_DIR / glb_name
        if not glb_path.exists():
            raise FileNotFoundError(f"Expected stage GLB not found: {glb_path}")

        fbx_name = Path(glb_name).with_suffix(".fbx").name
        fbx_path = OUTPUT_STAGES_DIR / fbx_name

        print(f"[{idx:02d}/{len(stage_catalog):02d}] Processing {glb_name} -> {fbx_name} ...")
        reset_scene()

        stage_col = ensure_collection("Stage_Geometry")
        collision_col = ensure_collection("UE5_Collisions")
        light_col = ensure_collection("Lighting_Renacimiento_Sfumato")

        setup_renacimiento_sfumato_lighting(light_col)
        mesh_objs, collision_objs, stats = import_and_process_stage(
            glb_path=glb_path,
            stage_col=stage_col,
            collision_col=collision_col,
            collision_suffix="",
        )
        export_ue5_fbx(mesh_objs, collision_objs, fbx_path)

        fbx_size = fbx_path.stat().st_size
        print(
            f"        OK | Size: {fbx_size:,} bytes | Meshes: {stats['mesh_object_count']} | "
            f"Collisions: {stats['collision_object_count']} ({', '.join(stats['collision_names'])}) | "
            f"Tris: {stats['triangle_count']} | UVs OK: {stats['uvs_verified']}"
        )

        exported_stages.append({
            "stage_id": entry["stage_id"],
            "display_name": entry["display_name"],
            "source_glb": glb_name,
            "source_glb_size_bytes": glb_path.stat().st_size,
            "fbx_file": fbx_name,
            "fbx_relative_path": str(fbx_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "fbx_size_bytes": fbx_size,
            **stats,
        })

    print("-" * 78)
    print(f"Building Master Flagship Scene: {MASTER_BLEND_PATH.name} ...")
    master_info = build_master_blend(MASTER_BLEND_PATH)
    print(
        f"        OK | Size: {master_info['file_size_bytes']:,} bytes | "
        f"Meshes: {master_info['total_mesh_objects']} | Collisions: {master_info['total_collision_objects']}"
    )

    manifest = {
        "schema_version": "1.0.0-BLENDER52-UE54-STAGES",
        "project": "LA COPA ETERNA: SANGRE Y POTRERO",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "blender_version": bpy.app.version_string,
        "blender_version_tuple": list(bpy.app.version),
        "target_engine": "Unreal Engine 5.4+",
        "fbx_export_settings": {
            "axis_forward": "-Y",
            "axis_up": "Z",
            "global_scale": 1.0,
            "apply_unit_scale": True,
            "mesh_smooth_type": "FACE",
            "use_mesh_modifiers": True,
            "use_tspace": True,
            "embed_textures": True,
        },
        "zone_a_collision_spec": {
            "zone_a_x_meters": [-ZONE_A_HALF_WIDTH, ZONE_A_HALF_WIDTH],
            "arena_y_depth_meters": [-ARENA_HALF_DEPTH, ARENA_HALF_DEPTH],
            "hulls": ["UCX_PitchFloor", "UCX_WallLeft", "UCX_WallRight"],
        },
        "total_stages_exported": len(exported_stages),
        "all_uvs_verified": all(s["uvs_verified"] for s in exported_stages),
        "all_weighted_normals_applied": all(s["weighted_normals_applied"] for s in exported_stages),
        "total_fbx_bytes": sum(s["fbx_size_bytes"] for s in exported_stages),
        "master_blend": master_info,
        "stages": exported_stages,
    }

    with open(OUTPUT_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("-" * 78)
    print(f"Manifest written: {OUTPUT_MANIFEST_PATH}")
    print(f"SUCCESS: {len(exported_stages)} FBX stages + 1 master .blend generated with 0 errors.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
