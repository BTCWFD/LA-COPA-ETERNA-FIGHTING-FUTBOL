#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crop Gemini Lightbox screenshots into clean SheetA_<CODE>.png / SheetB_<CODE>.png."""
from __future__ import annotations

import os
import sys
import numpy as np
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEETS_DIR = os.path.join(PROJECT_ROOT, "Assets", "Sprites2D", "ActionFrames", "Sheets")


def save_lightbox_sheet(src_png: str, out_png: str) -> tuple[int, int]:
    im = Image.open(src_png).convert("RGBA")
    arr = np.asarray(im)
    rgb = arr[:, :, :3].astype(np.float32)
    h, w, _ = rgb.shape
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    is_grey = (
        (rgb[:, :, 0] > 32) & (rgb[:, :, 0] < 90)
        & (rgb[:, :, 1] > 32) & (rgb[:, :, 1] < 92)
        & (rgb[:, :, 2] > 36) & (rgb[:, :, 2] < 98)
        & (sat < 14)
    )
    sx, sy = w / 1024.0, h / 640.0
    mask = is_grey.copy()
    mask[:int(48 * sy), :] = False
    mask[int(485 * sy):, :] = False
    mask[:, :int(140 * sx)] = False
    mask[:, int(885 * sx):] = False
    ys = np.where(mask.mean(axis=1) > 0.22)[0]
    if len(ys) > 20:
        y0, y1 = int(ys.min()) + 3, int(ys.max()) - 3
        xs = np.where(mask[y0:y1, :].mean(axis=0) > 0.22)[0]
        x0, x1 = (int(xs.min()) + 3, int(xs.max()) - 3) if len(xs) > 20 else (int(157 * sx), int(866 * sx))
    else:
        # Exact Gemini Lightbox rect scaled from 1280x800 {x:192.08, y:78, w:895.83, h:500}
        x0, y0, x1, y1 = int(round(157 * sx)), int(round(65 * sy)), int(round(866 * sx)), int(round(458 * sy))

    crop_arr = arr[y0:y1, x0:x1].copy()
    # Normalize slight lightbox transition dimness back up to studio #383B42 (~lum 60)
    crgb = crop_arr[:, :, :3].astype(np.float32)
    csat = crgb.max(axis=2) - crgb.min(axis=2)
    bg_pix = crgb[csat < 10]
    if len(bg_pix) > 100:
        bg_med = float(np.median(bg_pix))
        if 25.0 < bg_med < 53.0:
            gain = min(1.85, 59.0 / bg_med)
            crop_arr[:, :, :3] = np.clip(crgb * gain, 0.0, 255.0).astype(np.uint8)

    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    Image.fromarray(crop_arr, mode="RGBA").save(out_png)
    return (x1 - x0, y1 - y0)


def main() -> None:
    os.makedirs(SHEETS_DIR, exist_ok=True)
    for arg in sys.argv[1:]:
        if "=" not in arg:
            continue
        target_name, src_png = arg.split("=", 1)
        if not target_name.endswith(".png"):
            target_name += ".png"
        out_png = os.path.join(SHEETS_DIR, target_name)
        cw, ch = save_lightbox_sheet(src_png, out_png)
        print(f"[CROP OK] {target_name} -> {cw}x{ch}")


if __name__ == "__main__":
    main()
