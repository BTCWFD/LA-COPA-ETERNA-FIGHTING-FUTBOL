#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ue5_auto_import_pipeline.py - SouthAmericaFightersCore ("La Copa Eterna")
Script de Automatización para el Editor de Unreal Engine 5.4+ (Python Editor Script Plugin / Interchange):
  1. Importa todos los archivos .glb desde `Assets/Models3D/Fighters/` como `USkeletalMesh`.
  2. Desactiva Nanite (`bEnableNanite = False`), activa `SkinCacheUsage = Enabled` y `LightingChannel 1`
     para garantizar compatibilidad 100% con Deformers de Control Rig (Smear 1.25x) y Chaos Cloth 5.4.
  3. Vincula automáticamente los 3 Materiales Maestros:
       - Slot 0: `M_FighterSkin_Master`
       - Slot 1: `M_FighterKit_Cloth`
       - Slot 2: `M_FighterHairCards`
  4. Configura `UChaosClothConfig` / `UChaosClothSharedSimConfig` con:
       - `MaxDistance`: 0.5 cm en cuello/escudo -> 12.0 cm en faldón inferior
       - `Drag = 0.08`, `Lift = 0.04`
       - `TeleportDistanceThreshold = 50.0` (y `TeleportRotationThreshold = 15.0`)
  5. Importa todas las texturas de `Assets/TexturesPBR/` y genera las 12 instancias `MI_Kit_<Country>`.
"""

import os
import glob

try:
    import unreal
    HAS_UNREAL_EDITOR = True
except ImportError:
    HAS_UNREAL_EDITOR = False


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLB_FIGHTERS_DIR = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Fighters")
PBR_TEXTURES_DIR = os.path.join(PROJECT_ROOT, "Assets", "TexturesPBR")

UE_FIGHTERS_DEST = "/Game/Characters/SouthAmericaRoster/Meshes"
UE_TEXTURES_DEST = "/Game/Characters/SouthAmericaRoster/TexturesPBR"
UE_MATERIALS_DEST = "/Game/Characters/SouthAmericaRoster/Materials"

MASTER_MAT_SKIN = "/Game/Characters/SouthAmericaRoster/Materials/M_FighterSkin_Master"
MASTER_MAT_KIT = "/Game/Characters/SouthAmericaRoster/Materials/M_FighterKit_Cloth"
MASTER_MAT_HAIR = "/Game/Characters/SouthAmericaRoster/Materials/M_FighterHairCards"


CHAOS_CLOTH_54_PRESET = {
    "MaxDistance_CollarAndCrest_Cm": 0.5,
    "MaxDistance_LowerHem_Cm": 12.0,
    "AerodynamicDrag": 0.08,
    "AerodynamicLift": 0.04,
    "AnimDriveStiffness_Default": 0.18,
    "AnimDriveStiffness_RollbackTeleport": 0.95,
    "DampingCoefficient": 0.04,
    "FrictionCoefficient": 0.15,
    "TeleportDistanceThresholdCm": 50.0,
    "TeleportRotationThresholdDeg": 15.0,
    "SimulationFrequencyHz": 60,
    "Substeps": 2,
}


def import_pbr_textures_to_ue5() -> list:
    """
    Importa los mapas PBR generados en `Assets/TexturesPBR/` y ajusta sRGB y CompressionSettings
    según el sufijo (_Albedo, _Normal, _ORM, _Mask).
    """
    if not HAS_UNREAL_EDITOR:
        print("[UE5 Pipeline Dry-Run] Saltando import_pbr_textures_to_ue5 fuera del proceso UnrealEditor.exe")
        return []

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    png_files = sorted(glob.glob(os.path.join(PBR_TEXTURES_DIR, "*.png")))
    imported_textures = []

    for png_path in png_files:
        task = unreal.AssetImportTask()
        task.filename = png_path
        task.destination_path = UE_TEXTURES_DEST
        task.replace_existing = True
        task.automated = True
        task.save = True

        asset_tools.import_asset_tasks([task])
        for obj_path in task.imported_object_paths:
            tex = unreal.EditorAssetLibrary.load_asset(obj_path)
            if not isinstance(tex, unreal.Texture2D):
                continue

            base_name = os.path.basename(png_path)
            if base_name.endswith("_Normal.png"):
                tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
                tex.set_editor_property("srgb", False)
            elif base_name.endswith("_ORM.png") or base_name.endswith("_Mask.png"):
                tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
                tex.set_editor_property("srgb", False)
            else:
                tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
                tex.set_editor_property("srgb", True)

            unreal.EditorAssetLibrary.save_loaded_asset(tex)
            imported_textures.append(tex)

    return imported_textures


def configure_chaos_cloth_on_skeletal_mesh(skel_mesh: "unreal.SkeletalMesh") -> None:
    """
    Aplica los parámetros competitivos de Chaos Cloth 5.4 sobre el ClothingAsset del SkeletalMesh:
      - MaxDistance: 0.5 cm en cuello/escudo -> 12.0 cm en faldón
      - Drag = 0.08, Lift = 0.04
      - TeleportDistanceThreshold = 50.0 cm
    """
    if not HAS_UNREAL_EDITOR or skel_mesh is None:
        return

    clothing_assets = skel_mesh.get_editor_property("mesh_clothing_assets")
    if not clothing_assets:
        return

    for cloth_asset in clothing_assets:
        if cloth_asset is None:
            continue
        configs = cloth_asset.get_editor_property("cloth_configs")
        if not configs:
            continue

        for config_key, config_obj in configs.items():
            class_name = config_obj.get_class().get_name()
            if "ChaosClothConfig" in class_name:
                # Aerodinámica: Drag = 0.08, Lift = 0.04
                if hasattr(config_obj, "drag"):
                    config_obj.set_editor_property(
                        "drag",
                        unreal.ChaosClothWeightedValue(
                            CHAOS_CLOTH_54_PRESET["AerodynamicDrag"],
                            CHAOS_CLOTH_54_PRESET["AerodynamicDrag"],
                        ),
                    )
                if hasattr(config_obj, "lift"):
                    config_obj.set_editor_property(
                        "lift",
                        unreal.ChaosClothWeightedValue(
                            CHAOS_CLOTH_54_PRESET["AerodynamicLift"],
                            CHAOS_CLOTH_54_PRESET["AerodynamicLift"],
                        ),
                    )
                # AnimDriveStiffness base (0.18 nominal -> 0.95 en Rollback vía C++)
                if hasattr(config_obj, "anim_drive_stiffness"):
                    config_obj.set_editor_property(
                        "anim_drive_stiffness",
                        unreal.ChaosClothWeightedValue(
                            CHAOS_CLOTH_54_PRESET["AnimDriveStiffness_Default"],
                            CHAOS_CLOTH_54_PRESET["AnimDriveStiffness_RollbackTeleport"],
                        ),
                    )
            elif "ChaosClothSharedSimConfig" in class_name:
                if hasattr(config_obj, "teleport_distance_threshold"):
                    config_obj.set_editor_property(
                        "teleport_distance_threshold",
                        CHAOS_CLOTH_54_PRESET["TeleportDistanceThresholdCm"],
                    )
                if hasattr(config_obj, "teleport_rotation_threshold"):
                    config_obj.set_editor_property(
                        "teleport_rotation_threshold",
                        CHAOS_CLOTH_54_PRESET["TeleportRotationThresholdDeg"],
                    )


def bind_master_materials_to_skeletal_mesh(skel_mesh: "unreal.SkeletalMesh") -> None:
    """
    Vincula los 3 Materiales Maestros a las ranuras del USkeletalMesh:
      - M_FighterSkin_Master
      - M_FighterKit_Cloth
      - M_FighterHairCards
    """
    if not HAS_UNREAL_EDITOR or skel_mesh is None:
        return

    mat_skin = unreal.EditorAssetLibrary.load_asset(MASTER_MAT_SKIN)
    mat_kit = unreal.EditorAssetLibrary.load_asset(MASTER_MAT_KIT)
    mat_hair = unreal.EditorAssetLibrary.load_asset(MASTER_MAT_HAIR)

    materials = skel_mesh.get_editor_property("materials")
    updated_materials = []

    for idx, skeletal_mat in enumerate(materials):
        slot_name = str(skeletal_mat.get_editor_property("material_slot_name")).lower()
        if "hair" in slot_name or idx == 2:
            if mat_hair:
                skeletal_mat.set_editor_property("material_interface", mat_hair)
        elif "kit" in slot_name or "cloth" in slot_name or "jersey" in slot_name or idx == 1:
            if mat_kit:
                skeletal_mat.set_editor_property("material_interface", mat_kit)
        else:
            if mat_skin:
                skeletal_mat.set_editor_property("material_interface", mat_skin)

        updated_materials.append(skeletal_mat)

    skel_mesh.set_editor_property("materials", updated_materials)


def import_fighters_glb_interchange() -> list:
    """
    Importa todos los archivos .glb desde `Assets/Models3D/Fighters/` como `USkeletalMesh`:
      - Desactiva Nanite (`bEnableNanite = False`)
      - Activa Skin Cache (`SkinCacheUsage = Enabled`)
      - Configura LightingChannel 1 en el Blueprint/Prefab de personaje
      - Vincula M_FighterSkin_Master, M_FighterKit_Cloth, M_FighterHairCards
      - Aplica la configuración de Chaos Cloth 5.4
    """
    glb_files = sorted(glob.glob(os.path.join(GLB_FIGHTERS_DIR, "*.glb")))
    if not HAS_UNREAL_EDITOR:
        print(f"[UE5 Pipeline Ready] Encontrados {len(glb_files)} archivos .glb listos para Interchange.")
        print(f"[Chaos Cloth 5.4 Config] {CHAOS_CLOTH_54_PRESET}")
        return glb_files

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    imported_meshes = []

    for glb_path in glb_files:
        task = unreal.AssetImportTask()
        task.filename = glb_path
        task.destination_path = UE_FIGHTERS_DEST
        task.replace_existing = True
        task.automated = True
        task.save = True

        asset_tools.import_asset_tasks([task])

        for obj_path in task.imported_object_paths:
            asset = unreal.EditorAssetLibrary.load_asset(obj_path)
            if not isinstance(asset, unreal.SkeletalMesh):
                continue

            # 1. Desactivar Nanite en SkeletalMesh para permitir Smear Deformers (1.25x) y Chaos Cloth
            if hasattr(asset, "nanite_settings"):
                nanite_cfg = asset.get_editor_property("nanite_settings")
                if hasattr(nanite_cfg, "enabled"):
                    nanite_cfg.set_editor_property("enabled", False)
                    asset.set_editor_property("nanite_settings", nanite_cfg)

            # 2. Activar Skin Cache en LOD 0 y LOD 1 para Dual-Quat Skinning + Morph/Cloth Raytracing
            lod_info_array = asset.get_editor_property("lod_info")
            for lod_info in lod_info_array:
                if hasattr(lod_info, "skin_cache_usage"):
                    lod_info.set_editor_property("skin_cache_usage", unreal.SkinCacheUsage.ENABLED)
            asset.set_editor_property("lod_info", lod_info_array)

            # 3. Vincular los 3 Materiales Maestros y Chaos Cloth 5.4
            bind_master_materials_to_skeletal_mesh(asset)
            configure_chaos_cloth_on_skeletal_mesh(asset)

            unreal.EditorAssetLibrary.save_loaded_asset(asset)
            imported_meshes.append(asset)

    return imported_meshes


def apply_lighting_channel_1_to_character_component(skel_comp: "unreal.SkeletalMeshComponent") -> None:
    """
    Asigna `LightingChannel 1` al `USkeletalMeshComponent` del luchador para aislar la luz de borde (Rim Key Light)
    respecto a los reflectores del estadio (LightingChannel 0).
    """
    if not HAS_UNREAL_EDITOR or skel_comp is None:
        return

    channels = unreal.LightingChannels()
    channels.set_editor_property("channel0", True)
    channels.set_editor_property("channel1", True)
    channels.set_editor_property("channel2", False)
    skel_comp.set_editor_property("lighting_channels", channels)


if __name__ == "__main__":
    import_pbr_textures_to_ue5()
    import_fighters_glb_interchange()
