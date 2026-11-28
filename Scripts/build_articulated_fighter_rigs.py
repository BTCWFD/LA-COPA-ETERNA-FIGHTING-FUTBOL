#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_articulated_fighter_rigs.py
Segments each of the 17 photorealistic `Sprite_<ID>_Front.png` cutouts into a 10-part
articulated fighting-game rig (`torso`, `head`, `armL_upper`, `armL_lower`, `armR_upper`,
`armR_lower`, `legL_thigh`, `legL_shin`, `legR_thigh`, `legR_shin`) with exact shoulder,
elbow, hip, and knee pivot coordinates + intrinsic rest angles, packed into a single
512x512 atlas `Assets/Sprites2D/Fighters/Rig_<ID>.png` and `FightersRigManifest.json`.
"""

from __future__ import annotations

import json
import math
import os
import numpy as np
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "Assets", "Sprites2D", "Fighters")
MANIFEST_PATH = os.path.join(SPRITES_DIR, "FightersRigManifest.json")

FIGHTER_CODES = [
    "FENOMENO_BR", "BRUXO_BR", "CANON_AR", "PULGA_AR",
    "PIBE_CO", "LOCO_CO", "PISTOLERO_UY", "MATADOR_UY",
    "BAMBAM_CL", "REY_CL", "BULLDOG_PY", "MAESTRO_PE",
    "TREN_EC", "HURACAN_VE", "DIABLO_BO", "GENERAL_FR",
    "VAR_ZERO_BOSS",
]


def _fit_arm_chain(rgba: np.ndarray, mask: np.ndarray, sh_pt: tuple[float, float]) -> tuple[tuple[float, float], tuple[float, float], float, float]:
    """Find elbow midpoint and hand tip from an arm mask relative to shoulder pivot."""
    ys, xs = np.where(mask & (rgba[:, :, 3] > 60))
    if len(xs) < 10:
        sx, sy = sh_pt
        return (sx - 12.0, sy + 45.0), (sx - 24.0, sy + 95.0), 0.3, 0.3

    sx, sy = sh_pt
    dx = xs.astype(np.float32) - sx
    dy = ys.astype(np.float32) - sy
    dist = np.hypot(dx, dy)
    max_d = float(dist.max())

    # Elbow ~46%..54% down arm length, hand ~88%..98%
    m_elb = (dist >= max_d * 0.44) & (dist <= max_d * 0.56)
    m_hand = dist >= max_d * 0.86
    ex = float(xs[m_elb].mean()) if m_elb.any() else float(sx + dx.mean())
    ey = float(ys[m_elb].mean()) if m_elb.any() else float(sy + max_d * 0.50)
    hx = float(xs[m_hand].mean()) if m_hand.any() else float(ex + (ex - sx))
    hy = float(ys[m_hand].mean()) if m_hand.any() else float(ey + max_d * 0.45)

    # Rest angle relative to straight down (+Y): angle = atan2(dx, dy) where 0=down, + = viewer right, - = viewer left
    ang_upper = math.atan2(ex - sx, max(1.0, ey - sy))
    ang_lower = math.atan2(hx - ex, max(1.0, hy - ey))
    return (ex, ey), (hx, hy), ang_upper, ang_lower


def _extract_side_profile_parts(
    code: str,
    target_w: int,
    target_h: int,
    front_neck_y: int,
    front_waist_y: int,
    front_hip_y: float,
    front_sh_y: float,
) -> dict:
    """Extract aligned right-facing head_side and torso_side from Sprite_<CODE>_Side.png."""
    side_path = os.path.join(SPRITES_DIR, f"Sprite_{code}_Side.png")
    im = Image.open(side_path).convert("RGBA")
    if code == "VAR_ZERO_BOSS":
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if im.height != target_h:
        new_w = max(16, int(round(im.width * (target_h / float(im.height)))))
        im = im.resize((new_w, target_h), Image.Resampling.LANCZOS)

    arr = np.asarray(im).copy()
    h, w, _ = arr.shape
    a = arr[:, :, 3] > 60
    yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")

    # Find side neck_y & head center X (stay strictly below visor/face band)
    best_neck_y = front_neck_y
    best_neck_w = 10**9
    y_scan_lo = max(int(h * 0.125), int(front_neck_y - 10))
    y_scan_hi = min(h - 20, int(front_neck_y + 18))
    if code == "VAR_ZERO_BOSS":
        y_scan_lo = int(h * 0.145)
        y_scan_hi = int(h * 0.215)
    for y in range(y_scan_lo, y_scan_hi):
        cnt = int(a[y].sum())
        if 12 < cnt < best_neck_w:
            best_neck_w = cnt
            best_neck_y = y

    neck_xs = np.where(a[best_neck_y])[0]
    head_cx = float(neck_xs.mean()) if len(neck_xs) > 0 else w * 0.5

    # Torso center X sampled across upper chest (neck_y + 8 .. front_waist_y)
    chest_band = a[max(0, best_neck_y + 6) : min(h, front_waist_y)]
    chest_xs = np.where(chest_band)[1]
    torso_cx = float(np.median(chest_xs)) if len(chest_xs) > 0 else w * 0.5

    torso_bottom_y = int(front_waist_y - 1)
    head_mask = yy <= best_neck_y + 9
    torso_mask = (yy >= best_neck_y - 3) & (yy <= torso_bottom_y) & a

    # Compute side torso shoulder anchors (near shoulder right on upper sleeve, far shoulder slightly forward)
    sh_row = min(h - 1, int(front_sh_y))
    sh_xs = np.where(a[sh_row])[0]
    if len(sh_xs) > 4:
        sh_left_edge = float(sh_xs[0])
        sh_right_edge = float(sh_xs[-1])
        sh_mid_x = sh_left_edge + (sh_right_edge - sh_left_edge) * 0.40
        sh_front_x = sh_mid_x - torso_cx
        sh_back_x = sh_left_edge + (sh_right_edge - sh_left_edge) * 0.62 - torso_cx
    else:
        sh_front_x = -3.0
        sh_back_x = 6.0

    # Clean dangling forearm overlap inside lower jersey so articulated arms never double-up over shirt
    torso_arr = arr.copy()
    face_mask = (yy >= max(0, best_neck_y - 24)) & (yy <= best_neck_y + 3) & (xx >= head_cx - 4) & a
    skin_ref = np.median(arr[face_mask, :3].astype(np.float32), axis=0) if face_mask.sum() > 20 else None

    cuff_y = int(best_neck_y + max(16, (torso_bottom_y - best_neck_y) * 0.44))
    if skin_ref is not None and code not in ("VAR_ZERO_BOSS", "BULLDOG_PY", "LOCO_CO"):
        for y in range(cuff_y, min(h, torso_bottom_y + 1)):
            row_xs = np.where(torso_mask[y])[0]
            if len(row_xs) < 12:
                continue
            rx0, rx1 = int(row_xs[0]), int(row_xs[-1])
            rw = rx1 - rx0
            band0 = rx0 + int(rw * 0.16)
            band1 = rx0 + int(rw * 0.70)
            clean_back = arr[y, min(rx1 - 1, rx0 + int(rw * 0.10)), :3].astype(np.float32)
            clean_chest = arr[y, min(rx1 - 2, rx0 + int(rw * 0.85)), :3].astype(np.float32)
            for x in range(band0, band1):
                if not torso_mask[y, x]:
                    continue
                px_rgb = torso_arr[y, x, :3].astype(np.float32)
                d_skin = float(np.linalg.norm(px_rgb - skin_ref))
                d_jersey = min(float(np.linalg.norm(px_rgb - clean_back)), float(np.linalg.norm(px_rgb - clean_chest)))
                if (d_skin < 98.0 or d_jersey > 26.0) and d_jersey > 22.0:
                    t_row = (x - band0) / max(1.0, float(band1 - band0))
                    torso_arr[y, x, :3] = np.clip((1.0 - t_row) * clean_back + t_row * clean_chest, 0, 255).astype(np.uint8)

    return {
        "arr": arr,
        "torso_arr": torso_arr,
        "head_mask": head_mask,
        "torso_mask": torso_mask,
        "head_pivot": (head_cx, float(best_neck_y + 3)),
        "torso_pivot": (torso_cx, float(front_hip_y)),
        "neck_from_hip_y": float(front_hip_y - best_neck_y),
        "sh_front": [round(float(sh_front_x), 2), round(float(front_sh_y - front_hip_y), 2)],
        "sh_back": [round(float(sh_back_x), 2), round(float(front_sh_y - front_hip_y + 2.0), 2)],
    }


def _segment_fighter(code: str) -> dict:
    front_path = os.path.join(SPRITES_DIR, f"Sprite_{code}_Front.png")
    im = Image.open(front_path).convert("RGBA")
    arr = np.asarray(im).copy()
    h, w, _ = arr.shape
    a = arr[:, :, 3] > 60
    cx = w * 0.5

    # 1. Detect neck_y (minimum horizontal central alpha width in head/neck band)
    best_neck_y = int(h * 0.13)
    best_neck_w = 10**9
    for y in range(int(h * 0.09), int(h * 0.25)):
        # count contiguous opaque pixels around cx
        row_seg = a[y, int(cx - w * 0.22) : int(cx + w * 0.22)]
        cnt = int(row_seg.sum())
        if 8 < cnt < best_neck_w:
            best_neck_w = cnt
            best_neck_y = y
    neck_y = best_neck_y

    # 2. Detect crotch_y (first gap in central column below 44% height)
    c_strip = a[int(h * 0.44) : int(h * 0.72), int(cx - 3) : int(cx + 4)].mean(axis=1)
    gaps = np.where(c_strip < 0.35)[0]
    crotch_y = int(h * 0.44) + (int(gaps[0]) if len(gaps) > 0 else int(h * 0.16))

    # 3. Locate waist_y (jersey-to-shorts hem ~65% of distance from neck_y to crotch_y) and armpit_y
    waist_y = int(neck_y + (crotch_y - neck_y) * 0.72)
    armpit_y = min(waist_y - 18, neck_y + int(h * 0.145))
    sh_top_y = neck_y + int(h * 0.020)

    yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
    torso_left = np.full(h, cx - w * 0.17, dtype=np.float32)
    torso_right = np.full(h, cx + w * 0.17, dtype=np.float32)

    # Scan rib/waist row-by-row from center to find exact inner gap between chest & arms
    rib_L, rib_R = [], []
    for y in range(armpit_y, waist_y + 12):
        lx = int(cx)
        while lx > 4 and a[y, lx]:
            lx -= 1
        rx = int(cx)
        while rx < w - 5 and a[y, rx]:
            rx += 1
        max_hw = min(w * 0.21, 40.0)
        lx = max(int(cx - max_hw), lx)
        rx = min(int(cx + max_hw), rx)
        rib_L.append(lx)
        rib_R.append(rx)
        torso_left[y] = float(lx)
        torso_right[y] = float(rx)

    sh_lx = float(np.median(rib_L[:6])) + 1.0 if rib_L else cx - w * 0.15
    sh_rx = float(np.median(rib_R[:6])) - 1.0 if rib_R else cx + w * 0.15
    sh_y = float(sh_top_y + (armpit_y - sh_top_y) * 0.42)

    # Smooth diagonal sleeve-to-torso cut from neck base down to armpit
    for y in range(neck_y, armpit_y):
        t = (y - neck_y) / max(1.0, float(armpit_y - neck_y))
        torso_left[y] = (cx - w * 0.08) * (1.0 - t) + sh_lx * t
        torso_right[y] = (cx + w * 0.08) * (1.0 - t) + sh_rx * t

    # Keep waist width clean down to crotch_y for shorts overlap
    for y in range(waist_y + 12, crotch_y + 16):
        torso_left[y] = float(np.median(rib_L[-6:])) if rib_L else cx - w * 0.17
        torso_right[y] = float(np.median(rib_R[-6:])) if rib_R else cx + w * 0.17

    # Clean masks:
    # - head: above neck_y + 9 (plus Boss drones stay inside head box)
    # - torso: jersey from neck_y - 3 down to waist_y + 10 (plus rounded shorts waist bridge down to crotch_y - 2)
    # - arms: strictly OUTSIDE torso boundary and strictly ABOVE waist_y + 6 (zero hip/shorts bleed!)
    head_mask = (yy <= neck_y + 9) & ((yy < sh_top_y) | (np.abs(xx - cx) < w * 0.145))
    if code == "VAR_ZERO_BOSS":
        head_mask = yy <= neck_y + 12

    torso_mask = (yy >= neck_y - 3) & (yy <= crotch_y - 2) & (xx >= torso_left[:, None] - 1) & (xx <= torso_right[:, None] + 1)

    # Distance outside arm-gap scan from outer image border inward (stops cleanly at torso gap!)
    arm_gap_L = np.zeros_like(a)
    arm_gap_R = np.zeros_like(a)
    for y in range(sh_top_y - 4, waist_y + 14):
        # For y below armpit, arm must have at least 1 empty pixel separating from torso_left[y]
        if y >= armpit_y:
            tl = int(torso_left[y])
            tr = int(torso_right[y])
            # scan outward left until arm ends or starts cleanly
            arm_gap_L[y, : max(0, tl - 1)] = a[y, : max(0, tl - 1)]
            arm_gap_R[y, min(w, tr + 2) :] = a[y, min(w, tr + 2) :]
        else:
            arm_gap_L[y, : int(torso_left[y] + 4)] = a[y, : int(torso_left[y] + 4)]
            arm_gap_R[y, int(torso_right[y] - 4) :] = a[y, int(torso_right[y] - 4) :]

    # Keep BOSS floating drones out of arm masks
    if code == "VAR_ZERO_BOSS":
        arm_gap_L[: neck_y + 12, :] = False
        arm_gap_R[: neck_y + 12, :] = False

    armL_mask = arm_gap_L & (yy >= sh_top_y - 4) & (yy <= waist_y + 14)
    armR_mask = arm_gap_R & (yy >= sh_top_y - 4) & (yy <= waist_y + 14)

    el_L, hd_L, ang_armLU, ang_armLL = _fit_arm_chain(arr, armL_mask, (sh_lx, sh_y))
    el_R, hd_R, ang_armRU, ang_armRL = _fit_arm_chain(arr, armR_mask, (sh_rx, sh_y))

    def split_arm(a_mask: np.ndarray, sh_pt: tuple[float, float], el_pt: tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
        sx, sy = sh_pt
        ex, ey = el_pt
        vx, vy = ex - sx, ey - sy
        vlen2 = max(1.0, vx * vx + vy * vy)
        proj = ((xx - sx) * vx + (yy - sy) * vy) / vlen2
        dist_el = np.hypot(xx - ex, yy - ey)
        upper = a_mask & ((proj <= 1.03) | (dist_el <= 5.5))
        lower = a_mask & ((proj >= 0.95) | (dist_el <= 5.5))
        return upper, lower

    armL_u_mask, armL_l_mask = split_arm(armL_mask, (sh_lx, sh_y), el_L)
    armR_u_mask, armR_l_mask = split_arm(armR_mask, (sh_rx, sh_y), el_R)

    # Legs start cleanly at hip_y = waist_y + (crotch_y - waist_y)*0.35 (full shorts + thigh + knee + shin + boot!)
    hip_y = float(waist_y + max(6.0, (crotch_y - waist_y) * 0.30))
    knee_y = int(crotch_y + (h - crotch_y) * 0.42)

    leg_sample_y = min(h - 1, crotch_y + 18)
    xs_legL = np.where(a[leg_sample_y, : int(cx)])[0]
    xs_legR = np.where(a[leg_sample_y, int(cx) :])[0] + int(cx)
    hip_lx = float(xs_legL.mean()) if len(xs_legL) > 0 else cx - w * 0.11
    hip_rx = float(xs_legR.mean()) if len(xs_legR) > 0 else cx + w * 0.11

    # Thighs start smoothly under jersey hem with rounded upper-hip overlap and exclude arms
    legL_full = (yy >= int(hip_y - 10)) & (xx <= cx + 2) & (xx >= torso_left[:, None] - 5) & (~armL_mask)
    legR_full = (yy >= int(hip_y - 10)) & (xx >= cx - 2) & (xx <= torso_right[:, None] + 5) & (~armR_mask)

    # Shrink torso cleanly down to waist_y + 10 so shorts belong smoothly to each hinged thigh (zero chopped shorts box!)
    torso_mask = (yy >= neck_y - 3) & (yy <= int(waist_y + 12)) & (xx >= torso_left[:, None] - 1) & (xx <= torso_right[:, None] + 1)

    legL_thigh_mask = legL_full & (yy <= knee_y + 7)
    legL_shin_mask = legL_full & (yy >= knee_y - 7)
    legR_thigh_mask = legR_full & (yy <= knee_y + 7)
    legR_shin_mask = legR_full & (yy >= knee_y - 7)

    # Pack front 10 parts + side-profile head_side & torso_side into a 512x768 RGBA atlas
    side_info = _extract_side_profile_parts(code, w, h, neck_y, waist_y, hip_y, sh_y)

    parts_spec = [
        ("head",       head_mask,       (cx, float(neck_y + 3)), 0.0, arr),
        ("torso",      torso_mask,      (cx, float(hip_y)),      0.0, arr),
        ("armL_upper", armL_u_mask,     (sh_lx, sh_y),           ang_armLU, arr),
        ("armL_lower", armL_l_mask,     el_L,                    ang_armLL, arr),
        ("armR_upper", armR_u_mask,     (sh_rx, sh_y),           ang_armRU, arr),
        ("armR_lower", armR_l_mask,     el_R,                    ang_armRL, arr),
        ("legL_thigh", legL_thigh_mask, (hip_lx, hip_y),         0.0, arr),
        ("legL_shin",  legL_shin_mask,  (hip_lx, float(knee_y)), 0.0, arr),
        ("legR_thigh", legR_thigh_mask, (hip_rx, hip_y),         0.0, arr),
        ("legR_shin",  legR_shin_mask,  (hip_rx, float(knee_y)), 0.0, arr),
        ("head_side",  side_info["head_mask"],  side_info["head_pivot"],  0.0, side_info["arr"]),
        ("torso_side", side_info["torso_mask"], side_info["torso_pivot"], 0.0, side_info["torso_arr"]),
    ]

    atlas = Image.new("RGBA", (512, 768), (0, 0, 0, 0))
    cur_x, cur_y, row_h = 2, 2, 0
    packed_parts: dict[str, dict] = {}

    for pname, pmask, pivot, rest_ang, src_arr in parts_spec:
        valid = pmask & (src_arr[:, :, 3] > 25)
        ys, xs = np.where(valid)
        if len(ys) == 0:
            packed_parts[pname] = {"x": 0, "y": 0, "w": 2, "h": 2, "px": 1, "py": 1, "restAngle": 0.0}
            continue
        sh_src, sw_src = src_arr.shape[:2]
        y0, y1 = max(0, int(ys.min()) - 1), min(sh_src, int(ys.max()) + 2)
        x0, x1 = max(0, int(xs.min()) - 1), min(sw_src, int(xs.max()) + 2)
        sub_rgba = src_arr[y0:y1, x0:x1].copy()
        sub_rgba[~pmask[y0:y1, x0:x1], 3] = 0
        pw, ph = x1 - x0, y1 - y0

        if cur_x + pw + 4 > 512:
            cur_x = 2
            cur_y += row_h + 4
            row_h = 0
        if cur_y + ph + 2 > 768:
            raise RuntimeError(f"Rig atlas overflow for {code} at {pname}")

        atlas.paste(Image.fromarray(sub_rgba, "RGBA"), (cur_x, cur_y))
        packed_parts[pname] = {
            "x": int(cur_x),
            "y": int(cur_y),
            "w": int(pw),
            "h": int(ph),
            "px": round(float(pivot[0] - x0), 2),
            "py": round(float(pivot[1] - y0), 2),
            "restAngle": round(float(rest_ang), 4),
        }
        cur_x += pw + 4
        row_h = max(row_h, ph)

    atlas_path = os.path.join(SPRITES_DIR, f"Rig_{code}.png")
    atlas.save(atlas_path)

    return {
        "code": code,
        "atlas": f"Rig_{code}.png",
        "srcSize": [int(w), int(h)],
        "skeleton": {
            "hipOffsetFromFeetY": round(float(h - hip_y), 2),
            "neckFromHipY": round(float(hip_y - neck_y), 2),
            "neckFromHipSideY": round(float(side_info["neck_from_hip_y"]), 2),
            "shL": [round(float(sh_lx - cx), 2), round(float(sh_y - hip_y), 2)],
            "shR": [round(float(sh_rx - cx), 2), round(float(sh_y - hip_y), 2)],
            "shSideF": side_info["sh_front"],
            "shSideB": side_info["sh_back"],
            "elLFromSh": [round(float(el_L[0] - sh_lx), 2), round(float(el_L[1] - sh_y), 2)],
            "elRFromSh": [round(float(el_R[0] - sh_rx), 2), round(float(el_R[1] - sh_y), 2)],
            "upperArmLenL": round(float(math.hypot(el_L[0] - sh_lx, el_L[1] - sh_y)), 2),
            "upperArmLenR": round(float(math.hypot(el_R[0] - sh_rx, el_R[1] - sh_y)), 2),
            "hipL": [round(float(hip_lx - cx), 2), 0.0],
            "hipR": [round(float(hip_rx - cx), 2), 0.0],
            "thighLen": round(float(knee_y - hip_y), 2),
            "shinLen": round(float(h - knee_y), 2),
        },
        "parts": packed_parts,
    }


def main() -> None:
    manifest: dict[str, dict] = {}
    for code in FIGHTER_CODES:
        info = _segment_fighter(code)
        manifest[code] = info
        print(f"[RIG OK] {code:15s} -> {info['atlas']} thigh={info['skeleton']['thighLen']} shin={info['skeleton']['shinLen']}")

    with open(MANIFEST_PATH, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)
    print(f"[DONE] Saved {len(manifest)}/17 articulated fighter rigs -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
