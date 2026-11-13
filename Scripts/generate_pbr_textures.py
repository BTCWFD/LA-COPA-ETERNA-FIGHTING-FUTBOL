#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_pbr_textures.py - SouthAmericaFightersCore ("La Copa Eterna")
Generador Procedural Determinista de Texturas PBR (Albedos de las 10 Selecciones CONMEBOL
+ Invitado Francia 98 + Boss Juez Supremo V.A.R., Normales Jacquard 90s, Micro-Poros de Piel,
Empaquetado ORM, Máscara de Barro/Césped y Balón de 32 Paneles).
"""

import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Assets",
    "TexturesPBR",
)


def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


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

    # 1. T_Retro90s_Jacquard_Normal.png
    jacquard_h = generate_jacquard_watermark_field(size, size)
    jacquard_normal = height_to_normal_map(jacquard_h, strength=4.5)
    p_jacquard = os.path.join(OUTPUT_DIR, "T_Retro90s_Jacquard_Normal.png")
    jacquard_normal.save(p_jacquard)
    generated.append(p_jacquard)

    # 2. T_Skin_MicroPores_Normal.png (Micro-poros Voronoi cutáneos para M_FighterSkin_Master)
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
    skin_normal = height_to_normal_map(pore_cavity, strength=2.8)
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


def main() -> None:
    ensure_output_dir()
    kits = generate_kit_albedos(size=1024)
    masters = generate_master_pbr_maps(size=1024)
    total = len(kits) + len(masters)
    print(f"[OK] Generadas {total} texturas PBR en: {OUTPUT_DIR}")
    for path in kits + masters:
        print(f"  - {os.path.basename(path)} ({os.path.getsize(path):,} bytes)")


if __name__ == "__main__":
    main()
