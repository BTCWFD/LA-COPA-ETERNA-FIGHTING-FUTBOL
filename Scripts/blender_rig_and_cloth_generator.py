#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blender_rig_and_cloth_generator.py - SouthAmericaFightersCore ("La Copa Eterna")
Script de Automatización en Python para Blender 4.x (`bpy`, `bmesh`, `mathutils`):
  1. Construye la jerarquía competitiva de 184 huesos compatible con UE5 Mannequin + Extensiones Fighting:
       - `root` -> `pelvis` -> `pelvis_visual_offset` (Pivote de Hitstop Shake desacoplado de la cápsula Q32.32)
       - Columna (`spine_01..04`), cuello (`neck_01..02`), cabeza (`head`) y 34 huesos faciales para cámaras Super
       - Extremidades con huesos `Twist_01..02`, `Corrective` de articulación y `calf_smear_scale_l/r` (Smear 1.25x)
       - Manos completas (30 falanges) y pies con pivotes de chilena/volea (`foot`, `ball`, `toe`, `heel_pivot`)
       - 12 cadenas de resortes `hair_chain_01..12` (4 segmentos por mechón = 48 huesos capilares para El Pibe y El Loco)
  2. Genera las tarjetas capilares anisotrópicas (`M_FighterHairCards`) y la casaca noventera (`M_FighterKit_Cloth`).
  3. Pinta automáticamente el Vertex Group `ChaosCloth_MaxDistance`:
       - `0.5 cm` (peso normalizado 0.0416) en cuello, hombros y escudo de federación
       - `12.0 cm` (peso normalizado 1.0000) en el faldón inferior de la camiseta
  4. Fuerza interpolación `CONSTANT` (`STEP`) a 60 FPS exactos en todas las curvas de animación y exporta a `.glb` con tangentes.
"""

import os
import math

try:
    import bpy
    import bmesh
    from mathutils import Vector, Matrix, Euler
    HAS_BLENDER_BPY = True
except ImportError:
    HAS_BLENDER_BPY = False


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_FIGHTERS_DIR = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Fighters")


def build_bone_specification_184() -> list[tuple[str, str | None, tuple[float, float, float], tuple[float, float, float]]]:
    """
    Devuelve la lista determinista de los 184 huesos del esqueleto competitivo:
    (bone_name, parent_name, head_xyz_meters, tail_xyz_meters)
    """
    bones: list[tuple[str, str | None, tuple[float, float, float], tuple[float, float, float]]] = [
        # Raíz y Pivote de Hitstop Visual (3 huesos)
        ("root", None, (0.0, 0.0, 0.0), (0.0, 0.0, 0.15)),
        ("pelvis", "root", (0.0, 0.0, 0.96), (0.0, 0.0, 1.06)),
        ("pelvis_visual_offset", "pelvis", (0.0, 0.0, 0.96), (0.0, 0.0, 1.08)),

        # Columna, Cuello y Cabeza (7 huesos)
        ("spine_01", "pelvis_visual_offset", (0.0, 0.0, 1.06), (0.0, 0.0, 1.18)),
        ("spine_02", "spine_01", (0.0, 0.0, 1.18), (0.0, 0.0, 1.30)),
        ("spine_03", "spine_02", (0.0, 0.0, 1.30), (0.0, 0.0, 1.42)),
        ("spine_04", "spine_03", (0.0, 0.0, 1.42), (0.0, 0.0, 1.50)),
        ("neck_01", "spine_04", (0.0, 0.0, 1.50), (0.0, 0.0, 1.56)),
        ("neck_02", "neck_01", (0.0, 0.0, 1.56), (0.0, 0.0, 1.62)),
        ("head", "neck_02", (0.0, 0.0, 1.62), (0.0, 0.0, 1.82)),
    ]

    # Brazo, Twist, Correctivos y 5 Dedos por lado (30 huesos x 2 = 60 huesos)
    for side, sign in [("l", 1.0), ("r", -1.0)]:
        bones.extend([
            (f"clavicle_{side}", "spine_04", (0.04 * sign, 0.0, 1.46), (0.18 * sign, 0.0, 1.46)),
            (f"upperarm_{side}", f"clavicle_{side}", (0.18 * sign, 0.0, 1.46), (0.46 * sign, 0.0, 1.46)),
            (f"upperarm_twist_01_{side}", f"upperarm_{side}", (0.22 * sign, 0.0, 1.46), (0.34 * sign, 0.0, 1.46)),
            (f"upperarm_twist_02_{side}", f"upperarm_{side}", (0.34 * sign, 0.0, 1.46), (0.45 * sign, 0.0, 1.46)),
            (f"upperarm_corrective_deltoid_{side}", f"upperarm_{side}", (0.19 * sign, 0.0, 1.50), (0.26 * sign, 0.0, 1.54)),
            (f"lowerarm_{side}", f"upperarm_{side}", (0.46 * sign, 0.0, 1.46), (0.72 * sign, 0.0, 1.46)),
            (f"lowerarm_twist_01_{side}", f"lowerarm_{side}", (0.50 * sign, 0.0, 1.46), (0.60 * sign, 0.0, 1.46)),
            (f"lowerarm_twist_02_{side}", f"lowerarm_{side}", (0.60 * sign, 0.0, 1.46), (0.71 * sign, 0.0, 1.46)),
            (f"elbow_corrective_{side}", f"lowerarm_{side}", (0.46 * sign, 0.04, 1.46), (0.46 * sign, 0.09, 1.46)),
            (f"hand_{side}", f"lowerarm_{side}", (0.72 * sign, 0.0, 1.46), (0.80 * sign, 0.0, 1.46)),
        ])

        finger_names = ["thumb", "index", "middle", "ring", "pinky"]
        for f_idx, f_name in enumerate(finger_names):
            y_off = (f_idx - 2) * 0.018
            parent_b = f"hand_{side}"
            for phalanx in range(1, 5):  # Metacarpal + 3 falanges = 4 huesos por dedo (20 por mano)
                b_name = f"{f_name}_0{phalanx}_{side}"
                x0 = (0.78 + (phalanx - 1) * 0.025) * sign
                x1 = (0.78 + phalanx * 0.025) * sign
                bones.append((b_name, parent_b, (x0, y_off, 1.46), (x1, y_off, 1.46)))
                parent_b = b_name

    # Piernas, Twist, Correctivos y Smear Scale Targets (14 huesos x 2 = 28 huesos)
    for side, sign in [("l", 1.0), ("r", -1.0)]:
        bones.extend([
            (f"thigh_{side}", "pelvis_visual_offset", (0.11 * sign, 0.0, 0.96), (0.11 * sign, 0.0, 0.52)),
            (f"thigh_twist_01_{side}", f"thigh_{side}", (0.11 * sign, 0.0, 0.90), (0.11 * sign, 0.0, 0.72)),
            (f"thigh_twist_02_{side}", f"thigh_{side}", (0.11 * sign, 0.0, 0.72), (0.11 * sign, 0.0, 0.54)),
            (f"glute_corrective_{side}", f"thigh_{side}", (0.12 * sign, 0.08, 0.94), (0.16 * sign, 0.14, 0.92)),
            (f"knee_corrective_{side}", f"thigh_{side}", (0.11 * sign, -0.05, 0.52), (0.11 * sign, -0.10, 0.52)),
            (f"calf_{side}", f"thigh_{side}", (0.11 * sign, 0.0, 0.52), (0.11 * sign, 0.0, 0.10)),
            (f"calf_twist_01_{side}", f"calf_{side}", (0.11 * sign, 0.0, 0.46), (0.11 * sign, 0.0, 0.28)),
            (f"calf_twist_02_{side}", f"calf_{side}", (0.11 * sign, 0.0, 0.28), (0.11 * sign, 0.0, 0.12)),
            (f"calf_smear_scale_{side}", f"calf_{side}", (0.11 * sign, 0.0, 0.50), (0.11 * sign, 0.0, 0.08)),
            (f"foot_{side}", f"calf_{side}", (0.11 * sign, 0.0, 0.10), (0.11 * sign, -0.14, 0.03)),
            (f"foot_smear_scale_{side}", f"foot_{side}", (0.11 * sign, 0.0, 0.10), (0.11 * sign, -0.18, 0.02)),
            (f"ball_{side}", f"foot_{side}", (0.11 * sign, -0.14, 0.03), (0.11 * sign, -0.22, 0.02)),
            (f"toe_{side}", f"ball_{side}", (0.11 * sign, -0.22, 0.02), (0.11 * sign, -0.26, 0.02)),
            (f"heel_pivot_{side}", f"foot_{side}", (0.11 * sign, 0.05, 0.02), (0.11 * sign, 0.05, 0.0)),
        ])

    # Rig Facial Expresivo para Cámaras de Super / Intros (38 huesos)
    facial_names = [
        "jaw", "chin", "tongue_01", "tongue_02",
        "lip_upper_mid", "lip_lower_mid", "lip_corner_l", "lip_corner_r",
        "lip_upper_l", "lip_upper_r", "lip_lower_l", "lip_lower_r",
        "cheek_upper_l", "cheek_upper_r", "cheek_lower_l", "cheek_lower_r",
        "nostril_l", "nostril_r", "nose_tip", "brow_mid",
        "brow_inner_l", "brow_mid_l", "brow_outer_l",
        "brow_inner_r", "brow_mid_r", "brow_outer_r",
        "eyeball_l", "eyeball_r",
        "eyelid_upper_l", "eyelid_lower_l", "eyelid_upper_r", "eyelid_lower_r",
        "ear_l", "ear_r",
        "neck_tendon_l", "neck_tendon_r", "throat_adams_apple", "head_smear_crown",
    ]
    for idx, f_bone in enumerate(facial_names):
        angle = (idx / len(facial_names)) * math.pi * 2.0
        hx = math.cos(angle) * 0.06
        hy = -0.08 + math.sin(angle) * 0.03
        hz = 1.66 + (idx % 5) * 0.025
        bones.append((f"face_{f_bone}", "head", (hx, hy, hz), (hx, hy - 0.02, hz + 0.01)))

    # 12 Cadenas de Resortes Capilares `hair_chain_01..12` (4 segmentos c/u = 48 huesos)
    for strand_idx in range(1, 13):
        theta = (strand_idx / 12.0) * math.pi * 2.0
        rx = math.cos(theta) * 0.09
        ry = math.sin(theta) * 0.09
        parent_hair = "head"
        for seg in range(1, 5):
            b_name = f"hair_chain_{strand_idx:02d}_0{seg}"
            z0 = 1.76 - (seg - 1) * 0.06
            z1 = 1.76 - seg * 0.06
            bones.append((b_name, parent_hair, (rx, ry, z0), (rx * 1.08, ry * 1.08, z1)))
            parent_hair = b_name

    return bones


def create_competitive_armature_in_blender(fighter_name: str = "ElPibe_10") -> "bpy.types.Object":
    """
    Crea el objeto Armature en Blender con los 184 huesos de la especificación competitiva.
    """
    bone_specs = build_bone_specification_184()

    arm_data = bpy.data.armatures.new(f"SK_{fighter_name}_Armature")
    arm_obj = bpy.data.objects.new(f"SK_{fighter_name}", arm_data)
    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj

    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = arm_data.edit_bones

    created_map = {}
    for b_name, parent_name, head_xyz, tail_xyz in bone_specs:
        eb = edit_bones.new(b_name)
        eb.head = Vector(head_xyz)
        eb.tail = Vector(tail_xyz)
        eb.use_deform = True
        if parent_name and parent_name in created_map:
            eb.parent = created_map[parent_name]
        created_map[b_name] = eb

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


def create_fighter_meshes_and_paint_chaos_cloth_weights(arm_obj: "bpy.types.Object") -> "bpy.types.Object":
    """
    Genera la malla unificada con las 3 ranuras de Material Maestro:
      - Slot 0: `M_FighterSkin_Master`
      - Slot 1: `M_FighterKit_Cloth`
      - Slot 2: `M_FighterHairCards`
    y pinta el Vertex Group `ChaosCloth_MaxDistance` (0.5cm en cuello/escudo -> 12.0cm en faldón).
    """
    bm = bmesh.new()
    # Torso / Camiseta holgada de los años 90 subdividida para simulación Chaos Cloth
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=32,
        radius1=0.24,
        radius2=0.21,
        depth=0.62,
        matrix=Matrix.Translation((0.0, 0.0, 1.22)),
    )

    # Tarjetas capilares anisotrópicas (Hair Cards) alrededor del cráneo
    for card_idx in range(12):
        ang = (card_idx / 12.0) * math.pi * 2.0
        card_mat = (
            Matrix.Translation((math.cos(ang) * 0.10, math.sin(ang) * 0.10, 1.68))
            @ Euler((0.25, 0.0, ang), "XYZ").to_matrix().to_4x4()
        )
        bmesh.ops.create_grid(bm, x_segments=2, y_segments=6, size=0.05, matrix=card_mat)

    mesh_data = bpy.data.meshes.new(f"{arm_obj.name}_Mesh")
    bm.to_mesh(mesh_data)
    bm.free()

    mesh_obj = bpy.data.objects.new(f"{arm_obj.name}_Geo", mesh_data)
    bpy.context.collection.objects.link(mesh_obj)

    # Crear los 3 Materiales Maestros esperados por ue5_auto_import_pipeline.py
    for mat_name in ("M_FighterSkin_Master", "M_FighterKit_Cloth", "M_FighterHairCards"):
        mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)
        mesh_obj.data.materials.append(mat)

    # Pintar Vertex Group `ChaosCloth_MaxDistance`
    # En UE5 Chaos Cloth: MaxDistance = 12.0 cm * Weight
    #   - Cuello / Hombros / Escudo (Z >= 1.40m): 0.5 cm -> Weight = 0.5 / 12.0 = 0.04167
    #   - Faldón inferior de camiseta (Z <= 0.95m): 12.0 cm -> Weight = 1.0
    vg_cloth = mesh_obj.vertex_groups.new(name="ChaosCloth_MaxDistance")
    vg_pelvis = mesh_obj.vertex_groups.new(name="spine_02")

    for v in mesh_obj.data.vertices:
        z_height = v.co.z
        if z_height >= 1.40:
            normalized_weight = 0.5 / 12.0  # 0.5 cm en cuello y escudo
        elif z_height <= 0.95:
            normalized_weight = 1.0         # 12.0 cm en faldón libre
        else:
            t = (1.40 - z_height) / (1.40 - 0.95)
            cm_val = 0.5 + t * (12.0 - 0.5)
            normalized_weight = cm_val / 12.0

        vg_cloth.add([v.index], float(normalized_weight), "REPLACE")
        vg_pelvis.add([v.index], 1.0, "REPLACE")

    # Vincular al Armature
    mesh_obj.parent = arm_obj
    mod = mesh_obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = arm_obj

    return mesh_obj


def enforce_stepped_60fps_animations_and_export_glb(output_glb_path: str) -> None:
    """
    Configura la escena a 60 FPS exactos, convierte todas las F-Curves a interpolación `CONSTANT` (`STEP`)
    para preservar la lectura competitiva de Startup/Active frames y exporta a `.glb` con tangentes.
    """
    scene = bpy.context.scene
    scene.render.fps = 60
    scene.render.fps_base = 1.0

    for action in bpy.data.actions:
        for fcurve in action.fcurves:
            for kp in fcurve.keyframe_points:
                kp.interpolation = "CONSTANT"

    os.makedirs(os.path.dirname(output_glb_path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=output_glb_path,
        export_format="GLB",
        export_tangents=True,
        export_yup=True,
        export_skins=True,
        export_all_influences=False,
        export_animations=True,
        export_frame_range=True,
        export_frame_step=1,
        export_force_sampling=True,
    )


def main() -> None:
    specs = build_bone_specification_184()
    print(f"[Blender 4.x Rig Generator] Especificación verificada con {len(specs)} huesos competitivos.")

    if not HAS_BLENDER_BPY:
        print("[Blender 4.x Dry-Run] Ejecuta `blender -b -P Scripts/blender_rig_and_cloth_generator.py` para exportar los .glb.")
        return

    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm_obj = create_competitive_armature_in_blender("ElPibe_10")
    create_fighter_meshes_and_paint_chaos_cloth_weights(arm_obj)

    out_path = os.path.join(EXPORT_FIGHTERS_DIR, "SK_ElPibe_10_MasterRig.glb")
    enforce_stepped_60fps_animations_and_export_glb(out_path)
    print(f"[OK] Exportado rig competitivo de {len(specs)} huesos a: {out_path}")


if __name__ == "__main__":
    main()
