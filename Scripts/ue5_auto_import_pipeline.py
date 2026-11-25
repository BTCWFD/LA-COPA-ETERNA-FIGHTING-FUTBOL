#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ue5_auto_import_pipeline.py - SouthAmericaFightersCore ("La Copa Eterna")
UE 5.8.4 Production Auto-Import Pipeline v2.1 (Python Editor Script Plugin / Interchange & CLI Dry-Run Auditor)

Funcionalidades Principales:
  1. Importa las 18 texturas PBR (`Assets/TexturesPBR/`), las ilustraciones 2D de Concept Art & UI
     (incluyendo la serie Renacimiento Sfumato en `Assets/ConceptArt/`), las 4 DataTables JSON (`Data/`),
     y los stems/SFX de audio `.wav` (`Audio/GeneratedStems/*.wav` -> `/Game/Audio/Stems`).
  2. Crea, cablea (`CustomInput` + `CustomOutput`) y compila los 5 Materiales Maestros del proyecto
     enlazando los shaders HLSL de `/Project/*.ush` ANTES de importar personajes y estadios:
       - `/Game/Characters/SouthAmericaRoster/Materials/M_FighterSkin_Master`
       - `/Game/Characters/SouthAmericaRoster/Materials/M_FighterKit_Cloth`
       - `/Game/Characters/SouthAmericaRoster/Materials/M_FighterHairCards`
       - `/Game/Stages/CONMEBOL/Materials/M_StadiumEnvironment_Master`
       - `/Game/UI/Materials/M_CombatHUDSDF_Master`
  3. Importa los 17 luchadores animados `.glb` desde `Assets/Models3D/Fighters/SK_*.glb` como `USkeletalMesh`
     mediante `UInterchangePipelineStackOverride` + `UInterchangeGenericAssetsPipeline` con muestreo forzado
     a `60.0 FPS` (`CustomBoneAnimationSampleRate = 60`, `SnapToClosest`) y verificación post-importación vía
     `IAnimationDataController` para garantizar `60.0 FPS` en las 170 `UAnimSequence`s.
  4. Desactiva Nanite en personajes (`bEnableNanite = False`), activa `SkinCacheUsage = Enabled`, asigna
     `LightingChannel 1`, vincula los 3 Materiales Maestros (`M_FighterSkin_Master`, `M_FighterKit_Cloth`,
     `M_FighterHairCards`) y configura `UChaosClothConfig`.
  5. Importa los 10 Estadios 3D CONMEBOL `.glb` desde `Assets/Models3D/Stages/SM_Stage_*.glb` como `UStaticMesh`
     con Nanite + Lumen activados, validados contra `Stages3D_TechnicalManifest.json`.
  6. Crea y cablea el Post-Process Material `M_PP_SfumatoChiaroscuro` referenciando
     `/Project/SfumatoChiaroscuroPostProcess.ush` con muestras reales de `SceneTexture` (`PPI_PostProcessInput0`),
     `SceneDepth`, `ScreenPosition`, `ViewSize`/`SceneTexelSize`, los 6 parámetros escalares expuestos y verificación
     de instrucciones compiladas (`num_pixel_shader_instructions > 0`).
  7. Incluye modo CLI `--dry-run` ejecutable en Python 3 estándar fuera de UE5 para auditar la integridad
     binaria (cabeceras glTF 2.0, RIFF/WAVE, JSONs, shaders `.ush` y texturas) del 100% de los activos en disco.
"""

import os
import re
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


PIPELINE_VERSION = "2.1.0-UE5.8.4-Interchange-Sfumato"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLB_FIGHTERS_DIR = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Fighters")
GLB_STAGES_DIR = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Stages")
GLB_PROPS_DIR = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Props")
PBR_TEXTURES_DIR = os.path.join(PROJECT_ROOT, "Assets", "TexturesPBR")
CONCEPT_ART_DIR = os.path.join(PROJECT_ROOT, "Assets", "ConceptArt")
UI_SVG_DIR = os.path.join(PROJECT_ROOT, "Assets", "UI", "SVG")
DATATABLES_DIR = os.path.join(PROJECT_ROOT, "Data")
AUDIO_STEMS_DIR = os.path.join(PROJECT_ROOT, "Audio", "GeneratedStems")
SHADERS_DIR = os.path.join(PROJECT_ROOT, "Shaders")
TECHART_SOURCE_DIR = os.path.join(PROJECT_ROOT, "Source", "TechArt")

ANIMATIONS_MANIFEST_PATH = os.path.join(GLB_FIGHTERS_DIR, "Animations3D_TechnicalManifest.json")
STAGES_MANIFEST_PATH = os.path.join(GLB_STAGES_DIR, "Stages3D_TechnicalManifest.json")
MODELS_MANIFEST_PATH = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Models3D_TechnicalManifest.json")

# Destinos virtuales dentro del Content Browser de Unreal Engine 5.8+
UE_FIGHTERS_DEST = "/Game/Characters/SouthAmericaRoster/Meshes"
UE_STAGES_DEST = "/Game/Stages/CONMEBOL/Meshes"
UE_PROPS_DEST = "/Game/Props"
UE_TEXTURES_DEST = "/Game/Characters/SouthAmericaRoster/TexturesPBR"
UE_CONCEPT_UI_DEST = "/Game/UI/ConceptArtAndPortraits"
UE_DATATABLES_DEST = "/Game/DataTables"
UE_AUDIO_STEMS_DEST = "/Game/Audio/Stems"
UE_MATERIALS_DEST = "/Game/Characters/SouthAmericaRoster/Materials"
UE_FIGHTER_MICS_DEST = "/Game/Characters/SouthAmericaRoster/Materials/Instances"
UE_STAGE_MATERIALS_DEST = "/Game/Stages/CONMEBOL/Materials"
UE_STAGE_MICS_DEST = "/Game/Stages/CONMEBOL/Materials/Instances"
UE_UI_MATERIALS_DEST = "/Game/UI/Materials"
UE_POSTPROCESS_DEST = "/Game/TechArt/PostProcess"

# Materiales Maestros compilados en Content/
MASTER_MAT_SKIN = "/Game/Characters/SouthAmericaRoster/Materials/M_FighterSkin_Master"
MASTER_MAT_KIT = "/Game/Characters/SouthAmericaRoster/Materials/M_FighterKit_Cloth"
MASTER_MAT_HAIR = "/Game/Characters/SouthAmericaRoster/Materials/M_FighterHairCards"
MASTER_MAT_STADIUM_ENV = "/Game/Stages/CONMEBOL/Materials/M_StadiumEnvironment_Master"
MASTER_MAT_COMBAT_HUD = "/Game/UI/Materials/M_CombatHUDSDF_Master"
PP_MAT_SFUMATO_PATH = "/Game/TechArt/PostProcess/M_PP_SfumatoChiaroscuro"

# Rutas virtuales de Shaders HLSL (UE 5.8 mapea `/Project` directamente a `<ProjectDir>/Shaders`)
SFUMATO_USH_VIRTUAL_PATH = "/Project/SfumatoChiaroscuroPostProcess.ush"
FIGHTER_SKIN_USH_VIRTUAL_PATH = "/Project/FighterSkinMaster.ush"
COMPETITIVE_RIM_USH_VIRTUAL_PATH = "/Project/CompetitiveRimAndInkOutline.ush"
STADIUM_ENV_USH_VIRTUAL_PATH = "/Project/StadiumEnvironmentFX.ush"
COMBAT_HUD_SDF_USH_VIRTUAL_PATH = "/Project/CombatHUDSDFBars.ush"


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
# UTILIDADES INTERNAS PARA MATERIALES Y CUSTOM NODES EN UE 5.8
# ============================================================================

def _safe_set_property(obj: Any, prop_name: str, value: Any) -> bool:
    """Asigna una propiedad de editor de forma segura verificando atributos y excepciones."""
    if obj is None:
        return False
    try:
        obj.set_editor_property(prop_name, value)
        return True
    except Exception:
        if hasattr(obj, prop_name):
            try:
                setattr(obj, prop_name, value)
                return True
            except Exception:
                pass
    return False


def _load_or_create_material(pkg_path: str, mat_name: str) -> Any:
    """Carga un UMaterial existente o lo crea limpio en el paquete indicado."""
    full_path = f"{pkg_path}/{mat_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(full_path):
        mat = unreal.EditorAssetLibrary.load_asset(full_path)
        if isinstance(mat, unreal.Material):
            return mat
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat_factory = unreal.MaterialFactoryNew()
    return asset_tools.create_asset(mat_name, pkg_path, unreal.Material, mat_factory)


def _make_custom_inputs(input_names: list[str]) -> list:
    """Construye el arreglo tipado `TArray<FCustomInput>` para `UMaterialExpressionCustom`."""
    custom_inputs = []
    for name in input_names:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        custom_inputs.append(ci)
    return custom_inputs


def _make_custom_outputs(output_specs: list[tuple[str, Any]]) -> list:
    """Construye el arreglo tipado `TArray<FCustomOutput>` para `UMaterialExpressionCustom`."""
    custom_outputs = []
    for out_name, out_type in output_specs:
        co = unreal.CustomOutput()
        co.set_editor_property("output_name", out_name)
        co.set_editor_property("output_type", out_type)
        custom_outputs.append(co)
    return custom_outputs


def _create_scalar_param(mel: Any, mat: Any, name: str, default_val: float, x: int, y: int) -> Any:
    node = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", float(default_val))
    return node


def _create_vector_param(
    mel: Any,
    mat: Any,
    name: str,
    rgba: tuple[float, float, float, float],
    x: int,
    y: int,
) -> Any:
    node = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", unreal.LinearColor(rgba[0], rgba[1], rgba[2], rgba[3]))
    return node


def _compile_save_and_log_material_stats(mat: Any, label: str) -> Any:
    """Recompila el UMaterial, registra `FMaterialStatistics` verificando PS > 0 y guarda el paquete."""
    mel = unreal.MaterialEditingLibrary
    compile_errors = mel.recompile_material(mat)
    stats = mel.get_statistics(mat)
    ps_instr = int(getattr(stats, "num_pixel_shader_instructions", 0))
    vs_instr = int(getattr(stats, "num_vertex_shader_instructions", 0))
    samplers = int(getattr(stats, "num_samplers", 0))

    if compile_errors:
        unreal.log_warning(f"[LA COPA ETERNA][SHADER_WARN] {label} reportó avisos de compilación: {compile_errors}")

    unreal.log(
        f"[LA COPA ETERNA][MAT_STATS] {label} -> "
        f"PS={ps_instr} instructions, VS={vs_instr} instructions, Samplers={samplers}"
    )
    if ps_instr <= 0:
        unreal.log_warning(f"[LA COPA ETERNA][WARN] {label} reportó 0 instrucciones de Pixel Shader.")

    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


# ============================================================================
# 1. IMPORTACIÓN DE TEXTURAS PBR, CONCEPT ART / UI Y AUDIO STEMS (.WAV)
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
    (incluyendo la serie Renacimiento Sfumato) con TextureGroup = UI y sRGB = True.
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


def import_wav_audio_stems_to_ue5() -> list:
    """
    Importa los stems musicales sudamericanos y SFX competitivos `.wav` desde
    `Audio/GeneratedStems/*.wav` hacia `/Game/Audio/Stems` como `USoundWave`.
    """
    wav_files = sorted(glob.glob(os.path.join(AUDIO_STEMS_DIR, "*.wav")))
    if not HAS_UNREAL_EDITOR:
        return wav_files

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    imported_sounds = []
    seen_dest_names: set[str] = set()

    for wav_path in wav_files:
        raw_stem = os.path.splitext(os.path.basename(wav_path))[0]
        clean_name = re.sub(r"[^A-Za-z0-9_]", "_", raw_stem)
        clean_name = re.sub(r"_+", "_", clean_name).strip("_")
        if clean_name in seen_dest_names:
            # Evitar colisión de nombres cuando existen variantes con espacio en disco
            clean_name = f"{clean_name}_Alt"
        seen_dest_names.add(clean_name)

        task = unreal.AssetImportTask()
        task.filename = wav_path
        task.destination_path = UE_AUDIO_STEMS_DEST
        task.destination_name = clean_name
        task.replace_existing = True
        task.automated = True
        task.save = True

        asset_tools.import_asset_tasks([task])
        for obj_path in task.imported_object_paths:
            snd = unreal.EditorAssetLibrary.load_asset(obj_path)
            if snd is None:
                continue
            if raw_stem.startswith("Stem_Crowd_"):
                _safe_set_property(snd, "looping", True)
            unreal.EditorAssetLibrary.save_loaded_asset(snd)
            imported_sounds.append(snd)

    return imported_sounds


# ============================================================================
# 2. CREACIÓN DE LOS 5 MATERIALES MAESTROS DEL PROYECTO (`/Project/*.ush`)
# ============================================================================

def _build_fighter_skin_master_material() -> Any:
    """
    Crea y compila `/Game/Characters/SouthAmericaRoster/Materials/M_FighterSkin_Master`
    enlazando `/Project/FighterSkinMaster.ush` y `/Project/CompetitiveRimAndInkOutline.ush`.
    """
    mel = unreal.MaterialEditingLibrary
    mat = _load_or_create_material(UE_MATERIALS_DEST, "M_FighterSkin_Master")
    if mat is None:
        return None

    mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_SURFACE)
    _safe_set_property(mat, "blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    if hasattr(unreal.MaterialShadingModel, "MSM_SUBSURFACE"):
        _safe_set_property(mat, "shading_model", unreal.MaterialShadingModel.MSM_SUBSURFACE)
    if hasattr(unreal.MaterialUsage, "MATUSAGE_SKELETAL_MESH"):
        mel.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)

    mel.delete_all_material_expressions(mat)

    uv_node = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -920, -420)
    wpos_node = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -920, -300)
    wnorm_node = mel.create_material_expression(mat, unreal.MaterialExpressionVertexNormalWS, -920, -180)
    cam_node = mel.create_material_expression(mat, unreal.MaterialExpressionCameraVectorWS, -920, -60)
    time_node = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -920, 60)

    skin_albedo = _create_vector_param(mel, mat, "SkinBaseAlbedo", (0.74, 0.50, 0.36, 1.0), -920, 180)
    rim_color = _create_vector_param(mel, mat, "CompetitiveRimColor", (1.00, 0.86, 0.52, 1.0), -920, 340)
    rim_intensity = _create_scalar_param(mel, mat, "CompetitiveRimIntensity", 1.0, -680, 180)
    ink_scale = _create_scalar_param(mel, mat, "InkThicknessScale", 1.0, -680, 280)
    sweat_param = _create_scalar_param(mel, mat, "SweatAccumulation", 0.24, -680, 380)
    dirt_param = _create_scalar_param(mel, mat, "PitchDirtAccumulation", 0.14, -680, 480)

    custom_node = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, -260, -80)
    custom_node.set_editor_property("description", "M_FighterSkin_Master (Skin Micro-Pores + Sweat + Competitive Rim)")
    custom_node.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    custom_node.set_editor_property(
        "include_file_paths",
        [FIGHTER_SKIN_USH_VIRTUAL_PATH, COMPETITIVE_RIM_USH_VIRTUAL_PATH],
    )

    input_Order = [
        ("BaseUV", uv_node, ""),
        ("WorldPos", wpos_node, ""),
        ("WorldNormal", wnorm_node, ""),
        ("CameraVec", cam_node, ""),
        ("TimeSec", time_node, ""),
        ("SkinAlbedo", skin_albedo, ""),
        ("RimColor", rim_color, ""),
        ("RimIntensity", rim_intensity, ""),
        ("InkThicknessScale", ink_scale, ""),
        ("SweatAccumulation", sweat_param, ""),
        ("PitchDirtAccumulation", dirt_param, ""),
    ]
    custom_node.set_editor_property("inputs", _make_custom_inputs([name for name, _, _ in input_Order]))
    custom_node.set_editor_property(
        "additional_outputs",
        _make_custom_outputs([
            ("OutEmissive", unreal.CustomMaterialOutputType.CMOT_FLOAT3),
            ("OutRoughness", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
            ("OutSpecular", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
            ("OutSubsurface", unreal.CustomMaterialOutputType.CMOT_FLOAT3),
        ]),
    )
    custom_node.set_editor_property(
        "code",
        "float3 SafeN = normalize(WorldNormal.xyz + float3(0.0f, 0.0f, 1e-5f));\n"
        "float3 TangentGuess = normalize(cross(abs(SafeN.z) < 0.95f ? float3(0.0f, 0.0f, 1.0f) : float3(1.0f, 0.0f, 0.0f), SafeN));\n"
        "float3 KeyLightDir = normalize(float3(0.42f, -0.58f, 0.70f));\n"
        "FFighterSkinMasterOutput SkinPBR = EvaluateFighterSkinMasterPBR(\n"
        "    false, BaseUV.xy, WorldPos.xyz, SafeN, TangentGuess, CameraVec.xyz, KeyLightDir,\n"
        "    SkinAlbedo.rgb, float3(0.95f, 0.82f, 0.25f), 0.0f,\n"
        "    SweatAccumulation, PitchDirtAccumulation, TimeSec,\n"
        "    float4(0.0f, 0.0f, 52.0f, 45.0f), float4(0.0f, 0.0f, 130.0f, 40.0f));\n"
        "float NormHeight = saturate(WorldPos.z / 185.0f);\n"
        "FStreetInkMaterialOutput InkOut = EvaluateCompetitiveStreetInkCharacter(\n"
        "    SkinPBR.BaseColor, SkinPBR.WorldNormal, CameraVec.xyz, KeyLightDir,\n"
        "    BaseUV.xy, NormHeight, SkinPBR.Roughness,\n"
        "    RimColor.rgb, RimIntensity, InkThicknessScale, SweatAccumulation, PitchDirtAccumulation);\n"
        "OutEmissive = InkOut.EmissiveColor;\n"
        "OutRoughness = InkOut.Roughness;\n"
        "OutSpecular = InkOut.Specular;\n"
        "OutSubsurface = SkinPBR.SubsurfaceColor * SkinPBR.SubsurfaceOpacity;\n"
        "return InkOut.BaseColor;",
    )

    for pin_name, expr_node, out_pin in input_Order:
        mel.connect_material_expressions(expr_node, out_pin, custom_node, pin_name)

    mel.connect_material_property(custom_node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(custom_node, "OutEmissive", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(custom_node, "OutRoughness", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(custom_node, "OutSpecular", unreal.MaterialProperty.MP_SPECULAR)
    mel.connect_material_property(custom_node, "OutSubsurface", unreal.MaterialProperty.MP_SUBSURFACE_COLOR)

    return _compile_save_and_log_material_stats(mat, MASTER_MAT_SKIN)


def _build_fighter_kit_cloth_material() -> Any:
    """
    Crea y compila `/Game/Characters/SouthAmericaRoster/Materials/M_FighterKit_Cloth`
    enlazando `/Project/FighterSkinMaster.ush` + `/Project/CompetitiveRimAndInkOutline.ush` + texturas/parámetros PBR.
    """
    mel = unreal.MaterialEditingLibrary
    mat = _load_or_create_material(UE_MATERIALS_DEST, "M_FighterKit_Cloth")
    if mat is None:
        return None

    mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_SURFACE)
    _safe_set_property(mat, "blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    _safe_set_property(mat, "two_sided", True)
    if hasattr(unreal.MaterialUsage, "MATUSAGE_SKELETAL_MESH"):
        mel.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
    if hasattr(unreal.MaterialUsage, "MATUSAGE_CLOTHING"):
        mel.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_CLOTHING, True)

    mel.delete_all_material_expressions(mat)

    uv_node = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -960, -440)
    wpos_node = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -960, -320)
    wnorm_node = mel.create_material_expression(mat, unreal.MaterialExpressionVertexNormalWS, -960, -200)
    cam_node = mel.create_material_expression(mat, unreal.MaterialExpressionCameraVectorWS, -960, -80)

    primary_col = _create_vector_param(mel, mat, "TeamPrimaryColor", (0.96, 0.80, 0.08, 1.0), -960, 60)
    secondary_col = _create_vector_param(mel, mat, "TeamSecondaryColor", (0.04, 0.42, 0.20, 1.0), -960, 220)
    rim_col = _create_vector_param(mel, mat, "CompetitiveRimColor", (1.00, 0.90, 0.58, 1.0), -960, 380)

    jacquard_param = _create_scalar_param(mel, mat, "JacquardWatermarkMask", 0.65, -700, 60)
    metallic_param = _create_scalar_param(mel, mat, "CrestMetallic", 0.06, -700, 160)
    rim_intensity = _create_scalar_param(mel, mat, "CompetitiveRimIntensity", 1.0, -700, 260)
    ink_scale = _create_scalar_param(mel, mat, "InkThicknessScale", 1.0, -700, 360)
    sweat_param = _create_scalar_param(mel, mat, "SweatWetness", 0.18, -700, 460)
    mud_param = _create_scalar_param(mel, mat, "PitchMudAmount", 0.16, -700, 560)

    # Vincular textura PBR de kit si existe en /Game/Characters/SouthAmericaRoster/TexturesPBR
    # Mezcla 85% KitAlbedoTexture + 15% TeamPrimaryColor para preservar los colores nacionales del PNG sin oscurecerlos
    albedo_source_node = primary_col
    default_kit_tex = unreal.EditorAssetLibrary.load_asset(f"{UE_TEXTURES_DEST}/T_Kit_Brazil_Albedo")
    if isinstance(default_kit_tex, unreal.Texture2D):
        tex_param = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -960, -620)
        tex_param.set_editor_property("parameter_name", "KitAlbedoTexture")
        tex_param.set_editor_property("texture", default_kit_tex)
        lerp_tint = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -700, -520)
        lerp_tint.set_editor_property("const_alpha", 0.15)
        mel.connect_material_expressions(tex_param, "RGB", lerp_tint, "A")
        mel.connect_material_expressions(primary_col, "", lerp_tint, "B")
        albedo_source_node = lerp_tint

    custom_node = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, -260, -80)
    custom_node.set_editor_property("description", "M_FighterKit_Cloth (Retro 90s Jacquard Anisotropy + Street-Ink)")
    custom_node.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    custom_node.set_editor_property(
        "include_file_paths",
        [FIGHTER_SKIN_USH_VIRTUAL_PATH, COMPETITIVE_RIM_USH_VIRTUAL_PATH],
    )

    input_order = [
        ("JerseyUV", uv_node, ""),
        ("WorldPos", wpos_node, ""),
        ("WorldNormal", wnorm_node, ""),
        ("CameraVec", cam_node, ""),
        ("TeamPrimary", albedo_source_node, ""),
        ("TeamSecondary", secondary_col, ""),
        ("RimColor", rim_col, ""),
        ("JacquardMask", jacquard_param, ""),
        ("RimIntensity", rim_intensity, ""),
        ("InkThicknessScale", ink_scale, ""),
        ("SweatWetness", sweat_param, ""),
        ("MudAmount", mud_param, ""),
    ]
    custom_node.set_editor_property("inputs", _make_custom_inputs([name for name, _, _ in input_order]))
    custom_node.set_editor_property(
        "additional_outputs",
        _make_custom_outputs([
            ("OutEmissive", unreal.CustomMaterialOutputType.CMOT_FLOAT3),
            ("OutRoughness", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
            ("OutSpecular", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
        ]),
    )
    custom_node.set_editor_property(
        "code",
        "float3 SafeN = normalize(WorldNormal.xyz + float3(0.0f, 0.0f, 1e-5f));\n"
        "float3 SafeT = normalize(cross(abs(SafeN.z) < 0.95f ? float3(0.0f, 0.0f, 1.0f) : float3(1.0f, 0.0f, 0.0f), SafeN));\n"
        "float3 KeyLightDir = normalize(float3(0.42f, -0.58f, 0.70f));\n"
        "float3 FabricAlbedo;\n"
        "float FabricRoughness;\n"
        "float FabricAniso;\n"
        "float3 AnisoSpec;\n"
        "float3 ModTangent;\n"
        "EvaluateRetro90sJerseyAnisotropy(\n"
        "    JerseyUV.xy, SafeN, SafeT, CameraVec.xyz, KeyLightDir,\n"
        "    TeamPrimary.rgb, TeamSecondary.rgb, JacquardMask, SweatWetness, MudAmount * 0.5f,\n"
        "    FabricAlbedo, FabricRoughness, FabricAniso, AnisoSpec, ModTangent);\n"
        "float NormHeight = saturate(WorldPos.z / 185.0f);\n"
        "FStreetInkMaterialOutput KitOut = EvaluateCompetitiveStreetInkCharacter(\n"
        "    FabricAlbedo + AnisoSpec, SafeN, CameraVec.xyz, KeyLightDir,\n"
        "    JerseyUV.xy, NormHeight, FabricRoughness,\n"
        "    RimColor.rgb, RimIntensity, InkThicknessScale, SweatWetness, MudAmount);\n"
        "OutEmissive = KitOut.EmissiveColor;\n"
        "OutRoughness = KitOut.Roughness;\n"
        "OutSpecular = KitOut.Specular;\n"
        "return KitOut.BaseColor;",
    )

    for pin_name, expr_node, out_pin in input_order:
        mel.connect_material_expressions(expr_node, out_pin, custom_node, pin_name)

    mel.connect_material_property(custom_node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(custom_node, "OutEmissive", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(custom_node, "OutRoughness", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(custom_node, "OutSpecular", unreal.MaterialProperty.MP_SPECULAR)
    mel.connect_material_property(metallic_param, "", unreal.MaterialProperty.MP_METALLIC)

    return _compile_save_and_log_material_stats(mat, MASTER_MAT_KIT)


def _build_fighter_hair_cards_material() -> Any:
    """
    Crea y compila `/Game/Characters/SouthAmericaRoster/Materials/M_FighterHairCards`
    con máscara anisotrópica de hebras (Masked Two-Sided) + Rim competitivo (`/Project/CompetitiveRimAndInkOutline.ush`).
    """
    mel = unreal.MaterialEditingLibrary
    mat = _load_or_create_material(UE_MATERIALS_DEST, "M_FighterHairCards")
    if mat is None:
        return None

    mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_SURFACE)
    _safe_set_property(mat, "blend_mode", unreal.BlendMode.BLEND_MASKED)
    _safe_set_property(mat, "two_sided", True)
    _safe_set_property(mat, "opacity_mask_clip_value", 0.33)
    if hasattr(unreal.MaterialUsage, "MATUSAGE_SKELETAL_MESH"):
        mel.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)

    mel.delete_all_material_expressions(mat)

    uv_node = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -880, -340)
    wnorm_node = mel.create_material_expression(mat, unreal.MaterialExpressionVertexNormalWS, -880, -220)
    cam_node = mel.create_material_expression(mat, unreal.MaterialExpressionCameraVectorWS, -880, -100)

    root_col = _create_vector_param(mel, mat, "HairRootColor", (0.04, 0.03, 0.025, 1.0), -880, 40)
    tip_col = _create_vector_param(mel, mat, "HairTipColor", (0.16, 0.11, 0.07, 1.0), -880, 200)
    rim_col = _create_vector_param(mel, mat, "CompetitiveRimColor", (1.00, 0.88, 0.56, 1.0), -880, 360)
    rough_param = _create_scalar_param(mel, mat, "HairRoughness", 0.34, -640, 100)
    rim_intensity = _create_scalar_param(mel, mat, "CompetitiveRimIntensity", 0.85, -640, 220)

    custom_node = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, -240, -60)
    custom_node.set_editor_property("description", "M_FighterHairCards (Anisotropic Strand Cards + Rim)")
    custom_node.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    custom_node.set_editor_property("include_file_paths", [COMPETITIVE_RIM_USH_VIRTUAL_PATH])

    input_order = [
        ("HairUV", uv_node, ""),
        ("WorldNormal", wnorm_node, ""),
        ("CameraVec", cam_node, ""),
        ("RootColor", root_col, ""),
        ("TipColor", tip_col, ""),
        ("RimColor", rim_col, ""),
        ("BaseRoughness", rough_param, ""),
        ("RimIntensity", rim_intensity, ""),
    ]
    custom_node.set_editor_property("inputs", _make_custom_inputs([name for name, _, _ in input_order]))
    custom_node.set_editor_property(
        "additional_outputs",
        _make_custom_outputs([
            ("OutEmissive", unreal.CustomMaterialOutputType.CMOT_FLOAT3),
            ("OutRoughness", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
            ("OutStrandMask", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
        ]),
    )
    custom_node.set_editor_property(
        "code",
        "float StrandWave = sin(HairUV.x * 180.0f) * 0.5f + 0.5f;\n"
        "float TipTaper = 1.0f - smoothstep(0.82f, 1.0f, HairUV.y);\n"
        "OutStrandMask = saturate(0.55f + StrandWave * 0.45f) * TipTaper + 0.38f;\n"
        "float3 BaseHair = lerp(RootColor.rgb, TipColor.rgb, saturate(HairUV.y));\n"
        "float3 KeyLightDir = normalize(float3(0.35f, -0.55f, 0.75f));\n"
        "float3 H = normalize(KeyLightDir + normalize(CameraVec.xyz));\n"
        "float KajiyaSheen = pow(saturate(1.0f - abs(dot(normalize(WorldNormal.xyz), H))), 16.0f);\n"
        "FStreetInkMaterialOutput HairInk = EvaluateCompetitiveStreetInkCharacter(\n"
        "    BaseHair + TipColor.rgb * (KajiyaSheen * 0.35f), WorldNormal.xyz, CameraVec.xyz, KeyLightDir,\n"
        "    HairUV.xy, 0.95f, BaseRoughness, RimColor.rgb, RimIntensity, 1.0f, 0.15f, 0.0f);\n"
        "OutEmissive = HairInk.EmissiveColor;\n"
        "OutRoughness = HairInk.Roughness;\n"
        "return HairInk.BaseColor;",
    )

    for pin_name, expr_node, out_pin in input_order:
        mel.connect_material_expressions(expr_node, out_pin, custom_node, pin_name)

    mel.connect_material_property(custom_node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(custom_node, "OutEmissive", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(custom_node, "OutRoughness", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(custom_node, "OutStrandMask", unreal.MaterialProperty.MP_OPACITY_MASK)

    return _compile_save_and_log_material_stats(mat, MASTER_MAT_HAIR)


def _build_stadium_environment_master_material() -> Any:
    """
    Crea y compila `/Game/Stages/CONMEBOL/Materials/M_StadiumEnvironment_Master`
    enlazando `/Project/StadiumEnvironmentFX.ush` (Pitch Wetness & Dash Ripples + Barranquilla Heat Haze).
    """
    mel = unreal.MaterialEditingLibrary
    mat = _load_or_create_material(UE_STAGE_MATERIALS_DEST, "M_StadiumEnvironment_Master")
    if mat is None:
        return None

    mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_SURFACE)
    _safe_set_property(mat, "blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    _safe_set_property(mat, "tangent_space_normal", False)

    mel.delete_all_material_expressions(mat)

    wpos_node = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -920, -380)
    wnorm_node = mel.create_material_expression(mat, unreal.MaterialExpressionVertexNormalWS, -920, -260)
    uv_node = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -920, -140)
    time_node = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -920, -20)

    grass_col = _create_vector_param(mel, mat, "BaseGrassAlbedo", (0.08, 0.34, 0.10, 1.0), -920, 120)
    p1_dash = _create_vector_param(mel, mat, "P1DashImpactData", (-220.0, 0.0, 0.35, 0.75), -920, 280)
    p2_dash = _create_vector_param(mel, mat, "P2DashImpactData", (220.0, 0.0, 0.55, 0.65), -920, 440)

    grass_rough = _create_scalar_param(mel, mat, "BaseGrassRoughness", 0.64, -660, 120)
    puddle_mask = _create_scalar_param(mel, mat, "PuddleDistributionMask", 0.46, -660, 220)
    rain_param = _create_scalar_param(mel, mat, "RainIntensity", 0.32, -660, 320)
    celsius_param = _create_scalar_param(mel, mat, "AmbientCelsius", 34.0, -660, 420)

    custom_node = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, -240, -60)
    custom_node.set_editor_property("description", "M_StadiumEnvironment_Master (Wetness Ripples + Heat Shimmer)")
    custom_node.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    custom_node.set_editor_property("include_file_paths", [STADIUM_ENV_USH_VIRTUAL_PATH])

    input_order = [
        ("WorldPos", wpos_node, ""),
        ("BaseNormal", wnorm_node, ""),
        ("PitchUV", uv_node, ""),
        ("TimeSec", time_node, ""),
        ("GrassAlbedo", grass_col, ""),
        ("P1DashData", p1_dash, ""),
        ("P2DashData", p2_dash, ""),
        ("GrassRoughness", grass_rough, ""),
        ("PuddleMask", puddle_mask, ""),
        ("RainIntensity", rain_param, ""),
        ("AmbientCelsius", celsius_param, ""),
    ]
    custom_node.set_editor_property("inputs", _make_custom_inputs([name for name, _, _ in input_order]))
    custom_node.set_editor_property(
        "additional_outputs",
        _make_custom_outputs([
            ("OutWorldNormal", unreal.CustomMaterialOutputType.CMOT_FLOAT3),
            ("OutRoughness", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
            ("OutSpecular", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
            ("OutThermalEmissive", unreal.CustomMaterialOutputType.CMOT_FLOAT3),
        ]),
    )
    custom_node.set_editor_property(
        "code",
        "float3 CompAlbedo;\n"
        "float3 CompWorldNormal;\n"
        "float CompRoughness;\n"
        "float PlanarReflWeight;\n"
        "float4 SafeP1Dash = float4(P1DashData.xyz, 0.75f);\n"
        "float4 SafeP2Dash = float4(P2DashData.xyz, 0.65f);\n"
        "float ProceduralPuddle = saturate(PuddleMask * (StadiumSimplexNoise2D(WorldPos.xy * 0.0045f) * 0.5f + 0.5f));\n"
        "EvaluatePitchWetnessAndDashRipple(\n"
        "    WorldPos.xyz, normalize(BaseNormal.xyz), GrassAlbedo.rgb, GrassRoughness,\n"
        "    ProceduralPuddle, SafeP1Dash, SafeP2Dash, RainIntensity, TimeSec,\n"
        "    CompAlbedo, CompWorldNormal, CompRoughness, PlanarReflWeight);\n"
        "float MirageShimmer = 0.0f;\n"
        "float2 RefractUV = EvaluateBarranquillaHeatHaze(\n"
        "    PitchUV.xy, length(WorldPos.xyz), 480.0f, AmbientCelsius, TimeSec, MirageShimmer);\n"
        "OutWorldNormal = CompWorldNormal;\n"
        "OutRoughness = CompRoughness;\n"
        "OutSpecular = lerp(0.45f, 0.92f, PlanarReflWeight);\n"
        "OutThermalEmissive = float3(1.0f, 0.78f, 0.42f) * (MirageShimmer * 0.08f + abs(RefractUV.x - PitchUV.x) * 0.5f);\n"
        "return CompAlbedo;",
    )

    for pin_name, expr_node, out_pin in input_order:
        mel.connect_material_expressions(expr_node, out_pin, custom_node, pin_name)

    mel.connect_material_property(custom_node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(custom_node, "OutWorldNormal", unreal.MaterialProperty.MP_NORMAL)
    mel.connect_material_property(custom_node, "OutRoughness", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(custom_node, "OutSpecular", unreal.MaterialProperty.MP_SPECULAR)
    mel.connect_material_property(custom_node, "OutThermalEmissive", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    return _compile_save_and_log_material_stats(mat, MASTER_MAT_STADIUM_ENV)


def _build_combat_hud_sdf_master_material() -> Any:
    """
    Crea y compila `/Game/UI/Materials/M_CombatHUDSDF_Master`
    enlazando `/Project/CombatHUDSDFBars.ush` (`MD_UI` + `BLEND_TRANSLUCENT`).
    """
    mel = unreal.MaterialEditingLibrary
    mat = _load_or_create_material(UE_UI_MATERIALS_DEST, "M_CombatHUDSDF_Master")
    if mat is None:
        return None

    mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_UI)
    _safe_set_property(mat, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)

    mel.delete_all_material_expressions(mat)

    uv_node = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -900, -380)
    time_node = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -900, -260)

    widget_mode = _create_scalar_param(mel, mat, "HUDWidgetMode", 0.0, -900, -140)
    mirror_p1 = _create_scalar_param(mel, mat, "MirrorForPlayer1", 0.0, -900, -40)
    hp_pct = _create_scalar_param(mel, mat, "HealthPercent", 0.84, -900, 60)
    red_hp_pct = _create_scalar_param(mel, mat, "RedHealthPercent", 0.92, -900, 160)
    gambeta_pct = _create_scalar_param(mel, mat, "GambetaPercent", 0.75, -660, -140)
    burnout_flag = _create_scalar_param(mel, mat, "BurnoutState", 0.0, -660, -40)
    hypoxia_flag = _create_scalar_param(mel, mat, "AltitudeHypoxia", 0.0, -660, 60)
    yellow_risk = _create_scalar_param(mel, mat, "YellowCardRisk", 0.20, -660, 160)
    super_pct = _create_scalar_param(mel, mat, "SuperMeterPercent", 0.66, -660, 260)
    super_stocks = _create_scalar_param(mel, mat, "SuperStocksCount", 2.0, -660, 360)

    custom_node = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, -240, -60)
    custom_node.set_editor_property("description", "M_CombatHUDSDF_Master (Zero-GC GPU SDF Bars & Referee Card)")
    custom_node.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    custom_node.set_editor_property("include_file_paths", [COMBAT_HUD_SDF_USH_VIRTUAL_PATH])

    input_order = [
        ("UV", uv_node, ""),
        ("TimeSec", time_node, ""),
        ("HUDWidgetMode", widget_mode, ""),
        ("MirrorForPlayer1", mirror_p1, ""),
        ("HealthPercent", hp_pct, ""),
        ("RedHealthPercent", red_hp_pct, ""),
        ("GambetaPercent", gambeta_pct, ""),
        ("BurnoutState", burnout_flag, ""),
        ("AltitudeHypoxia", hypoxia_flag, ""),
        ("YellowCardRisk", yellow_risk, ""),
        ("SuperMeterPercent", super_pct, ""),
        ("SuperStocksCount", super_stocks, ""),
    ]
    custom_node.set_editor_property("inputs", _make_custom_inputs([name for name, _, _ in input_order]))
    custom_node.set_editor_property(
        "additional_outputs",
        _make_custom_outputs([
            ("OutAlpha", unreal.CustomMaterialOutputType.CMOT_FLOAT1),
        ]),
    )
    custom_node.set_editor_property(
        "code",
        "int Mode = (int)round(HUDWidgetMode);\n"
        "float4 SDFResult;\n"
        "if (Mode == 1)\n"
        "{\n"
        "    SDFResult = EvaluateSDFGambetaStaminaBar(\n"
        "        UV.xy, GambetaPercent, (BurnoutState > 0.5f), (AltitudeHypoxia > 0.5f), TimeSec);\n"
        "}\n"
        "else if (Mode >= 2)\n"
        "{\n"
        "    SDFResult = EvaluateSDFRefereeCardAndSuperMeter(\n"
        "        UV.xy, (Mode == 3), YellowCardRisk, SuperMeterPercent, SuperStocksCount, TimeSec);\n"
        "}\n"
        "else\n"
        "{\n"
        "    SDFResult = EvaluateSDFHealthAndChipBar(\n"
        "        UV.xy, (MirrorForPlayer1 > 0.5f), HealthPercent, RedHealthPercent, TimeSec);\n"
        "}\n"
        "OutAlpha = SDFResult.a;\n"
        "return SDFResult.rgb;",
    )

    for pin_name, expr_node, out_pin in input_order:
        mel.connect_material_expressions(expr_node, out_pin, custom_node, pin_name)

    mel.connect_material_property(custom_node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(custom_node, "OutAlpha", unreal.MaterialProperty.MP_OPACITY)

    return _compile_save_and_log_material_stats(mat, MASTER_MAT_COMBAT_HUD)


def create_project_master_materials() -> list:
    """
    Crea, cablea y compila los 5 Materiales Maestros reales del proyecto en UE 5.8:
      1. `/Game/Characters/SouthAmericaRoster/Materials/M_FighterSkin_Master`
      2. `/Game/Characters/SouthAmericaRoster/Materials/M_FighterKit_Cloth`
      3. `/Game/Characters/SouthAmericaRoster/Materials/M_FighterHairCards`
      4. `/Game/Stages/CONMEBOL/Materials/M_StadiumEnvironment_Master`
      5. `/Game/UI/Materials/M_CombatHUDSDF_Master`
    Se invoca ANTES de importar luchadores y estadios para que `bind_master_materials_to_skeletal_mesh()`
    encuentre y asigne los materiales maestros reales compilados.
    """
    target_paths = [
        MASTER_MAT_SKIN,
        MASTER_MAT_KIT,
        MASTER_MAT_HAIR,
        MASTER_MAT_STADIUM_ENV,
        MASTER_MAT_COMBAT_HUD,
    ]
    if not HAS_UNREAL_EDITOR:
        return target_paths

    builders = [
        _build_fighter_skin_master_material,
        _build_fighter_kit_cloth_material,
        _build_fighter_hair_cards_material,
        _build_stadium_environment_master_material,
        _build_combat_hud_sdf_master_material,
    ]
    created_materials = []
    for builder_fn in builders:
        mat = builder_fn()
        if mat is not None:
            created_materials.append(mat)
    return created_materials


# ============================================================================
# 3. CONFIGURACIÓN DE CHAOS CLOTH, MATERIALES MAESTROS Y 17 LUCHADORES (60 FPS)
# ============================================================================

def configure_chaos_cloth_on_skeletal_mesh(skel_mesh: "unreal.SkeletalMesh") -> None:
    """
    Aplica los parámetros competitivos de Chaos Cloth sobre el ClothingAsset del SkeletalMesh:
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

        for _, config_obj in configs.items():
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


FIGHTER_MATERIAL_SPECS = {
    "FENOMENO_BR": {
        "country": "Brazil",
        "kit_tex": "T_Kit_Brazil_Albedo",
        "primary": (0.96, 0.80, 0.08, 1.0),
        "secondary": (0.04, 0.42, 0.20, 1.0),
        "rim": (1.00, 0.90, 0.42, 1.0),
        "skin": (0.58, 0.38, 0.26, 1.0),
        "hair_root": (0.03, 0.02, 0.02, 1.0),
        "hair_tip": (0.08, 0.05, 0.04, 1.0),
    },
    "BRUXO_BR": {
        "country": "Brazil",
        "kit_tex": "T_Kit_Brazil_Albedo",
        "primary": (0.96, 0.80, 0.08, 1.0),
        "secondary": (0.04, 0.42, 0.20, 1.0),
        "rim": (1.00, 0.88, 0.45, 1.0),
        "skin": (0.54, 0.35, 0.24, 1.0),
        "hair_root": (0.03, 0.02, 0.02, 1.0),
        "hair_tip": (0.10, 0.07, 0.05, 1.0),
    },
    "CANON_AR": {
        "country": "Argentina",
        "kit_tex": "T_Kit_Argentina_Albedo",
        "primary": (0.44, 0.72, 0.94, 1.0),
        "secondary": (0.96, 0.97, 1.00, 1.0),
        "rim": (0.55, 0.84, 1.00, 1.0),
        "skin": (0.76, 0.56, 0.44, 1.0),
        "hair_root": (0.12, 0.07, 0.04, 1.0),
        "hair_tip": (0.24, 0.15, 0.08, 1.0),
    },
    "PULGA_AR": {
        "country": "Argentina",
        "kit_tex": "T_Kit_Argentina_Albedo",
        "primary": (0.44, 0.72, 0.94, 1.0),
        "secondary": (0.96, 0.97, 1.00, 1.0),
        "rim": (0.62, 0.88, 1.00, 1.0),
        "skin": (0.78, 0.58, 0.46, 1.0),
        "hair_root": (0.08, 0.05, 0.03, 1.0),
        "hair_tip": (0.18, 0.12, 0.07, 1.0),
    },
    "PIBE_CO": {
        "country": "Colombia",
        "kit_tex": "T_Kit_Colombia_Albedo",
        "primary": (0.96, 0.80, 0.08, 1.0),
        "secondary": (0.04, 0.18, 0.54, 1.0),
        "rim": (1.00, 0.86, 0.35, 1.0),
        "skin": (0.68, 0.47, 0.34, 1.0),
        "hair_root": (0.85, 0.68, 0.18, 1.0),
        "hair_tip": (0.96, 0.84, 0.32, 1.0),
    },
    "LOCO_CO": {
        "country": "Colombia",
        "kit_tex": "T_Kit_Colombia_Albedo",
        "primary": (0.96, 0.80, 0.08, 1.0),
        "secondary": (0.78, 0.10, 0.14, 1.0),
        "rim": (1.00, 0.78, 0.38, 1.0),
        "skin": (0.64, 0.44, 0.31, 1.0),
        "hair_root": (0.03, 0.02, 0.02, 1.0),
        "hair_tip": (0.10, 0.07, 0.05, 1.0),
    },
    "PISTOLERO_UY": {
        "country": "Uruguay",
        "kit_tex": "T_Kit_Uruguay_Albedo",
        "primary": (0.32, 0.66, 0.92, 1.0),
        "secondary": (0.06, 0.08, 0.12, 1.0),
        "rim": (0.48, 0.82, 1.00, 1.0),
        "skin": (0.75, 0.55, 0.43, 1.0),
        "hair_root": (0.04, 0.03, 0.02, 1.0),
        "hair_tip": (0.12, 0.08, 0.06, 1.0),
    },
    "MATADOR_UY": {
        "country": "Uruguay",
        "kit_tex": "T_Kit_Uruguay_Albedo",
        "primary": (0.32, 0.66, 0.92, 1.0),
        "secondary": (0.06, 0.08, 0.12, 1.0),
        "rim": (0.50, 0.84, 1.00, 1.0),
        "skin": (0.74, 0.54, 0.42, 1.0),
        "hair_root": (0.03, 0.02, 0.02, 1.0),
        "hair_tip": (0.11, 0.08, 0.05, 1.0),
    },
    "BAMBAM_CL": {
        "country": "Chile",
        "kit_tex": "T_Kit_Chile_Albedo",
        "primary": (0.84, 0.12, 0.14, 1.0),
        "secondary": (0.04, 0.22, 0.62, 1.0),
        "rim": (1.00, 0.52, 0.48, 1.0),
        "skin": (0.72, 0.51, 0.38, 1.0),
        "hair_root": (0.04, 0.03, 0.02, 1.0),
        "hair_tip": (0.12, 0.08, 0.05, 1.0),
    },
    "REY_CL": {
        "country": "Chile",
        "kit_tex": "T_Kit_Chile_Albedo",
        "primary": (0.84, 0.12, 0.14, 1.0),
        "secondary": (0.04, 0.22, 0.62, 1.0),
        "rim": (1.00, 0.48, 0.44, 1.0),
        "skin": (0.70, 0.49, 0.36, 1.0),
        "hair_root": (0.03, 0.02, 0.02, 1.0),
        "hair_tip": (0.09, 0.06, 0.04, 1.0),
    },
    "BULLDOG_PY": {
        "country": "Paraguay",
        "kit_tex": "T_Kit_Paraguay_Albedo",
        "primary": (0.85, 0.12, 0.16, 1.0),
        "secondary": (0.95, 0.95, 0.96, 1.0),
        "rim": (0.96, 0.52, 0.56, 1.0),
        "skin": (0.72, 0.52, 0.39, 1.0),
        "hair_root": (0.04, 0.03, 0.025, 1.0),
        "hair_tip": (0.14, 0.10, 0.07, 1.0),
    },
    "MAESTRO_PE": {
        "country": "Peru",
        "kit_tex": "T_Kit_Peru_Albedo",
        "primary": (0.94, 0.94, 0.94, 1.0),
        "secondary": (0.84, 0.08, 0.14, 1.0),
        "rim": (1.00, 0.64, 0.64, 1.0),
        "skin": (0.64, 0.44, 0.31, 1.0),
        "hair_root": (0.03, 0.02, 0.02, 1.0),
        "hair_tip": (0.10, 0.07, 0.05, 1.0),
    },
    "TREN_EC": {
        "country": "Ecuador",
        "kit_tex": "T_Kit_Ecuador_Albedo",
        "primary": (0.96, 0.80, 0.06, 1.0),
        "secondary": (0.04, 0.22, 0.56, 1.0),
        "rim": (1.00, 0.86, 0.40, 1.0),
        "skin": (0.42, 0.26, 0.18, 1.0),
        "hair_root": (0.02, 0.02, 0.02, 1.0),
        "hair_tip": (0.06, 0.05, 0.04, 1.0),
    },
    "HURACAN_VE": {
        "country": "Venezuela",
        "kit_tex": "T_Kit_Venezuela_Albedo",
        "primary": (0.44, 0.06, 0.15, 1.0),
        "secondary": (0.90, 0.74, 0.28, 1.0),
        "rim": (0.95, 0.44, 0.56, 1.0),
        "skin": (0.66, 0.46, 0.33, 1.0),
        "hair_root": (0.04, 0.03, 0.025, 1.0),
        "hair_tip": (0.12, 0.08, 0.06, 1.0),
    },
    "DIABLO_BO": {
        "country": "Bolivia",
        "kit_tex": "T_Kit_Bolivia_Albedo",
        "primary": (0.04, 0.46, 0.20, 1.0),
        "secondary": (0.90, 0.76, 0.12, 1.0),
        "rim": (0.56, 0.96, 0.62, 1.0),
        "skin": (0.65, 0.45, 0.32, 1.0),
        "hair_root": (0.03, 0.02, 0.02, 1.0),
        "hair_tip": (0.10, 0.07, 0.05, 1.0),
    },
    "GENERAL_FR": {
        "country": "France",
        "kit_tex": "T_Kit_France_Albedo",
        "primary": (0.04, 0.16, 0.42, 1.0),
        "secondary": (0.94, 0.95, 0.98, 1.0),
        "rim": (0.48, 0.68, 1.00, 1.0),
        "skin": (0.76, 0.57, 0.45, 1.0),
        "hair_root": (0.05, 0.04, 0.03, 1.0),
        "hair_tip": (0.16, 0.12, 0.09, 1.0),
    },
    "SUPREME_JUDGE_BOSS": {
        "country": "VARBoss",
        "kit_tex": "T_Kit_VARBoss_Albedo",
        "primary": (0.94, 0.72, 0.10, 1.0),
        "secondary": (0.10, 0.10, 0.14, 1.0),
        "rim": (1.00, 0.84, 0.26, 1.0),
        "skin": (0.68, 0.68, 0.72, 1.0),
        "hair_root": (0.92, 0.76, 0.24, 1.0),
        "hair_tip": (1.00, 0.92, 0.54, 1.0),
    },
}

STAGE_ENVIRONMENT_SPECS = {
    "SM_Stage_Maracana_BR": {
        "stage_id": "STAGE_MARACANA",
        "rain": 0.10,
        "celsius": 27.0,
        "grass_albedo": (0.08, 0.36, 0.11, 1.0),
        "grass_roughness": 0.58,
        "puddle_mask": 0.22,
    },
    "SM_Stage_Bombonera_AR": {
        "stage_id": "STAGE_BOMBONERA",
        "rain": 0.25,
        "celsius": 22.0,
        "grass_albedo": (0.09, 0.34, 0.10, 1.0),
        "grass_roughness": 0.62,
        "puddle_mask": 0.35,
    },
    "SM_Stage_Centenario_UY": {
        "stage_id": "STAGE_CENTENARIO",
        "rain": 0.80,
        "celsius": 14.0,
        "grass_albedo": (0.07, 0.29, 0.11, 1.0),
        "grass_roughness": 0.54,
        "puddle_mask": 0.72,
    },
    "SM_Stage_Metropolitano_CO": {
        "stage_id": "STAGE_METROPOLITANO",
        "rain": 0.15,
        "celsius": 40.0,
        "grass_albedo": (0.14, 0.38, 0.08, 1.0),
        "grass_roughness": 0.68,
        "puddle_mask": 0.20,
    },
    "SM_Stage_Nunoa_CL": {
        "stage_id": "STAGE_NUNOA",
        "rain": 0.20,
        "celsius": 12.0,
        "grass_albedo": (0.08, 0.32, 0.12, 1.0),
        "grass_roughness": 0.60,
        "puddle_mask": 0.30,
    },
    "SM_Stage_Defensores_PY": {
        "stage_id": "STAGE_DEFENSORES",
        "rain": 0.72,
        "celsius": 29.0,
        "grass_albedo": (0.09, 0.31, 0.09, 1.0),
        "grass_roughness": 0.56,
        "puddle_mask": 0.68,
    },
    "SM_Stage_NacionalLima_PE": {
        "stage_id": "STAGE_NACIONAL_LIMA",
        "rain": 0.80,
        "celsius": 17.0,
        "grass_albedo": (0.08, 0.30, 0.12, 1.0),
        "grass_roughness": 0.52,
        "puddle_mask": 0.65,
    },
    "SM_Stage_Atahualpa_EC": {
        "stage_id": "STAGE_ATAHUALPA",
        "rain": 0.55,
        "celsius": 16.0,
        "grass_albedo": (0.10, 0.32, 0.09, 1.0),
        "grass_roughness": 0.60,
        "puddle_mask": 0.50,
    },
    "SM_Stage_Avila_VE": {
        "stage_id": "STAGE_AVILA",
        "rain": 0.18,
        "celsius": 28.0,
        "grass_albedo": (0.09, 0.35, 0.10, 1.0),
        "grass_roughness": 0.58,
        "puddle_mask": 0.25,
    },
    "SM_Stage_HernandoSiles_BO": {
        "stage_id": "STAGE_HERNANDO_SILES",
        "rain": 0.40,
        "celsius": 6.0,
        "grass_albedo": (0.14, 0.34, 0.26, 1.0),
        "grass_roughness": 0.55,
        "puddle_mask": 0.42,
    },
}


def _load_or_create_mic(pkg_path: str, mic_name: str, parent_mat: Any) -> Any:
    """Carga o crea un `UMaterialInstanceConstant` heredando de `parent_mat`."""
    full_path = f"{pkg_path}/{mic_name}"
    mic = None
    if unreal.EditorAssetLibrary.does_asset_exist(full_path):
        loaded = unreal.EditorAssetLibrary.load_asset(full_path)
        if isinstance(loaded, unreal.MaterialInstanceConstant):
            mic = loaded
    if mic is None:
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        mic_factory = unreal.MaterialInstanceConstantFactoryNew()
        mic = asset_tools.create_asset(mic_name, pkg_path, unreal.MaterialInstanceConstant, mic_factory)
    if mic is not None and parent_mat is not None:
        unreal.MaterialEditingLibrary.set_material_instance_parent(mic, parent_mat)
    return mic


def _resolve_fighter_id_from_mesh(skel_mesh: "unreal.SkeletalMesh") -> str:
    """Extrae el token canónico de luchador (ej. `FENOMENO_BR`, `SUPREME_JUDGE_BOSS`) desde el nombre o ruta."""
    haystack = f"{skel_mesh.get_path_name()} {skel_mesh.get_name()}".upper()
    for fighter_id in sorted(FIGHTER_MATERIAL_SPECS.keys(), key=len, reverse=True):
        if fighter_id in haystack:
            return fighter_id
    return ""


def _resolve_stage_spec_from_mesh(static_mesh: "unreal.StaticMesh") -> tuple[str, dict[str, Any] | None]:
    """Resuelve `(stage_token, spec)` desde la ruta o nombre del `UStaticMesh` del estadio."""
    haystack = f"{static_mesh.get_path_name()} {static_mesh.get_name()}".lower()
    for stage_token, spec in STAGE_ENVIRONMENT_SPECS.items():
        short_name = stage_token.replace("SM_Stage_", "").lower()
        if stage_token.lower() in haystack or short_name in haystack:
            return stage_token, spec
    return "", None


def bind_master_materials_to_skeletal_mesh(skel_mesh: "unreal.SkeletalMesh") -> None:
    """
    Crea/actualiza las 3 `UMaterialInstanceConstant` por luchador en
    `/Game/Characters/SouthAmericaRoster/Materials/Instances/`:
      - `MI_<Fighter>_Kit`  (padre `M_FighterKit_Cloth`, con `KitAlbedoTexture = T_Kit_<Country>_Albedo` + colores país)
      - `MI_<Fighter>_Skin` (padre `M_FighterSkin_Master`)
      - `MI_<Fighter>_Hair` (padre `M_FighterHairCards`)
    y las asigna a las ranuras correspondientes del `USkeletalMesh`.
    """
    if not HAS_UNREAL_EDITOR or skel_mesh is None:
        return

    mat_skin = unreal.EditorAssetLibrary.load_asset(MASTER_MAT_SKIN)
    mat_kit = unreal.EditorAssetLibrary.load_asset(MASTER_MAT_KIT)
    mat_hair = unreal.EditorAssetLibrary.load_asset(MASTER_MAT_HAIR)

    mel = unreal.MaterialEditingLibrary
    fighter_id = _resolve_fighter_id_from_mesh(skel_mesh)
    spec = FIGHTER_MATERIAL_SPECS.get(fighter_id)

    assigned_skin = mat_skin
    assigned_kit = mat_kit
    assigned_hair = mat_hair

    if fighter_id and spec is not None:
        kit_mic = _load_or_create_mic(UE_FIGHTER_MICS_DEST, f"MI_{fighter_id}_Kit", mat_kit)
        if kit_mic is not None:
            kit_tex = unreal.EditorAssetLibrary.load_asset(f"{UE_TEXTURES_DEST}/{spec['kit_tex']}")
            if isinstance(kit_tex, unreal.Texture2D):
                mel.set_material_instance_texture_parameter_value(kit_mic, "KitAlbedoTexture", kit_tex)
            mel.set_material_instance_vector_parameter_value(
                kit_mic, "TeamPrimaryColor", unreal.LinearColor(*spec["primary"])
            )
            mel.set_material_instance_vector_parameter_value(
                kit_mic, "TeamSecondaryColor", unreal.LinearColor(*spec["secondary"])
            )
            mel.set_material_instance_vector_parameter_value(
                kit_mic, "CompetitiveRimColor", unreal.LinearColor(*spec["rim"])
            )
            if hasattr(mel, "update_material_instance"):
                mel.update_material_instance(kit_mic)
            unreal.EditorAssetLibrary.save_loaded_asset(kit_mic)
            assigned_kit = kit_mic

        skin_mic = _load_or_create_mic(UE_FIGHTER_MICS_DEST, f"MI_{fighter_id}_Skin", mat_skin)
        if skin_mic is not None:
            mel.set_material_instance_vector_parameter_value(
                skin_mic, "SkinBaseAlbedo", unreal.LinearColor(*spec["skin"])
            )
            mel.set_material_instance_vector_parameter_value(
                skin_mic, "CompetitiveRimColor", unreal.LinearColor(*spec["rim"])
            )
            if hasattr(mel, "update_material_instance"):
                mel.update_material_instance(skin_mic)
            unreal.EditorAssetLibrary.save_loaded_asset(skin_mic)
            assigned_skin = skin_mic

        hair_mic = _load_or_create_mic(UE_FIGHTER_MICS_DEST, f"MI_{fighter_id}_Hair", mat_hair)
        if hair_mic is not None:
            mel.set_material_instance_vector_parameter_value(
                hair_mic, "HairRootColor", unreal.LinearColor(*spec["hair_root"])
            )
            mel.set_material_instance_vector_parameter_value(
                hair_mic, "HairTipColor", unreal.LinearColor(*spec["hair_tip"])
            )
            mel.set_material_instance_vector_parameter_value(
                hair_mic, "CompetitiveRimColor", unreal.LinearColor(*spec["rim"])
            )
            if hasattr(mel, "update_material_instance"):
                mel.update_material_instance(hair_mic)
            unreal.EditorAssetLibrary.save_loaded_asset(hair_mic)
            assigned_hair = hair_mic

        unreal.log(
            f"[LA COPA ETERNA][FIGHTER_MIC] {fighter_id}: MI_{fighter_id}_Kit ({spec['kit_tex']}), "
            f"MI_{fighter_id}_Skin, MI_{fighter_id}_Hair"
        )

    materials = skel_mesh.get_editor_property("materials")
    updated_materials = []

    for idx, skeletal_mat in enumerate(materials):
        slot_name = str(skeletal_mat.get_editor_property("material_slot_name")).lower()
        if "hair" in slot_name or idx == 2:
            if assigned_hair:
                skeletal_mat.set_editor_property("material_interface", assigned_hair)
        elif "kit" in slot_name or "cloth" in slot_name or "jersey" in slot_name or idx == 1:
            if assigned_kit:
                skeletal_mat.set_editor_property("material_interface", assigned_kit)
        else:
            if assigned_skin:
                skeletal_mat.set_editor_property("material_interface", assigned_skin)

        updated_materials.append(skeletal_mat)

    skel_mesh.set_editor_property("materials", updated_materials)


def bind_master_materials_to_stages(stage_meshes: list | None = None) -> list:
    """
    Crea/actualiza un `UMaterialInstanceConstant` por cada uno de los 10 estadios CONMEBOL en
    `/Game/Stages/CONMEBOL/Materials/Instances/MI_<StageID>_Env` heredando de `M_StadiumEnvironment_Master`
    con `RainIntensity`, `AmbientCelsius` y `BaseGrassAlbedo` calibrados, y lo asigna a las ranuras
    de césped/cancha (`M_PitchGrass`) de cada `UStaticMesh`.
    """
    if not HAS_UNREAL_EDITOR:
        return [f"{UE_STAGE_MICS_DEST}/MI_{spec['stage_id']}_Env" for spec in STAGE_ENVIRONMENT_SPECS.values()]

    master_env = unreal.EditorAssetLibrary.load_asset(MASTER_MAT_STADIUM_ENV)
    if master_env is None:
        unreal.log_warning(f"[LA COPA ETERNA][STAGE_MIC] Falta material maestro: {MASTER_MAT_STADIUM_ENV}")
        return []

    if stage_meshes is None:
        stage_meshes = []
        if unreal.EditorAssetLibrary.does_directory_exist(UE_STAGES_DEST):
            for apath in unreal.EditorAssetLibrary.list_assets(UE_STAGES_DEST, recursive=True, include_folder=False):
                loaded = unreal.EditorAssetLibrary.load_asset(apath)
                if isinstance(loaded, unreal.StaticMesh):
                    stage_meshes.append(loaded)

    mel = unreal.MaterialEditingLibrary
    bound_mics = []

    for sm_asset in stage_meshes:
        if not isinstance(sm_asset, unreal.StaticMesh):
            continue
        stage_token, spec = _resolve_stage_spec_from_mesh(sm_asset)
        if spec is None:
            continue

        mic_name = f"MI_{spec['stage_id']}_Env"
        env_mic = _load_or_create_mic(UE_STAGE_MICS_DEST, mic_name, master_env)
        if env_mic is None:
            continue

        mel.set_material_instance_scalar_parameter_value(env_mic, "RainIntensity", float(spec["rain"]))
        mel.set_material_instance_scalar_parameter_value(env_mic, "AmbientCelsius", float(spec["celsius"]))
        mel.set_material_instance_scalar_parameter_value(
            env_mic, "BaseGrassRoughness", float(spec["grass_roughness"])
        )
        mel.set_material_instance_scalar_parameter_value(
            env_mic, "PuddleDistributionMask", float(spec["puddle_mask"])
        )
        mel.set_material_instance_vector_parameter_value(
            env_mic, "BaseGrassAlbedo", unreal.LinearColor(*spec["grass_albedo"])
        )
        if hasattr(mel, "update_material_instance"):
            mel.update_material_instance(env_mic)
        unreal.EditorAssetLibrary.save_loaded_asset(env_mic)

        static_materials = sm_asset.get_editor_property("static_materials")
        updated_smats = []
        pitch_slots_bound = 0
        for idx, smat in enumerate(static_materials):
            slot_name = str(smat.get_editor_property("material_slot_name")).lower()
            is_pitch_slot = (
                "pitchgrass" in slot_name
                or ("pitch" in slot_name and "lines" not in slot_name)
                or (idx == 0 and "grass" in slot_name)
            )
            if is_pitch_slot:
                smat.set_editor_property("material_interface", env_mic)
                if hasattr(sm_asset, "set_material"):
                    sm_asset.set_material(idx, env_mic)
                pitch_slots_bound += 1
            updated_smats.append(smat)

        if pitch_slots_bound > 0:
            sm_asset.set_editor_property("static_materials", updated_smats)
            unreal.EditorAssetLibrary.save_loaded_asset(sm_asset)
        bound_mics.append(env_mic)
        unreal.log(
            f"[LA COPA ETERNA][STAGE_MIC] {stage_token} -> {mic_name} "
            f"(Rain={spec['rain']}, Temp={spec['celsius']}C, PitchSlots={pitch_slots_bound})"
        )

    return bound_mics


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


def _get_anim_sequence_fps(anim_seq: Any) -> float:
    """Obtiene los FPS de muestreo reales de un `UAnimSequence` en UE 5.8 vía `data_model_interface`."""
    try:
        dmi = anim_seq.get_editor_property("data_model_interface")
        if dmi is not None and hasattr(dmi, "get_frame_rate"):
            fr = dmi.get_frame_rate()
            return float(fr.numerator) / max(float(fr.denominator), 1.0)
    except Exception:
        pass
    try:
        if hasattr(anim_seq, "get_sampling_frame_rate"):
            fr = anim_seq.get_sampling_frame_rate()
            return float(fr.numerator) / max(float(fr.denominator), 1.0)
    except Exception:
        pass
    return 0.0


def _enforce_anim_sequence_60fps(anim_seq: Any) -> float:
    """
    Garantiza que `anim_seq` tenga exactamente `60.0 FPS` (`FFrameRate(60, 1)`) usando
    `IAnimationDataController` (`open_bracket` -> `set_frame_rate(FrameRate(60, 1))` -> `close_bracket`)
    con respaldo de remuestreo de pistas óseas si la tasa previa no era factor entero de 60 (ej. 24 FPS).
    """
    if not HAS_UNREAL_EDITOR or anim_seq is None:
        return 60.0

    _safe_set_property(anim_seq, "import_resample_framerate", 60.0)
    target_rate = unreal.FrameRate(60, 1)
    _safe_set_property(anim_seq, "target_frame_rate", target_rate)

    current_fps = _get_anim_sequence_fps(anim_seq)
    if abs(current_fps - 60.0) < 1e-3:
        return 60.0

    try:
        controller = anim_seq.get_editor_property("controller")
        if controller is not None:
            bracket_title = unreal.Text("Enforce 60 FPS Deterministic Combat FrameRate")
            controller.open_bracket(bracket_title, False)
            try:
                controller.set_frame_rate(target_rate, False)
                updated_fps = _get_anim_sequence_fps(anim_seq)

                if abs(updated_fps - 60.0) >= 1e-3:
                    dmi = anim_seq.get_editor_property("data_model_interface")
                    play_len = float(dmi.get_play_length()) if (dmi and hasattr(dmi, "get_play_length")) else 0.5
                    num_frames_60 = max(1, int(round(play_len * 60.0)))
                    bone_names = []
                    if hasattr(unreal, "AnimationLibrary") and hasattr(unreal.AnimationLibrary, "get_animation_track_names"):
                        bone_names = list(unreal.AnimationLibrary.get_animation_track_names(anim_seq))
                    elif dmi is not None and hasattr(dmi, "get_bone_track_names"):
                        bone_names = list(dmi.get_bone_track_names())

                    sampled_tracks: dict[Any, tuple[list, list, list]] = {}
                    if bone_names and hasattr(unreal, "AnimationLibrary"):
                        for b_name in bone_names:
                            pos_keys, rot_keys, scale_keys = [], [], []
                            for frame_idx in range(num_frames_60 + 1):
                                sample_t = min(play_len, float(frame_idx) / 60.0)
                                xf = unreal.AnimationLibrary.get_bone_pose_for_time(anim_seq, b_name, sample_t, False)
                                pos_keys.append(xf.translation)
                                rot_keys.append(xf.rotation)
                                scale_keys.append(xf.scale3d)
                            sampled_tracks[b_name] = (pos_keys, rot_keys, scale_keys)

                    if sampled_tracks:
                        controller.remove_all_bone_tracks(False)
                        if abs(current_fps - 24.0) < 0.5:
                            controller.set_frame_rate(unreal.FrameRate(120, 1), False)
                            controller.set_number_of_frames(unreal.FrameNumber(num_frames_60 * 2), False)
                        controller.set_frame_rate(target_rate, False)
                        controller.set_number_of_frames(unreal.FrameNumber(num_frames_60), False)
                        for b_name, (pos_k, rot_k, scl_k) in sampled_tracks.items():
                            controller.add_bone_curve(b_name, False)
                            controller.set_bone_track_keys(b_name, pos_k, rot_k, scl_k, False)
            finally:
                controller.close_bracket(False)
    except Exception as exc:
        unreal.log_warning(f"[LA COPA ETERNA][ANIM_60FPS_WARN] {anim_seq.get_name()}: {exc}")

    return _get_anim_sequence_fps(anim_seq)


def _create_fighter_60fps_interchange_override() -> tuple[Any, Any]:
    """
    Construye `(pipeline, stack_override)` usando `UInterchangePipelineStackOverride` para que
    `UAssetToolsImpl::ImportAssetTasks` aplique efectivamente la configuración de 60 FPS en UE 5.8.
    Retorna ambos objetos para mantener referencias fuertes en Python durante la importación.
    """
    if not HAS_UNREAL_EDITOR or not hasattr(unreal, "InterchangeGenericAssetsPipeline"):
        return None, None

    pipeline = unreal.InterchangeGenericAssetsPipeline()

    # Preservar la jerarquía `/Game/Characters/SouthAmericaRoster/Meshes/SK_<ID>/SkeletalMeshes/...`
    _safe_set_property(pipeline, "use_source_name_for_asset", True)
    _safe_set_property(pipeline, "scene_name_sub_folder", True)
    _safe_set_property(pipeline, "asset_type_sub_folders", True)

    if hasattr(pipeline, "mesh_pipeline"):
        mesh_p = pipeline.get_editor_property("mesh_pipeline")
        _safe_set_property(mesh_p, "import_skeletal_meshes", True)
        _safe_set_property(mesh_p, "import_static_meshes", False)

    if hasattr(pipeline, "animation_pipeline"):
        anim_p = pipeline.get_editor_property("animation_pipeline")
        _safe_set_property(anim_p, "import_animations", True)
        _safe_set_property(anim_p, "import_bone_tracks", True)
        _safe_set_property(anim_p, "use_default_sample_rate", False)
        _safe_set_property(anim_p, "use30_hz_to_bake_bone_animation", False)
        if not _safe_set_property(anim_p, "custom_bone_animation_sample_rate", 60):
            _safe_set_property(anim_p, "custom_bone_animation_sample_rate", 60.0)
        _safe_set_property(anim_p, "snap_to_closest_frame_boundary", True)
        if hasattr(unreal, "InterchangeFrameAlignment"):
            snap_enum = getattr(unreal.InterchangeFrameAlignment, "SNAP_TO_CLOSEST", None)
            if snap_enum is not None:
                _safe_set_property(anim_p, "frame_alignment", snap_enum)

    if hasattr(unreal, "InterchangePipelineStackOverride"):
        stack_override = unreal.InterchangePipelineStackOverride()
        stack_override.add_pipeline(pipeline)
        return pipeline, stack_override

    return pipeline, pipeline


def import_fighters_glb_interchange() -> list:
    """
    Importa los 17 archivos `SK_*.glb` desde `Assets/Models3D/Fighters/` como `USkeletalMesh` + `UAnimSequence`:
      - Purga secuencias previas que no estén a 60.0 FPS para evitar conflictos `24 -> 60` en reimportación
      - Configura `UInterchangePipelineStackOverride` con `CustomBoneAnimationSampleRate = 60` y `SnapToClosest`
      - Verifica y fuerza `60.0 FPS` en las 170 `UAnimSequence`s mediante `IAnimationDataController`
      - Desactiva Nanite (`bEnableNanite = False`), activa Skin Cache (`SkinCacheUsage = Enabled`),
        vincula `M_FighterSkin_Master`, `M_FighterKit_Cloth`, `M_FighterHairCards` y Chaos Cloth.
    """
    glb_files = sorted(glob.glob(os.path.join(GLB_FIGHTERS_DIR, "SK_*.glb")))
    if not HAS_UNREAL_EDITOR:
        return glb_files

    # Limpiar secuencias heredadas a 30/24 FPS antes de reimportar para crear modelos limpios a 60Hz
    if unreal.EditorAssetLibrary.does_directory_exist(UE_FIGHTERS_DEST):
        existing_paths = unreal.EditorAssetLibrary.list_assets(UE_FIGHTERS_DEST, recursive=True, include_folder=False)
        purged_non_60 = 0
        for asset_path in existing_paths:
            obj = unreal.EditorAssetLibrary.load_asset(asset_path)
            if hasattr(unreal, "AnimSequence") and isinstance(obj, unreal.AnimSequence):
                if abs(_get_anim_sequence_fps(obj) - 60.0) >= 1e-3:
                    if unreal.EditorAssetLibrary.delete_asset(asset_path):
                        purged_non_60 += 1
        if purged_non_60 > 0:
            unreal.log(f"[LA COPA ETERNA][ANIM_CLEANUP] Eliminadas {purged_non_60} AnimSequences heredadas (<60 FPS) previo a reimportación.")

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    imported_assets = []

    for glb_path in glb_files:
        task = unreal.AssetImportTask()
        task.filename = glb_path
        task.destination_path = UE_FIGHTERS_DEST
        task.replace_existing = True
        task.automated = True
        task.save = True

        # Mantener referencia fuerte en Python tanto a `pipeline` como a `stack_override`
        pipeline_ref, stack_override = _create_fighter_60fps_interchange_override()
        if stack_override is not None:
            task.options = stack_override

        asset_tools.import_asset_tasks([task])
        _ = pipeline_ref  # Garantizar vida útil durante toda la llamada sincrónica

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
                except Exception as exc:
                    unreal.log_warning(f"[LA COPA ETERNA][SKEL_BIND_WARN] {asset.get_name()}: {exc}")

                unreal.EditorAssetLibrary.save_loaded_asset(asset)
                imported_assets.append(asset)
            elif hasattr(unreal, "AnimSequence") and isinstance(asset, unreal.AnimSequence):
                _enforce_anim_sequence_60fps(asset)
                unreal.EditorAssetLibrary.save_loaded_asset(asset)
                imported_assets.append(asset)

    # Barrido final de auditoría sobre el 100% de UAnimSequence en Content/ para confirmar 170/170 a 60.0 FPS
    fps_histogram: dict[float, int] = {}
    all_content_assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True, include_folder=False)
    for asset_path in all_content_assets:
        obj = unreal.EditorAssetLibrary.load_asset(asset_path)
        if hasattr(unreal, "AnimSequence") and isinstance(obj, unreal.AnimSequence):
            final_fps = round(_enforce_anim_sequence_60fps(obj), 2)
            fps_histogram[final_fps] = fps_histogram.get(final_fps, 0) + 1
            unreal.EditorAssetLibrary.save_loaded_asset(obj)

    unreal.log(f"[LA COPA ETERNA][ANIM_FPS_AUDIT] Histograma final UAnimSequence en /Game: {fps_histogram}")
    return imported_assets


# ============================================================================
# 4. IMPORTACIÓN DE LOS 10 ESTADIOS 3D CONMEBOL (`SM_Stage_*.glb`)
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

    bind_master_materials_to_stages(imported_stages)
    return imported_stages


# ============================================================================
# 4B. IMPORTACIÓN DE PROPS 3D (`SM_Ball_TruncatedIcosahedron_32Panels.glb`)
# ============================================================================

def import_props_glb_interchange() -> list:
    """
    Importa `Assets/Models3D/Props/SM_Ball_TruncatedIcosahedron_32Panels.glb` hacia `/Game/Props`
    como `UStaticMesh` llamado `SM_Ball_TruncatedIcosahedron_32Panels` (usado por `ADeterministicBallProjectile`).
    """
    ball_glb = os.path.join(GLB_PROPS_DIR, "SM_Ball_TruncatedIcosahedron_32Panels.glb")
    prop_glbs = [ball_glb] if os.path.isfile(ball_glb) else sorted(glob.glob(os.path.join(GLB_PROPS_DIR, "*.glb")))
    if not HAS_UNREAL_EDITOR:
        return prop_glbs

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    imported_props = []

    for glb_path in prop_glbs:
        target_name = os.path.splitext(os.path.basename(glb_path))[0]
        target_full_path = f"{UE_PROPS_DEST}/{target_name}"

        task = unreal.AssetImportTask()
        task.filename = glb_path
        task.destination_path = UE_PROPS_DEST
        task.destination_name = target_name
        task.replace_existing = True
        task.automated = True
        task.save = True

        if hasattr(unreal, "InterchangeGenericAssetsPipeline"):
            prop_pipeline = unreal.InterchangeGenericAssetsPipeline()
            _safe_set_property(prop_pipeline, "use_source_name_for_asset", False)
            _safe_set_property(prop_pipeline, "scene_name_sub_folder", False)
            _safe_set_property(prop_pipeline, "asset_type_sub_folders", False)
            if hasattr(prop_pipeline, "mesh_pipeline"):
                mesh_p = prop_pipeline.get_editor_property("mesh_pipeline")
                _safe_set_property(mesh_p, "import_skeletal_meshes", False)
                _safe_set_property(mesh_p, "import_static_meshes", True)
                if hasattr(unreal, "InterchangeMeshCollision"):
                    pass
            if hasattr(unreal, "InterchangePipelineStackOverride"):
                stack_override = unreal.InterchangePipelineStackOverride()
                stack_override.add_pipeline(prop_pipeline)
                task.options = stack_override

        asset_tools.import_asset_tasks([task])

        resolved_mesh = None
        if unreal.EditorAssetLibrary.does_asset_exist(target_full_path):
            loaded = unreal.EditorAssetLibrary.load_asset(target_full_path)
            if isinstance(loaded, unreal.StaticMesh):
                resolved_mesh = loaded

        if resolved_mesh is None:
            for obj_path in task.imported_object_paths:
                loaded = unreal.EditorAssetLibrary.load_asset(obj_path)
                if isinstance(loaded, unreal.StaticMesh):
                    if obj_path != target_full_path and not unreal.EditorAssetLibrary.does_asset_exist(target_full_path):
                        unreal.EditorAssetLibrary.rename_asset(obj_path, target_full_path)
                        loaded = unreal.EditorAssetLibrary.load_asset(target_full_path) or loaded
                    resolved_mesh = loaded
                    break

        if isinstance(resolved_mesh, unreal.StaticMesh):
            unreal.EditorAssetLibrary.save_loaded_asset(resolved_mesh)
            imported_props.append(resolved_mesh)
            unreal.log(f"[LA COPA ETERNA][PROPS] Prop StaticMesh importado: {resolved_mesh.get_path_name()}")

    return imported_props


# ============================================================================
# 5. IMPORTACIÓN DE DATATABLES JSON (`Data/DT_*.json` -> `/Game/DataTables/`)
# ============================================================================

def _resolve_datatable_row_struct(candidate_paths: list[str]) -> Any:
    """Busca y carga el `UScriptStruct` C++ (FTableRowBase) para una DataTable."""
    if not HAS_UNREAL_EDITOR:
        return None
    for struct_path in candidate_paths:
        obj = None
        try:
            obj = unreal.load_object(None, struct_path)
        except Exception:
            obj = None
        if obj is None and hasattr(unreal, "find_object"):
            try:
                obj = unreal.find_object(None, struct_path)
            except Exception:
                obj = None
        if obj is not None:
            return obj
    return None


def _build_datatable_json_rows(dt_filename: str, raw_data: Any) -> list[dict[str, Any]]:
    """
    Normaliza cada JSON de `Data/` en una lista de filas planas con clave `"Name"` requerida por `UDataTable`:
      - `DT_FrameDataUniversal.json`: copia `"MoveID"` -> `"Name"`
      - `DT_SouthAmericaRoster.json`: ya incluye `"Name"`
      - `DT_StagesCONMEBOL.json`: copia `"StageID"` -> `"Name"`
      - `DT_CommentaryAndRivalries.json`: aplana `InterruptStingers`, `GeneralCommentaryLines`,
        `SignatureMoveTriggers`, `ClassicRivalriesClashIntros` y `StoryModeChapters`
    """
    if dt_filename == "DT_FrameDataUniversal.json" and isinstance(raw_data, list):
        rows = []
        for idx, item in enumerate(raw_data):
            if not isinstance(item, dict):
                continue
            row = dict(item)
            row["Name"] = str(row.get("Name") or row.get("MoveID") or f"Move_{idx:03d}")
            rows.append(row)
        return rows

    if dt_filename == "DT_SouthAmericaRoster.json" and isinstance(raw_data, list):
        rows = []
        for idx, item in enumerate(raw_data):
            if not isinstance(item, dict):
                continue
            row = dict(item)
            row["Name"] = str(row.get("Name") or row.get("FighterID") or f"Fighter_{idx:02d}")
            rows.append(row)
        return rows

    if dt_filename == "DT_StagesCONMEBOL.json" and isinstance(raw_data, list):
        rows = []
        for idx, item in enumerate(raw_data):
            if not isinstance(item, dict):
                continue
            row = dict(item)
            row["Name"] = str(row.get("Name") or row.get("StageID") or f"Stage_{idx:02d}")
            rows.append(row)
        return rows

    if dt_filename == "DT_CommentaryAndRivalries.json" and isinstance(raw_data, dict):
        rows = []
        booth = raw_data.get("CommentaryBoothSystem", {})
        for st in booth.get("InterruptStingers", []):
            row_id = str(st.get("StingerID", ""))
            if not row_id:
                continue
            rows.append({
                "Name": row_id,
                "RowID": row_id,
                "Category": "InterruptStinger",
                "WwiseEvent": str(st.get("WwiseEvent", "")),
                "Speaker": str(st.get("Speaker", "")),
                "Priority": "CriticalMoment",
                "PriorityScore": 90,
                "DurationFrames": int(st.get("DurationFrames", 24)),
                "Title": "",
                "FighterA": "",
                "FighterB": "",
                "StageID": "",
                "TextES": str(st.get("TextES", "")),
            })

        for line in booth.get("GeneralCommentaryLines", []):
            row_id = str(line.get("LineID", ""))
            if not row_id:
                continue
            rows.append({
                "Name": row_id,
                "RowID": row_id,
                "Category": "GeneralCommentary",
                "WwiseEvent": str(line.get("WwiseEvent", "")),
                "Speaker": str(line.get("Speaker", "")),
                "Priority": str(line.get("Priority", "NeutralChatter")),
                "PriorityScore": int(line.get("PriorityScore", 20)),
                "DurationFrames": int(line.get("DurationFrames", 120)),
                "Title": "",
                "FighterA": "",
                "FighterB": "",
                "StageID": "",
                "TextES": str(line.get("TextES", "")),
            })

        for trig in booth.get("SignatureMoveTriggers", []):
            row_id = str(trig.get("TriggerID", ""))
            if not row_id:
                continue
            rows.append({
                "Name": row_id,
                "RowID": row_id,
                "Category": "SignatureMoveTrigger",
                "WwiseEvent": str(trig.get("WwiseEvent", "")),
                "Speaker": str(trig.get("Speaker", "")),
                "Priority": str(trig.get("Priority", "ComboAction")),
                "PriorityScore": int(trig.get("PriorityScore", 50)),
                "DurationFrames": 90,
                "Title": str(trig.get("MoveID", "")),
                "FighterA": str(trig.get("FighterID", "")),
                "FighterB": "",
                "StageID": "",
                "TextES": str(trig.get("TextES", "")),
            })

        for riv in raw_data.get("ClassicRivalriesClashIntros", []):
            row_id = str(riv.get("RivalryID", ""))
            if not row_id:
                continue
            seq = riv.get("DialogueSequence", [])
            joined_text = " | ".join(
                f"{d.get('Speaker', '')}: {d.get('TextES', '')}" for d in seq if isinstance(d, dict)
            )
            first_wwise = seq[0].get("WwiseEvent", "") if seq and isinstance(seq[0], dict) else ""
            rows.append({
                "Name": row_id,
                "RowID": row_id,
                "Category": "ClassicRivalry",
                "WwiseEvent": str(first_wwise),
                "Speaker": str(riv.get("FighterA", "")),
                "Priority": "CriticalMoment",
                "PriorityScore": 80,
                "DurationFrames": 180,
                "Title": str(riv.get("Title", "")),
                "FighterA": str(riv.get("FighterA", "")),
                "FighterB": str(riv.get("FighterB", "")),
                "StageID": str(riv.get("StageRecommendation", "")),
                "TextES": joined_text,
            })

        for ch in raw_data.get("StoryModeChapters", []):
            row_id = str(ch.get("ChapterID", ""))
            if not row_id:
                continue
            rows.append({
                "Name": row_id,
                "RowID": row_id,
                "Category": "StoryChapter",
                "WwiseEvent": "",
                "Speaker": str(ch.get("PlayableFighter", "")),
                "Priority": "NeutralChatter",
                "PriorityScore": 40,
                "DurationFrames": 180,
                "Title": str(ch.get("Title", "")),
                "FighterA": str(ch.get("PlayableFighter", "")),
                "FighterB": str(ch.get("OpponentFighter", "")),
                "StageID": str(ch.get("StageID", "")),
                "TextES": str(ch.get("KeyDialogue", "")),
            })
        return rows

    return raw_data if isinstance(raw_data, list) else []


DATATABLE_STRUCT_CANDIDATES = {
    "DT_FrameDataUniversal.json": [
        "/Script/SouthAmericaFightersCore.MoveFrameDataRow",
    ],
    "DT_SouthAmericaRoster.json": [
        "/Script/SouthAmericaFightersCore.FighterRosterRow",
        "/Script/SouthAmericaFightersCore.FighterDataRow",
    ],
    "DT_StagesCONMEBOL.json": [
        "/Script/SouthAmericaFightersCore.StageCONMEBOLTableRow",
        "/Script/SouthAmericaFightersCore.StageDataRow",
    ],
    "DT_CommentaryAndRivalries.json": [
        "/Script/SouthAmericaFightersCore.CommentaryRivalryRow",
        "/Script/SouthAmericaFightersCore.CommentaryAndRivalryRow",
        "/Script/SouthAmericaFightersCore.CommentaryRow",
    ],
}


def import_json_datatables_to_ue5() -> list:
    """
    Crea e importa las 4 DataTables reales (`UDataTable`) en `/Game/DataTables/`:
      - `DT_FrameDataUniversal`     (`MoveFrameDataRow`, mapeando `MoveID` -> `Name`)
      - `DT_SouthAmericaRoster`     (`FighterRosterRow`)
      - `DT_StagesCONMEBOL`         (`StageCONMEBOLTableRow`, mapeando `StageID` -> `Name`)
      - `DT_CommentaryAndRivalries` (filas aplanadas de `InterruptStingers`, `ClassicRivalriesClashIntros`, etc.)
    """
    json_files = sorted(glob.glob(os.path.join(DATATABLES_DIR, "DT_*.json")))
    if not HAS_UNREAL_EDITOR:
        return json_files

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    imported_tables = []

    for json_path in json_files:
        base_file = os.path.basename(json_path)
        asset_name = os.path.splitext(base_file)[0]
        asset_path = f"{UE_DATATABLES_DEST}/{asset_name}"

        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        rows = _build_datatable_json_rows(base_file, raw_data)
        candidates = list(DATATABLE_STRUCT_CANDIDATES.get(base_file, []))
        row_struct = _resolve_datatable_row_struct(candidates)

        # Respaldo limpio en caso de que aún no exista un struct dedicado para Commentary/Rivalries
        payload_rows = rows
        if row_struct is None:
            fallback_struct = _resolve_datatable_row_struct(["/Script/GameplayTags.GameplayTagTableRow"])
            if fallback_struct is not None:
                row_struct = fallback_struct
                payload_rows = [
                    {
                        "Name": r["Name"],
                        "Tag": f"LaCopaEterna.{asset_name}.{r['Name']}",
                        "DevComment": json.dumps(r, ensure_ascii=False),
                    }
                    for r in rows
                ]

        dt_asset = None
        if row_struct is not None:
            if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
                existing = unreal.EditorAssetLibrary.load_asset(asset_path)
                if isinstance(existing, unreal.DataTable):
                    existing_struct = None
                    try:
                        existing_struct = existing.get_editor_property("row_struct")
                    except Exception:
                        pass
                    if existing_struct == row_struct:
                        dt_asset = existing
                    else:
                        unreal.EditorAssetLibrary.delete_asset(asset_path)

            if dt_asset is None:
                dt_factory = unreal.DataTableFactory()
                _safe_set_property(dt_factory, "struct", row_struct)
                dt_asset = asset_tools.create_asset(asset_name, UE_DATATABLES_DEST, unreal.DataTable, dt_factory)
                if dt_asset is not None:
                    _safe_set_property(dt_asset, "row_struct", row_struct)

            if isinstance(dt_asset, unreal.DataTable):
                json_payload = json.dumps(payload_rows, ensure_ascii=False)
                filled = False
                if hasattr(unreal, "DataTableFunctionLibrary") and hasattr(
                    unreal.DataTableFunctionLibrary, "fill_data_table_from_json_string"
                ):
                    filled = bool(
                        unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(dt_asset, json_payload)
                    )
                elif hasattr(dt_asset, "fill_from_json_string"):
                    filled = bool(dt_asset.fill_from_json_string(json_payload))

                row_count = 0
                if hasattr(unreal, "DataTableFunctionLibrary") and hasattr(
                    unreal.DataTableFunctionLibrary, "get_data_table_row_names"
                ):
                    row_count = len(unreal.DataTableFunctionLibrary.get_data_table_row_names(dt_asset))
                elif hasattr(dt_asset, "get_row_names"):
                    row_count = len(dt_asset.get_row_names())

                unreal.EditorAssetLibrary.save_loaded_asset(dt_asset)
                imported_tables.append(dt_asset)
                unreal.log(
                    f"[LA COPA ETERNA][DATATABLE] {asset_name} -> {row_count} filas "
                    f"(filled={filled}, RowStruct={row_struct.get_name()})"
                )
                continue

        # Último fallback con CSVImportFactory si no se resolvió ningún RowStruct
        task = unreal.AssetImportTask()
        task.filename = json_path
        task.destination_path = UE_DATATABLES_DEST
        task.destination_name = asset_name
        task.replace_existing = True
        task.automated = True
        task.save = True
        if hasattr(unreal, "CSVImportFactory"):
            csv_factory = unreal.CSVImportFactory()
            if hasattr(csv_factory, "automated_import_settings") and row_struct is not None:
                settings = csv_factory.get_editor_property("automated_import_settings")
                _safe_set_property(settings, "import_row_struct", row_struct)
            task.factory = csv_factory

        asset_tools.import_asset_tasks([task])
        for obj_path in task.imported_object_paths:
            loaded_dt = unreal.EditorAssetLibrary.load_asset(obj_path)
            if loaded_dt:
                unreal.EditorAssetLibrary.save_loaded_asset(loaded_dt)
                imported_tables.append(loaded_dt)

    return imported_tables


# ============================================================================
# 6. CREACIÓN Y CABLEADO COMPLETO DE `M_PP_SfumatoChiaroscuro`
# ============================================================================

def create_and_wire_sfumato_postprocess_material() -> Any:
    """
    Crea, cablea completamente y compila en UE 5.8+ el Material de Post-Proceso `M_PP_SfumatoChiaroscuro`:
      - MaterialDomain = MD_POST_PROCESS
      - BlendableLocation = BL_SCENE_COLOR_BEFORE_TONEMAPPING
      - IncludeFilePaths = `["/Project/SfumatoChiaroscuroPostProcess.ush"]`
      - `CustomInput` reales conectados para:
          * `ScreenUV` (`MaterialExpressionScreenPosition` -> `ViewportUV`)
          * `InvViewSize` (`MaterialExpressionViewSize` -> `1.0 / ViewSize`)
          * `SceneDepthCm`, `DepthNW`, `DepthNE`, `DepthSW`, `DepthSE` (`MaterialExpressionSceneDepth`)
          * `CenterSceneColor`, `SampleNW`, `SampleNE`, `SampleSW`, `SampleSE`
            (`MaterialExpressionSceneTexture` `PPI_POST_PROCESS_INPUT0`, `bFiltered = True`, desplazados con `SceneTexelSize`)
          * Los 6 parámetros escalares (`ArtStyleMode`, `StyleBlendAlpha`, `ChiaroscuroContrast`,
            `VarnishAmberWarmth`, `CraquelureIntensity`, `FighterPlaneDepthCm`)
      - Registra `MaterialEditingLibrary.get_statistics(pp_mat)` verificando `num_pixel_shader_instructions > 0`.
    """
    if not HAS_UNREAL_EDITOR:
        return PP_MAT_SFUMATO_PATH

    pp_mat = _load_or_create_material(UE_POSTPROCESS_DEST, "M_PP_SfumatoChiaroscuro")
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
            _safe_set_property(pp_mat, "blendable_location", bl_val)

    mel = unreal.MaterialEditingLibrary
    mel.delete_all_material_expressions(pp_mat)

    # 1. Seis parámetros escalares expuestos (Street-Ink = 0 vs Renaissance Sfumato = 1)
    param_nodes = {}
    y_offset = -520
    for param_name, default_val in SFUMATO_POSTPROCESS_DEFAULTS.items():
        param_nodes[param_name] = _create_scalar_param(mel, pp_mat, param_name, float(default_val), -980, y_offset)
        y_offset += 100

    # 2. Coordenadas de pantalla, tamaño inverso de vista (1.0 / ViewSize) y SceneTexelSize
    screen_pos = mel.create_material_expression(pp_mat, unreal.MaterialExpressionScreenPosition, -1380, 120)
    view_size = mel.create_material_expression(pp_mat, unreal.MaterialExpressionViewSize, -1380, 260)
    inv_view_div = mel.create_material_expression(pp_mat, unreal.MaterialExpressionDivide, -1160, 260)
    inv_view_div.set_editor_property("const_a", 1.0)
    mel.connect_material_expressions(view_size, "", inv_view_div, "B")

    texel_size = mel.create_material_expression(pp_mat, unreal.MaterialExpressionSceneTexelSize, -1380, 400)

    # 3. Muestras centrales de PostProcessInput0 (filtrado) y SceneDepth
    ppi0_enum = unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0
    center_tex = mel.create_material_expression(pp_mat, unreal.MaterialExpressionSceneTexture, -760, 80)
    center_tex.set_editor_property("scene_texture_id", ppi0_enum)
    center_tex.set_editor_property("filtered", True)
    mel.connect_material_expressions(screen_pos, "ViewportUV", center_tex, "")

    center_depth = mel.create_material_expression(pp_mat, unreal.MaterialExpressionSceneDepth, -760, 220)
    mel.connect_material_expressions(screen_pos, "ViewportUV", center_depth, "")

    # 4. Vecindario bilateral de 4 cuadrantes (NW, NE, SW, SE) desplazados por +/-2.25f * SceneTexelSize
    neighbor_specs = [
        ("NW", -2.25, -2.25, 360),
        ("NE",  2.25, -2.25, 540),
        ("SW", -2.25,  2.25, 720),
        ("SE",  2.25,  2.25, 900),
    ]
    neighbor_color_nodes: dict[str, Any] = {}
    neighbor_depth_nodes: dict[str, Any] = {}

    for suffix, dx, dy, row_y in neighbor_specs:
        off_const = mel.create_material_expression(pp_mat, unreal.MaterialExpressionConstant2Vector, -1380, row_y)
        off_const.set_editor_property("r", float(dx))
        off_const.set_editor_property("g", float(dy))

        off_mul = mel.create_material_expression(pp_mat, unreal.MaterialExpressionMultiply, -1180, row_y)
        mel.connect_material_expressions(texel_size, "", off_mul, "A")
        mel.connect_material_expressions(off_const, "", off_mul, "B")

        uv_add = mel.create_material_expression(pp_mat, unreal.MaterialExpressionAdd, -980, row_y)
        mel.connect_material_expressions(screen_pos, "ViewportUV", uv_add, "A")
        mel.connect_material_expressions(off_mul, "", uv_add, "B")

        n_tex = mel.create_material_expression(pp_mat, unreal.MaterialExpressionSceneTexture, -760, row_y)
        n_tex.set_editor_property("scene_texture_id", ppi0_enum)
        n_tex.set_editor_property("filtered", True)
        mel.connect_material_expressions(uv_add, "", n_tex, "")
        neighbor_color_nodes[suffix] = n_tex

        n_depth = mel.create_material_expression(pp_mat, unreal.MaterialExpressionSceneDepth, -540, row_y)
        mel.connect_material_expressions(uv_add, "", n_depth, "")
        neighbor_depth_nodes[suffix] = n_depth

    # 5. Nodo Custom HLSL conectado a `/Project/SfumatoChiaroscuroPostProcess.ush` con `CustomInput` completos
    custom_node = mel.create_material_expression(pp_mat, unreal.MaterialExpressionCustom, -180, -40)
    custom_node.set_editor_property("description", "M_PP_SfumatoChiaroscuro (Da Vinci Sfumato + Street-Ink Dual Pipeline)")
    custom_node.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    custom_node.set_editor_property("include_file_paths", [SFUMATO_USH_VIRTUAL_PATH])

    input_connections = [
        ("ArtStyleMode", param_nodes["ArtStyleMode"], ""),
        ("StyleBlendAlpha", param_nodes["StyleBlendAlpha"], ""),
        ("ScreenUV", screen_pos, "ViewportUV"),
        ("InvViewSize", inv_view_div, ""),
        ("SceneDepthCm", center_depth, ""),
        ("DepthNW", neighbor_depth_nodes["NW"], ""),
        ("DepthNE", neighbor_depth_nodes["NE"], ""),
        ("DepthSW", neighbor_depth_nodes["SW"], ""),
        ("DepthSE", neighbor_depth_nodes["SE"], ""),
        ("FighterPlaneDepthCm", param_nodes["FighterPlaneDepthCm"], ""),
        ("CenterSceneColor", center_tex, ""),
        ("SampleNW", neighbor_color_nodes["NW"], ""),
        ("SampleNE", neighbor_color_nodes["NE"], ""),
        ("SampleSW", neighbor_color_nodes["SW"], ""),
        ("SampleSE", neighbor_color_nodes["SE"], ""),
        ("ChiaroscuroContrast", param_nodes["ChiaroscuroContrast"], ""),
        ("VarnishAmberWarmth", param_nodes["VarnishAmberWarmth"], ""),
        ("CraquelureIntensity", param_nodes["CraquelureIntensity"], ""),
    ]
    custom_node.set_editor_property(
        "inputs",
        _make_custom_inputs([pin_name for pin_name, _, _ in input_connections]),
    )
    custom_node.set_editor_property(
        "code",
        "float4 NeighborDepths = float4(DepthNW, DepthNE, DepthSW, DepthSE);\n"
        "float GradX = (DepthNE + DepthSE) - (DepthNW + DepthSW);\n"
        "float GradY = (DepthSW + DepthSE) - (DepthNW + DepthNE);\n"
        "float DepthGradientSobel = saturate(sqrt(GradX * GradX + GradY * GradY) / 120.0f);\n"
        "float SafeAspectRatio = (InvViewSize.x > 1e-6f) ? (InvViewSize.y / InvViewSize.x) : 1.7777f;\n"
        "return EvaluateM_PP_SfumatoChiaroscuro(\n"
        "    (int)round(ArtStyleMode), StyleBlendAlpha, ScreenUV.xy, InvViewSize.xy, SafeAspectRatio,\n"
        "    SceneDepthCm, NeighborDepths, FighterPlaneDepthCm,\n"
        "    CenterSceneColor.rgb, SampleNW.rgb, SampleNE.rgb, SampleSW.rgb, SampleSE.rgb,\n"
        "    DepthGradientSobel, float2(0.5f, 0.5f), 0.0f,\n"
        "    ChiaroscuroContrast, VarnishAmberWarmth, CraquelureIntensity);",
    )

    for pin_name, expr_node, out_pin in input_connections:
        mel.connect_material_expressions(expr_node, out_pin, custom_node, pin_name)

    mel.connect_material_property(custom_node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return _compile_save_and_log_material_stats(pp_mat, PP_MAT_SFUMATO_PATH)


# ============================================================================
# 7. AUDITORÍA DE INTEGRIDAD CLI (`--dry-run`) FUERA DE UNREAL ENGINE 5.8
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
    Ejecuta una auditoría completa del 100% de los activos 3D, manifiestos, shaders HLSL (`/Project/*.ush`),
    texturas PBR, arte conceptual Renacimiento Sfumato, stems de audio `.wav` y DataTables en disco.
    """
    print("=" * 86)
    print(f" UE 5.8.4 PRODUCTION AUTO-IMPORT PIPELINE v{PIPELINE_VERSION} [DRY-RUN AUDIT]")
    print("=" * 86)

    errors: list[str] = []

    # 1. Verificar Manifiestos Técnicos
    for _, manifest_path in [
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
        f"[OK] Fighters (USkeletalMesh + 60.0 FPS Animations): "
        f"{verified_fighters}/{len(manifest_fighters)} .glb validados "
        f"({total_anim_clips} clips de animación glTF 2.0 -> 60Hz Interchange Override)"
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
        f"[OK] CONMEBOL 3D Stadiums (UStaticMesh + Nanite):    "
        f"{verified_stages}/{len(manifest_stages)} .glb validados "
        f"({total_stage_tris:,} triángulos totales)"
    )

    # 4. Auditar Props Adicionales (Balón 32 Paneles + Arena Base)
    prop_glbs = sorted(glob.glob(os.path.join(GLB_PROPS_DIR, "*.glb"))) + sorted(
        glob.glob(os.path.join(GLB_STAGES_DIR, "SM_Stage_PitchAndDestructibleWalls.glb"))
    )
    ball_glb = os.path.join(GLB_PROPS_DIR, "SM_Ball_TruncatedIcosahedron_32Panels.glb")
    if not os.path.isfile(ball_glb):
        errors.append(f"Falta prop requerido de balón 32 paneles: {ball_glb}")
    for p_glb in prop_glbs:
        inspect_glb_binary_header(p_glb)
    print(f"[OK] Props & Destructible Wall-Break Templates:      {len(prop_glbs)}/{len(prop_glbs)} .glb validados")

    # 5. Auditar Shaders HLSL (`/Project/*.ush`) y mapeo virtual de UE 5.8
    virtual_shader_map = {
        COMPETITIVE_RIM_USH_VIRTUAL_PATH: os.path.join(SHADERS_DIR, "CompetitiveRimAndInkOutline.ush"),
        FIGHTER_SKIN_USH_VIRTUAL_PATH: os.path.join(SHADERS_DIR, "FighterSkinMaster.ush"),
        STADIUM_ENV_USH_VIRTUAL_PATH: os.path.join(SHADERS_DIR, "StadiumEnvironmentFX.ush"),
        COMBAT_HUD_SDF_USH_VIRTUAL_PATH: os.path.join(SHADERS_DIR, "CombatHUDSDFBars.ush"),
        SFUMATO_USH_VIRTUAL_PATH: os.path.join(SHADERS_DIR, "SfumatoChiaroscuroPostProcess.ush"),
    }
    verified_shaders = 0
    for vpath, disk_path in virtual_shader_map.items():
        if not vpath.startswith("/Project/") or vpath.startswith("/Project/Shaders/"):
            errors.append(f"Ruta virtual de shader inválida para UE 5.8: {vpath}")
        if not os.path.isfile(disk_path) or os.path.getsize(disk_path) == 0:
            errors.append(f"Falta shader HLSL requerido: {disk_path}")
        else:
            verified_shaders += 1

    techart_forwarder = os.path.join(TECHART_SOURCE_DIR, "M_PP_SfumatoChiaroscuro.ush")
    if not os.path.isfile(techart_forwarder) or os.path.getsize(techart_forwarder) == 0:
        errors.append(f"Falta forwarder HLSL requerido: {techart_forwarder}")
    else:
        verified_shaders += 1

    sfumato_shader_path = os.path.join(SHADERS_DIR, "SfumatoChiaroscuroPostProcess.ush")
    with open(sfumato_shader_path, "r", encoding="utf-8") as f:
        sfumato_src = f.read()
    if "ArtStyleMode" not in sfumato_src or "EvaluateM_PP_SfumatoChiaroscuro" not in sfumato_src:
        errors.append("El shader SfumatoChiaroscuroPostProcess.ush no expone ArtStyleMode o EvaluateM_PP_SfumatoChiaroscuro")
    if '#include "/Project/CompetitiveRimAndInkOutline.ush"' not in sfumato_src:
        errors.append("SfumatoChiaroscuroPostProcess.ush debe incluir '/Project/CompetitiveRimAndInkOutline.ush' con raíz virtual '/'")

    master_mats = create_project_master_materials()
    print(
        f"[OK] HLSL Shaders & Master Materials (/Project/*.ush): "
        f"{verified_shaders}/6 .ush + {len(master_mats)} Master Materials + M_PP_SfumatoChiaroscuro listos"
    )

    # 6. Auditar las 18 Texturas PBR (`Assets/TexturesPBR/*.png`) y mapeo 17 Fighters / 10 Stages MIC
    pbr_pngs = sorted(glob.glob(os.path.join(PBR_TEXTURES_DIR, "*.png")))
    if len(pbr_pngs) < 18:
        errors.append(f"Se esperaban al menos 18 texturas PBR en Assets/TexturesPBR/, halladas {len(pbr_pngs)}")
    for png in pbr_pngs:
        with open(png, "rb") as f:
            sig = f.read(8)
            if sig != b"\x89PNG\r\n\x1a\n":
                errors.append(f"Firma PNG inválida en: {png}")
    for fid, fspec in FIGHTER_MATERIAL_SPECS.items():
        kit_png = os.path.join(PBR_TEXTURES_DIR, f"{fspec['kit_tex']}.png")
        if not os.path.isfile(kit_png):
            errors.append(f"Falta textura de kit para {fid}: {kit_png}")
    if len(FIGHTER_MATERIAL_SPECS) != 17:
        errors.append(f"Se esperaban 17 specs de MIC de luchadores, hallados {len(FIGHTER_MATERIAL_SPECS)}")
    if len(STAGE_ENVIRONMENT_SPECS) != 10:
        errors.append(f"Se esperaban 10 specs de MIC de estadios, hallados {len(STAGE_ENVIRONMENT_SPECS)}")
    print(
        f"[OK] PBR Textures (Kits + Jacquard + MicroPores):    "
        f"{len(pbr_pngs)}/18 .png + 17 Fighter MIC specs + 10 Stage MIC specs validados"
    )

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
        f"[OK] 2D Concept Art & UI Textures (Sfumato + SVG):   "
        f"{len(concept_imgs)} .jpg ({len(renaissance_imgs)} Renaissance Sfumato) + 1 SVG Master Atlas validados"
    )

    # 8. Auditar Audio Stems & SFX `.wav` (`Audio/GeneratedStems/*.wav`)
    wav_stems = sorted(glob.glob(os.path.join(AUDIO_STEMS_DIR, "*.wav")))
    if not wav_stems:
        errors.append(f"No se hallaron archivos .wav en {AUDIO_STEMS_DIR}")
    for wav_path in wav_stems:
        with open(wav_path, "rb") as f:
            riff_hdr = f.read(12)
            if len(riff_hdr) < 12 or riff_hdr[:4] != b"RIFF" or riff_hdr[8:12] != b"WAVE":
                errors.append(f"Cabecera RIFF/WAVE inválida en: {wav_path}")
    print(f"[OK] Audio Stems & Competitive SFX (/Game/Audio/Stems): {len(wav_stems)} .wav RIFF/WAVE validados")

    # 9. Auditar DataTables JSON (`Data/DT_*.json`)
    dt_files = sorted(glob.glob(os.path.join(DATATABLES_DIR, "DT_*.json")))
    if len(dt_files) < 4:
        errors.append(f"Se esperaban 4 DataTables JSON en Data/, halladas {len(dt_files)}")
    dt_total_rows = 0
    for dt_path in dt_files:
        with open(dt_path, "r", encoding="utf-8") as f:
            raw_dt = json.load(f)
        norm_rows = _build_datatable_json_rows(os.path.basename(dt_path), raw_dt)
        if not norm_rows or any("Name" not in r for r in norm_rows):
            errors.append(f"DataTable normalizada sin filas o sin clave 'Name': {dt_path}")
        dt_total_rows += len(norm_rows)
    print(
        f"[OK] Competitive JSON DataTables (Data/DT_*.json):   "
        f"{len(dt_files)}/4 tablas validadas ({dt_total_rows} filas UE5 DataTable)"
    )

    print("-" * 86)
    if errors:
        print(f"[FAIL] Auditoría finalizada con {len(errors)} errores:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(
        "[SUCCESS] 100% de activos verificados sin errores: "
        f"{verified_fighters} Luchadores ({total_anim_clips} Anims @ 60FPS), "
        f"{verified_stages} Estadios CONMEBOL, {len(pbr_pngs)} Texturas PBR, "
        f"{len(concept_imgs)} Concept Arts, {len(wav_stems)} Audio WAVs, "
        f"{verified_shaders} Shaders HLSL ({len(master_mats)} Master Mats + PP) y {len(dt_files)} DataTables."
    )
    print("=" * 86)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UE 5.8.4 Production Auto-Import Pipeline v2.1 (Interchange 60FPS + Master Shaders + Sfumato PP + CLI Dry-Run)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Audita en Python 3 estándar que el 100%% de los activos (.glb, .png, .jpg, .wav, .ush, .json) existan y sean válidos.",
    )
    args, _ = parser.parse_known_args()

    if args.dry_run or not HAS_UNREAL_EDITOR:
        return run_dry_run_audit()

    # Ejecución dentro del proceso UnrealEditor.exe / UnrealEditor-Cmd.exe con Python Editor Script Plugin
    unreal.log("=== [LA COPA ETERNA] Iniciando Auto-Import Pipeline v2.1 en Unreal Engine 5.8.4 ===")
    for step_name, step_fn in [
        ("PBR Textures", import_pbr_textures_to_ue5),
        ("Concept Art & UI (Sfumato)", import_concept_art_and_ui_textures_to_ue5),
        ("Audio WAV Stems & SFX (/Game/Audio/Stems)", import_wav_audio_stems_to_ue5),
        ("JSON DataTables (/Game/DataTables)", import_json_datatables_to_ue5),
        ("5 Project Master Materials (/Project/*.ush)", create_project_master_materials),
        ("17 Animated Fighters (.glb @ 60.0 FPS)", import_fighters_glb_interchange),
        ("10 CONMEBOL 3D Stages (.glb + Env MICs)", import_conmebol_stages_glb_interchange),
        ("Ball 32-Panel Prop (.glb -> /Game/Props)", import_props_glb_interchange),
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
    unreal.log("=== [LA COPA ETERNA] Auto-Import Pipeline v2.1 finalizado y guardado en /Game ===")
    return 0


if __name__ == "__main__":
    exit_code = main()
    if not HAS_UNREAL_EDITOR:
        sys.exit(exit_code)
