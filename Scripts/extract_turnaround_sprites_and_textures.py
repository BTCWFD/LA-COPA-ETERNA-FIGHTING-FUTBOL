#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_turnaround_sprites_and_textures.py
Extracts clean alpha-matted photorealistic sprites (`Sprite_<ROSTER_ID>_{Front,Side,Back,Portrait}.png`)
from all 17 Gemini Turnaround Sheets (`Assets/Design3D_Turnarounds/Turnaround_*.png`) AND
projects real photorealistic face, jersey front/back, shorts, socks, boots, and hair patches
into `Assets/TexturesPBR/Fighters/T_<ID>_{Skin,Kit,Hair}_Albedo.png` so both 3D GLB/FBX models
and the 2D fallback Arena renderer match the Turnaround art sheets 1:1.
"""

from __future__ import annotations

import os
from collections import deque
import numpy as np
from PIL import Image, ImageFilter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TURNAROUND_DIR = os.path.join(PROJECT_ROOT, "Assets", "Design3D_Turnarounds")
SPRITES_DIR = os.path.join(PROJECT_ROOT, "Assets", "Sprites2D", "Fighters")
TEXTURES_DIR = os.path.join(PROJECT_ROOT, "Assets", "TexturesPBR", "Fighters")

# (roster_id used by WebLab ROSTER_DATA & Turnaround filename, fighter_id used by 3D GLB/FBX)
ROSTER_MAP: list[tuple[str, str]] = [
    ("FENOMENO_BR", "FENOMENO_BR"),
    ("BRUXO_BR", "BRUXO_BR"),
    ("CANON_AR", "CANON_AR"),
    ("PULGA_AR", "PULGA_AR"),
    ("PIBE_CO", "PIBE_CO"),
    ("LOCO_CO", "LOCO_CO"),
    ("PISTOLERO_UY", "PISTOLERO_UY"),
    ("MATADOR_UY", "MATADOR_UY"),
    ("BAMBAM_CL", "BAMBAM_CL"),
    ("REY_CL", "REY_CL"),
    ("BULLDOG_PY", "BULLDOG_PY"),
    ("MAESTRO_PE", "MAESTRO_PE"),
    ("TREN_EC", "TREN_EC"),
    ("HURACAN_VE", "HURACAN_VE"),
    ("DIABLO_BO", "DIABLO_BO"),
    ("GENERAL_FR", "GENERAL_FR"),
    ("VAR_ZERO_BOSS", "SUPREME_JUDGE_BOSS"),
]


def _find_pose_splits(rgb: np.ndarray) -> tuple[int, int, int, np.ndarray]:
    """Locate x boundaries separating Front, Side, Back, and 3/4 Portrait panel."""
    h, w, _ = rgb.shape
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    # Estimate studio grey background per (y, x) via horizontal & vertical neutral strips
    strip_cols = [1, 2, w - 165, 222, 326]
    row_bg = np.median(rgb[:, strip_cols, :], axis=1)
    diff = np.linalg.norm(rgb - row_bg[:, None, :], axis=2) + sat * 0.55

    col_energy = (diff > 20.0)[: h - 14, :550].mean(axis=0)

    def min_x(lo: int, hi: int) -> int:
        sub = col_energy[lo:hi]
        return lo + int(np.argmin(sub))

    s1 = min_x(182, 245)   # Front | Side
    s2 = min_x(295, 360)   # Side  | Back
    s3 = min_x(512, 560)   # Back  | Portrait box
    return s1, s2, s3, diff


def _compute_clean_alpha(rgb: np.ndarray, s1: int, s2: int, s3: int) -> np.ndarray:
    """
    Remove studio grey backdrop cleanly including corner radial vignette and enclosed
    inter-leg / arm-gap holes without punching out black hair, shorts, or boots.
    """
    h, w, _ = rgb.shape
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    lum = rgb.mean(axis=2)

    # Smooth row-by-row studio reference from multiple vertical neutral columns
    col_profile = np.median(rgb[:, [s1, s2, max(0, s3 - 4)], :], axis=1)
    # Also compute edge vignette brightness ratio using top/bottom strips
    left_strip = rgb[:, 2:8, :].mean(axis=1)

    diff_center = np.linalg.norm(rgb - col_profile[:, None, :], axis=2)
    diff_left = np.linalg.norm(rgb - left_strip[:, None, :], axis=2)
    diff_min = np.minimum(diff_center, diff_left)

    # True studio grey has very low saturation (<12) and matches background within tight tolerance
    is_bg_candidate = ((diff_min < 17.5) & (sat < 12.5)) | ((diff_center < 14.0) & (sat < 14.0))
    # Remove tiny rounded card corner bezel artifacts (dark border < 35x35 in top-left/bottom-left)
    corner_mask = np.zeros((h, w), dtype=bool)
    corner_mask[:36, :32] = (lum[:36, :32] < 48.0) & (sat[:36, :32] < 12.0)
    corner_mask[h - 14:, :s3] = (lum[h - 14:, :s3] < 48.0) & (sat[h - 14:, :s3] < 12.0)
    is_bg_candidate = is_bg_candidate | corner_mask

    bg_mask = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    seed_xs = [0, 1, 2, s1 - 1, s1, s1 + 1, s2 - 1, s2, s2 + 1, max(0, s3 - 4), max(0, s3 - 2)]
    for x in seed_xs:
        for y in range(h):
            if is_bg_candidate[y, x] and not bg_mask[y, x]:
                bg_mask[y, x] = True
                q.append((y, x))
    for x in range(s3):
        for y in (0, 1, h - 2, h - 1):
            if is_bg_candidate[y, x] and not bg_mask[y, x]:
                bg_mask[y, x] = True
                q.append((y, x))

    # Seed center-gap vertical strip ONLY below crotch/knees (y > 63%) with tighter grey check so metallic armor stays solid
    for view_mid_x in (s1 // 2, (s2 + s3) // 2):
        for dx in range(-6, 7):
            xx = view_mid_x + dx
            if 0 <= xx < s3:
                for y in range(int(h * 0.64), h - 8):
                    if diff_center[y, xx] < 15.0 and sat[y, xx] < 9.0 and 30.0 < lum[y, xx] < 72.0 and not bg_mask[y, xx]:
                        bg_mask[y, xx] = True
                        q.append((y, xx))

    # Floodfill through background candidates
    while q:
        cy, cx = q.popleft()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < h and 0 <= nx < s3 and not bg_mask[ny, nx]:
                if is_bg_candidate[ny, nx]:
                    bg_mask[ny, nx] = True
                    q.append((ny, nx))

    alpha = np.where(bg_mask, 0, 255).astype(np.uint8)
    # Trim 1px outer card edge margin & top-left screenshot rounded corner bezel
    alpha[:4, :] = 0
    alpha[:, :4] = 0
    alpha[h - 3:, :] = 0
    alpha[:16, :75] = np.where((lum[:16, :75] < 60.0) & (sat[:16, :75] < 16.0), 0, alpha[:16, :75])
    # Soften 1px contour anti-aliasing
    alpha_img = Image.fromarray(alpha, mode="L").filter(ImageFilter.GaussianBlur(radius=0.65))
    alpha_soft = np.asarray(alpha_img, dtype=np.uint8)
    alpha_final = np.where(alpha == 255, np.maximum(alpha_soft, 225), np.where(alpha_soft > 80, alpha_soft, 0)).astype(np.uint8)
    return alpha_final


def _crop_masked_region(rgba: np.ndarray, x_lo: int, x_hi: int, pad: int = 3) -> Image.Image:
    sub = rgba[:, x_lo:x_hi].copy()
    ys, xs = np.where(sub[:, :, 3] > 28)
    if len(ys) == 0 or len(xs) == 0:
        return Image.fromarray(sub, mode="RGBA")
    y0 = max(0, int(ys.min()) - pad)
    y1 = min(sub.shape[0], int(ys.max()) + pad + 1)
    x0 = max(0, int(xs.min()) - pad)
    x1 = min(sub.shape[1], int(xs.max()) + pad + 1)
    return Image.fromarray(sub[y0:y1, x0:x1], mode="RGBA")


def _extract_torso_texture_patch(img_rgba: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Crop clean torso cloth core (inside chest, free of neck/arms/grey bg) and resize smoothly."""
    arr = np.asarray(img_rgba)
    h, w, _ = arr.shape
    ty0, ty1 = int(h * 0.215), int(h * 0.435)
    tx0, tx1 = int(w * 0.365), int(w * 0.635)
    crop = img_rgba.crop((tx0, ty0, tx1, ty1)).convert("RGB")
    return crop.resize((target_w, target_h), Image.Resampling.LANCZOS)


def _update_fighter_pbr_from_turnaround(
    roster_id: str,
    gl_id: str,
    front_img: Image.Image,
    back_img: Image.Image,
    portrait_img: Image.Image,
) -> None:
    """
    Project real photorealistic crops from the Turnaround Sheet onto our existing
    1024x1024 UV Atlas (`T_<ID>_{Skin,Kit,Hair}_Albedo.png`) so the 3D `.glb`/`.fbx`
    models share the exact faces, jerseys, numbers, shorts, socks, and boots.
    """
    os.makedirs(TEXTURES_DIR, exist_ok=True)
    f_arr = np.asarray(front_img)
    fh, fw, _ = f_arr.shape

    # Sample mean skin tone from front upper chest/neck so margins blend seamlessly
    neck_patch = f_arr[int(fh * 0.14):int(fh * 0.18), int(fw * 0.46):int(fw * 0.54), :3]
    skin_rgb = np.median(neck_patch.reshape(-1, 3), axis=0).astype(np.uint8)

    # 1. T_<ID>_Skin_Albedo.png
    skin_path = os.path.join(TEXTURES_DIR, f"T_{gl_id}_Skin_Albedo.png")
    skin_tex = Image.open(skin_path).convert("RGB") if os.path.isfile(skin_path) else Image.new("RGB", (1024, 1024), tuple(int(c) for c in skin_rgb))

    # Extract clean central facial features ONLY (eyes/nose/mouth/mustache/chin, excluding side hair locks)
    fx0, fx1 = int(fw * 0.448), int(fw * 0.552)
    fy0, fy1 = int(fh * 0.036), int(fh * 0.132)
    face_crop = front_img.crop((fx0, fy0, fx1, fy1)).convert("RGBA")
    fc_arr = np.asarray(face_crop).copy()
    fy_g, fx_g = np.meshgrid(np.linspace(-1, 1, fc_arr.shape[0]), np.linspace(-1, 1, fc_arr.shape[1]), indexing="ij")
    oval_mask = np.clip(1.22 - np.hypot(fx_g * 1.18, fy_g * 0.98), 0.0, 1.0)
    fc_arr[:, :, 3] = np.minimum(fc_arr[:, :, 3], (oval_mask * 255.0).astype(np.uint8))
    face_clean = Image.fromarray(fc_arr, "RGBA")

    face_bg = Image.new("RGB", (512, 512), tuple(int(c) for c in skin_rgb))
    face_resized = face_crop and face_clean.resize((380, 410), Image.Resampling.LANCZOS)
    face_bg.paste(face_resized, (66, 52), face_resized)
    skin_tex.paste(face_bg, (0, 0))
    skin_tex.save(skin_path)

    # 2. T_<ID>_Kit_Albedo.png
    kit_path = os.path.join(TEXTURES_DIR, f"T_{gl_id}_Kit_Albedo.png")
    kit_tex = Image.open(kit_path).convert("RGB") if os.path.isfile(kit_path) else Image.new("RGB", (1024, 1024), (220, 220, 220))

    # Front Jersey -> (0, 0, 512, 512)
    j_front = _extract_torso_texture_patch(front_img, 512, 512)
    kit_tex.paste(j_front, (0, 0))

    # Back Jersey -> (512, 0, 1024, 512)
    bh, bw = back_img.height, back_img.width
    j_back_raw = back_img.crop((int(bw * 0.365), int(bh * 0.215), int(bw * 0.635), int(bh * 0.435))).convert("RGB")
    kit_tex.paste(j_back_raw.resize((512, 512), Image.Resampling.LANCZOS), (512, 0))

    # Shorts -> (512, 512, 1024, 768)
    shorts_raw = front_img.crop((int(fw * 0.365), int(fh * 0.47), int(fw * 0.635), int(fh * 0.64))).convert("RGB")
    kit_tex.paste(shorts_raw.resize((512, 256), Image.Resampling.LANCZOS), (512, 512))

    # Socks (inner solid shin region) -> (0, 768, 512, 1024)
    socks_raw = front_img.crop((int(fw * 0.36), int(fh * 0.74), int(fw * 0.435), int(fh * 0.87))).convert("RGB")
    kit_tex.paste(socks_raw.resize((512, 256), Image.Resampling.LANCZOS), (0, 768))

    # Boots (bottom shoe core) -> (512, 768, 1024, 1024)
    boots_raw = front_img.crop((int(fw * 0.325), int(fh * 0.915), int(fw * 0.435), int(fh * 0.978))).convert("RGB")
    kit_tex.paste(boots_raw.resize((512, 256), Image.Resampling.LANCZOS), (512, 768))

    kit_tex.save(kit_path)

    # 3. T_<ID>_Hair_Albedo.png: keep pure curly/strand procedural albedo intact (avoid skin crown bleed on side locks)
    hair_path = os.path.join(TEXTURES_DIR, f"T_{gl_id}_Hair_Albedo.png")
    if os.path.isfile(hair_path):
        hair_tex = Image.open(hair_path).convert("RGB")
        hair_tex.save(hair_path)


def main() -> None:
    os.makedirs(SPRITES_DIR, exist_ok=True)
    os.makedirs(TEXTURES_DIR, exist_ok=True)

    for roster_id, gl_id in ROSTER_MAP:
        t_path = os.path.join(TURNAROUND_DIR, f"Turnaround_{roster_id}.png")
        if not os.path.isfile(t_path):
            raise FileNotFoundError(f"Missing turnaround image: {t_path}")

        im = Image.open(t_path).convert("RGBA")
        arr = np.asarray(im)
        rgb = arr[:, :, :3].astype(np.float32)

        s1, s2, s3, _ = _find_pose_splits(rgb)
        alpha = _compute_clean_alpha(rgb, s1, s2, s3)
        rgba = arr.copy()
        rgba[:, :, 3] = alpha

        front_img = _crop_masked_region(rgba, 0, s1)
        side_img = _crop_masked_region(rgba, s1, s2)
        back_img = _crop_masked_region(rgba, s2, s3)

        # Clean 3/4 Portrait crop (inside the right-hand inset box, excluding top share/download icons)
        ph, pw = im.height, im.width
        p_raw = im.crop((min(pw - 10, s3 + 6), 44, pw - 4, int(ph * 0.72))).convert("RGBA")

        front_img.save(os.path.join(SPRITES_DIR, f"Sprite_{roster_id}_Front.png"))
        side_img.save(os.path.join(SPRITES_DIR, f"Sprite_{roster_id}_Side.png"))
        back_img.save(os.path.join(SPRITES_DIR, f"Sprite_{roster_id}_Back.png"))
        p_raw.save(os.path.join(SPRITES_DIR, f"Sprite_{roster_id}_Portrait.png"))

        _update_fighter_pbr_from_turnaround(roster_id, gl_id, front_img, back_img, p_raw)
        print(f"[OK] {roster_id:15s} -> Front={front_img.size} Side={side_img.size} Back={back_img.size} PBR={gl_id}")

    # Refresh embedded PNG textures inside existing sculpted SK_*.glb binaries cleanly (preserving LOD0 + 16 animations)
    import json, struct
    GLB_MAGIC = 0x46546C67
    CHUNK_JSON = 0x4E4F534A
    CHUNK_BIN = 0x004E4942
    MODELS_DIR = os.path.join(PROJECT_ROOT, "Assets", "Models3D", "Fighters")

    for _, gl_id in ROSTER_MAP:
        glb_path = os.path.join(MODELS_DIR, f"SK_{gl_id}.glb")
        if not os.path.isfile(glb_path):
            continue
        with open(glb_path, "rb") as gf:
            raw = gf.read()
        jlen = struct.unpack("<I", raw[12:16])[0]
        gltf = json.loads(raw[20:20 + jlen].decode("utf-8"))
        blen = struct.unpack("<I", raw[20 + jlen + 4:20 + jlen + 8])[0]
        old_bin = raw[20 + jlen + 8:20 + jlen + 8 + blen]

        tex_files = [
            os.path.join(TEXTURES_DIR, f"T_{gl_id}_Skin_Albedo.png"),
            os.path.join(TEXTURES_DIR, f"T_{gl_id}_Kit_Albedo.png"),
            os.path.join(TEXTURES_DIR, f"T_{gl_id}_Hair_Albedo.png"),
        ]
        # Replace image bufferView chunks cleanly at the end of BIN
        new_bin = bytearray(old_bin)
        images = gltf.get("images", [])
        bvs = gltf.get("bufferViews", [])
        if len(images) >= 3:
            for idx_img, tpath in enumerate(tex_files):
                if os.path.isfile(tpath):
                    with open(tpath, "rb") as tf:
                        png_bytes = tf.read()
                    while len(new_bin) % 4 != 0:
                        new_bin.append(0)
                    off = len(new_bin)
                    new_bin.extend(png_bytes)
                    bv_idx = images[idx_img]["bufferView"]
                    bvs[bv_idx]["byteOffset"] = off
                    bvs[bv_idx]["byteLength"] = len(png_bytes)

        while len(new_bin) % 4 != 0:
            new_bin.append(0)
        gltf["buffers"][0]["byteLength"] = len(new_bin)
        json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        while len(json_bytes) % 4 != 0:
            json_bytes += b" "
        total_len = 12 + 8 + len(json_bytes) + 8 + len(new_bin)
        with open(glb_path, "wb") as out_gf:
            out_gf.write(struct.pack("<III", GLB_MAGIC, 2, total_len))
            out_gf.write(struct.pack("<II", len(json_bytes), CHUNK_JSON))
            out_gf.write(json_bytes)
            out_gf.write(struct.pack("<II", len(new_bin), CHUNK_BIN))
            out_gf.write(new_bin)
        print(f"  [GLB TEX EMBEDDED] SK_{gl_id}.glb ({total_len:,} B)")


if __name__ == "__main__":
    main()
