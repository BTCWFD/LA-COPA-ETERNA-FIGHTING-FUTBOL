#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_startup_level_ue5.py - SouthAmericaFightersCore ("La Copa Eterna")
Genera y guarda los 10 niveles oficiales CONMEBOL en `/Game/Maps/L_01..L_10`
y mantiene actualizado `/Game/Maps/L_Maracana_Versus1v1` en Unreal Engine 5.8+:
  - Estadio 3D correspondiente (`SM_Stage_*`) instanciado en el origen
  - Iluminación Renacimiento Sfumato (`DirectionalLight` + `SkyLight` + `ExponentialHeightFog`)
    calibrada por clima y altitud (40°C Barranquilla, 3600m La Paz, garúa Lima, ceniza Quito, etc.)
  - `PostProcessVolume` global Unbound con `/Game/TechArt/PostProcess/M_PP_SfumatoChiaroscuro`
  - Cámara lateral 2.5D Broadcast + `PlayerStart`
  - `WorldSettings.DefaultGameMode` = `/Script/SouthAmericaFightersCore.FightingMatchGameMode`
    (sin duplicar `SkeletalMeshActor`s estáticos: `AFightingMatchGameMode::BeginPlay()` instancia
    dinámicamente los pawns jugables P1 y P2 en tiempo de ejecución).
"""

import argparse
import sys
from typing import Any

try:
    import unreal
    HAS_UNREAL_EDITOR = True
except ImportError:
    HAS_UNREAL_EDITOR = False


GAME_MODE_CLASS_PATH = "/Script/SouthAmericaFightersCore.FightingMatchGameMode"
PP_SFUMATO_MAT_PATH = "/Game/TechArt/PostProcess/M_PP_SfumatoChiaroscuro"
STAGES_MESH_ROOT = "/Game/Stages/CONMEBOL/Meshes"


CONMEBOL_LEVEL_SPECS = [
    {
        "map_path": "/Game/Maps/L_01_Maracana_BR",
        "stage_mesh_token": "SM_Stage_Maracana_BR",
        "stage_label": "Arena_TemploDoMaracana_3D",
        "sun_label": "Sun_RenacimientoSfumato_GoldenAmber",
        "sun_rot": (-38.0, 48.0, 0.0),
        "sun_intensity": 6.5,
        "sun_color": (1.0, 0.84, 0.58, 1.0),
        "sky_intensity": 1.15,
        "sky_color": (0.88, 0.84, 0.78, 1.0),
        "fog_density": 0.016,
        "fog_color": (0.72, 0.56, 0.38, 1.0),
    },
    {
        "map_path": "/Game/Maps/L_02_Bombonera_AR",
        "stage_mesh_token": "SM_Stage_Bombonera_AR",
        "stage_label": "Arena_LaCalderaDeLaBoca_3D",
        "sun_label": "Sun_Bombonera_TardeDorada",
        "sun_rot": (-32.0, 56.0, 0.0),
        "sun_intensity": 7.2,
        "sun_color": (1.0, 0.72, 0.38, 1.0),
        "sky_intensity": 1.05,
        "sky_color": (0.75, 0.72, 0.88, 1.0),
        "fog_density": 0.022,
        "fog_color": (0.86, 0.62, 0.32, 1.0),
    },
    {
        "map_path": "/Game/Maps/L_03_Centenario_UY",
        "stage_mesh_token": "SM_Stage_Centenario_UY",
        "stage_label": "Arena_MonumentoCentenario_3D",
        "sun_label": "Sun_Centenario_NocturnaCeleste",
        "sun_rot": (-44.0, 35.0, 0.0),
        "sun_intensity": 4.8,
        "sun_color": (0.64, 0.80, 1.00, 1.0),
        "sky_intensity": 0.95,
        "sky_color": (0.52, 0.72, 0.94, 1.0),
        "fog_density": 0.036,
        "fog_color": (0.48, 0.64, 0.82, 1.0),
    },
    {
        "map_path": "/Game/Maps/L_04_Metropolitano_CO",
        "stage_mesh_token": "SM_Stage_Metropolitano_CO",
        "stage_label": "Arena_ColosoDeBarranquilla_3D",
        "sun_label": "Sun_Barranquilla_40C_SolCaribeno",
        "sun_rot": (-58.0, 22.0, 0.0),
        "sun_intensity": 9.2,
        "sun_color": (1.00, 0.88, 0.52, 1.0),
        "sky_intensity": 1.35,
        "sky_color": (1.00, 0.88, 0.66, 1.0),
        "fog_density": 0.024,
        "fog_color": (0.98, 0.78, 0.42, 1.0),
    },
    {
        "map_path": "/Game/Maps/L_05_Nunoa_CL",
        "stage_mesh_token": "SM_Stage_Nunoa_CL",
        "stage_label": "Arena_ColiseoDeNunoa_3D",
        "sun_label": "Sun_Nunoa_AtardecerCordillerano",
        "sun_rot": (-26.0, 62.0, 0.0),
        "sun_intensity": 6.8,
        "sun_color": (1.00, 0.68, 0.48, 1.0),
        "sky_intensity": 1.10,
        "sky_color": (0.68, 0.78, 0.96, 1.0),
        "fog_density": 0.015,
        "fog_color": (0.82, 0.64, 0.58, 1.0),
    },
    {
        "map_path": "/Game/Maps/L_06_Defensores_PY",
        "stage_mesh_token": "SM_Stage_Defensores_PY",
        "stage_label": "Arena_ElFortinDeSajonia_3D",
        "sun_label": "Sun_Sajonia_TormentaElectrica",
        "sun_rot": (-48.0, -30.0, 0.0),
        "sun_intensity": 4.4,
        "sun_color": (0.70, 0.78, 0.98, 1.0),
        "sky_intensity": 0.88,
        "sky_color": (0.46, 0.54, 0.72, 1.0),
        "fog_density": 0.032,
        "fog_color": (0.42, 0.48, 0.64, 1.0),
    },
    {
        "map_path": "/Game/Maps/L_07_NacionalLima_PE",
        "stage_mesh_token": "SM_Stage_NacionalLima_PE",
        "stage_label": "Arena_TemploJoseDiazLima_3D",
        "sun_label": "Sun_Lima_GaruaCostera",
        "sun_rot": (-42.0, 40.0, 0.0),
        "sun_intensity": 4.6,
        "sun_color": (0.76, 0.82, 0.88, 1.0),
        "sky_intensity": 1.00,
        "sky_color": (0.68, 0.74, 0.80, 1.0),
        "fog_density": 0.048,
        "fog_color": (0.66, 0.72, 0.78, 1.0),
    },
    {
        "map_path": "/Game/Maps/L_08_Atahualpa_EC",
        "stage_mesh_token": "SM_Stage_Atahualpa_EC",
        "stage_label": "Arena_ElVolcanDeQuito_3D",
        "sun_label": "Sun_Quito_AmbarVolcanico",
        "sun_rot": (-34.0, 52.0, 0.0),
        "sun_intensity": 6.4,
        "sun_color": (1.00, 0.62, 0.34, 1.0),
        "sky_intensity": 1.05,
        "sky_color": (0.78, 0.58, 0.44, 1.0),
        "fog_density": 0.028,
        "fog_color": (0.88, 0.52, 0.28, 1.0),
    },
    {
        "map_path": "/Game/Maps/L_09_Avila_VE",
        "stage_mesh_token": "SM_Stage_Avila_VE",
        "stage_label": "Arena_MonumentalDelAvila_3D",
        "sun_label": "Sun_Avila_CrepusculoCaribeno",
        "sun_rot": (-29.0, 46.0, 0.0),
        "sun_intensity": 5.6,
        "sun_color": (0.94, 0.64, 0.80, 1.0),
        "sky_intensity": 1.08,
        "sky_color": (0.62, 0.56, 0.86, 1.0),
        "fog_density": 0.020,
        "fog_color": (0.76, 0.52, 0.68, 1.0),
    },
    {
        "map_path": "/Game/Maps/L_10_HernandoSiles_BO",
        "stage_mesh_token": "SM_Stage_HernandoSiles_BO",
        "stage_label": "Arena_ElNidoDelCondor_3600m_3D",
        "sun_label": "Sun_LaPaz_3600m_NubesAndinas",
        "sun_rot": (-46.0, 38.0, 0.0),
        "sun_intensity": 7.8,
        "sun_color": (0.90, 0.96, 1.00, 1.0),
        "sky_intensity": 1.25,
        "sky_color": (0.76, 0.88, 1.00, 1.0),
        "fog_density": 0.030,
        "fog_color": (0.82, 0.90, 0.98, 1.0),
    },
]

STARTUP_ALIAS_SPEC = {
    **CONMEBOL_LEVEL_SPECS[0],
    "map_path": "/Game/Maps/L_Maracana_Versus1v1",
}


def _safe_set_property(obj: Any, prop_name: str, value: Any) -> bool:
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


def find_first_asset_by_class(folder_path: str, class_name: str, name_hint: str = ""):
    if not unreal.EditorAssetLibrary.does_directory_exist(folder_path):
        return None
    assets = unreal.EditorAssetLibrary.list_assets(folder_path, recursive=True, include_folder=False)
    fallback = None
    for asset_path in assets:
        obj = unreal.EditorAssetLibrary.load_asset(asset_path)
        if obj and obj.get_class().get_name() == class_name:
            if fallback is None:
                fallback = obj
            if name_hint and name_hint.lower() in obj.get_name().lower():
                return obj
    return fallback


def find_stage_static_mesh(stage_mesh_token: str):
    direct_path = f"{STAGES_MESH_ROOT}/{stage_mesh_token}"
    if unreal.EditorAssetLibrary.does_asset_exist(direct_path):
        obj = unreal.EditorAssetLibrary.load_asset(direct_path)
        if isinstance(obj, unreal.StaticMesh):
            return obj

    subfolder_mesh = find_first_asset_by_class(direct_path, "StaticMesh")
    if subfolder_mesh is not None:
        return subfolder_mesh

    short_hint = stage_mesh_token.replace("SM_Stage_", "")
    return find_first_asset_by_class(STAGES_MESH_ROOT, "StaticMesh", short_hint)


def _get_current_editor_world(actor_hint: Any = None):
    if hasattr(unreal, "UnrealEditorSubsystem"):
        try:
            ue_subsys = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            if ue_subsys is not None:
                world = ue_subsys.get_editor_world()
                if world is not None:
                    return world
        except Exception:
            pass
    if hasattr(unreal, "EditorLevelLibrary") and hasattr(unreal.EditorLevelLibrary, "get_editor_world"):
        try:
            world = unreal.EditorLevelLibrary.get_editor_world()
            if world is not None:
                return world
        except Exception:
            pass
    if actor_hint is not None and hasattr(actor_hint, "get_world"):
        try:
            return actor_hint.get_world()
        except Exception:
            pass
    return None


def build_single_conmebol_level(spec: dict[str, Any]) -> bool:
    map_path = spec["map_path"]
    stage_token = spec["stage_mesh_token"]
    unreal.log(f"=== [LA COPA ETERNA] Construyendo nivel {map_path} ({stage_token}) ===")

    level_subsys = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actor_subsys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    level_subsys.new_level(map_path)

    # 1. Estadio 3D CONMEBOL correspondiente (UStaticMeshActor)
    stage_mesh = find_stage_static_mesh(stage_token)
    stage_actor = None
    if stage_mesh:
        stage_actor = actor_subsys.spawn_actor_from_class(
            unreal.StaticMeshActor, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator(0.0, 0.0, 0.0)
        )
        stage_actor.set_actor_label(spec["stage_label"])
        sm_comp = stage_actor.get_editor_property("static_mesh_component")
        _safe_set_property(sm_comp, "mobility", unreal.ComponentMobility.MOVABLE)
        sm_comp.set_static_mesh(stage_mesh)
        unreal.log(f"[LA COPA ETERNA][MAP] Estadio instanciado: {stage_mesh.get_path_name()}")
    else:
        unreal.log_warning(f"[LA COPA ETERNA][MAP] StaticMesh no encontrado para {stage_token} en {STAGES_MESH_ROOT}")

    # 2. Iluminación Renacimiento Sfumato calibrada por clima y altitud
    sun_pitch, sun_yaw, sun_roll = spec["sun_rot"]
    sun = actor_subsys.spawn_actor_from_class(
        unreal.DirectionalLight,
        unreal.Vector(0.0, -500.0, 900.0),
        unreal.Rotator(sun_pitch, sun_yaw, sun_roll),
    )
    sun.set_actor_label(spec["sun_label"])
    try:
        lc = sun.get_editor_property("light_component")
        _safe_set_property(lc, "mobility", unreal.ComponentMobility.MOVABLE)
        lc.set_intensity(float(spec["sun_intensity"]))
        lc.set_light_color(unreal.LinearColor(*spec["sun_color"]))
    except Exception:
        pass

    sky = actor_subsys.spawn_actor_from_class(
        unreal.SkyLight, unreal.Vector(0.0, 0.0, 600.0), unreal.Rotator(0.0, 0.0, 0.0)
    )
    sky.set_actor_label("SkyLight_SfumatoChiaroscuro")
    try:
        slc = sky.get_editor_property("light_component")
        _safe_set_property(slc, "mobility", unreal.ComponentMobility.MOVABLE)
        _safe_set_property(slc, "real_time_capture", True)
        _safe_set_property(slc, "intensity", float(spec["sky_intensity"]))
        _safe_set_property(slc, "light_color", unreal.LinearColor(*spec["sky_color"]))
    except Exception:
        pass

    fog = actor_subsys.spawn_actor_from_class(
        unreal.ExponentialHeightFog, unreal.Vector(0.0, 0.0, 120.0), unreal.Rotator(0.0, 0.0, 0.0)
    )
    fog.set_actor_label("Fog_LeonardoAerialPerspective")
    try:
        fog_comp = fog.get_editor_property("component")
        _safe_set_property(fog_comp, "fog_density", float(spec["fog_density"]))
        _safe_set_property(fog_comp, "fog_height_falloff", 0.2)
        _safe_set_property(fog_comp, "fog_inscattering_luminance", unreal.LinearColor(*spec["fog_color"]))
    except Exception:
        pass

    # 3. PostProcessVolume Unbound global con M_PP_SfumatoChiaroscuro
    pp_vol = actor_subsys.spawn_actor_from_class(
        unreal.PostProcessVolume, unreal.Vector(0.0, 0.0, 200.0), unreal.Rotator(0.0, 0.0, 0.0)
    )
    pp_vol.set_actor_label("PPV_SfumatoChiaroscuro_Global")
    _safe_set_property(pp_vol, "unbound", True)
    pp_mat = unreal.EditorAssetLibrary.load_asset(PP_SFUMATO_MAT_PATH)
    if pp_mat:
        try:
            settings = pp_vol.get_editor_property("settings")
            blendables = unreal.WeightedBlendables()
            blendables.set_editor_property("array", [unreal.WeightedBlendable(1.0, pp_mat)])
            settings.set_editor_property("weighted_blendables", blendables)
            pp_vol.set_editor_property("settings", settings)
            unreal.log(f"[LA COPA ETERNA][MAP] M_PP_SfumatoChiaroscuro vinculado en {map_path}.")
        except Exception as exc:
            unreal.log_warning(f"[LA COPA ETERNA][MAP] Aviso vinculando blendable en {map_path}: {exc}")

    # 4. Cámara Lateral 2.5D Broadcast + PlayerStart (sin SkeletalMeshActors estáticos duplicados;
    # AFightingMatchGameMode::BeginPlay() instancia P1 y P2 reales en tiempo de ejecución).
    cam = actor_subsys.spawn_actor_from_class(
        unreal.CameraActor, unreal.Vector(0.0, 680.0, 165.0), unreal.Rotator(-6.0, -90.0, 0.0)
    )
    cam.set_actor_label("Camera_25D_FightingBroadcast")

    pstart = actor_subsys.spawn_actor_from_class(
        unreal.PlayerStart, unreal.Vector(0.0, 680.0, 165.0), unreal.Rotator(-6.0, -90.0, 0.0)
    )
    pstart.set_actor_label("PlayerStart_BroadcastView")

    # 5. WorldSettings -> GameMode Override = AFightingMatchGameMode
    world = _get_current_editor_world(pstart or stage_actor or cam)
    if world is not None:
        try:
            ws = world.get_world_settings()
            gm_class = unreal.load_class(None, GAME_MODE_CLASS_PATH)
            if ws is not None and gm_class is not None:
                _safe_set_property(ws, "default_game_mode", gm_class)
                unreal.log(f"[LA COPA ETERNA][MAP] WorldSettings GameMode -> {GAME_MODE_CLASS_PATH}")
            elif gm_class is None:
                unreal.log_warning(f"[LA COPA ETERNA][MAP] Clase GameMode no cargada aún: {GAME_MODE_CLASS_PATH}")
        except Exception as exc:
            unreal.log_warning(f"[LA COPA ETERNA][MAP] No se pudo asignar WorldSettings GameMode en {map_path}: {exc}")

    saved = bool(level_subsys.save_current_level())
    unreal.log(f"=== [LA COPA ETERNA] Nivel guardado ({saved}): {map_path} ===")
    return saved


def build_all_conmebol_levels() -> list[str]:
    """Genera los 10 niveles CONMEBOL (/Game/Maps/L_01..L_10) más /Game/Maps/L_Maracana_Versus1v1."""
    all_specs = CONMEBOL_LEVEL_SPECS + [STARTUP_ALIAS_SPEC]
    if not HAS_UNREAL_EDITOR:
        return [spec["map_path"] for spec in all_specs]

    built_maps: list[str] = []
    for spec in all_specs:
        if build_single_conmebol_level(spec):
            built_maps.append(spec["map_path"])
    return built_maps


def build_startup_level():
    """Punto de entrada retrocompatible: construye los 10 estadios CONMEBOL + L_Maracana_Versus1v1."""
    return build_all_conmebol_levels()


def run_dry_run_audit() -> int:
    all_specs = CONMEBOL_LEVEL_SPECS + [STARTUP_ALIAS_SPEC]
    print(f"[OK] CONMEBOL Level Generator listo: {len(CONMEBOL_LEVEL_SPECS)} estadios + L_Maracana_Versus1v1 ({len(all_specs)} .umap)")
    for spec in all_specs:
        print(f"  - {spec['map_path']} -> {spec['stage_mesh_token']} (Sun={spec['sun_intensity']}, Fog={spec['fog_density']})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UE 5.8.4 10-Stage CONMEBOL + L_Maracana_Versus1v1 .umap Level Generator"
    )
    parser.add_argument("--dry-run", action="store_true", help="Imprime el plan de los 11 mapas sin abrir UE5.")
    args, _ = parser.parse_known_args()

    if args.dry_run or not HAS_UNREAL_EDITOR:
        return run_dry_run_audit()

    built = build_all_conmebol_levels()
    unreal.log(f"=== [LA COPA ETERNA] {len(built)}/11 niveles .umap generados y guardados en /Game/Maps ===")
    return 0


if __name__ == "__main__":
    exit_code = main()
    if not HAS_UNREAL_EDITOR:
        sys.exit(exit_code)
