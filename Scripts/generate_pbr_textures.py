#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_pbr_textures.py - SouthAmericaFightersCore ("La Copa Eterna")
Generador Procedural Determinista de Texturas PBR (Albedos de las 10 Selecciones CONMEBOL
+ Invitado Francia 98 + Boss Juez Supremo V.A.R., Normales Jacquard 90s, Micro-Poros de Piel,
Empaquetado ORM, Máscara de Barro/Césped, Balón de 32 Paneles y Atlas 1024x1024 por Luchador
en Assets/TexturesPBR/Fighters/ emparejados con las 17 Turnaround Sheets).
"""

import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Assets",
    "TexturesPBR",
)

FIGHTERS_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "Fighters")


def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FIGHTERS_OUTPUT_DIR, exist_ok=True)


def generate_jacquard_watermark_field(width: int, height: int) -> np.ndarray:
    """
    Genera un patrón geométrico de marca de agua estilo años 90 (rombos Jacquard + trama de hilo)
    en rango [0.0, 1.0].
    """
    y, x = np.meshgrid(
        np.linspace(0.0, 1.0, height, endpoint=False),
        np.linspace(0.0, 1.0, width, endpoint=False),
        indexing="ij",
    )
    # Rombos diagonales estilo casacas clásicas 1994-1998
    u = (x * 16.0) + (y * 16.0)
    v = (x * 16.0) - (y * 16.0)
    diamond = (np.abs(np.mod(u, 1.0) - 0.5) + np.abs(np.mod(v, 1.0) - 0.5))
    diamond_mask = ((diamond > 0.38) & (diamond < 0.62)).astype(np.float32)

    # Micro-trama de poliéster (urdimbre y trama)
    warp = 0.5 + 0.5 * np.sin(x * width * math.pi * 0.5)
    weft = 0.5 + 0.5 * np.cos(y * height * math.pi * 0.5)
    micro_weave = (warp * 0.6 + weft * 0.4).astype(np.float32)

    return np.clip(diamond_mask * 0.65 + micro_weave * 0.35, 0.0, 1.0)


def apply_fabric_shading_and_seams(rgb: np.ndarray, jacquard: np.ndarray) -> Image.Image:
    """
    Aplica el sutil brillo satinado del tejido Jacquard de los años 90, costuras de hombros/cuello
    y pliegues suaves de camiseta holgada.
    """
    h, w, _ = rgb.shape
    y, x = np.meshgrid(
        np.linspace(0.0, 1.0, h, endpoint=False),
        np.linspace(0.0, 1.0, w, endpoint=False),
        indexing="ij",
    )

    # Sutil modulación Jacquard (+4% en rombos satinados)
    mod = 0.96 + 0.07 * jacquard[:, :, None]

    # Pliegues de caída textil en la mitad inferior del torso
    drape_folds = 1.0 + 0.035 * np.sin(x * 14.0 * math.pi + np.sin(y * 6.0 * math.pi) * 0.8) * (y ** 0.7)
    rgb_out = np.clip(rgb.astype(np.float32) * mod * drape_folds[:, :, None], 0.0, 255.0).astype(np.uint8)

    img = Image.fromarray(rgb_out, mode="RGB")
    draw = ImageDraw.Draw(img)

    # Costura de cuello en V retro 90s y dobladillo inferior
    collar_box = [int(w * 0.38), int(h * 0.02), int(w * 0.62), int(h * 0.18)]
    draw.arc(collar_box, start=0, end=180, fill=(28, 30, 36), width=4)
    draw.line([(0, int(h * 0.96)), (w, int(h * 0.96))], fill=(24, 24, 28), width=3)

    return img


def generate_kit_albedos(size: int = 1024) -> list[str]:
    """
    Genera los 12 Albedos históricos de las 10 Selecciones CONMEBOL + Francia 98 + Juez Supremo V.A.R.
    """
    generated_files = []
    jacquard = generate_jacquard_watermark_field(size, size)
    y, x = np.meshgrid(
        np.linspace(0.0, 1.0, size, endpoint=False),
        np.linspace(0.0, 1.0, size, endpoint=False),
        indexing="ij",
    )

    # 1. ARGENTINA: Franjas verticales celestes y blancas + vivos negros + Sol dorado
    arg = np.zeros((size, size, 3), dtype=np.uint8)
    stripe_arg = (np.mod(x * 9.0, 1.0) < 0.52)
    arg[stripe_arg] = [116, 172, 223]   # Celeste Albiceleste
    arg[~stripe_arg] = [246, 248, 252]  # Blanco Puro
    arg[y < 0.06] = [20, 22, 26]        # Cuello polo negro 1994
    img_arg = apply_fabric_shading_and_seams(arg, jacquard)
    path_arg = os.path.join(OUTPUT_DIR, "T_Kit_Argentina_Albedo.png")
    img_arg.save(path_arg)
    generated_files.append(path_arg)

    # 2. BRASIL: Verde-Amarela (Amarillo Canarinha con cuello/puños verde bandera y marca de agua)
    bra = np.full((size, size, 3), [255, 214, 0], dtype=np.uint8)
    green_trim = (y < 0.07) | ((y > 0.88) & (y < 0.93))
    bra[green_trim] = [0, 156, 59]
    # Escudo central de agua en pecho
    chest_diamond = (np.abs(x - 0.5) + np.abs(y - 0.35)) < 0.14
    bra[chest_diamond] = [245, 198, 0]
    img_bra = apply_fabric_shading_and_seams(bra, jacquard)
    path_bra = os.path.join(OUTPUT_DIR, "T_Kit_Brazil_Albedo.png")
    img_bra.save(path_bra)
    generated_files.append(path_bra)

    # 3. URUGUAY: Celeste Charrúa con cuello blanco clásico y vivos dorados
    uru = np.full((size, size, 3), [85, 166, 230], dtype=np.uint8)
    uru[y < 0.075] = [248, 248, 250]
    uru[(y >= 0.075) & (y < 0.09)] = [212, 175, 55]
    img_uru = apply_fabric_shading_and_seams(uru, jacquard)
    path_uru = os.path.join(OUTPUT_DIR, "T_Kit_Uruguay_Albedo.png")
    img_uru.save(path_uru)
    generated_files.append(path_uru)

    # 4. COLOMBIA: Amarillo Cafetero con franjas tricolor en mangas/hombros
    col = np.full((size, size, 3), [252, 209, 22], dtype=np.uint8)
    shoulder_blue = ((x < 0.14) | (x > 0.86)) & (y < 0.45)
    shoulder_red = ((x < 0.07) | (x > 0.93)) & (y < 0.45)
    col[shoulder_blue] = [0, 56, 147]
    col[shoulder_red] = [206, 17, 38]
    img_col = apply_fabric_shading_and_seams(col, jacquard)
    path_col = os.path.join(OUTPUT_DIR, "T_Kit_Colombia_Albedo.png")
    img_col.save(path_col)
    generated_files.append(path_col)

    # 5. CHILE: Rojo Intenso "La Roja" con cuello azul/blanco
    chi = np.full((size, size, 3), [213, 43, 30], dtype=np.uint8)
    chi[y < 0.06] = [0, 57, 166]
    chi[(y >= 0.06) & (y < 0.085)] = [250, 250, 252]
    img_chi = apply_fabric_shading_and_seams(chi, jacquard)
    path_chi = os.path.join(OUTPUT_DIR, "T_Kit_Chile_Albedo.png")
    img_chi.save(path_chi)
    generated_files.append(path_chi)

    # 6. PARAGUAY: Albirroja de bastones verticales rojos y blancos con detalles azules
    par = np.zeros((size, size, 3), dtype=np.uint8)
    stripe_par = (np.mod(x * 11.0, 1.0) < 0.5)
    par[stripe_par] = [213, 43, 30]
    par[~stripe_par] = [248, 248, 250]
    par[y < 0.065] = [0, 56, 168]
    img_par = apply_fabric_shading_and_seams(par, jacquard)
    path_par = os.path.join(OUTPUT_DIR, "T_Kit_Paraguay_Albedo.png")
    img_par.save(path_par)
    generated_files.append(path_par)

    # 7. PERÚ: Blanca con la histórica banda diagonal roja de hombro izquierdo a cadera derecha
    per = np.full((size, size, 3), [248, 248, 250], dtype=np.uint8)
    sash_mask = np.abs((x - 0.15) - (y * 0.72)) < 0.11
    per[sash_mask] = [217, 16, 35]
    per[y < 0.05] = [217, 16, 35]
    img_per = apply_fabric_shading_and_seams(per, jacquard)
    path_per = os.path.join(OUTPUT_DIR, "T_Kit_Peru_Albedo.png")
    img_per.save(path_per)
    generated_files.append(path_per)

    # 8. ECUADOR: Amarillo con banda pectoral azul marino y ribetes rojos
    ecu = np.full((size, size, 3), [255, 209, 0], dtype=np.uint8)
    chest_band = (y > 0.24) & (y < 0.36)
    ecu[chest_band] = [0, 51, 160]
    ecu[(y >= 0.36) & (y < 0.39)] = [239, 51, 64]
    img_ecu = apply_fabric_shading_and_seams(ecu, jacquard)
    path_ecu = os.path.join(OUTPUT_DIR, "T_Kit_Ecuador_Albedo.png")
    img_ecu.save(path_ecu)
    generated_files.append(path_ecu)

    # 9. VENEZUELA: La Vinotinto con vivos dorados y cuello blanco
    ven = np.full((size, size, 3), [110, 18, 38], dtype=np.uint8)
    ven[y < 0.06] = [244, 196, 48]
    ven[(y >= 0.06) & (y < 0.08)] = [248, 248, 250]
    img_ven = apply_fabric_shading_and_seams(ven, jacquard)
    path_ven = os.path.join(OUTPUT_DIR, "T_Kit_Venezuela_Albedo.png")
    img_ven.save(path_ven)
    generated_files.append(path_ven)

    # 10. BOLIVIA: Verde Altiplano con guarda andina Tiahuanaco en el pecho
    bol = np.full((size, size, 3), [0, 121, 52], dtype=np.uint8)
    andean_band = (y > 0.28) & (y < 0.35)
    step_pattern = (np.mod(x * 24.0 + np.floor(y * 48.0) * 0.25, 1.0) < 0.5)
    bol[andean_band & step_pattern] = [249, 227, 0]
    bol[andean_band & (~step_pattern)] = [213, 43, 30]
    img_bol = apply_fabric_shading_and_seams(bol, jacquard)
    path_bol = os.path.join(OUTPUT_DIR, "T_Kit_Bolivia_Albedo.png")
    img_bol.save(path_bol)
    generated_files.append(path_bol)

    # 11. FRANCIA (Invitado Clásico 1998): Azul Francia con franja pectoral blanca y roja
    fra = np.full((size, size, 3), [0, 38, 100], dtype=np.uint8)
    fra[(y > 0.26) & (y <= 0.31)] = [248, 248, 252]
    fra[(y > 0.31) & (y <= 0.36)] = [239, 65, 53]
    fra[y < 0.05] = [212, 175, 55]
    img_fra = apply_fabric_shading_and_seams(fra, jacquard)
    path_fra = os.path.join(OUTPUT_DIR, "T_Kit_France_Albedo.png")
    img_fra.save(path_fra)
    generated_files.append(path_fra)

    # 12. JUEZ SUPREMO V.A.R. (Final Boss): Fibra de carbono negra y circuitos de oro cibernético
    var_boss = np.full((size, size, 3), [18, 20, 26], dtype=np.uint8)
    cyber_grid = (np.abs(np.mod(x * 32.0, 1.0) - 0.5) < 0.04) | (np.abs(np.mod(y * 32.0, 1.0) - 0.5) < 0.04)
    gold_stripes = (np.abs(x - 0.5) < 0.08) | ((y > 0.18) & (y < 0.22))
    var_boss[cyber_grid] = [48, 54, 68]
    var_boss[gold_stripes] = [245, 190, 25]
    img_var = apply_fabric_shading_and_seams(var_boss, jacquard)
    path_var = os.path.join(OUTPUT_DIR, "T_Kit_VARBoss_Albedo.png")
    img_var.save(path_var)
    generated_files.append(path_var)

    return generated_files


def height_to_normal_map(height_field: np.ndarray, strength: float = 3.0) -> Image.Image:
    """
    Convierte un campo de alturas [0..1] en un Mapa de Normales Tangent-Space (OpenGL/UE5 RGB).
    """
    dh_dy, dh_dx = np.gradient(height_field.astype(np.float32))
    nx = -dh_dx * strength
    ny = -dh_dy * strength
    nz = np.ones_like(height_field, dtype=np.float32)

    inv_len = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-8)
    nx *= inv_len
    ny *= inv_len
    nz *= inv_len

    r = np.clip((nx * 0.5 + 0.5) * 255.0, 0.0, 255.0).astype(np.uint8)
    g = np.clip((ny * 0.5 + 0.5) * 255.0, 0.0, 255.0).astype(np.uint8)
    b = np.clip((nz * 0.5 + 0.5) * 255.0, 0.0, 255.0).astype(np.uint8)

    return Image.fromarray(np.stack([r, g, b], axis=-1), mode="RGB")


def generate_master_pbr_maps(size: int = 1024) -> list[str]:
    """
    Genera los mapas PBR maestros compartidos:
      - T_Retro90s_Jacquard_Normal.png
      - T_Skin_MicroPores_Normal.png
      - T_FighterKit_ORM.png
      - T_PitchDirt_And_Grass_Mask.png
      - T_Ball_32Panels_Albedo.png
      - T_Ball_32Panels_Normal.png
    """
    generated = []

    # 1. T_Retro90s_Jacquard_Normal.png (sutil micro-trama textil sin cuadrículas bruscas)
    jacquard_h = generate_jacquard_watermark_field(size, size)
    jacquard_soft = np.asarray(
        Image.fromarray(np.clip(jacquard_h * 255.0, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=1.8)),
        dtype=np.float32,
    ) / 255.0
    jacquard_normal = height_to_normal_map(jacquard_soft, strength=0.85)
    p_jacquard = os.path.join(OUTPUT_DIR, "T_Retro90s_Jacquard_Normal.png")
    jacquard_normal.save(p_jacquard)
    generated.append(p_jacquard)

    # 2. T_Skin_MicroPores_Normal.png (Micro-poros Voronoi cutáneos sutiles para M_FighterSkin_Master)
    rng = np.random.default_rng(seed=19861990)
    pore_size = 512
    num_seeds = 950
    seed_pts = rng.uniform(0.0, pore_size, size=(num_seeds, 2)).astype(np.float32)

    yy, xx = np.meshgrid(
        np.arange(pore_size, dtype=np.float32),
        np.arange(pore_size, dtype=np.float32),
        indexing="ij",
    )
    min_dist_sq = np.full((pore_size, pore_size), 1e9, dtype=np.float32)
    for sx, sy in seed_pts:
        dx = np.minimum(np.abs(xx - sx), pore_size - np.abs(xx - sx))
        dy = np.minimum(np.abs(yy - sy), pore_size - np.abs(yy - sy))
        d2 = dx * dx + dy * dy
        min_dist_sq = np.minimum(min_dist_sq, d2)

    pore_cavity = 1.0 - np.exp(-min_dist_sq / 14.0)
    skin_normal = height_to_normal_map(pore_cavity, strength=0.65)
    p_skin = os.path.join(OUTPUT_DIR, "T_Skin_MicroPores_Normal.png")
    skin_normal.save(p_skin)
    generated.append(p_skin)

    # 3. T_FighterKit_ORM.png (R = Ambient Occlusion, G = Roughness, B = Metallic/Anisotropy)
    y, x = np.meshgrid(
        np.linspace(0.0, 1.0, size, endpoint=False),
        np.linspace(0.0, 1.0, size, endpoint=False),
        indexing="ij",
    )
    ao_channel = np.clip((0.88 + 0.12 * np.sin(x * 12.0 * math.pi)) * 255.0, 0.0, 255.0).astype(np.uint8)
    rough_channel = np.clip((0.52 - 0.26 * jacquard_h) * 255.0, 35.0, 235.0).astype(np.uint8)
    aniso_channel = np.clip((0.35 + 0.45 * jacquard_h) * 255.0, 0.0, 255.0).astype(np.uint8)

    orm_img = Image.fromarray(np.stack([ao_channel, rough_channel, aniso_channel], axis=-1), mode="RGB")
    p_orm = os.path.join(OUTPUT_DIR, "T_FighterKit_ORM.png")
    orm_img.save(p_orm)
    generated.append(p_orm)

    # 4. T_PitchDirt_And_Grass_Mask.png (R = Barro denso, G = Manchas de césped/clorofila, B = Salpicadura fina)
    noise_low = rng.uniform(0.0, 1.0, size=(128, 128)).astype(np.float32)
    img_low = Image.fromarray((noise_low * 255).astype(np.uint8)).resize((size, size), resample=Image.Resampling.BICUBIC)
    img_LowBlur = img_low.filter(ImageFilter.GaussianBlur(radius=6))
    arr_mud = np.asarray(img_LowBlur, dtype=np.float32) / 255.0

    vertical_boot_bias = np.clip(1.25 - y * 1.15, 0.0, 1.0)
    mud_r = np.clip(((arr_mud > 0.44).astype(np.float32) * arr_mud * vertical_boot_bias) * 255.0, 0.0, 255.0).astype(np.uint8)
    grass_g = np.clip(((arr_mud > 0.50).astype(np.float32) * (1.0 - np.abs(arr_mud - 0.62) * 3.0)) * 255.0, 0.0, 255.0).astype(np.uint8)
    splatter_b = np.clip((rng.uniform(0.0, 1.0, size=(size, size)) > 0.82).astype(np.float32) * arr_mud * 255.0, 0.0, 255.0).astype(np.uint8)

    dirt_img = Image.fromarray(np.stack([mud_r, grass_g, splatter_b], axis=-1), mode="RGB")
    p_dirt = os.path.join(OUTPUT_DIR, "T_PitchDirt_And_Grass_Mask.png")
    dirt_img.save(p_dirt)
    generated.append(p_dirt)

    # 5. T_Ball_32Panels_Albedo.png y T_Ball_32Panels_Normal.png (Balón Clásico de 32 Paneles Hexágonos/Pentágonos)
    ball_size = 1024
    by, bx = np.meshgrid(
        np.linspace(0.0, 1.0, ball_size, endpoint=False),
        np.linspace(0.0, 1.0, ball_size, endpoint=False),
        indexing="ij",
    )

    # Grilla hexagonal/pentagonal de 32 paneles en espacio UV esférico
    scale_u, scale_v = 6.0, 3.4641016
    u_scaled = bx * scale_u
    v_scaled = by * scale_v

    def hex_dist(u_coord: np.ndarray, v_coord: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        r1x = np.mod(u_coord, 1.0) - 0.5
        r1y = np.mod(v_coord, 1.73205) - 0.866025
        r2x = np.mod(u_coord + 0.5, 1.0) - 0.5
        r2y = np.mod(v_coord + 0.866025, 1.73205) - 0.866025

        d1 = np.maximum(np.abs(r1x), np.abs(r1x) * 0.5 + np.abs(r1y) * 0.866025)
        d2 = np.maximum(np.abs(r2x), np.abs(r2x) * 0.5 + np.abs(r2y) * 0.866025)
        is_center_cell = d1 < d2
        return np.minimum(d1, d2), is_center_cell

    panel_dist, is_pentagon = hex_dist(u_scaled, v_scaled)
    seam_mask = panel_dist > 0.455

    ball_albedo = np.full((ball_size, ball_size, 3), [245, 245, 242], dtype=np.uint8)
    # Paneles oscuros con triángulos dorados estilo Tango/Azteca
    ball_albedo[is_pentagon] = [24, 26, 32]
    aztec_ring = (panel_dist > 0.28) & (panel_dist < 0.37) & (~is_pentagon)
    ball_albedo[aztec_ring] = [212, 168, 42]
    ball_albedo[seam_mask] = [14, 14, 16]

    p_ball_albedo = os.path.join(OUTPUT_DIR, "T_Ball_32Panels_Albedo.png")
    Image.fromarray(ball_albedo, mode="RGB").save(p_ball_albedo)
    generated.append(p_ball_albedo)

    # Mapa de normales acolchado de los 32 paneles de cuero
    panel_height = np.clip(1.0 - (panel_dist / 0.48) ** 4, 0.0, 1.0)
    leather_grain = 0.04 * np.sin(bx * 420.0) * np.cos(by * 420.0)
    ball_normal = height_to_normal_map(panel_height + leather_grain, strength=6.5)
    p_ball_normal = os.path.join(OUTPUT_DIR, "T_Ball_32Panels_Normal.png")
    ball_normal.save(p_ball_normal)
    generated.append(p_ball_normal)

    return generated


# ============================================================================
# ESPECIFICACIONES DE ATLAS 1024x1024 POR LUCHADOR (EMPAREJADAS A TURNAROUNDS)
# Contrato UV glTF/OpenGL: PIL y=0..512 -> glTF v=0.5..1.0; y=512..1024 -> v=0.0..0.5
# ============================================================================

FIGHTER_TEXTURE_SPECS = [
    {
        "id": "FENOMENO_BR",
        "skin": (176, 125, 92),
        "lip": (146, 92, 74),
        "brow": (36, 26, 20),
        "facial_hair": "none",
        "facial_hair_color": (32, 24, 20),
        "hair_color": (46, 35, 28),
        "hair_style": "buzz_r9",
        "eye_color": (72, 46, 28),
        "headband": None,
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "9",
        "kit_pattern": "solid_trim",
        "shirt_primary": (244, 206, 24),
        "shirt_secondary": (12, 138, 62),
        "shirt_accent": (12, 138, 62),
        "collar_style": "v_neck",
        "collar_color": (12, 138, 62),
        "collar_trim": (244, 206, 24),
        "number_color": (12, 138, 62),
        "number_outline": (244, 206, 24),
        "crest_colors": ((12, 138, 62), (244, 206, 24), (27, 75, 184)),
        "sleeve_color": (244, 206, 24),
        "sleeve_stripe": (12, 138, 62),
        "cuff_color": (12, 138, 62),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (26, 72, 178),
        "shorts_stripe": (12, 138, 62),
        "socks_color": (236, 238, 242),
        "socks_cuff": ((236, 238, 242), (12, 138, 62)),
        "ankle_tape": (204, 188, 158),
        "boot_style": "silver_blue_volt",
    },
    {
        "id": "BRUXO_BR",
        "skin": (162, 112, 82),
        "lip": (138, 84, 68),
        "brow": (30, 22, 18),
        "facial_hair": "goatee",
        "facial_hair_color": (28, 22, 18),
        "hair_color": (34, 25, 20),
        "hair_style": "curly_ponytail",
        "eye_color": (68, 42, 26),
        "headband": (238, 240, 244),
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "10",
        "kit_pattern": "solid_trim",
        "shirt_primary": (244, 206, 24),
        "shirt_secondary": (12, 138, 62),
        "shirt_accent": (12, 138, 62),
        "collar_style": "v_neck",
        "collar_color": (12, 138, 62),
        "collar_trim": (244, 206, 24),
        "number_color": (12, 138, 62),
        "number_outline": (244, 206, 24),
        "crest_colors": ((12, 138, 62), (244, 206, 24), (27, 75, 184)),
        "sleeve_color": (244, 206, 24),
        "sleeve_stripe": None,
        "cuff_color": (12, 138, 62),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (26, 72, 178),
        "shorts_stripe": (12, 138, 62),
        "socks_color": (236, 238, 242),
        "socks_cuff": ((236, 238, 242), (12, 138, 62)),
        "ankle_tape": (204, 188, 158),
        "boot_style": "white_gold",
    },
    {
        "id": "CANON_AR",
        "skin": (184, 134, 102),
        "lip": (146, 94, 78),
        "brow": (92, 62, 34),
        "facial_hair": "lion_beard",
        "facial_hair_color": (74, 52, 32),
        "hair_color": (156, 102, 46),
        "hair_style": "long_mane",
        "eye_color": (102, 110, 74),
        "headband": (22, 26, 36),
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "9",
        "kit_pattern": "vertical_stripes",
        "shirt_primary": (116, 182, 232),
        "shirt_secondary": (242, 244, 248),
        "shirt_accent": (22, 24, 30),
        "collar_style": "polo_v",
        "collar_color": (22, 24, 30),
        "collar_trim": (242, 244, 248),
        "number_color": (20, 22, 28),
        "number_outline": (242, 244, 248),
        "crest_colors": ((116, 182, 232), (242, 244, 248), (212, 172, 54)),
        "sleeve_color": (116, 182, 232),
        "sleeve_stripe": (242, 244, 248),
        "cuff_color": (22, 24, 30),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (22, 24, 29),
        "shorts_stripe": (116, 182, 232),
        "socks_color": (238, 240, 244),
        "socks_cuff": ((116, 182, 232), (242, 244, 248)),
        "ankle_tape": (204, 188, 158),
        "boot_style": "classic_black_white",
    },
    {
        "id": "PULGA_AR",
        "skin": (206, 156, 126),
        "lip": (166, 108, 92),
        "brow": (66, 44, 30),
        "facial_hair": "ginger_beard",
        "facial_hair_color": (118, 58, 32),
        "hair_color": (54, 38, 28),
        "hair_style": "short_fade",
        "eye_color": (74, 48, 30),
        "headband": None,
        "wrist_tape": (240, 242, 245),
        "arm_tattoo": True,
        "calf_tattoo": True,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "10",
        "kit_pattern": "vertical_stripes",
        "shirt_primary": (104, 178, 226),
        "shirt_secondary": (244, 246, 250),
        "shirt_accent": (202, 168, 76),
        "collar_style": "v_neck",
        "collar_color": (202, 168, 76),
        "collar_trim": (244, 246, 250),
        "number_color": (38, 114, 184),
        "number_outline": (244, 246, 250),
        "crest_colors": ((104, 178, 226), (244, 246, 250), (202, 168, 76)),
        "sleeve_color": (244, 246, 250),
        "sleeve_stripe": (104, 178, 226),
        "cuff_color": (104, 178, 226),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (242, 244, 247),
        "shorts_stripe": (104, 178, 226),
        "socks_color": (98, 174, 224),
        "socks_cuff": ((244, 246, 250), (98, 174, 224)),
        "ankle_tape": (206, 190, 160),
        "boot_style": "gold_white",
    },
    {
        "id": "PIBE_CO",
        "skin": (182, 128, 94),
        "lip": (148, 92, 74),
        "brow": (36, 26, 18),
        "facial_hair": "blonde_stache",
        "facial_hair_color": (176, 128, 42),
        "hair_color": (229, 188, 70),
        "hair_style": "golden_afro",
        "eye_color": (72, 46, 28),
        "headband": None,
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": True,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "10",
        "kit_pattern": "colombia_shoulder",
        "shirt_primary": (244, 196, 22),
        "shirt_secondary": (22, 48, 122),
        "shirt_accent": (196, 24, 38),
        "collar_style": "polo_v",
        "collar_color": (22, 48, 122),
        "collar_trim": (196, 24, 38),
        "number_color": (28, 42, 98),
        "number_outline": (196, 24, 38),
        "crest_colors": ((244, 196, 22), (22, 48, 122), (196, 24, 38)),
        "sleeve_color": (244, 196, 22),
        "sleeve_stripe": (22, 48, 122),
        "cuff_color": (22, 48, 122),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (22, 68, 168),
        "shorts_stripe": (196, 24, 38),
        "socks_color": (238, 240, 244),
        "socks_cuff": ((22, 48, 122), (196, 24, 38)),
        "ankle_tape": (204, 188, 158),
        "boot_style": "classic_black_white",
    },
    {
        "id": "LOCO_CO",
        "skin": (180, 130, 96),
        "lip": (144, 92, 74),
        "brow": (24, 18, 16),
        "facial_hair": "thick_stache",
        "facial_hair_color": (24, 18, 16),
        "hair_color": (34, 26, 22),
        "hair_style": "black_afro",
        "eye_color": (64, 42, 26),
        "headband": None,
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "1",
        "kit_pattern": "gk_90s_shatter",
        "shirt_primary": (108, 42, 212),
        "shirt_secondary": (34, 206, 232),
        "shirt_accent": (176, 62, 238),
        "collar_style": "crew",
        "collar_color": (20, 20, 26),
        "collar_trim": (34, 206, 232),
        "number_color": (20, 20, 28),
        "number_outline": (34, 206, 232),
        "crest_colors": ((244, 196, 22), (22, 48, 122), (196, 24, 38)),
        "sleeve_color": (108, 42, 212),
        "sleeve_stripe": (34, 206, 232),
        "cuff_color": (18, 18, 24),
        "keeper_pads": True,
        "captain_band": False,
        "shorts_color": (20, 21, 26),
        "shorts_stripe": (108, 42, 212),
        "socks_color": (22, 23, 28),
        "socks_cuff": ((108, 42, 212), (34, 206, 232)),
        "ankle_tape": (150, 142, 130),
        "boot_style": "classic_black_white",
    },
    {
        "id": "PISTOLERO_UY",
        "skin": (186, 138, 106),
        "lip": (150, 96, 78),
        "brow": (32, 24, 20),
        "facial_hair": "stubble",
        "facial_hair_color": (38, 30, 26),
        "hair_color": (38, 30, 24),
        "hair_style": "short_fade",
        "eye_color": (72, 54, 34),
        "headband": None,
        "wrist_tape": (240, 242, 245),
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "9",
        "kit_pattern": "solid_trim",
        "shirt_primary": (90, 164, 214),
        "shirt_secondary": (242, 244, 248),
        "shirt_accent": (204, 174, 78),
        "collar_style": "crew",
        "collar_color": (242, 244, 248),
        "collar_trim": (204, 174, 78),
        "number_color": (246, 248, 250),
        "number_outline": (26, 48, 84),
        "crest_colors": ((90, 164, 214), (242, 244, 248), (204, 174, 78)),
        "sleeve_color": (90, 164, 214),
        "sleeve_stripe": None,
        "cuff_color": (242, 244, 248),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (20, 21, 26),
        "shorts_stripe": (90, 164, 214),
        "socks_color": (22, 23, 28),
        "socks_cuff": ((22, 23, 28), (90, 164, 214)),
        "ankle_tape": (176, 162, 138),
        "boot_style": "orange_blue",
    },
    {
        "id": "MATADOR_UY",
        "skin": (196, 148, 118),
        "lip": (156, 102, 86),
        "brow": (24, 20, 18),
        "facial_hair": "matador_beard",
        "facial_hair_color": (32, 26, 24),
        "hair_color": (24, 24, 28),
        "hair_style": "long_straight",
        "eye_color": (60, 40, 26),
        "headband": (26, 26, 30),
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "10",
        "kit_pattern": "solid_trim",
        "shirt_primary": (88, 162, 212),
        "shirt_secondary": (242, 244, 248),
        "shirt_accent": (204, 174, 78),
        "collar_style": "polo_v",
        "collar_color": (242, 244, 248),
        "collar_trim": (204, 174, 78),
        "number_color": (246, 248, 250),
        "number_outline": (26, 48, 84),
        "crest_colors": ((88, 162, 212), (242, 244, 248), (204, 174, 78)),
        "sleeve_color": (88, 162, 212),
        "sleeve_stripe": None,
        "cuff_color": (242, 244, 248),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (20, 21, 26),
        "shorts_stripe": (242, 244, 248),
        "socks_color": (22, 23, 28),
        "socks_cuff": ((22, 23, 28), (88, 162, 212)),
        "ankle_tape": (168, 156, 134),
        "boot_style": "crimson_black",
    },
    {
        "id": "BAMBAM_CL",
        "skin": (186, 136, 102),
        "lip": (148, 94, 76),
        "brow": (30, 22, 18),
        "facial_hair": "light_stache",
        "facial_hair_color": (42, 32, 26),
        "hair_color": (34, 26, 22),
        "hair_style": "wavy_90s",
        "eye_color": (66, 42, 26),
        "headband": None,
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": True,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "9",
        "kit_pattern": "chile_yoke",
        "shirt_primary": (200, 28, 36),
        "shirt_secondary": (244, 246, 248),
        "shirt_accent": (22, 46, 118),
        "collar_style": "polo_v",
        "collar_color": (22, 46, 118),
        "collar_trim": (244, 246, 248),
        "number_color": (246, 248, 250),
        "number_outline": (22, 46, 118),
        "crest_colors": ((200, 28, 36), (22, 46, 118), (244, 246, 248)),
        "sleeve_color": (200, 28, 36),
        "sleeve_stripe": (244, 246, 248),
        "cuff_color": (22, 46, 118),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (24, 70, 168),
        "shorts_stripe": (200, 28, 36),
        "socks_color": (236, 238, 242),
        "socks_cuff": ((236, 238, 242), (24, 70, 168)),
        "ankle_tape": (204, 188, 158),
        "boot_style": "classic_black_red",
    },
    {
        "id": "REY_CL",
        "skin": (182, 130, 96),
        "lip": (146, 92, 74),
        "brow": (24, 18, 16),
        "facial_hair": "king_beard",
        "facial_hair_color": (26, 20, 18),
        "hair_color": (28, 22, 20),
        "hair_style": "mohawk",
        "eye_color": (64, 40, 24),
        "headband": None,
        "wrist_tape": None,
        "arm_tattoo": True,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": True,
        "eyebrow_slit": True,
        "number": "8",
        "kit_pattern": "solid_blue_sleeves",
        "shirt_primary": (190, 34, 42),
        "shirt_secondary": (30, 68, 150),
        "shirt_accent": (244, 246, 248),
        "collar_style": "v_neck",
        "collar_color": (24, 48, 108),
        "collar_trim": (244, 246, 248),
        "number_color": (246, 248, 250),
        "number_outline": (24, 48, 108),
        "crest_colors": ((190, 34, 42), (30, 68, 150), (244, 246, 248)),
        "sleeve_color": (30, 68, 150),
        "sleeve_stripe": None,
        "cuff_color": (24, 48, 108),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (28, 66, 148),
        "shorts_stripe": (244, 246, 248),
        "socks_color": (182, 32, 42),
        "socks_cuff": ((24, 48, 108), (244, 246, 248)),
        "ankle_tape": (204, 188, 158),
        "boot_style": "silver_red",
    },
    {
        "id": "BULLDOG_PY",
        "skin": (178, 128, 96),
        "lip": (142, 92, 74),
        "brow": (46, 40, 38),
        "facial_hair": "heavy_stubble",
        "facial_hair_color": (56, 52, 50),
        "hair_color": (62, 60, 62),
        "hair_style": "short_buzz",
        "eye_color": (72, 52, 34),
        "headband": None,
        "wrist_tape": (236, 236, 232),
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "1",
        "kit_pattern": "gk_bulldog_slash",
        "shirt_primary": (42, 54, 58),
        "shirt_secondary": (12, 166, 90),
        "shirt_accent": (18, 20, 24),
        "collar_style": "crew",
        "collar_color": (18, 20, 24),
        "collar_trim": (12, 166, 90),
        "number_color": (176, 186, 192),
        "number_outline": (18, 20, 24),
        "crest_colors": ((236, 238, 240), (190, 34, 42), (42, 54, 58)),
        "sleeve_color": (42, 54, 58),
        "sleeve_stripe": (12, 166, 90),
        "cuff_color": (18, 20, 24),
        "keeper_pads": True,
        "captain_band": False,
        "shorts_color": (20, 21, 24),
        "shorts_stripe": (12, 166, 90),
        "socks_color": (22, 23, 27),
        "socks_cuff": ((22, 23, 27), (12, 166, 90)),
        "ankle_tape": (196, 182, 152),
        "boot_style": "classic_black_white",
    },
    {
        "id": "MAESTRO_PE",
        "skin": (174, 122, 88),
        "lip": (140, 88, 70),
        "brow": (24, 20, 18),
        "facial_hair": "neat_stache",
        "facial_hair_color": (24, 18, 16),
        "hair_color": (24, 24, 28),
        "hair_style": "classic_90s",
        "eye_color": (62, 40, 24),
        "headband": None,
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "10",
        "kit_pattern": "peru_sash",
        "shirt_primary": (242, 243, 246),
        "shirt_secondary": (184, 28, 42),
        "shirt_accent": (206, 170, 74),
        "collar_style": "v_neck",
        "collar_color": (184, 28, 42),
        "collar_trim": (206, 170, 74),
        "number_color": (184, 28, 42),
        "number_outline": (242, 243, 246),
        "crest_colors": ((184, 28, 42), (242, 243, 246), (206, 170, 74)),
        "sleeve_color": (242, 243, 246),
        "sleeve_stripe": None,
        "cuff_color": (184, 28, 42),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (242, 243, 246),
        "shorts_stripe": (184, 28, 42),
        "socks_color": (238, 240, 244),
        "socks_cuff": ((184, 28, 42), (238, 240, 244)),
        "ankle_tape": (204, 188, 158),
        "boot_style": "classic_black_white",
    },
    {
        "id": "TREN_EC",
        "skin": (98, 62, 44),
        "lip": (86, 52, 42),
        "brow": (20, 16, 14),
        "facial_hair": "short_chin",
        "facial_hair_color": (22, 18, 16),
        "hair_color": (24, 20, 18),
        "hair_style": "short_fade",
        "eye_color": (48, 30, 18),
        "headband": None,
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "16",
        "kit_pattern": "ecuador_tricolor",
        "shirt_primary": (244, 184, 22),
        "shirt_secondary": (24, 46, 94),
        "shirt_accent": (176, 28, 40),
        "collar_style": "v_neck",
        "collar_color": (24, 46, 94),
        "collar_trim": (176, 28, 40),
        "number_color": (24, 46, 94),
        "number_outline": (244, 184, 22),
        "crest_colors": ((244, 184, 22), (24, 46, 94), (176, 28, 40)),
        "sleeve_color": (24, 46, 94),
        "sleeve_stripe": (176, 28, 40),
        "cuff_color": (176, 28, 40),
        "keeper_pads": False,
        "captain_band": True,
        "shorts_color": (24, 46, 94),
        "shorts_stripe": (244, 184, 22),
        "socks_color": (24, 46, 94),
        "socks_cuff": ((244, 184, 22), (176, 28, 40)),
        "ankle_tape": (196, 184, 158),
        "boot_style": "volt_green",
    },
    {
        "id": "HURACAN_VE",
        "skin": (182, 134, 102),
        "lip": (146, 94, 76),
        "brow": (26, 20, 18),
        "facial_hair": "goatee",
        "facial_hair_color": (26, 20, 18),
        "hair_color": (30, 24, 22),
        "hair_style": "swept_back",
        "eye_color": (66, 42, 26),
        "headband": None,
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "18",
        "kit_pattern": "solid_trim",
        "shirt_primary": (96, 20, 38),
        "shirt_secondary": (210, 184, 122),
        "shirt_accent": (210, 184, 122),
        "collar_style": "v_neck",
        "collar_color": (210, 184, 122),
        "collar_trim": (96, 20, 38),
        "number_color": (214, 188, 126),
        "number_outline": (64, 12, 24),
        "crest_colors": ((96, 20, 38), (210, 184, 122), (244, 206, 24)),
        "sleeve_color": (96, 20, 38),
        "sleeve_stripe": None,
        "cuff_color": (210, 184, 122),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (96, 20, 38),
        "shorts_stripe": (210, 184, 122),
        "socks_color": (96, 20, 38),
        "socks_cuff": ((210, 184, 122), (96, 20, 38)),
        "ankle_tape": (162, 134, 118),
        "boot_style": "metallic_gold",
    },
    {
        "id": "DIABLO_BO",
        "skin": (176, 126, 92),
        "lip": (142, 90, 72),
        "brow": (22, 18, 16),
        "facial_hair": "thick_stache",
        "facial_hair_color": (20, 16, 14),
        "hair_color": (24, 22, 24),
        "hair_style": "wavy_90s",
        "eye_color": (60, 38, 22),
        "headband": None,
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "10",
        "kit_pattern": "bolivia_tricolor",
        "shirt_primary": (14, 122, 66),
        "shirt_secondary": (214, 34, 34),
        "shirt_accent": (244, 212, 24),
        "collar_style": "polo_v",
        "collar_color": (214, 34, 34),
        "collar_trim": (244, 212, 24),
        "number_color": (244, 246, 248),
        "number_outline": (14, 122, 66),
        "crest_colors": ((14, 122, 66), (244, 212, 24), (214, 34, 34)),
        "sleeve_color": (14, 122, 66),
        "sleeve_stripe": None,
        "cuff_color": (214, 34, 34),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (242, 244, 246),
        "shorts_stripe": (14, 122, 66),
        "socks_color": (14, 122, 66),
        "socks_cuff": ((214, 34, 34), (244, 212, 24)),
        "ankle_tape": (204, 188, 158),
        "boot_style": "classic_black_white",
    },
    {
        "id": "GENERAL_FR",
        "skin": (204, 156, 128),
        "lip": (162, 108, 92),
        "brow": (56, 46, 40),
        "facial_hair": "stubble",
        "facial_hair_color": (68, 60, 56),
        "hair_color": (76, 68, 64),
        "hair_style": "buzz_receding",
        "eye_color": (92, 104, 72),
        "headband": None,
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "10",
        "kit_pattern": "france_98",
        "shirt_primary": (22, 55, 150),
        "shirt_secondary": (196, 30, 44),
        "shirt_accent": (244, 246, 250),
        "collar_style": "polo_white",
        "collar_color": (244, 246, 250),
        "collar_trim": (22, 55, 150),
        "number_color": (246, 248, 252),
        "number_outline": (22, 55, 150),
        "crest_colors": ((22, 55, 150), (244, 246, 250), (206, 168, 62)),
        "sleeve_color": (22, 55, 150),
        "sleeve_stripe": None,
        "cuff_color": (22, 55, 150),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (242, 244, 247),
        "shorts_stripe": (22, 55, 150),
        "socks_color": (162, 26, 40),
        "socks_cuff": ((22, 55, 150), (244, 246, 250)),
        "ankle_tape": (204, 188, 158),
        "boot_style": "white_gold",
    },
    {
        "id": "SUPREME_JUDGE_BOSS",
        "skin": (166, 123, 82),
        "lip": (118, 86, 58),
        "brow": (68, 52, 38),
        "facial_hair": "cyber_var",
        "facial_hair_color": (38, 42, 50),
        "hair_color": (44, 224, 240),
        "hair_style": "var_drones",
        "eye_color": (44, 245, 255),
        "headband": None,
        "wrist_tape": None,
        "arm_tattoo": False,
        "calf_tattoo": False,
        "bracelets": False,
        "knee_brace": False,
        "neck_tattoo": False,
        "eyebrow_slit": False,
        "number": "00",
        "kit_pattern": "var_armor",
        "shirt_primary": (28, 30, 38),
        "shirt_secondary": (196, 154, 68),
        "shirt_accent": (38, 236, 250),
        "collar_style": "armor_gorget",
        "collar_color": (196, 154, 68),
        "collar_trim": (38, 236, 250),
        "number_color": (38, 236, 250),
        "number_outline": (146, 28, 38),
        "crest_colors": ((38, 236, 250), (196, 154, 68), (146, 28, 38)),
        "sleeve_color": (138, 30, 38),
        "sleeve_stripe": (196, 154, 68),
        "cuff_color": (38, 42, 50),
        "keeper_pads": False,
        "captain_band": False,
        "shorts_color": (26, 28, 34),
        "shorts_stripe": (196, 154, 68),
        "socks_color": (24, 26, 32),
        "socks_cuff": ((196, 154, 68), (38, 236, 250)),
        "ankle_tape": (166, 123, 82),
        "boot_style": "var_cyber",
    },
]


def _load_athletic_font(pixel_size: int) -> ImageFont.ImageFont:
    """Carga Impact o Arial Bold en Windows con fallback determinista."""
    candidates = [
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for font_path in candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, pixel_size)
            except OSError:
                continue
    return ImageFont.load_default()


def _clamp_rgb(rgb: tuple[int, int, int], scale: float = 1.0, offset: int = 0) -> tuple[int, int, int]:
    return (
        int(max(0, min(255, rgb[0] * scale + offset))),
        int(max(0, min(255, rgb[1] * scale + offset))),
        int(max(0, min(255, rgb[2] * scale + offset))),
    )


def _draw_retro_number(
    draw: ImageDraw.ImageDraw,
    center_xy: tuple[int, int],
    text: str,
    pixel_size: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    stroke_width: int = 3,
) -> None:
    font = _load_athletic_font(pixel_size)
    draw.text(
        center_xy,
        text,
        font=font,
        fill=fill,
        anchor="mm",
        stroke_width=stroke_width,
        stroke_fill=outline,
    )


def _draw_crest_badge(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    radius: int,
    crest_colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
) -> None:
    c1, c2, c3 = crest_colors
    # Escudo clásico CONMEBOL / retro 90s
    shield = [
        (cx - radius, cy - int(radius * 0.95)),
        (cx + radius, cy - int(radius * 0.95)),
        (cx + radius, cy + int(radius * 0.15)),
        (cx, cy + int(radius * 1.1)),
        (cx - radius, cy + int(radius * 0.15)),
    ]
    draw.polygon(shield, fill=c1, outline=c3, width=max(2, radius // 8))
    inner_r = int(radius * 0.65)
    draw.ellipse(
        [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
        fill=c2,
        outline=c3,
        width=max(1, radius // 10),
    )
    dot_r = max(2, radius // 4)
    draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=c3)


def _build_fighter_skin_albedo(spec: dict, size: int = 1024) -> Image.Image:
    """
    Genera T_<ID>_Skin_Albedo.png (1024x1024) respetando el contrato UV:
      - x: 0..512,   y: 0..512   -> Rostro frontal (cejas, nariz, labios, barba/bigote/visor)
      - x: 512..1024, y: 0..512  -> Nuca / Laterales / Cuello (+ taper / tatuaje cuello)
      - x: 0..1024,  y: 512..1024 -> Brazos, manos, muñequeras/tatuajes y pantorrillas
    """
    half = size // 2
    q = size // 4
    base_rgb = np.array(spec["skin"], dtype=np.float32)

    yy, xx = np.meshgrid(
        np.linspace(0.0, 1.0, size, endpoint=False),
        np.linspace(0.0, 1.0, size, endpoint=False),
        indexing="ij",
    )

    rng = np.random.default_rng(abs(hash(spec["id"])) % (2**31))
    # Micro-variación cutánea sutil (poros y tono cálido)
    skin_noise = (rng.normal(0.0, 2.2, size=(size, size))).astype(np.float32)
    arr = np.broadcast_to(base_rgb, (size, size, 3)).copy() + skin_noise[:, :, None]

    # Coordenadas normalizadas locales dentro del cuadrante Rostro Frontal (x:0..512, y:0..512 -> u_f, v_f in [0,1])
    u_f = xx * 2.0
    v_f = yy * 2.0
    in_face = (xx < 0.5) & (yy < 0.5)

    # Sombreado facial tridimensional (pómulos cálidos, puente nasal, cuenca ocular, mandíbula)
    cheek_l = np.exp(-(((u_f - 0.30) / 0.14) ** 2 + ((v_f - 0.56) / 0.11) ** 2))
    cheek_r = np.exp(-(((u_f - 0.70) / 0.14) ** 2 + ((v_f - 0.56) / 0.11) ** 2))
    nose_hi = np.exp(-(((u_f - 0.50) / 0.045) ** 2 + ((v_f - 0.48) / 0.13) ** 2))
    brow_ao = np.exp(-(((u_f - 0.50) / 0.34) ** 2 + ((v_f - 0.39) / 0.05) ** 2))
    eye_socket_l = np.exp(-(((u_f - 0.355) / 0.085) ** 2 + ((v_f - 0.455) / 0.045) ** 2))
    eye_socket_r = np.exp(-(((u_f - 0.645) / 0.085) ** 2 + ((v_f - 0.455) / 0.045) ** 2))
    jaw_ao = np.clip((v_f - 0.80) / 0.20, 0.0, 1.0)
    temple_ao = np.clip((np.abs(u_f - 0.50) - 0.33) / 0.17, 0.0, 1.0)

    if spec["id"] == "SUPREME_JUDGE_BOSS":
        # Acabado metálico bronce/cobre cepillado en rostro frontal
        arr[in_face] += (nose_hi[in_face, None] * 26.0 - jaw_ao[in_face, None] * 28.0)
        arr[in_face, 0] += cheek_l[in_face] * 8.0 + cheek_r[in_face] * 8.0
    else:
        # Rubor cálido en mejillas + iluminación nasal + oclusión de arco superciliar, cuencas y mandíbula
        arr[in_face, 0] += (cheek_l[in_face] + cheek_r[in_face]) * 14.0
        arr[in_face, 1] += (cheek_l[in_face] + cheek_r[in_face]) * 4.0
        arr[in_face] += nose_hi[in_face, None] * 16.0
        arr[in_face] -= brow_ao[in_face, None] * 14.0
        arr[in_face] -= (eye_socket_l[in_face, None] + eye_socket_r[in_face, None]) * 18.0
        arr[in_face] -= jaw_ao[in_face, None] * 22.0
        arr[in_face] -= temple_ao[in_face, None] * 18.0

    # Sombreado de nuca/cuello (x: 512..1024, y: 0..512) y extremidades (y: 512..1024)
    in_neck = (xx >= 0.5) & (yy < 0.5)
    u_n = (xx - 0.5) * 2.0
    v_n = yy * 2.0
    neck_grad = 1.0 - 0.12 * np.abs(u_n - 0.5) - 0.10 * np.exp(-((v_n - 0.72) / 0.14) ** 2)
    arr[in_neck] *= neck_grad[in_neck, None]

    # Sombreado muscular sutil en brazos/pantorrillas (y: 512..1024)
    in_limbs = yy >= 0.5
    limb_tone = 1.0 + 0.06 * np.sin(xx * 8.0 * math.pi) - 0.05 * ((yy - 0.5) * 2.0)
    arr[in_limbs] *= limb_tone[in_limbs, None]

    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")
    draw = ImageDraw.Draw(img)

    # --- ROSTRO FRONTAL (x: 0..512, y: 0..512) ---
    cx_face = half // 2  # 256
    skin_rgb = spec["skin"]
    brow_rgb = spec["brow"]
    lip_rgb = spec["lip"]

    # Hairline / buzz fade en parte superior de frente y sienes
    hs = spec["hair_style"]
    hair_rgb = spec["hair_color"]
    if hs == "buzz_r9":
        # Icónico copete R9 en media luna sobre la frente
        draw.pieslice([cx_face - 76, 18, cx_face + 76, 128], start=180, end=360, fill=hair_rgb)
        draw.rectangle([0, 0, half, 32], fill=_clamp_rgb(skin_rgb, 0.85))
    elif hs in ("short_fade", "short_buzz", "buzz_receding", "mohawk"):
        fade_col = _clamp_rgb(hair_rgb, 0.7, 25) if hs != "mohawk" else _clamp_rgb(skin_rgb, 0.92)
        if hs == "buzz_receding":
            draw.rectangle([0, 0, half, 42], fill=fade_col)
            draw.polygon([(140, 42), (cx_face, 14), (372, 42)], fill=skin_rgb)
        elif hs == "mohawk":
            draw.rectangle([cx_face - 38, 0, cx_face + 38, 72], fill=hair_rgb)
        else:
            draw.rectangle([0, 0, half, 54], fill=fade_col)
            # Taper en sienes del cuadrante trasero/lateral
            draw.rectangle([half, 0, size, 175], fill=fade_col)
            draw.rectangle([half, 175, size, 230], fill=_clamp_rgb(skin_rgb, 0.88))

    if spec["id"] == "SUPREME_JUDGE_BOSS":
        # Visor cibernético eléctrico cian en rostro + mandíbula articulada gris acero
        draw.rounded_rectangle([68, 198, half - 68, 258], radius=16, fill=(24, 30, 38), outline=(196, 154, 68), width=4)
        draw.rounded_rectangle([84, 210, half - 84, 246], radius=10, fill=(28, 218, 240))
        draw.rounded_rectangle([110, 218, half - 110, 238], radius=6, fill=(165, 252, 255))
        # Placas de mandíbula y mentón slate metálico
        draw.polygon(
            [(76, 355), (170, 392), (cx_face, 412), (half - 170, 392), (half - 76, 355), (half - 56, 488), (56, 488)],
            fill=(42, 46, 56),
            outline=(196, 154, 68),
            width=3,
        )
        # Línea nasal metálica y respirador
        draw.line([(cx_face, 258), (cx_face, 326)], fill=(216, 172, 92), width=4)
        draw.line([(cx_face - 38, 362), (cx_face + 38, 362)], fill=(70, 52, 38), width=4)
        # Nuca y cables cibernéticos en x:512..1024, y:0..512
        draw.rectangle([half + 40, 28, size - 40, 210], fill=(38, 42, 50), outline=(196, 154, 68), width=3)
        for cx_c in range(half + 140, size - 120, 56):
            draw.line([(cx_c, 195), (cx_c, 485)], fill=(26, 28, 34), width=14)
            draw.line([(cx_c, 195), (cx_c, 485)], fill=(38, 236, 250), width=2)
    else:
        # Cejas naturales (con corte en ceja izquierda para El Rey)
        draw.polygon([(128, 196), (176, 180), (224, 186), (222, 200), (174, 194), (130, 204)], fill=brow_rgb)
        draw.polygon([(half - 128, 196), (half - 176, 180), (half - 224, 186), (half - 222, 200), (half - 174, 194), (half - 130, 204)], fill=brow_rgb)
        if spec.get("eyebrow_slit"):
            draw.line([(half - 154, 178), (half - 144, 204)], fill=skin_rgb, width=6)

        # Sombras suaves de alas nasales (cuencas oculares ya sombreadas suavemente en NumPy)
        draw.arc([cx_face - 28, 296, cx_face + 28, 320], start=20, end=160, fill=_clamp_rgb(skin_rgb, 0.78), width=2)

        # Labios
        draw.polygon(
            [(204, 364), (234, 353), (cx_face, 357), (278, 353), (308, 364), (cx_face, 378)],
            fill=lip_rgb,
        )
        draw.line([(206, 364), (306, 364)], fill=_clamp_rgb(lip_rgb, 0.65), width=2)
        draw.arc([224, 366, 288, 380], start=10, end=170, fill=_clamp_rgb(lip_rgb, 1.12), width=3)

        # Vello facial específico (labio superior y ~ 335, mentón/mandíbula y ~ 380..470)
        fh = spec["facial_hair"]
        fhc = spec["facial_hair_color"]
        if fh == "goatee":
            draw.polygon([(208, 336), (cx_face, 330), (304, 336), (294, 348), (cx_face, 344), (218, 348)], fill=fhc)
            draw.polygon([(204, 388), (308, 388), (290, 456), (cx_face, 468), (222, 456)], fill=fhc)
            draw.ellipse([238, 378, 274, 396], fill=fhc)
        elif fh == "lion_beard":
            for sy in range(324, 472, 5):
                span = 112 + int((sy - 324) * 0.25)
                for sx in range(cx_face - span, cx_face + span, 6):
                    if 346 < sy < 386 and 202 < sx < 310:
                        continue
                    draw.point((sx + (sy % 3), sy), fill=fhc)
            draw.polygon([(192, 330), (cx_face, 324), (320, 330), (312, 348), (cx_face, 342), (200, 348)], fill=fhc)
        elif fh == "ginger_beard":
            # Barba pelirroja continua y perfilada de La Pulga
            draw.chord([132, 310, 380, 476], start=0, end=180, fill=fhc)
            draw.polygon([(176, 328), (cx_face, 322), (336, 328), (334, 354), (cx_face, 346), (178, 354)], fill=fhc)
            draw.rectangle([144, 328, 198, 418], fill=fhc)
            draw.rectangle([314, 328, 368, 418], fill=fhc)
            draw.polygon([(204, 354), (308, 354), (298, 378), (214, 378)], fill=lip_rgb)
            draw.line([(208, 364), (304, 364)], fill=_clamp_rgb(lip_rgb, 0.65), width=2)
            draw.polygon([(242, 378), (270, 378), (264, 404), (248, 404)], fill=fhc)
        elif fh in ("blonde_stache", "thick_stache"):
            # Bigote icónico espeso (El Pibe / El Loco / El Diablo)
            draw.polygon(
                [(174, 348), (208, 324), (cx_face, 328), (304, 324), (338, 348), (326, 360), (cx_face, 346), (186, 360)],
                fill=fhc,
            )
            for hx in range(182, 330, 5):
                draw.line([(hx, 330), (hx + (4 if hx > cx_face else -4), 356)], fill=_clamp_rgb(fhc, 0.8), width=2)
        elif fh == "neat_stache":
            draw.polygon([(196, 340), (cx_face, 328), (316, 340), (310, 352), (cx_face, 344), (202, 352)], fill=fhc)
        elif fh == "light_stache":
            for sx in range(198, 314, 3):
                for sy in range(332, 350, 3):
                    draw.point((sx, sy), fill=fhc)
        elif fh in ("stubble", "heavy_stubble"):
            step = 3 if fh == "heavy_stubble" else 4
            for sy in range(324, 472, step):
                span = 110 + int((sy - 324) * 0.22)
                for sx in range(cx_face - span, cx_face + span, step):
                    if 348 < sy < 386 and 202 < sx < 310:
                        continue
                    if (sx * 13 + sy * 7) % 5 != 0:
                        draw.point((sx, sy), fill=fhc)
        elif fh == "matador_beard":
            draw.arc([136, 318, 376, 470], start=15, end=165, fill=fhc, width=18)
            draw.polygon([(194, 334), (cx_face, 328), (318, 334), (312, 346), (cx_face, 342), (200, 346)], fill=fhc)
        elif fh == "king_beard":
            # Barba perfilada con candado de El Rey
            draw.arc([124, 312, 388, 476], start=12, end=168, fill=fhc, width=26)
            draw.polygon([(188, 332), (cx_face, 324), (324, 332), (320, 350), (cx_face, 344), (192, 350)], fill=fhc)
            draw.polygon([(216, 382), (296, 382), (284, 466), (228, 466)], fill=fhc)
            # Separación esculpida bajo labios
            draw.rectangle([226, 384, 240, 416], fill=skin_rgb)
            draw.rectangle([272, 384, 286, 416], fill=skin_rgb)
        elif fh == "short_chin":
            draw.arc([148, 338, 364, 468], start=25, end=155, fill=fhc, width=14)
            draw.polygon([(200, 336), (cx_face, 330), (312, 336), (306, 346), (206, 346)], fill=fhc)

    # Tatuaje de cuello de El Rey (x: 512..1024, y: 340..505)
    if spec.get("neck_tattoo"):
        ink = (36, 42, 48)
        ncx, ncy = half + q, 420
        draw.line([(ncx, ncy - 45), (ncx, ncy + 45)], fill=ink, width=8)
        draw.line([(ncx - 36, ncy - 12), (ncx + 36, ncy - 12)], fill=ink, width=7)
        for wing in (-1, 1):
            for f_i in range(4):
                draw.line(
                    [(ncx + wing * 14, ncy - 10 + f_i * 12), (ncx + wing * (78 - f_i * 8), ncy - 28 + f_i * 14)],
                    fill=ink,
                    width=5,
                )

    # --- BRAZOS / MANOS / PANTORRILLAS (x: 0..1024, y: 512..1024) ---
    # Pliegues de palma y nudillos (x: 0..512, y: 700..768)
    crease_col = _clamp_rgb(skin_rgb, 0.74)
    for kx in range(36, half - 36, 68):
        draw.arc([kx, 712, kx + 46, 742], start=10, end=170, fill=crease_col, width=2)
    draw.line([(32, 748), (half - 32, 756)], fill=crease_col, width=2)

    # Tatuaje de manga en brazo (REY_CL y PULGA_AR)
    if spec.get("arm_tattoo"):
        ink = _clamp_rgb(skin_rgb, 0.42)
        ink_soft = _clamp_rgb(skin_rgb, 0.62)
        draw.rectangle([0, 518, half, 656], fill=_clamp_rgb(skin_rgb, 0.84))
        for ty in range(524, 654, 16):
            draw.line([(0, ty), (half, ty)], fill=ink_soft, width=3)
        for cx_t in range(44, half, 84):
            draw.ellipse([cx_t - 32, 548, cx_t + 32, 612], outline=ink, width=3)
            draw.ellipse([cx_t - 18, 562, cx_t + 18, 598], outline=ink, width=2)
            for deg in range(0, 360, 45):
                ang = math.radians(deg)
                draw.line(
                    [(cx_t + int(math.cos(ang) * 18), 580 + int(math.sin(ang) * 18)),
                     (cx_t + int(math.cos(ang) * 34), 580 + int(math.sin(ang) * 34))],
                    fill=ink,
                    width=2,
                )

    # Tatuaje en pantorrilla (PULGA_AR)
    if spec.get("calf_tattoo"):
        ink = _clamp_rgb(skin_rgb, 0.44)
        ink_soft = _clamp_rgb(skin_rgb, 0.72)
        for cx_t in (half + 150, half + 360):
            draw.ellipse([cx_t - 48, 795, cx_t + 48, 925], fill=ink_soft, outline=ink, width=4)
            draw.polygon([(cx_t, 808), (cx_t + 30, 860), (cx_t, 912), (cx_t - 30, 860)], outline=ink, width=3)
            draw.line([(cx_t - 36, 860), (cx_t + 36, 860)], fill=ink, width=3)
            draw.line([(cx_t, 808), (cx_t, 912)], fill=ink, width=3)

    # Vendaje blanco de muñeca (PISTOLERO_UY, PULGA_AR, BULLDOG_PY) en x: 0..512, y: 512..768
    if spec.get("wrist_tape") is not None:
        tape_col = spec["wrist_tape"]
        draw.rectangle([0, 658, half, 722], fill=tape_col)
        for wy in range(664, 720, 11):
            draw.line([(0, wy), (half, wy)], fill=_clamp_rgb(tape_col, 0.85), width=2)

    # Pulseras tejidas de El Pibe
    if spec.get("bracelets"):
        b_cols = [(210, 32, 38), (244, 200, 24), (22, 64, 168), (24, 152, 68)]
        for i, bc in enumerate(b_cols):
            by0 = 672 + i * 9
            draw.rectangle([0, by0, half, by0 + 7], fill=bc)

    # Rodillera negra de Bam-Bam (x: 512..1024, y: 512..620)
    if spec.get("knee_brace"):
        draw.rectangle([half, 524, size, 558], fill=(24, 26, 30))
        draw.rectangle([half, 578, size, 610], fill=(24, 26, 30))

    # Circuitos cibernéticos y guanteletes carmesí para El Juez Supremo V.A.R.
    if spec["id"] == "SUPREME_JUDGE_BOSS":
        draw.rectangle([0, 512, half, 768], fill=(138, 30, 38))
        draw.rectangle([0, 512, half, 532], fill=(196, 154, 68))
        draw.rectangle([0, 742, half, 768], fill=(38, 42, 50))
        for cx_l in range(48, half, 96):
            draw.line([(cx_l, 540), (cx_l, 730)], fill=(38, 236, 250), width=3)
            draw.ellipse([cx_l - 8, 620, cx_l + 8, 636], fill=(38, 236, 250))
        # Grebas y circuitos en piernas
        draw.rectangle([half, 512, size, 1024], fill=(30, 32, 40))
        draw.rectangle([half, 512, size, 540], fill=(196, 154, 68))
        for cx_l in range(half + 64, size, 112):
            draw.line([(cx_l, 555), (cx_l, 990)], fill=(38, 236, 250), width=3)

    return img


def _fill_jersey_pattern(
    arr: np.ndarray,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    spec: dict,
    is_back: bool = False,
) -> None:
    """Rellena la región de camiseta frontal o dorsal con el diseño exacto del Turnaround."""
    h = y1 - y0
    w = x1 - x0
    yy, xx = np.meshgrid(
        np.linspace(0.0, 1.0, h, endpoint=False),
        np.linspace(0.0, 1.0, w, endpoint=False),
        indexing="ij",
    )
    region = np.full((h, w, 3), spec["shirt_primary"], dtype=np.uint8)
    pat = spec["kit_pattern"]
    p1 = np.array(spec["shirt_primary"], dtype=np.uint8)
    p2 = np.array(spec["shirt_secondary"], dtype=np.uint8)
    p3 = np.array(spec["shirt_accent"], dtype=np.uint8)

    if pat == "vertical_stripes":
        # 5-7 bastones verticales Albicelestes centrados
        stripe = np.mod((xx + 0.083) * 6.0, 1.0) < 0.5
        region[stripe] = p1
        region[~stripe] = p2
        if spec["id"] == "PULGA_AR":
            region[yy > 0.94] = p3  # Vivo dorado en ruedo
    elif pat == "colombia_shoulder":
        shoulder = ((xx < 0.14) | (xx > 0.86)) & (yy < 0.42)
        edge = (((xx >= 0.14) & (xx < 0.165)) | ((xx > 0.835) & (xx <= 0.86))) & (yy < 0.42)
        region[shoulder] = p2
        region[edge] = p3
    elif pat == "gk_90s_shatter":
        # Estampado geométrico noventero de El Loco (fragmentos diagonales cian, magenta y negro)
        d1 = (xx * 2.4 + yy * 1.9)
        d2 = (xx * 2.1 - yy * 2.3)
        shard_cyan = ((np.mod(d1, 1.0) < 0.22) & (yy < 0.45)) | ((np.mod(d2, 1.0) > 0.78) & (yy > 0.55))
        shard_mag = (np.mod(d1 + 0.35, 1.0) < 0.28)
        shard_blk = (np.mod(d2 + 0.5, 1.0) < 0.18)
        region[shard_mag] = p3
        region[shard_cyan] = p2
        region[shard_blk] = [18, 18, 24]
    elif pat == "chile_yoke":
        yoke = yy < 0.20
        region[yoke] = p2
    elif pat == "gk_bulldog_slash":
        # Cortes dinámicos esmeralda y negro sobre gris oscuro en pecho/hombros
        if not is_back:
            slash_blk = (yy < 0.36) & (np.abs((xx - 0.5) * 1.2 + (yy - 0.15)) < 0.22)
            slash_grn = (yy < 0.42) & (
                ((xx < 0.34) & (np.mod(xx * 6.0 + yy * 4.0, 1.0) < 0.45))
                | ((xx > 0.66) & (np.mod((1.0 - xx) * 6.0 + yy * 4.0, 1.0) < 0.45))
            )
            region[slash_grn] = p2
            region[slash_blk] = p3
    elif pat == "peru_sash":
        # Banda diagonal roja de hombro a cadera
        if not is_back:
            sash = np.abs((xx - 0.82) + (yy * 0.78)) < 0.145
        else:
            sash = np.abs((xx - 0.18) - (yy * 0.78)) < 0.145
        region[sash] = p2
    elif pat == "ecuador_tricolor":
        shoulder_n = ((xx < 0.16) | (xx > 0.84)) & (yy < 0.34)
        shoulder_r = ((xx < 0.10) | (xx > 0.90)) & (yy < 0.34)
        region[shoulder_n] = p2
        region[shoulder_r] = p3
    elif pat == "france_98":
        if not is_back:
            red_band = (yy > 0.28) & (yy < 0.35)
            region[red_band] = p2
            for wy in (0.41, 0.49, 0.57):
                line_mask = (yy > wy) & (yy < wy + 0.015)
                region[line_mask] = p3
    elif pat == "var_armor":
        # Armadura carbono con filigrana dorada y paneles cian
        grid = (np.abs(np.mod(xx * 24.0, 1.0) - 0.5) < 0.03) | (np.abs(np.mod(yy * 24.0, 1.0) - 0.5) < 0.03)
        region[grid] = [44, 48, 58]
        border = (xx < 0.07) | (xx > 0.93) | (yy > 0.92)
        region[border] = p2

    arr[y0:y1, x0:x1] = region


def _draw_boot_quadrant(draw: ImageDraw.ImageDraw, x0: int, y0: int, size_q: int, boot_style: str) -> None:
    """Dibuja el cuadrante de botines (x: 512..1024, y: 768..1024) con tacos metálicos en la suela."""
    x1 = x0 + size_q
    y1 = y0 + (size_q // 2)  # 256px alto

    palettes = {
        "classic_black_white": ((24, 25, 30), (242, 244, 248), (242, 244, 248)),
        "classic_black_red": ((24, 25, 30), (200, 28, 36), (200, 28, 36)),
        "silver_blue_volt": ((180, 188, 198), (26, 72, 178), (196, 232, 24)),
        "white_gold": ((236, 233, 224), (202, 164, 72), (24, 25, 30)),
        "orange_blue": ((196, 56, 28), (22, 48, 118), (24, 25, 30)),
        "crimson_black": ((124, 24, 34), (26, 27, 32), (210, 184, 122)),
        "silver_red": ((172, 178, 186), (174, 32, 40), (24, 25, 30)),
        "volt_green": ((182, 245, 22), (20, 22, 28), (24, 46, 94)),
        "metallic_gold": ((200, 160, 56), (24, 24, 28), (236, 214, 126)),
        "var_cyber": ((28, 30, 36), (166, 123, 82), (38, 236, 250)),
    }
    upper_col, stripe_col, accent_col = palettes.get(boot_style, palettes["classic_black_white"])

    # Empeine de cuero / sintético
    draw.rectangle([x0, y0, x1, y1], fill=upper_col)
    # Lengüeta doblada superior y cordones
    draw.rectangle([x0 + 180, y0 + 10, x0 + 332, y0 + 62], fill=accent_col)
    for ly in range(y0 + 18, y0 + 58, 12):
        draw.line([(x0 + 206, ly), (x0 + 306, ly)], fill=(24, 24, 28), width=3)

    # 3 franjas laterales icónicas
    for i in range(3):
        sx = x0 + 96 + i * 38
        draw.polygon([(sx, y0 + 185), (sx + 20, y0 + 185), (sx + 58, y0 + 72), (sx + 38, y0 + 72)], fill=stripe_col)
        sx_r = x1 - 96 - i * 38
        draw.polygon([(sx_r, y0 + 185), (sx_r - 20, y0 + 185), (sx_r - 58, y0 + 72), (sx_r - 38, y0 + 72)], fill=stripe_col)

    # Suela y tacos metálicos (y: 980..1024)
    draw.rectangle([x0, y1 - 44, x1, y1], fill=(20, 20, 24))
    for stud_x in range(x0 + 32, x1 - 16, 56):
        draw.rounded_rectangle([stud_x, y1 - 24, stud_x + 22, y1 - 4], radius=4, fill=(192, 198, 206))


def _build_fighter_kit_albedo(spec: dict, size: int, jacquard: np.ndarray) -> Image.Image:
    """
    Genera T_<ID>_Kit_Albedo.png (1024x1024) con tejido Jacquard 90s y sombreado de pliegues:
      - x: 0..512,    y: 0..512    -> Camiseta Frontal (cuello y=30..90, escudo x=330,y=140, # en x=256,y=195..310)
      - x: 512..1024, y: 0..512    -> Camiseta Dorsal (dorsal grande en x=768, y=140..360)
      - x: 0..512,    y: 512..768  -> Mangas + puños (y=710..768) + brazalete Capitán (TREN_EC) / coderas GK
      - x: 512..1024, y: 512..768  -> Pantalón corto + franjas laterales + mini número y escudo
      - x: 0..512,    y: 768..1024 -> Medias + bandas superiores (y=768..830) + cinta tobillera (y=960..1024)
      - x: 512..1024, y: 768..1024 -> Botines + tacos metálicos
    """
    half = size // 2   # 512
    q = size // 4      # 256
    three_q = q * 3    # 768

    arr = np.full((size, size, 3), 24, dtype=np.uint8)

    # 1. Camiseta Frontal y Dorsal
    _fill_jersey_pattern(arr, 0, 0, half, half, spec, is_back=False)
    _fill_jersey_pattern(arr, half, 0, size, half, spec, is_back=True)

    # 2. Mangas (x: 0..512, y: 512..768)
    arr[half:three_q, 0:half] = spec["sleeve_color"]
    if spec.get("sleeve_stripe") is not None:
        arr[half:three_q, 216:296] = spec["sleeve_stripe"]
    # Puños acanalados (y: 710..768)
    arr[710:three_q, 0:half] = spec["cuff_color"]

    # 3. Shorts (x: 512..1024, y: 512..768)
    arr[half:three_q, half:size] = spec["shorts_color"]
    arr[half:three_q, half + 18:half + 48] = spec["shorts_stripe"]
    arr[half:three_q, size - 48:size - 18] = spec["shorts_stripe"]

    # 4. Medias (x: 0..512, y: 768..1024)
    arr[three_q:size, 0:half] = spec["socks_color"]
    cuff_a, cuff_b = spec["socks_cuff"]
    arr[three_q:three_q + 26, 0:half] = cuff_a
    arr[three_q + 34:three_q + 56, 0:half] = cuff_b
    arr[960:size, 0:half] = spec["ankle_tape"]

    # Aplicar modulación Jacquard + pliegues suaves en las zonas textiles (todo excepto botines)
    yy, xx = np.meshgrid(
        np.linspace(0.0, 1.0, size, endpoint=False),
        np.linspace(0.0, 1.0, size, endpoint=False),
        indexing="ij",
    )
    fabric_mask = ~((xx >= 0.5) & (yy >= 0.75))
    mod = 0.96 + 0.065 * jacquard[:, :, None]
    folds = 1.0 + 0.03 * np.sin(xx * 18.0 * math.pi + np.sin(yy * 8.0 * math.pi) * 0.6)
    arr_f = arr.astype(np.float32)
    arr_f[fabric_mask] *= mod[fabric_mask] * folds[fabric_mask, None]
    img = Image.fromarray(np.clip(arr_f, 0, 255).astype(np.uint8), mode="RGB")
    draw = ImageDraw.Draw(img)

    # --- DETALLES VECTORIALES DE ALTA NITIDEZ SOBRE EL TEJIDO ---
    # Cuello frontal (x: 165..347, y: 30..90) y cuello dorsal (x: 677..859, y: 26..70)
    cc = spec["collar_color"]
    ct = spec["collar_trim"]
    cs = spec["collar_style"]
    if cs in ("polo_v", "polo_white"):
        draw.polygon([(165, 24), (256, 92), (347, 24), (347, 54), (256, 110), (165, 54)], fill=cc, outline=ct, width=3)
        draw.polygon([(140, 18), (218, 22), (244, 68), (168, 56)], fill=cc, outline=ct, width=2)
        draw.polygon([(372, 18), (294, 22), (268, 68), (344, 56)], fill=cc, outline=ct, width=2)
    elif cs == "armor_gorget":
        draw.arc([152, 16, 360, 108], start=0, end=180, fill=cc, width=14)
        draw.arc([164, 24, 348, 96], start=0, end=180, fill=ct, width=4)
    else:
        draw.arc([165, 20, 347, 94], start=0, end=180, fill=cc, width=16)
        draw.arc([173, 28, 339, 86], start=0, end=180, fill=ct, width=4)
    draw.arc([half + 165, 16, half + 347, 74], start=0, end=180, fill=cc, width=14)

    # Escudo pectoral en (330, 140)
    _draw_crest_badge(draw, 330, 140, 24, spec["crest_colors"])

    # Panel VAR pectoral para El Juez Supremo
    if spec["id"] == "SUPREME_JUDGE_BOSS":
        draw.ellipse([216, 108, 296, 188], fill=(16, 46, 58), outline=(196, 154, 68), width=5)
        draw.ellipse([230, 122, 282, 174], fill=(38, 236, 250), outline=(170, 252, 255), width=3)
        draw.rectangle([176, 198, 336, 308], fill=(22, 24, 32), outline=(146, 28, 38), width=4)

    # Número frontal centrado en x=256, y=252 (dentro de y: 195..310)
    _draw_retro_number(
        draw,
        (256, 252),
        spec["number"],
        pixel_size=92 if spec["id"] == "SUPREME_JUDGE_BOSS" else 104,
        fill=spec["number_color"],
        outline=spec["number_outline"],
        stroke_width=4,
    )

    # Número dorsal grande centrado en x=768, y=250 (dentro de y: 140..360)
    _draw_retro_number(
        draw,
        (half + q, 250),
        spec["number"],
        pixel_size=210,
        fill=spec["number_color"],
        outline=spec["number_outline"],
        stroke_width=6,
    )

    # Coderas acolchadas de portero (LOCO_CO, BULLDOG_PY)
    if spec.get("keeper_pads"):
        for px in (48, 300):
            draw.rounded_rectangle([px, 548, px + 164, 692], radius=16, fill=(24, 24, 32), outline=(48, 52, 64), width=3)
            for qy in range(568, 682, 22):
                draw.line([(px + 12, qy), (px + 152, qy)], fill=(42, 46, 56), width=3)

    # Brazalete de Capitán blanco con "C" (TREN_EC) en x: 0..512, y: 512..768
    if spec.get("captain_band"):
        draw.rectangle([0, 610, half, 676], fill=(246, 248, 250))
        draw.line([(0, 612), (half, 612)], fill=(24, 46, 94), width=3)
        draw.line([(0, 674), (half, 674)], fill=(24, 46, 94), width=3)
        _draw_retro_number(draw, (q, 643), "C", pixel_size=52, fill=(20, 28, 56), outline=(246, 248, 250), stroke_width=1)

    # Líneas de puño y costuras de mangas
    draw.line([(0, 712), (half, 712)], fill=_clamp_rgb(spec["cuff_color"], 0.7), width=3)
    draw.line([(0, 738), (half, 738)], fill=spec["shirt_accent"], width=4)

    # Detalles de shorts: pretina, cordones, mini número y mini escudo
    draw.line([(half, 542), (size, 542)], fill=_clamp_rgb(spec["shorts_color"], 0.65), width=3)
    draw.line([(half + 246, 526), (half + 240, 586)], fill=(242, 244, 246), width=4)
    draw.line([(half + 266, 526), (half + 272, 586)], fill=(242, 244, 246), width=4)
    _draw_retro_number(
        draw,
        (half + 120, 694),
        spec["number"],
        pixel_size=56,
        fill=spec["number_color"],
        outline=spec["number_outline"],
        stroke_width=2,
    )
    _draw_crest_badge(draw, half + 392, 694, 20, spec["crest_colors"])

    # Canalé vertical sutil en medias (x: 0..512, y: 768..1024)
    sock_rib = _clamp_rgb(spec["socks_color"], 0.90)
    for sx in range(12, half, 16):
        draw.line([(sx, three_q + 58), (sx, 958)], fill=sock_rib, width=2)

    # Botines (x: 512..1024, y: 768..1024)
    _draw_boot_quadrant(draw, half, three_q, half, spec["boot_style"])

    return img


def _build_fighter_hair_albedo(spec: dict, size: int = 1024) -> Image.Image:
    """
    Genera T_<ID>_Hair_Albedo.png (1024x1024):
      - x: 0..512,    y: 0..512    -> Ojos (esclerótica, iris detallado, pupila, brillo) o visor cian V.A.R.
      - x: 512..1024, y: 0..512 & y: 512..1024 -> Hebras de cabello / rizos / drones astrolabio + banda (y=400..500)
    """
    half = size // 2
    q = size // 4
    hair_rgb = np.array(spec["hair_color"], dtype=np.float32)

    yy, xx = np.meshgrid(
        np.linspace(0.0, 1.0, size, endpoint=False),
        np.linspace(0.0, 1.0, size, endpoint=False),
        indexing="ij",
    )

    arr = np.broadcast_to(hair_rgb, (size, size, 3)).copy()
    hs = spec["hair_style"]

    # Micro-textura de hebras y rizos en la zona de cabello
    if hs in ("golden_afro", "black_afro", "curly_ponytail"):
        curl = (
            np.sin(xx * 90.0 * math.pi + np.cos(yy * 75.0 * math.pi) * 2.5)
            * np.cos(yy * 90.0 * math.pi + np.sin(xx * 75.0 * math.pi) * 2.5)
        )
        arr += curl[:, :, None] * 26.0
    elif hs == "var_drones":
        # Bronce y carbono con anillos cian para drones astrolabio
        arr[:, :, 0] = 36.0
        arr[:, :, 1] = 42.0
        arr[:, :, 2] = 52.0
    else:
        strands = np.sin(xx * 260.0 * math.pi + np.sin(yy * 14.0 * math.pi) * 1.4)
        sheen = np.exp(-((yy - 0.65) / 0.12) ** 2) * 18.0
        arr += strands[:, :, None] * 18.0 + sheen[:, :, None]

    # Cuadrante Ojos (x: 0..512, y: 0..512)
    in_eyes = (xx < 0.5) & (yy < 0.5)
    if spec["id"] == "SUPREME_JUDGE_BOSS":
        arr[in_eyes] = np.array([22, 232, 252], dtype=np.float32)
    else:
        # Esclerótica suave con sombra superior de párpado
        sclera = np.array([236.0, 233.0, 229.0], dtype=np.float32)
        v_eye = yy * 2.0
        u_eye = xx * 2.0
        lid_shadow = 1.0 - 0.24 * np.exp(-((v_eye - 0.14) / 0.12) ** 2) - 0.12 * np.abs(u_eye - 0.5)
        arr[in_eyes] = sclera * lid_shadow[in_eyes, None]

    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")
    draw = ImageDraw.Draw(img)

    # Dibujo de iris, pupila y especular en (256, 256)
    ecx, ecy = q, q
    if spec["id"] == "SUPREME_JUDGE_BOSS":
        draw.rectangle([16, 16, half - 16, half - 16], outline=(196, 154, 68), width=12)
        for sy in range(44, half - 44, 18):
            draw.line([(36, sy), (half - 36, sy)], fill=(150, 252, 255), width=4)
        # Drones astrolabio en x:512..1024, y:0..512 y y:512..1024
        for dcx, dcy in ((half + q, 200), (q, 768), (half + q, 768)):
            for r_ring, r_col, w_ring in (
                (156, (176, 134, 68), 10),
                (122, (38, 236, 250), 6),
                (86, (176, 134, 68), 8),
                (44, (140, 250, 255), 14),
            ):
                draw.ellipse([dcx - r_ring, dcy - r_ring, dcx + r_ring, dcy + r_ring], outline=r_col, width=w_ring)
            draw.ellipse([dcx - 24, dcy - 24, dcx + 24, dcy + 24], fill=(180, 255, 255))
    else:
        iris_col = spec["eye_color"]
        r_iris = 136
        draw.ellipse([ecx - r_iris, ecy - r_iris, ecx + r_iris, ecy + r_iris], fill=_clamp_rgb(iris_col, 0.55))
        draw.ellipse([ecx - r_iris + 10, ecy - r_iris + 10, ecx + r_iris - 10, ecy + r_iris - 10], fill=iris_col)
        # Fibras radiales del iris
        for deg in range(0, 360, 12):
            ang = math.radians(deg)
            x_in = ecx + int(math.cos(ang) * 62)
            y_in = ecy + int(math.sin(ang) * 62)
            x_out = ecx + int(math.cos(ang) * (r_iris - 14))
            y_out = ecy + int(math.sin(ang) * (r_iris - 14))
            draw.line([(x_in, y_in), (x_out, y_out)], fill=_clamp_rgb(iris_col, 1.25), width=3)
        # Pupila negra nítida y reflejos especulares
        r_pupil = 58
        draw.ellipse([ecx - r_pupil, ecy - r_pupil, ecx + r_pupil, ecy + r_pupil], fill=(12, 12, 14))
        draw.ellipse([ecx - 54, ecy - 68, ecx - 18, ecy - 32], fill=(252, 252, 255))
        draw.ellipse([ecx + 28, ecy + 28, ecx + 46, ecy + 46], fill=(235, 240, 248))

    # Vincha / Headband horizontal (x: 512..1024, y: 400..500)
    if spec.get("headband") is not None:
        hb = spec["headband"]
        draw.rectangle([half, 400, size, 500], fill=hb)
        draw.line([(half, 408), (size, 408)], fill=_clamp_rgb(hb, 0.78), width=3)
        draw.line([(half, 492), (size, 492)], fill=_clamp_rgb(hb, 0.78), width=3)
        for hy in range(424, 488, 16):
            draw.line([(half, hy), (size, hy)], fill=_clamp_rgb(hb, 0.92), width=2)

    return img


def generate_fighter_pbr_textures(size: int = 1024) -> list[str]:
    """
    Genera las 51 texturas 1024x1024 (Skin, Kit y Hair Albedo) para los 17 personajes en
    Assets/TexturesPBR/Fighters/, fieles a las 17 Turnaround Sheets.
    """
    os.makedirs(FIGHTERS_OUTPUT_DIR, exist_ok=True)
    jacquard = generate_jacquard_watermark_field(size, size)
    generated = []

    for spec in FIGHTER_TEXTURE_SPECS:
        fid = spec["id"]

        skin_img = _build_fighter_skin_albedo(spec, size=size)
        skin_path = os.path.join(FIGHTERS_OUTPUT_DIR, f"T_{fid}_Skin_Albedo.png")
        skin_img.save(skin_path)
        generated.append(skin_path)

        kit_img = _build_fighter_kit_albedo(spec, size=size, jacquard=jacquard)
        kit_path = os.path.join(FIGHTERS_OUTPUT_DIR, f"T_{fid}_Kit_Albedo.png")
        kit_img.save(kit_path)
        generated.append(kit_path)

        hair_img = _build_fighter_hair_albedo(spec, size=size)
        hair_path = os.path.join(FIGHTERS_OUTPUT_DIR, f"T_{fid}_Hair_Albedo.png")
        hair_img.save(hair_path)
        generated.append(hair_path)

    return generated


def main() -> None:
    ensure_output_dir()
    kits = generate_kit_albedos(size=1024)
    masters = generate_master_pbr_maps(size=1024)
    fighters = generate_fighter_pbr_textures(size=1024)
    total = len(kits) + len(masters) + len(fighters)
    print(f"[OK] Generadas {total} texturas PBR en: {OUTPUT_DIR} (Fighters: {len(fighters)} en {FIGHTERS_OUTPUT_DIR})")
    for path in kits + masters + fighters:
        print(f"  - {os.path.relpath(path, OUTPUT_DIR)} ({os.path.getsize(path):,} bytes)")


if __name__ == "__main__":
    main()
