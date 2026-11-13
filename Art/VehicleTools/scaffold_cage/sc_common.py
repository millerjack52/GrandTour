"""Shared constants and numpy helpers for the scaffold cage stages (SC1-SC4).

Plan: docs/SCAFFOLD_CAGE_PLAN.md. Pure numpy so it imports in system Python and in Blender.
"""
import json
import os

import numpy as np

ROOT = r"C:\GrandTour"
REF_SIDE = os.path.join(ROOT, r"Art\References\Vehicles\Impreza2003\orthographic-reset-v01\02-side-profile.png")
TRIPO_DIR = os.path.join(ROOT, r"Art\References\Vehicles\Impreza2003\tripo-scaffold-v01")
TRIPO_GLB = os.path.join(TRIPO_DIR, "impreza-tripo.glb")
TRIPO_SIDE_REGISTERED = os.path.join(TRIPO_DIR, "tripo-side-registered.png")
# Output revision: set the environment variable SC_VERSION (v01 default, v02 = plan section 9).
VERSION = os.environ.get("SC_VERSION", "v01")
V2 = VERSION != "v01"
OUT_DIR = os.path.join(ROOT, r"Art\Export\VehicleTools", "impreza-scaffold-cage-" + VERSION)
DEBUG_DIR = os.path.join(OUT_DIR, "debug")

# Reference registration
PX_PER_M = 400.0
PX_MID = 893.0
PX_GROUND = 757.0
WHEEL_PX = [(386, 614), (1400, 614)]
WHEEL_R_PX = 143
REF_W, REF_H = 1881, 836
TRIPO_PAD = 100

# GLB native -> car frame
S = 4.5594
GLB_Y_OFFSET = 0.0025

WHEEL_Y = [-1.2675, 1.2675]
WHEEL_Z = 0.3575


def px_to_Y(px):
    return (np.asarray(px, dtype=float) - PX_MID) / PX_PER_M


def py_to_Z(py):
    return (PX_GROUND - np.asarray(py, dtype=float)) / PX_PER_M


def Y_to_px(Y):
    return PX_MID + PX_PER_M * np.asarray(Y, dtype=float)


def Z_to_py(Z):
    return PX_GROUND - PX_PER_M * np.asarray(Z, dtype=float)


def gaussian_kernel(sigma):
    r = int(np.ceil(4.0 * sigma))
    x = np.arange(-r, r + 1, dtype=float)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    return k / k.sum()


def gauss1d(a, sigma):
    """Gaussian filter of a 1-D array, edges extended with the end values."""
    a = np.asarray(a, dtype=float)
    if sigma <= 0:
        return a.copy()
    k = gaussian_kernel(sigma)
    r = (len(k) - 1) // 2
    p = np.concatenate([np.full(r, a[0]), a, np.full(r, a[-1])])
    return np.convolve(p, k, mode="valid")


def gauss1d_nan(a, sigma):
    """NaN-aware 1-D Gaussian (normalised convolution). NaN stays NaN."""
    a = np.asarray(a, dtype=float)
    m = np.isfinite(a)
    k = gaussian_kernel(sigma)
    num = np.convolve(np.where(m, a, 0.0), k, mode="same")
    den = np.convolve(m.astype(float), k, mode="same")
    out = np.full_like(a, np.nan)
    ok = m & (den > 1e-9)
    out[ok] = num[ok] / den[ok]
    return out


def gauss2d_nan(a, sigma):
    """NaN-aware separable 2-D Gaussian. NaN cells stay NaN."""
    a = np.asarray(a, dtype=float)
    m = np.isfinite(a)
    k = gaussian_kernel(sigma)
    v = np.where(m, a, 0.0)
    w = m.astype(float)

    def conv_axis(arr, axis):
        return np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), axis, arr)

    num = conv_axis(conv_axis(v, 0), 1)
    den = conv_axis(conv_axis(w, 0), 1)
    out = np.full_like(a, np.nan)
    ok = m & (den > 1e-9)
    out[ok] = num[ok] / den[ok]
    return out


def median1d(a, width):
    """Running median, odd window, edges use the shrunken window. NaN ignored."""
    a = np.asarray(a, dtype=float)
    h = width // 2
    out = np.empty_like(a)
    n = len(a)
    for i in range(n):
        seg = a[max(0, i - h): min(n, i + h + 1)]
        seg = seg[np.isfinite(seg)]
        out[i] = np.median(seg) if len(seg) else np.nan
    return out


def bilinear(grid, u0, v0, step, u, v):
    """Bilinear lookup in grid[iu, iv] whose cell (iu, iv) is at (u0 + iu*step, v0 + iv*step).
    NaN outside the grid or if a corner with non-zero weight is NaN."""
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    shape = np.broadcast(u, v).shape
    fu = np.broadcast_to((u - u0) / step, shape).astype(float)
    fv = np.broadcast_to((v - v0) / step, shape).astype(float)
    nu, nv = grid.shape
    inside = (fu >= -1e-9) & (fu <= nu - 1 + 1e-9) & (fv >= -1e-9) & (fv <= nv - 1 + 1e-9)
    fu_c = np.clip(np.nan_to_num(fu, nan=0.0), 0, nu - 1)
    fv_c = np.clip(np.nan_to_num(fv, nan=0.0), 0, nv - 1)
    iu = np.minimum(np.floor(fu_c).astype(int), nu - 2)
    iv = np.minimum(np.floor(fv_c).astype(int), nv - 2)
    tu = fu_c - iu
    tv = fv_c - iv
    acc = np.zeros(shape)
    bad = ~inside
    for du, dv, w in ((0, 0, (1 - tu) * (1 - tv)), (1, 0, tu * (1 - tv)), (0, 1, (1 - tu) * tv), (1, 1, tu * tv)):
        val = grid[iu + du, iv + dv]
        use = w > 1e-12
        bad |= use & ~np.isfinite(val)
        acc += np.where(use & np.isfinite(val), val * w, 0.0)
    out = np.where(bad, np.nan, acc)
    return out if out.shape else float(out)


def load_json(name):
    with open(os.path.join(OUT_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(name, data):
    with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
