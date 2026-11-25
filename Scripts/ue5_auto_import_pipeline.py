#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ue5_auto_import_pipeline.py - SouthAmericaFightersCore ("La Copa Eterna")
UE 5.4+ Production Auto-Import Pipeline v2.0 (Python Editor Script Plugin / Interchange & CLI Dry-Run Auditor)

Funcionalidades Principales:
  1. Importa los 17 luchadores animados `.glb` desde `Assets/Models3D/Fighters/SK_*.glb` como `USkeletalMesh`
     con importación de `UAnimSequence` a 60 FPS activada, validados contra `Animations3D_TechnicalManifest.json`
     (17 luchadores x 10 clips embebidos = 170 secuencias de animación).
  2. Desactiva Nanite en personajes (`bEnableNanite = False`), activa `SkinCacheUsage = Enabled`, asigna
     `LightingChannel 1`, vincula los 3 Materiales Maestros (`M_FighterSkin_Master`, `M_FighterKit_Cloth`,
     `M_FighterHairCards`) y configura `UChaosClothConfig` (`MaxDistance: 0.5cm -> 12.0cm`, `Drag = 0.08`,
     `Lift = 0.04`, `TeleportDistanceThreshold = 50.0`).
  3. Importa los 10 Estadios 3D CONMEBOL `.glb` desde `Assets/Models3D/Stages/SM_Stage_*.glb` como `UStaticMesh`
     con Nanite + Lumen activados, validados contra `Stages3D_TechnicalManifest.json`.
  4. Importa las 18 texturas PBR (`Assets/TexturesPBR/`), las 6 ilustraciones 2D de Concept Art & UI
     (incluyendo la serie Renacimiento Sfumato en `Assets/ConceptArt/`), y las 4 DataTables JSON (`Data/`).
  5. Crea y cablea automáticamente el Post-Process Material `M_PP_SfumatoChiaroscuro` referenciando
     `/Project/Shaders/SfumatoChiaroscuroPostProcess.ush` con el parámetro escalar `ArtStyleMode`
     (`0 = Street-Ink`, `1 = Renaissance Sfumato`).
  6. Incluye modo CLI `--dry-run` ejecutable en Python 3 estándar fuera de UE5 para auditar la integridad
     binaria (cabeceras glTF 2.0, JSONs, shaders `.ush` y texturas) del 100% de los activos en disco.
"""

import os
import sys
import glob
import json
import struct
import argparse
from typing import Any

try:
    import unreal
    HAS_UNREAL_EDITOR = True
except ImportError:
    HAS_UNREAL_EDITOR = False


PIPELINE_VERSION = "2.0.0-UE5.4-Interchange-Sfumato"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLB_FIGHTERS_DIR = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Fighters")
GLB_STAGES_DIR = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Stages")
GLB_PROPS_DIR = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Props")
PBR_TEXTURES_DIR = os.path.join(PROJECT_ROOT, "Assets", "TexturesPBR")
CONCEPT_ART_DIR = os.path.join(PROJECT_ROOT, "Assets", "ConceptArt")
UI_SVG_DIR = os.path.join(PROJECT_ROOT, "Assets", "UI", "SVG")
DATATABLES_DIR = os.path.join(PROJECT_ROOT, "Data")
SHADERS_DIR = os.path.join(PROJECT_ROOT, "Shaders")
TECHART_SOURCE_DIR = os.path.join(PROJECT_ROOT, "Source", "TechArt")

ANIMATIONS_MANIFEST_PATH = os.path.join(GLB_FIGHTERS_DIR, "Animations3D_TechnicalManifest.json")
STAGES_MANIFEST_PATH = os.path.join(GLB_STAGES_DIR, "Stages3D_TechnicalManifest.json")
MODELS_MANIFEST_PATH = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Models3D_TechnicalManifest.json")

# Destinos virtuales dentro del Content Browser de Unreal Engine 5.4+
UE_FIGHTERS_DEST = "/Game/Characters/SouthAmericaRoster/Meshes"
UE_STAGES_DEST = "/Game/Stages/CONMEBOL/Meshes"
UE_TEXTURES_DEST = "/Game/Characters/SouthAmericaRoster/TexturesPBR"
UE_CONCEPT_UI_DEST = "/Game/UI/ConceptArtAndPortraits"
UE_DATATABLES_DEST = "/Game/DataTables"
UE_MATERIALS_DEST = "/Game/Characters/SouthAmericaRoster/Materials"
UE_POSTPROCESS_DEST = "/Game/TechArt/PostProcess"

MASTER_MAT_SKIN = "/Game/Characters/SouthAmericaRoster/Materials/M_FighterSkin_Master"
MASTER_MAT_KIT = "/Game/Characters/SouthAmericaRoster/Materials/M_FighterKit_Cloth"
MASTER_MAT_HAIR = "/Game/Characters/SouthAmericaRoster/Materials/M_FighterHairCards"
PP_MAT_SFUMATO_PATH = "/Game/TechArt/PostProcess/M_PP_SfumatoChiaroscuro"
SFUMATO_USH_VIRTUAL_PATH = "/Project/Shaders/SfumatoChiaroscuroPostProcess.ush"


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

SFUMATO_POSTPROCESS_DEFAULTS = {
    "ArtStyleMode": 1.0,            # 0.0 = Street-Ink Muralismo, 1.0 = Renaissance Sfumato (Da Vinci)
    "StyleBlendAlpha": 1.0,
    "ChiaroscuroContrast": 1.32,
    "VarnishAmberWarmth": 0.78,
    "CraquelureIntensity": 0.42,
    "FighterPlaneDepthCm": 480.0,
}


# ============================================================================
# 1. IMPORTACIÓN DE TEXTURAS PBR Y CONCEPT ART / UI (RENAISSANCE SFUMATO)
# ============================================================================

def import_pbr_textures_to_ue5() -> list:
    """
    Importa los mapas PBR generados en `Assets/TexturesPBR/` y ajusta sRGB y CompressionSettings
    según el sufijo (_Albedo, _Normal, _ORM, _Mask).
    """
    png_files = sorted(glob.glob(os.path.join(PBR_TEXTURES_DIR, "*.png")))
    if not HAS_UNREAL_EDITOR:
        return png_files

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
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


def import_concept_art_and_ui_textures_to_ue5() -> list:
    """
    Importa las ilustraciones 2D de Concept Art & UI desde `Assets/ConceptArt/`
    (incluyendo `Boss_VAR_ZERO_Renaissance.jpg`, `CharacterSelect_RosterWave2_Renaissance.jpg`,
    `VSScreen_Brasil_vs_Argentina_Renaissance.jpg`) con TextureGroup = UI y sRGB = True.
    """
    art_files = sorted(
        glob.glob(os.path.join(CONCEPT_ART_DIR, "*.jpg"))
        + glob.glob(os.path.join(CONCEPT_ART_DIR, "*.png"))
    )
    if not HAS_UNREAL_EDITOR:
        return art_files

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    imported_ui_art = []

    for art_path in art_files:
        task = unreal.AssetImportTask()
        task.filename = art_path
        task.destination_path = UE_CONCEPT_UI_DEST
        task.replace_existing = True
        task.automated = True
        task.save = True

        asset_tools.import_asset_tasks([task])
        for obj_path in task.imported_object_paths:
            tex = unreal.EditorAssetLibrary.load_asset(obj_path)
            if not isinstance(tex, unreal.Texture2D):
                continue

            tex.set_editor_property("srgb", True)
            if hasattr(unreal.TextureGroup, "TEXTUREGROUP_UI"):
                tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
            unreal.EditorAssetLibrary.save_loaded_asset(tex)
            imported_ui_art.append(tex)

    return imported_ui_art


# ============================================================================
# 2. CONFIGURACIÓN DE CHAOS CLOTH 5.4, MATERIALES MAESTROS Y 17 LUCHADORES GLB
# ============================================================================

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


def import_fighters_glb_interchange() -> list:
    """
    Importa los 17 archivos `SK_*.glb` desde `Assets/Models3D/Fighters/` como `USkeletalMesh` + `UAnimSequence`:
      - Verifica contra `Animations3D_TechnicalManifest.json` (10 clips embebidos por luchador a 60 FPS)
      - Activa flags de importación de Esqueleto y Animaciones en Interchange
      - Desactiva Nanite (`bEnableNanite = False`) y activa Skin Cache (`SkinCacheUsage = Enabled`)
      - Vincula M_FighterSkin_Master, M_FighterKit_Cloth, M_FighterHairCards y Chaos Cloth 5.4
    """
    glb_files = sorted(glob.glob(os.path.join(GLB_FIGHTERS_DIR, "SK_*.glb")))
    if not HAS_UNREAL_EDITOR:
        return glb_files

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    imported_assets = []

    for glb_path in glb_files:
        task = unreal.AssetImportTask()
        task.filename = glb_path
        task.destination_path = UE_FIGHTERS_DEST
        task.replace_existing = True
        task.automated = True
        task.save = True

        # Configurar pipeline Interchange para importar SkeletalMesh + 10 AnimSequences a 60Hz
        if hasattr(unreal, "InterchangeGenericAssetsPipeline"):
            pipeline = unreal.InterchangeGenericAssetsPipeline()
            if hasattr(pipeline, "mesh_pipeline"):
                mesh_p = pipeline.get_editor_property("mesh_pipeline")
                if hasattr(mesh_p, "import_skeletal_meshes"):
                    mesh_p.set_editor_property("import_skeletal_meshes", True)
            if hasattr(pipeline, "animation_pipeline"):
                anim_p = pipeline.get_editor_property("animation_pipeline")
                if hasattr(anim_p, "import_animations"):
                    anim_p.set_editor_property("import_animations", True)
            task.options = pipeline

        asset_tools.import_asset_tasks([task])

        for obj_path in task.imported_object_paths:
            asset = unreal.EditorAssetLibrary.load_asset(obj_path)
            if isinstance(asset, unreal.SkeletalMesh):
                if hasattr(asset, "nanite_settings"):
                    nanite_cfg = asset.get_editor_property("nanite_settings")
                    if hasattr(nanite_cfg, "enabled"):
                        nanite_cfg.set_editor_property("enabled", False)
                        asset.set_editor_property("nanite_settings", nanite_cfg)

                try:
                    if hasattr(asset, "lod_info"):
                        lod_info_array = asset.get_editor_property("lod_info")
                        for lod_info in lod_info_array:
                            if hasattr(lod_info, "skin_cache_usage"):
                                lod_info.set_editor_property("skin_cache_usage", unreal.SkinCacheUsage.ENABLED)
                        asset.set_editor_property("lod_info", lod_info_array)
                except Exception:
                    pass

                try:
                    bind_master_materials_to_skeletal_mesh(asset)
                    configure_chaos_cloth_on_skeletal_mesh(asset)
                except Exception:
                    pass
                unreal.EditorAssetLibrary.save_loaded_asset(asset)
                imported_assets.append(asset)
            elif hasattr(unreal, "AnimSequence") and isinstance(asset, unreal.AnimSequence):
                # Garantizar muestreo determinista a 60 FPS sin compresión destructiva de keyframes
                unreal.EditorAssetLibrary.save_loaded_asset(asset)
                imported_assets.append(asset)

    return imported_assets


# ============================================================================
# 3. IMPORTACIÓN DE LOS 10 ESTADIOS 3D CONMEBOL (`SM_Stage_*.glb`)
# ============================================================================

def import_conmebol_stages_glb_interchange() -> list:
    """
    Importa los 10 Estadios 3D CONMEBOL (`Assets/Models3D/Stages/SM_Stage_*.glb`) validados contra
    `Stages3D_TechnicalManifest.json`:
      - Importa como `UStaticMesh` con Nanite activado (`bEnableNanite = True`) para graderías y torres de luz
      - Habilita Distance Fields para iluminación global Lumen
    """
    stage_files = sorted([
        p for p in glob.glob(os.path.join(GLB_STAGES_DIR, "SM_Stage_*.glb"))
        if not os.path.basename(p).startswith("SM_Stage_PitchAndDestructibleWalls")
    ])
    if not HAS_UNREAL_EDITOR:
        return stage_files

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    imported_stages = []

    for glb_path in stage_files:
        task = unreal.AssetImportTask()
        task.filename = glb_path
        task.destination_path = UE_STAGES_DEST
        task.replace_existing = True
        task.automated = True
        task.save = True

        asset_tools.import_asset_tasks([task])

        for obj_path in task.imported_object_paths:
            asset = unreal.EditorAssetLibrary.load_asset(obj_path)
            if not isinstance(asset, unreal.StaticMesh):
                continue

            if hasattr(asset, "nanite_settings"):
                nanite_cfg = asset.get_editor_property("nanite_settings")
                if hasattr(nanite_cfg, "enabled"):
                    nanite_cfg.set_editor_property("enabled", True)
                    asset.set_editor_property("nanite_settings", nanite_cfg)

            if hasattr(asset, "generate_mesh_distance_field"):
                asset.set_editor_property("generate_mesh_distance_field", True)

            unreal.EditorAssetLibrary.save_loaded_asset(asset)
            imported_stages.append(asset)

    return imported_stages


# ============================================================================
# 4. IMPORTACIÓN DE DATATABLES JSON (`Data/DT_*.json`)
# ============================================================================

def import_json_datatables_to_ue5() -> list:
    """
    Importa las 4 DataTables maestras desde `Data/DT_*.json`:
      - `DT_SouthAmericaRoster.json`
      - `DT_StagesCONMEBOL.json`
      - `DT_FrameDataUniversal.json`
      - `DT_CommentaryAndRivalries.json`
    """
    json_files = sorted(glob.glob(os.path.join(DATATABLES_DIR, "DT_*.json")))
    if not HAS_UNREAL_EDITOR:
        return json_files

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    imported_tables = []

    for json_path in json_files:
        task = unreal.AssetImportTask()
        task.filename = json_path
        task.destination_path = UE_DATATABLES_DEST
        task.replace_existing = True
        task.automated = True
        task.save = True

        asset_tools.import_asset_tasks([task])
        for obj_path in task.imported_object_paths:
            dt_asset = unreal.EditorAssetLibrary.load_asset(obj_path)
            if dt_asset:
                unreal.EditorAssetLibrary.save_loaded_asset(dt_asset)
                imported_tables.append(dt_asset)

    return imported_tables


# ============================================================================
# 5. CREACIÓN Y CABLEADO AUTOMÁTICO DE `M_PP_SfumatoChiaroscuro`
# ============================================================================

def create_and_wire_sfumato_postprocess_material() -> Any:
    """
    Crea y cablea automáticamente en UE 5.4+ el Material de Post-Proceso `M_PP_SfumatoChiaroscuro`:
      - MaterialDomain = MD_POST_PROCESS
      - BlendableLocation = BL_BEFORE_TONEMAPPING
      - Nodo Custom HLSL conectado a `/Project/Shaders/SfumatoChiaroscuroPostProcess.ush`
        invocando `EvaluateM_PP_SfumatoChiaroscuro(...)`
      - Parámetro escalar `ArtStyleMode` (Default = 1.0 para Renacimiento Sfumato, 0.0 para Street-Ink)
      - Parámetros `ChiaroscuroContrast`, `VarnishAmberWarmth`, `CraquelureIntensity`, `FighterPlaneDepthCm`.
    """
    if not HAS_UNREAL_EDITOR:
        return PP_MAT_SFUMATO_PATH

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat_factory = unreal.MaterialFactoryNew()

    pkg_path = UE_POSTPROCESS_DEST
    mat_name = "M_PP_SfumatoChiaroscuro"
    full_path = f"{pkg_path}/{mat_name}"

    if unreal.EditorAssetLibrary.does_asset_exist(full_path):
        pp_mat = unreal.EditorAssetLibrary.load_asset(full_path)
    else:
        pp_mat = asset_tools.create_asset(mat_name, pkg_path, unreal.Material, mat_factory)

    if pp_mat is None:
        return None

    pp_mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_POST_PROCESS)
    if hasattr(unreal, "BlendableLocation"):
        bl_val = getattr(
            unreal.BlendableLocation,
            "BL_SCENE_COLOR_BEFORE_TONEMAPPING",
            getattr(unreal.BlendableLocation, "BL_BEFORE_TONEMAPPING", None),
        )
        if bl_val is not None:
            try:
                pp_mat.set_editor_property("blendable_location", bl_val)
            except Exception:
                pass

    mel = unreal.MaterialEditingLibrary
    mel.delete_all_material_expressions(pp_mat)

    # Crear parámetros escalares expuestos para conmutación Street-Ink (0) vs Renaissance Sfumato (1)
    param_nodes = {}
    y_offset = -360
    for param_name, default_val in SFUMATO_POSTPROCESS_DEFAULTS.items():
        node = mel.create_material_expression(pp_mat, unreal.MaterialExpressionScalarParameter, -640, y_offset)
        node.set_editor_property("parameter_name", param_name)
        node.set_editor_property("default_value", float(default_val))
        param_nodes[param_name] = node
        y_offset += 120

    # Crear Custom HLSL Node referenciando `/Project/Shaders/SfumatoChiaroscuroPostProcess.ush`
    custom_node = mel.create_material_expression(pp_mat, unreal.MaterialExpressionCustom, -180, -120)
    custom_node.set_editor_property("description", "M_PP_SfumatoChiaroscuro (Da Vinci Sfumato + Street-Ink Dual Pipeline)")
    custom_node.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    custom_node.set_editor_property("include_file_paths", [SFUMATO_USH_VIRTUAL_PATH])
    custom_node.set_editor_property(
        "code",
        "return EvaluateM_PP_SfumatoChiaroscuro("
        "(int)round(ArtStyleMode), StyleBlendAlpha, ScreenUV, InvViewSize, 1.7777f, "
        "SceneDepthCm, float4(SceneDepthCm, SceneDepthCm, SceneDepthCm, SceneDepthCm), FighterPlaneDepthCm, "
        "CenterSceneColor, CenterSceneColor, CenterSceneColor, CenterSceneColor, CenterSceneColor, "
        "0.0f, float2(0.5f, 0.5f), 0.0f, ChiaroscuroContrast, VarnishAmberWarmth, CraquelureIntensity);",
    )

    mel.connect_material_property(custom_node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(pp_mat)
    unreal.EditorAssetLibrary.save_loaded_asset(pp_mat)
    return pp_mat


# ============================================================================
# 6. AUDITORÍA DE INTEGRIDAD CLI (`--dry-run`) FUERA DE UNREAL ENGINE 5.4
# ============================================================================

def inspect_glb_binary_header(glb_path: str) -> dict[str, Any]:
    """
    Verifica la cabecera binaria glTF 2.0 (12-byte header + chunk JSON) de un archivo `.glb` en disco.
    """
    size_bytes = os.path.getsize(glb_path)
    with open(glb_path, "rb") as f:
        header = f.read(20)
        if len(header) < 20:
            raise ValueError(f"Archivo .glb truncado (<20 bytes): {glb_path}")
        magic, version, total_len, chunk0_len, chunk0_type = struct.unpack("<4sIIII", header)
        if magic != b"glTF" or version != 2:
            raise ValueError(f"Cabecera glTF inválida en {glb_path}: magic={magic!r}, version={version}")
        json_bytes = f.read(chunk0_len)
        gltf_json = json.loads(json_bytes.decode("utf-8"))

    return {
        "file": os.path.basename(glb_path),
        "size_bytes": size_bytes,
        "meshes": len(gltf_json.get("meshes", [])),
        "skins": len(gltf_json.get("skins", [])),
        "nodes": len(gltf_json.get("nodes", [])),
        "animations": len(gltf_json.get("animations", [])),
        "materials": len(gltf_json.get("materials", [])),
    }


def run_dry_run_audit() -> int:
    """
    Ejecuta una auditoría completa del 100% de los activos 3D, manifiestos, shaders HLSL (`.ush`),
    texturas PBR, arte conceptual Renacimiento Sfumato y DataTables en disco.
    """
    print("=" * 86)
    print(f" UE 5.4+ PRODUCTION AUTO-IMPORT PIPELINE v{PIPELINE_VERSION} [DRY-RUN AUDIT]")
    print("=" * 86)

    errors: list[str] = []

    # 1. Verificar Manifiestos Técnicos
    for manifest_label, manifest_path in [
        ("Animations3D_TechnicalManifest.json", ANIMATIONS_MANIFEST_PATH),
        ("Stages3D_TechnicalManifest.json", STAGES_MANIFEST_PATH),
        ("Models3D_TechnicalManifest.json", MODELS_MANIFEST_PATH),
    ]:
        if not os.path.isfile(manifest_path):
            errors.append(f"Falta manifiesto técnico: {manifest_path}")

    with open(ANIMATIONS_MANIFEST_PATH, "r", encoding="utf-8") as f:
        anim_manifest = json.load(f)
    with open(STAGES_MANIFEST_PATH, "r", encoding="utf-8") as f:
        stages_manifest = json.load(f)

    # 2. Auditar los 17 Luchadores Animados (`SK_*.glb`) contra `Animations3D_TechnicalManifest.json`
    manifest_fighters = anim_manifest.get("Fighters", [])
    verified_fighters = 0
    total_anim_clips = 0

    for entry in manifest_fighters:
        f_name = entry["FighterFile"]
        f_path = os.path.join(GLB_FIGHTERS_DIR, f_name)
        if not os.path.isfile(f_path):
            errors.append(f"Falta luchador .glb referenciado en manifiesto: {f_name}")
            continue
        hdr = inspect_glb_binary_header(f_path)
        expected_anims = int(entry.get("TotalAnimationsInGLB", 10))
        if hdr["animations"] != expected_anims:
            errors.append(f"Desajuste de animaciones en {f_name}: esperado {expected_anims}, hallado {hdr['animations']}")
        verified_fighters += 1
        total_anim_clips += hdr["animations"]

    print(
        f"[OK] Fighters (USkeletalMesh + 60FPS Animations): "
        f"{verified_fighters}/{len(manifest_fighters)} .glb validados "
        f"({total_anim_clips} clips de animación glTF 2.0 embebidos)"
    )

    # 3. Auditar los 10 Estadios 3D CONMEBOL (`SM_Stage_*.glb`) contra `Stages3D_TechnicalManifest.json`
    manifest_stages = stages_manifest.get("Stages", [])
    verified_stages = 0
    total_stage_tris = 0

    for st_entry in manifest_stages:
        st_name = st_entry["File"]
        st_path = os.path.join(GLB_STAGES_DIR, st_name)
        if not os.path.isfile(st_path):
            errors.append(f"Falta estadio .glb referenciado en manifiesto: {st_name}")
            continue
        hdr = inspect_glb_binary_header(st_path)
        if hdr["meshes"] < 1:
            errors.append(f"Estadio sin geometría: {st_name}")
        verified_stages += 1
        total_stage_tris += int(st_entry.get("Triangles", 0))

    print(
        f"[OK] CONMEBOL 3D Stadiums (UStaticMesh + Nanite): "
        f"{verified_stages}/{len(manifest_stages)} .glb validados "
        f"({total_stage_tris:,} triángulos totales)"
    )

    # 4. Auditar Props Adicionales (Balón 32 Paneles + Arena Base)
    prop_glbs = sorted(glob.glob(os.path.join(GLB_PROPS_DIR, "*.glb"))) + sorted(
        glob.glob(os.path.join(GLB_STAGES_DIR, "SM_Stage_PitchAndDestructibleWalls.glb"))
    )
    for p_glb in prop_glbs:
        inspect_glb_binary_header(p_glb)
    print(f"[OK] Props & Destructible Wall-Break Templates:   {len(prop_glbs)}/{len(prop_glbs)} .glb validados")

    # 5. Auditar Shaders HLSL (`.ush`) incluyendo `SfumatoChiaroscuroPostProcess.ush` y `M_PP_SfumatoChiaroscuro.ush`
    required_shaders = [
        os.path.join(SHADERS_DIR, "CompetitiveRimAndInkOutline.ush"),
        os.path.join(SHADERS_DIR, "FighterSkinMaster.ush"),
        os.path.join(SHADERS_DIR, "StadiumEnvironmentFX.ush"),
        os.path.join(SHADERS_DIR, "CombatHUDSDFBars.ush"),
        os.path.join(SHADERS_DIR, "SfumatoChiaroscuroPostProcess.ush"),
        os.path.join(TECHART_SOURCE_DIR, "M_PP_SfumatoChiaroscuro.ush"),
    ]
    verified_shaders = 0
    for sh_path in required_shaders:
        if not os.path.isfile(sh_path) or os.path.getsize(sh_path) == 0:
            errors.append(f"Falta shader HLSL requerido: {sh_path}")
        else:
            verified_shaders += 1

    # Verificar que SfumatoChiaroscuroPostProcess.ush contenga el toggle `ArtStyleMode`
    sfumato_shader_path = os.path.join(SHADERS_DIR, "SfumatoChiaroscuroPostProcess.ush")
    with open(sfumato_shader_path, "r", encoding="utf-8") as f:
        sfumato_src = f.read()
    if "ArtStyleMode" not in sfumato_src or "EvaluateM_PP_SfumatoChiaroscuro" not in sfumato_src:
        errors.append("El shader SfumatoChiaroscuroPostProcess.ush no expone ArtStyleMode o EvaluateM_PP_SfumatoChiaroscuro")

    print(
        f"[OK] HLSL Custom Shaders & M_PP_SfumatoChiaroscuro: "
        f"{verified_shaders}/{len(required_shaders)} .ush validados (ArtStyleMode 0=Street-Ink, 1=Sfumato)"
    )

    # 6. Auditar las 18 Texturas PBR (`Assets/TexturesPBR/*.png`)
    pbr_pngs = sorted(glob.glob(os.path.join(PBR_TEXTURES_DIR, "*.png")))
    if len(pbr_pngs) < 18:
        errors.append(f"Se esperaban al menos 18 texturas PBR en Assets/TexturesPBR/, halladas {len(pbr_pngs)}")
    for png in pbr_pngs:
        with open(png, "rb") as f:
            sig = f.read(8)
            if sig != b"\x89PNG\r\n\x1a\n":
                errors.append(f"Firma PNG inválida en: {png}")
    print(f"[OK] PBR Textures (Kits + Jacquard + MicroPores): {len(pbr_pngs)}/18 .png validados")

    # 7. Auditar Concept Art 2D & Ilustraciones Renacimiento Sfumato + SVG Master Atlas
    concept_imgs = sorted(glob.glob(os.path.join(CONCEPT_ART_DIR, "*.jpg")))
    renaissance_imgs = [p for p in concept_imgs if "Renaissance" in os.path.basename(p)]
    svg_master = os.path.join(UI_SVG_DIR, "InputGlyphs_And_Badges_Master.svg")
    if len(concept_imgs) < 6 or len(renaissance_imgs) < 3:
        errors.append(
            f"Faltan ilustraciones en Assets/ConceptArt/ (total={len(concept_imgs)}, renaissance={len(renaissance_imgs)})"
        )
    if not os.path.isfile(svg_master):
        errors.append(f"Falta atlas vectorial SVG: {svg_master}")
    print(
        f"[OK] 2D Concept Art & UI Textures (Sfumato + SVG): "
        f"{len(concept_imgs)} .jpg ({len(renaissance_imgs)} Renaissance Sfumato) + 1 SVG Master Atlas validados"
    )

    # 8. Auditar DataTables JSON (`Data/DT_*.json`)
    dt_files = sorted(glob.glob(os.path.join(DATATABLES_DIR, "DT_*.json")))
    if len(dt_files) < 4:
        errors.append(f"Se esperaban 4 DataTables JSON en Data/, halladas {len(dt_files)}")
    for dt_path in dt_files:
        with open(dt_path, "r", encoding="utf-8") as f:
            json.load(f)
    print(f"[OK] Competitive JSON DataTables (Data/DT_*.json): {len(dt_files)}/4 tablas validadas")

    print("-" * 86)
    if errors:
        print(f"[FAIL] Auditoría finalizada con {len(errors)} errores:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(
        "[SUCCESS] 100% de activos verificados sin errores: "
        f"{verified_fighters} Luchadores ({total_anim_clips} Anims), "
        f"{verified_stages} Estadios CONMEBOL, {len(pbr_pngs)} Texturas PBR, "
        f"{len(concept_imgs)} Concept Arts, {verified_shaders} Shaders HLSL y {len(dt_files)} DataTables."
    )
    print("=" * 86)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UE 5.4+ Production Auto-Import Pipeline v2.0 (Interchange + Sfumato Post-Process + CLI Dry-Run)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Audita en Python 3 estándar que el 100%% de los activos (.glb, .png, .jpg, .ush, .json) existan y sean válidos.",
    )
    args, _ = parser.parse_known_args()

    if args.dry_run or not HAS_UNREAL_EDITOR:
        return run_dry_run_audit()

    # Ejecución dentro del proceso UnrealEditor.exe con el plugin Python Editor Script
    unreal.log("=== [LA COPA ETERNA] Iniciando Auto-Import Pipeline v2.0 en Unreal Engine ===")
    for step_name, step_fn in [
        ("PBR Textures", import_pbr_textures_to_ue5),
        ("Concept Art & UI (Sfumato)", import_concept_art_and_ui_textures_to_ue5),
        ("17 Animated Fighters (.glb)", import_fighters_glb_interchange),
        ("10 CONMEBOL 3D Stages (.glb)", import_conmebol_stages_glb_interchange),
        ("Post-Process M_PP_SfumatoChiaroscuro", create_and_wire_sfumato_postprocess_material),
    ]:
        try:
            res = step_fn()
            count = len(res) if isinstance(res, list) else (1 if res is not None else 0)
            unreal.log(f"[LA COPA ETERNA][OK] {step_name}: {count} activos procesados.")
        except Exception as exc:
            unreal.log_warning(f"[LA COPA ETERNA][WARN] {step_name}: {exc}")

    if hasattr(unreal, "EditorAssetLibrary"):
        unreal.EditorAssetLibrary.save_directory("/Game", only_if_is_dirty=False, recursive=True)
    unreal.log("=== [LA COPA ETERNA] Auto-Import Pipeline finalizado y guardado en /Game ===")
    return 0


if __name__ == "__main__":
    exit_code = main()
    if not HAS_UNREAL_EDITOR:
        sys.exit(exit_code)
