#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_startup_level_ue5.py - Crea y guarda el mapa inicial jugable `/Game/Maps/L_Maracana_Versus1v1`
en Unreal Engine 5.8+ con el estadio Maracanã 3D, O Fenômeno vs La Pulga (animados en Idle_Breath),
iluminación Renacimiento Sfumato, cámara 2.5D y PostProcessVolume con M_PP_SfumatoChiaroscuro.
"""

import unreal


MAP_PACKAGE_PATH = "/Game/Maps/L_Maracana_Versus1v1"


def find_first_asset_by_class(folder_path: str, class_name: str, name_hint: str = ""):
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


def build_startup_level():
    unreal.log("=== [LA COPA ETERNA] Construyendo nivel inicial /Game/Maps/L_Maracana_Versus1v1 ===")

    level_subsys = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actor_subsys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    level_subsys.new_level(MAP_PACKAGE_PATH)

    # 1. Estadio 3D Templo do Maracanã
    stage_mesh = find_first_asset_by_class("/Game/Stages/CONMEBOL/Meshes/SM_Stage_Maracana_BR", "StaticMesh")
    if stage_mesh:
        stage_actor = actor_subsys.spawn_actor_from_class(
            unreal.StaticMeshActor, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator(0.0, 0.0, 0.0)
        )
        stage_actor.set_actor_label("Arena_TemploDoMaracana_3D")
        sm_comp = stage_actor.get_editor_property("static_mesh_component")
        sm_comp.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        sm_comp.set_static_mesh(stage_mesh)
        unreal.log(f"[LA COPA ETERNA][MAP] Estadio instanciado: {stage_mesh.get_path_name()}")

    # 2. P1 O Fenômeno & P2 La Pulga (SkeletalMeshActor con Idle_Breath 60 FPS)
    fighters_spec = [
        ("P1_OFenomeno_BR", "/Game/Characters/SouthAmericaRoster/Meshes/SK_FENOMENO_BR", unreal.Vector(-260.0, 0.0, 5.0), unreal.Rotator(0.0, 0.0, 0.0)),
        ("P2_LaPulga_AR", "/Game/Characters/SouthAmericaRoster/Meshes/SK_PULGA_AR", unreal.Vector(260.0, 0.0, 5.0), unreal.Rotator(0.0, 180.0, 0.0)),
    ]
    for label, folder, loc, rot in fighters_spec:
        sk_mesh = find_first_asset_by_class(folder, "SkeletalMesh")
        idle_anim = find_first_asset_by_class(folder, "AnimSequence", "Idle_Breath")
        if sk_mesh:
            f_actor = actor_subsys.spawn_actor_from_class(unreal.SkeletalMeshActor, loc, rot)
            f_actor.set_actor_label(label)
            sk_comp = f_actor.get_editor_property("skeletal_mesh_component")
            sk_comp.set_skeletal_mesh_asset(sk_mesh)
            if idle_anim:
                try:
                    sk_comp.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                    sk_comp.override_animation_data(idle_anim, is_looping=True, is_playing=True)
                except Exception:
                    pass
            unreal.log(f"[LA COPA ETERNA][MAP] Luchador instanciado: {label} -> {sk_mesh.get_name()}")

    # 3. Iluminación Renacimiento Sfumato (DirectionalLight + SkyLight + ExponentialHeightFog)
    sun = actor_subsys.spawn_actor_from_class(
        unreal.DirectionalLight, unreal.Vector(0.0, -500.0, 900.0), unreal.Rotator(-38.0, 48.0, 0.0)
    )
    sun.set_actor_label("Sun_RenacimientoSfumato_GoldenAmber")
    try:
        lc = sun.get_editor_property("light_component")
        lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        lc.set_intensity(6.5)
        lc.set_light_color(unreal.LinearColor(1.0, 0.84, 0.58, 1.0))
    except Exception:
        pass

    sky = actor_subsys.spawn_actor_from_class(
        unreal.SkyLight, unreal.Vector(0.0, 0.0, 600.0), unreal.Rotator(0.0, 0.0, 0.0)
    )
    sky.set_actor_label("SkyLight_SfumatoChiaroscuro")
    try:
        slc = sky.get_editor_property("light_component")
        slc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        slc.set_editor_property("real_time_capture", True)
    except Exception:
        pass

    fog = actor_subsys.spawn_actor_from_class(
        unreal.ExponentialHeightFog, unreal.Vector(0.0, 0.0, 120.0), unreal.Rotator(0.0, 0.0, 0.0)
    )
    fog.set_actor_label("Fog_LeonardoAerialPerspective")

    # 4. PostProcessVolume Unbound con M_PP_SfumatoChiaroscuro
    pp_vol = actor_subsys.spawn_actor_from_class(
        unreal.PostProcessVolume, unreal.Vector(0.0, 0.0, 200.0), unreal.Rotator(0.0, 0.0, 0.0)
    )
    pp_vol.set_actor_label("PPV_SfumatoChiaroscuro_Global")
    pp_vol.set_editor_property("unbound", True)
    pp_mat = unreal.EditorAssetLibrary.load_asset("/Game/TechArt/PostProcess/M_PP_SfumatoChiaroscuro")
    if pp_mat:
        try:
            settings = pp_vol.get_editor_property("settings")
            blendables = unreal.WeightedBlendables()
            blendables.set_editor_property("array", [unreal.WeightedBlendable(1.0, pp_mat)])
            settings.set_editor_property("weighted_blendables", blendables)
            pp_vol.set_editor_property("settings", settings)
            unreal.log("[LA COPA ETERNA][MAP] M_PP_SfumatoChiaroscuro vinculado al PostProcessVolume global.")
        except Exception as exc:
            unreal.log_warning(f"[LA COPA ETERNA][MAP] Aviso vinculando blendable: {exc}")

    # 5. Cámara Lateral 2.5D Broadcast + PlayerStart
    cam = actor_subsys.spawn_actor_from_class(
        unreal.CameraActor, unreal.Vector(0.0, 680.0, 165.0), unreal.Rotator(-6.0, -90.0, 0.0)
    )
    cam.set_actor_label("Camera_25D_FightingBroadcast")

    pstart = actor_subsys.spawn_actor_from_class(
        unreal.PlayerStart, unreal.Vector(0.0, 680.0, 165.0), unreal.Rotator(-6.0, -90.0, 0.0)
    )
    pstart.set_actor_label("PlayerStart_BroadcastView")

    saved = level_subsys.save_current_level()
    unreal.log(f"=== [LA COPA ETERNA] Nivel guardado ({saved}): {MAP_PACKAGE_PATH} ===")


if __name__ == "__main__":
    build_startup_level()
