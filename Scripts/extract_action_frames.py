#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_action_frames.py
Deterministic 3x2 action-sheet slicer, studio-grey (#383B42) alpha matter,
connected-component cleaner, QA contact-sheet generator, and manifest builder
for `Assets/Sprites2D/ActionFrames/ActionFrames_Manifest.json`.

Usage:
    python Scripts/extract_action_frames.py
"""

from __future__ import annotations

import json
import os
from collections import deque
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    from scipy import ndimage as ndi
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTION_FRAMES_DIR = os.path.join(PROJECT_ROOT, "Assets", "Sprites2D", "ActionFrames")
SHEETS_DIR = os.path.join(ACTION_FRAMES_DIR, "Sheets")
CATALOG_PATH = os.path.join(ACTION_FRAMES_DIR, "ActionFrames_PromptCatalog.json")
MANIFEST_PATH = os.path.join(ACTION_FRAMES_DIR, "ActionFrames_Manifest.json")

DEFAULT_BG_RGB = np.array([56.0, 59.0, 66.0], dtype=np.float32)  # #383B42
MIN_SPECK_PIXELS = 25


def _estimate_global_bg(rgb: np.ndarray) -> np.ndarray:
    """Estimate studio-grey background RGB from outer perimeter low-saturation pixels."""
    h, w, _ = rgb.shape
    border = np.concatenate([
        rgb[:6, :, :].reshape(-1, 3),
        rgb[max(0, h - 6):, :, :].reshape(-1, 3),
        rgb[:, :6, :].reshape(-1, 3),
        rgb[:, max(0, w - 6):, :].reshape(-1, 3),
    ], axis=0)
    sat = border.max(axis=1) - border.min(axis=1)
    neutral = border[sat < 14.0]
    if len(neutral) >= 32:
        return np.median(neutral, axis=0).astype(np.float32)
    if len(border) > 0:
        return np.median(border, axis=0).astype(np.float32)
    return DEFAULT_BG_RGB.copy()


def detect_grid_splits_3x2(rgb: np.ndarray, bg_rgb: np.ndarray) -> tuple[list[int], list[int]]:
    """
    Detect exact 3-column x 2-row splits using minimum foreground energy valleys
    near 1/3 and 2/3 width and 1/2 height so tilted poses inside a cell aren't clipped.
    """
    h, w, _ = rgb.shape
    sat = rgb.max(axis=2) - rgb.min(axis=2)

    # Row-wise neutral studio background profile from left/right outer margins
    edge_cols = np.concatenate([rgb[:, :4, :], rgb[:, max(0, w - 4):, :]], axis=1)
    row_bg = np.median(edge_cols, axis=1)
    diff_row = np.linalg.norm(rgb - row_bg[:, None, :], axis=2)
    diff_glob = np.linalg.norm(rgb - bg_rgb[None, None, :], axis=2)
    diff = np.minimum(diff_row, diff_glob) + sat * 0.55

    fg_energy = (diff > 19.0).astype(np.float32) + np.clip((diff - 14.0) / 40.0, 0.0, 1.0) * 0.25

    col_energy = fg_energy.mean(axis=0)
    row_energy = fg_energy.mean(axis=1)

    # Smooth 1D energy slightly so single-pixel noise doesn't shift the valley center
    kernel = np.array([0.15, 0.2, 0.3, 0.2, 0.15], dtype=np.float32)
    col_smooth = np.convolve(col_energy, kernel, mode="same")
    row_smooth = np.convolve(row_energy, kernel, mode="same")

    def best_valley(profile: np.ndarray, nominal: int, lo: int, hi: int) -> int:
        lo_c = max(1, lo)
        hi_c = min(len(profile) - 1, hi)
        if hi_c <= lo_c:
            return nominal
        idx = np.arange(lo_c, hi_c, dtype=np.float32)
        # Tiny tie-breaker biases wide zero-energy valleys to the center nearest nominal
        penalty = np.abs(idx - float(nominal)) / float(max(1, len(profile))) * 1e-3
        best_offset = int(np.argmin(profile[lo_c:hi_c] + penalty))
        return lo_c + best_offset

    x1 = best_valley(col_smooth, w // 3, int(w * 0.25), int(w * 0.42))
    x2 = best_valley(col_smooth, (2 * w) // 3, int(w * 0.58), int(w * 0.75))
    y1 = best_valley(row_smooth, h // 2, int(h * 0.40), int(h * 0.60))

    if x2 <= x1 + 16:
        x1, x2 = w // 3, (2 * w) // 3
    if y1 <= 16 or y1 >= h - 16:
        y1 = h // 2

    return [0, x1, x2, w], [0, y1, h]


def _floodfill_edge_bg_fallback(is_bg_cand: np.ndarray) -> np.ndarray:
    """Pure-Python BFS edge-seeded floodfill fallback when SciPy is unavailable."""
    h, w = is_bg_cand.shape
    bg_mask = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_bg_cand[y, x] and not bg_mask[y, x]:
                bg_mask[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if is_bg_cand[y, x] and not bg_mask[y, x]:
                bg_mask[y, x] = True
                q.append((y, x))
    while q:
        cy, cx = q.popleft()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < h and 0 <= nx < w and not bg_mask[ny, nx] and is_bg_cand[ny, nx]:
                bg_mask[ny, nx] = True
                q.append((ny, nx))
    return bg_mask


def _filter_components(fg_mask: np.ndarray, cell_max_dim: int) -> np.ndarray:
    """
    Keep the largest main silhouette component plus closely nearby accessories
    (e.g., VAR_ZERO_BOSS floating drones, PIBE_CO afro curls) >= 25px,
    discarding isolated <25px speck noise.
    """
    if not fg_mask.any():
        return fg_mask

    if HAS_SCIPY:
        struct8 = np.ones((3, 3), dtype=np.int32)
        labels, num_features = ndi.label(fg_mask, structure=struct8)
        if num_features <= 1:
            return fg_mask if int(fg_mask.sum()) >= MIN_SPECK_PIXELS else np.zeros_like(fg_mask)
        counts = np.bincount(labels.ravel())
        counts[0] = 0
        main_label = int(np.argmax(counts))
        if counts[main_label] < MIN_SPECK_PIXELS:
            return np.zeros_like(fg_mask)

        # Bounding box of main silhouette
        main_ys, main_xs = np.where(labels == main_label)
        my0, my1 = int(main_ys.min()), int(main_ys.max())
        mx0, mx1 = int(main_xs.min()), int(main_xs.max())
        margin = max(40, int(0.15 * max(my1 - my0 + 1, mx1 - mx0 + 1, cell_max_dim)))

        # Distance transform from main silhouette for tight proximity check
        dist_from_main = ndi.distance_transform_edt(labels != main_label)

        keep = labels == main_label
        for lbl in range(1, num_features + 1):
            if lbl == main_label or counts[lbl] < MIN_SPECK_PIXELS:
                continue
            comp_mask = labels == lbl
            min_dist = float(dist_from_main[comp_mask].min())
            if min_dist <= float(margin):
                keep |= comp_mask
        return keep

    # Pure-Python fallback if SciPy is absent
    h, w = fg_mask.shape
    visited = np.zeros((h, w), dtype=bool)
    comps: list[list[tuple[int, int]]] = []
    for y in range(h):
        for x in range(w):
            if fg_mask[y, x] and not visited[y, x]:
                comp: list[tuple[int, int]] = []
                q: deque[tuple[int, int]] = deque([(y, x)])
                visited[y, x] = True
                while q:
                    cy, cx = q.popleft()
                    comp.append((cy, cx))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dy == 0 and dx == 0:
                                continue
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and fg_mask[ny, nx] and not visited[ny, nx]:
                                visited[ny, nx] = True
                                q.append((ny, nx))
                comps.append(comp)
    if not comps:
        return np.zeros_like(fg_mask)
    comps.sort(key=len, reverse=True)
    main = comps[0]
    if len(main) < MIN_SPECK_PIXELS:
        return np.zeros_like(fg_mask)
    mys = [p[0] for p in main]
    mxs = [p[1] for p in main]
    my0, my1, mx0, mx1 = min(mys), max(mys), min(mxs), max(mxs)
    margin = max(40, int(0.15 * max(my1 - my0 + 1, mx1 - mx0 + 1, cell_max_dim)))
    keep = np.zeros_like(fg_mask)
    for py, px in main:
        keep[py, px] = True
    for comp in comps[1:]:
        if len(comp) < MIN_SPECK_PIXELS:
            continue
        cys = [p[0] for p in comp]
        cxs = [p[1] for p in comp]
        if max(cys) >= my0 - margin and min(cys) <= my1 + margin and max(cxs) >= mx0 - margin and min(cxs) <= mx1 + margin:
            for py, px in comp:
                keep[py, px] = True
    return keep


def extract_cell_rgba(cell_arr: np.ndarray, global_bg: np.ndarray) -> Image.Image:
    """
    Remove studio-grey background from a single cell via edge-seeded floodfill,
    punch clean interior studio-grey enclosed loops, de-fringe 1px anti-aliased
    contours, and preserve dark hair/eyes/shorts/cleats at 100% opacity.
    """
    ch, cw, _ = cell_arr.shape
    rgb = cell_arr[:, :, :3].astype(np.float32)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    lum = rgb.mean(axis=2)

    # Estimate per-cell neutral background from cell perimeter
    border_pts = np.concatenate([
        rgb[:3, :, :].reshape(-1, 3),
        rgb[max(0, ch - 3):, :, :].reshape(-1, 3),
        rgb[:, :3, :].reshape(-1, 3),
        rgb[:, max(0, cw - 3):, :].reshape(-1, 3),
    ], axis=0)
    b_sat = border_pts.max(axis=1) - border_pts.min(axis=1)
    b_neut = border_pts[b_sat < 14.0]
    cell_bg = np.median(b_neut, axis=0).astype(np.float32) if len(b_neut) >= 16 else global_bg

    diff_cell = np.linalg.norm(rgb - cell_bg[None, None, :], axis=2)
    diff_glob = np.linalg.norm(rgb - global_bg[None, None, :], axis=2)
    # Row-wise edge grey estimate absorbs top/bottom studio lighting falloff cleanly
    edge_strip = np.concatenate([rgb[:, :3, :], rgb[:, max(0, cw - 3):, :]], axis=1)
    row_bg = np.median(edge_strip, axis=1)
    diff_row = np.linalg.norm(rgb - row_bg[:, None, :], axis=2)
    diff_min = np.minimum(np.minimum(diff_cell, diff_glob), diff_row)

    # Protect warm skin & white socks/gloves; #383B42 itself has cool B-R~10..12 so allow sat<16.5 when close to bg
    is_bright_warm_skin = (lum >= 74.0) & (rgb[:, :, 0] > rgb[:, :, 1] + 3.5) & ((rgb[:, :, 0] - rgb[:, :, 2]) >= 10.0)
    is_close_studio_grey = (diff_min < 12.5) & (sat < 16.5) & (lum <= 95.0)
    is_neutral_mid_grey = (diff_min < 24.0) & (sat < 11.5) & (lum >= 42.0) & (lum <= 86.0) & ((rgb[:, :, 0] - rgb[:, :, 2]) <= 4.0)
    is_bg_cand = (((diff_min < 15.8) & (sat < 12.5)) | is_close_studio_grey | is_neutral_mid_grey) & (~is_bright_warm_skin)
    # Strip thin 4px neutral-grey/light-grey divider line remnants along cell perimeter before floodfill
    perim_grey = (sat < 16.5) & (lum <= 145.0)
    is_bg_cand[:4, :] |= perim_grey[:4, :]
    is_bg_cand[-4:, :] |= perim_grey[-4:, :]
    is_bg_cand[:, :4] |= perim_grey[:, :4]
    is_bg_cand[:, -4:] |= perim_grey[:, -4:]

    if HAS_SCIPY:
        bg_labels, _ = ndi.label(is_bg_cand)
        edge_lbls = np.unique(np.concatenate([
            bg_labels[0, :],
            bg_labels[-1, :],
            bg_labels[:, 0],
            bg_labels[:, -1],
        ]))
        edge_lbls = edge_lbls[edge_lbls != 0]
        bg_mask = np.isin(bg_labels, edge_lbls)

        # Also clean large enclosed studio-grey holes (between legs/arms) with stricter tolerance
        strict_bg = (diff_min < 11.5) & (sat < 7.5) & (~bg_mask)
        if strict_bg.any():
            hole_labels, n_holes = ndi.label(strict_bg)
            hole_counts = np.bincount(hole_labels.ravel())
            for h_lbl in range(1, n_holes + 1):
                if hole_counts[h_lbl] >= 120:
                    bg_mask |= (hole_labels == h_lbl)
    else:
        bg_mask = _floodfill_edge_bg_fallback(is_bg_cand)

    fg_raw = ~bg_mask
    fg_clean = _filter_components(fg_raw, max(ch, cw))

    # Drop any remaining detached neutral-grey floor shadow islands (smaller non-main components with low saturation)
    if HAS_SCIPY and fg_clean.any():
        c_lbls, c_num = ndi.label(fg_clean, structure=np.ones((3, 3), dtype=np.int32))
        if c_num > 1:
            c_counts = np.bincount(c_lbls.ravel())
            c_counts[0] = 0
            c_main = int(np.argmax(c_counts))
            for lbl in range(1, c_num + 1):
                if lbl == c_main:
                    continue
                cm = c_lbls == lbl
                if float(np.median(sat[cm])) < 10.5 and 36.0 <= float(np.median(lum[cm])) <= 95.0:
                    fg_clean[cm] = False

    # Build initial binary alpha & de-fringe 1px contour pixels that blend toward studio grey
    out_rgb = rgb.copy()
    alpha = np.where(fg_clean, 255, 0).astype(np.uint8)

    if HAS_SCIPY and fg_clean.any():
        border_fg = fg_clean & ndi.binary_dilation(~fg_clean, iterations=1)
        fringe = border_fg & (diff_min < 34.0) & (sat < 16.0)
        if fringe.any():
            # Attenuate fringe alpha and un-premultiply grey spill
            ratio = np.clip((diff_min[fringe] - 12.0) / 22.0, 0.15, 0.92)
            alpha_f = (ratio * 255.0).astype(np.uint8)
            alpha[fringe] = alpha_f
            inv_r = 1.0 / np.maximum(ratio[:, None], 0.25)
            unblended = cell_bg[None, :] + (out_rgb[fringe] - cell_bg[None, :]) * inv_r
            out_rgb[fringe] = np.clip(unblended, 0.0, 255.0)

    # Soften 1px anti-aliased edge gently while preserving solid interior opacity
    alpha_img = Image.fromarray(alpha, mode="L").filter(ImageFilter.GaussianBlur(radius=0.5))
    alpha_soft = np.asarray(alpha_img, dtype=np.uint8)
    alpha_final = np.where(
        alpha == 255,
        np.maximum(alpha_soft, 230),
        np.where(alpha > 0, alpha, np.where(alpha_soft > 90, alpha_soft, 0)),
    ).astype(np.uint8)

    # Zero out RGB on completely transparent pixels for clean PNG compression
    out_rgb[alpha_final == 0] = 0.0
    rgba = np.dstack([np.clip(out_rgb, 0, 255).astype(np.uint8), alpha_final])

    # Crop tightly around visible silhouette with 2px pad
    ys, xs = np.where(alpha_final > 16)
    if len(ys) == 0 or len(xs) == 0:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    pad = 2
    y0 = max(0, int(ys.min()) - pad)
    y1 = min(ch, int(ys.max()) + pad + 1)
    x0 = max(0, int(xs.min()) - pad)
    x1 = min(cw, int(xs.max()) + pad + 1)
    return Image.fromarray(rgba[y0:y1, x0:x1], mode="RGBA")


def _draw_checkerboard(img: Image.Image, x0: int, y0: int, w: int, h: int, tile: int = 12) -> None:
    """Draw a dark studio checkerboard patch inside an RGB/RGBA image."""
    yy, xx = np.mgrid[0:h, 0:w]
    chk = ((xx // tile) + (yy // tile)) % 2 == 0
    patch = np.empty((h, w, 4), dtype=np.uint8)
    patch[chk] = (34, 38, 46, 255)
    patch[~chk] = (46, 51, 61, 255)
    img.paste(Image.fromarray(patch, mode="RGBA"), (x0, y0))


def generate_qa_contact_sheet(
    code: str,
    display_name: str,
    frame_order: list[str],
    extracted_imgs: dict[str, Image.Image],
    out_path: str,
    idle_h: int,
) -> None:
    """Generate QA_ContactSheet_<CODE>.png over a dark checkerboard strip with frame labels."""
    cols = 6
    rows = 2
    slot_w, slot_h = 260, 280
    header_h = 46
    pad = 12
    label_h = 34

    canvas_w = pad + cols * (slot_w + pad)
    canvas_h = header_h + pad + rows * (slot_h + label_h + pad)
    sheet = Image.new("RGBA", (canvas_w, canvas_h), (15, 18, 25, 255))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    draw.rectangle([(0, 0), (canvas_w, header_h)], fill=(22, 27, 38, 255))
    draw.text(
        (16, 14),
        f"QA CONTACT SHEET — {code} ({display_name}) | idleHeightPx={idle_h} | Frames={len(extracted_imgs)}/{len(frame_order)}",
        fill=(255, 224, 125, 255),
        font=font,
    )

    for idx, fname in enumerate(frame_order):
        r = idx // cols
        c = idx % cols
        sx = pad + c * (slot_w + pad)
        sy = header_h + pad + r * (slot_h + label_h + pad)

        _draw_checkerboard(sheet, sx, sy, slot_w, slot_h, tile=14)
        draw.rectangle([(sx, sy), (sx + slot_w - 1, sy + slot_h - 1)], outline=(68, 79, 98, 255), width=1)

        fimg = extracted_imgs.get(fname)
        if fimg is not None and fimg.width > 1 and fimg.height > 1:
            scale = min((slot_w - 16) / fimg.width, (slot_h - 16) / fimg.height)
            nw = max(1, int(round(fimg.width * scale)))
            nh = max(1, int(round(fimg.height * scale)))
            resized = fimg.resize((nw, nh), Image.Resampling.LANCZOS)
            px = sx + (slot_w - nw) // 2
            py = sy + slot_h - nh - 8  # Anchor feet near bottom of slot
            sheet.paste(resized, (px, py), resized)
            rel_h = round(fimg.height / max(1, idle_h), 3)
            meta_txt = f"{fname} ({fimg.width}x{fimg.height} | rel={rel_h})"
            txt_col = (0, 230, 118, 255)
        else:
            draw.text((sx + 70, sy + slot_h // 2 - 6), "PENDIENTE", fill=(255, 145, 0, 255), font=font)
            meta_txt = f"{fname} (MISSING)"
            txt_col = (180, 190, 208, 255)

        draw.rectangle([(sx, sy + slot_h), (sx + slot_w - 1, sy + slot_h + label_h - 1)], fill=(20, 24, 34, 255))
        draw.text((sx + 8, sy + slot_h + 10), meta_txt, fill=txt_col, font=font)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sheet.save(out_path)


def process_sheet_file(
    sheet_path: str,
    frame_names: list[str],
    out_dir: str,
) -> dict[str, Image.Image]:
    """Slice a single 3x2 sheet PNG into 6 transparent RGBA frames and save them."""
    im = Image.open(sheet_path).convert("RGBA")
    arr = np.asarray(im)
    rgb = arr[:, :, :3].astype(np.float32)

    global_bg = _estimate_global_bg(rgb)
    x_splits, y_splits = detect_grid_splits_3x2(rgb, global_bg)

    os.makedirs(out_dir, exist_ok=True)
    results: dict[str, Image.Image] = {}
    for idx, fname in enumerate(frame_names):
        r = idx // 3
        c = idx % 3
        y0 = y_splits[r] + (8 if r > 0 else 2)
        y1 = y_splits[r + 1] - (8 if r < 1 else 2)
        x0 = x_splits[c] + (8 if c > 0 else 2)
        x1 = x_splits[c + 1] - (8 if c < 2 else 2)
        cell = arr[y0:y1, x0:x1]
        cropped = extract_cell_rgba(cell, global_bg)
        if cropped.width > 1 and cropped.height > 1:
            out_file = os.path.join(out_dir, f"{fname}.png")
            cropped.save(out_file)
            results[fname] = cropped
    return results


def main() -> int:
    if not os.path.isfile(CATALOG_PATH):
        raise FileNotFoundError(f"Catalog not found: {CATALOG_PATH}")

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog: dict[str, Any] = json.load(f)

    sheet_a_frames: list[str] = catalog.get("sheetAFrames", ["IDLE_GUARD", "RUN_1", "RUN_2", "CROUCH", "PUNCH_LP", "KICK_HP"])
    sheet_b_frames: list[str] = catalog.get("sheetBFrames", ["JUMP", "BLOCK_GUARD", "HITSTUN", "SHOT_SK", "CHILENA_SP", "KO"])
    all_frame_order = sheet_a_frames + sheet_b_frames

    os.makedirs(SHEETS_DIR, exist_ok=True)

    manifest_fighters: dict[str, Any] = {}
    total_frames_extracted = 0

    for entry in catalog.get("fighters", []):
        code: str = entry["code"]
        display_name: str = entry.get("displayName", code)
        sheet_a_path = os.path.join(SHEETS_DIR, f"SheetA_{code}.png")
        sheet_b_path = os.path.join(SHEETS_DIR, f"SheetB_{code}.png")

        has_a = os.path.isfile(sheet_a_path)
        has_b = os.path.isfile(sheet_b_path)
        if not has_a and not has_b:
            continue

        fighter_dir = os.path.join(ACTION_FRAMES_DIR, code)
        extracted: dict[str, Image.Image] = {}

        if has_a:
            extracted.update(process_sheet_file(sheet_a_path, sheet_a_frames, fighter_dir))
        if has_b:
            extracted.update(process_sheet_file(sheet_b_path, sheet_b_frames, fighter_dir))

        if not extracted:
            continue

        # Compute idleHeightPx baseline (prefer IDLE_GUARD, fallback to median frame height)
        if "IDLE_GUARD" in extracted:
            idle_h = extracted["IDLE_GUARD"].height
        else:
            heights = sorted(im.height for im in extracted.values())
            idle_h = heights[len(heights) // 2]

        qa_path = os.path.join(fighter_dir, f"QA_ContactSheet_{code}.png")
        generate_qa_contact_sheet(code, display_name, all_frame_order, extracted, qa_path, idle_h)

        frames_meta: dict[str, Any] = {}
        for fname in all_frame_order:
            if fname in extracted:
                im = extracted[fname]
                frames_meta[fname] = {
                    "file": f"{code}/{fname}.png",
                    "w": im.width,
                    "h": im.height,
                    "relHeight": round(im.height / max(1, idle_h), 4),
                }
                total_frames_extracted += 1

        manifest_fighters[code] = {
            "idleHeightPx": idle_h,
            "sheetA": has_a,
            "sheetB": has_b,
            "frames": frames_meta,
        }
        print(f"[OK] {code:15s} -> {len(frames_meta):2d} frames | idleHeightPx={idle_h} | QA=QA_ContactSheet_{code}.png")

    manifest = {
        "version": "1.0.0",
        "fighters": manifest_fighters,
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    print(
        f"[DONE] ActionFrames_Manifest.json updated: "
        f"{len(manifest_fighters)} fighters, {total_frames_extracted} frames."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
