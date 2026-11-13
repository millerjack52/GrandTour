"""Cubic B-spline P-splines (numpy only): Cox-de Boor basis on uniform extended knots, 1-D and
tensor-product weighted least squares with a second-difference coefficient penalty, derivative
constraint rows, and penalty selection by the largest strength that keeps a weighted RMS target.

Plan: docs/BODY_BUILDER_PLAN.md section 4c/4d/4e.
"""
import numpy as np

DEG = 3


class Knots:
    """Uniform knots every h starting at u0, extended DEG knots beyond both ends."""

    def __init__(self, u0, u1, h):
        self.u0, self.u1, self.h = float(u0), float(u1), float(h)
        self.nseg = int(np.ceil((u1 - u0) / h - 1e-9))
        self.t = u0 + h * np.arange(-DEG, self.nseg + DEG + 1)
        self.n = self.nseg + DEG  # number of basis functions

    def clamp(self, u):
        return np.clip(np.asarray(u, float), self.u0, self.u0 + self.nseg * self.h - 1e-12)


def basis(u, kn, deg=DEG):
    """Cox-de Boor recursion. Returns (len(u), number of basis functions of degree deg)."""
    t = kn.t
    u = np.atleast_1d(kn.clamp(u))
    B = np.zeros((len(u), len(t) - 1))
    for i in range(len(t) - 1):
        B[:, i] = (u >= t[i]) & (u < t[i + 1])
    for d in range(1, deg + 1):
        Bn = np.zeros((len(u), len(t) - 1 - d))
        for i in range(len(t) - 1 - d):
            Bn[:, i] = ((u - t[i]) / (t[i + d] - t[i])) * B[:, i] + ((t[i + d + 1] - u) / (t[i + d + 1] - t[i + 1])) * B[:, i + 1]
        B = Bn
    return B


def dbasis(u, kn):
    """First derivative of the cubic basis."""
    t = kn.t
    Bm = basis(u, kn, DEG - 1)
    D = np.zeros((Bm.shape[0], kn.n))
    for i in range(kn.n):
        D[:, i] = DEG / (t[i + DEG] - t[i]) * Bm[:, i] - DEG / (t[i + DEG + 1] - t[i + 1]) * Bm[:, i + 1]
    return D


def d2mat(n):
    D = np.zeros((n - 2, n))
    for i in range(n - 2):
        D[i, i:i + 3] = [1.0, -2.0, 1.0]
    return D


class Fit2D:
    """Tensor-product cubic P-spline f(u, v)."""

    def __init__(self, ku, kv):
        self.ku, self.kv = ku, kv
        self.C = None
        self.lam = None
        self.exact = None  # rows G with G c = 0 imposed exactly (null-space elimination), BT2 7a

    def design(self, u, v):
        Bu = basis(u, self.ku)
        Bv = basis(v, self.kv)
        return (Bu[:, :, None] * Bv[:, None, :]).reshape(len(Bu), -1)

    def penalty(self):
        nu, nv = self.ku.n, self.kv.n
        Du, Dv = d2mat(nu), d2mat(nv)
        return np.kron(Du.T @ Du, np.eye(nv)) + np.kron(np.eye(nu), Dv.T @ Dv)

    def prepare(self, u, v, val, w, constraint_rows=None):
        A = self.design(u, v)
        N = null_basis(self.exact) if self.exact is not None else None
        self._N = N
        if N is not None:
            A = A @ N
        self._A = A
        self._AtWA = A.T @ (A * w[:, None])
        self._AtWy = A.T @ (w * val)
        P = self.penalty()
        self._P = N.T @ P @ N if N is not None else P
        self._K = None
        if constraint_rows is not None and len(constraint_rows):
            G = constraint_rows @ N if N is not None else constraint_rows
            kappa = 1e4 * max(1.0, float(np.max(np.diag(self._AtWA))))
            self._K = kappa * G.T @ G

    def solve(self, lam):
        M = self._AtWA + lam * self._P
        if self._K is not None:
            M = M + self._K
        c = np.linalg.solve(M, self._AtWy)
        pred = self._A @ c
        if self._N is not None:
            c = self._N @ c
        self.C = c.reshape(self.ku.n, self.kv.n)
        self.lam = lam
        return pred

    def fit(self, u, v, val, w, lam, constraint_rows=None):
        self.prepare(u, v, val, w, constraint_rows)
        return self.solve(lam)

    def dv_constraint(self, v_at):
        """Rows forcing df/dv = 0 at v = v_at for every u."""
        d = dbasis([v_at], self.kv)[0]
        rows = np.zeros((self.ku.n, self.ku.n * self.kv.n))
        for i in range(self.ku.n):
            rows[i, i * self.kv.n + np.arange(self.kv.n)] = d
        return rows

    def du_constraint(self, u_at):
        """Rows forcing df/du = 0 at u = u_at for every v (one row per v-basis column)."""
        d = dbasis([u_at], self.ku)[0]
        rows = np.zeros((self.kv.n, self.ku.n * self.kv.n))
        for j in range(self.kv.n):
            rows[j, np.arange(self.ku.n) * self.kv.n + j] = d
        return rows

    def __call__(self, u, v):
        u = np.atleast_1d(np.asarray(u, float))
        v = np.atleast_1d(np.asarray(v, float))
        u, v = np.broadcast_arrays(u, v)
        shp = u.shape
        Bu = basis(u.ravel(), self.ku)
        Bv = basis(v.ravel(), self.kv)
        return np.einsum("ni,ij,nj->n", Bu, self.C, Bv).reshape(shp)

    def du(self, u, v):
        u, v = np.broadcast_arrays(np.atleast_1d(np.asarray(u, float)), np.atleast_1d(np.asarray(v, float)))
        shp = u.shape
        return np.einsum("ni,ij,nj->n", dbasis(u.ravel(), self.ku), self.C, basis(v.ravel(), self.kv)).reshape(shp)

    def dv(self, u, v):
        u, v = np.broadcast_arrays(np.atleast_1d(np.asarray(u, float)), np.atleast_1d(np.asarray(v, float)))
        shp = u.shape
        return np.einsum("ni,ij,nj->n", basis(u.ravel(), self.ku), self.C, dbasis(v.ravel(), self.kv)).reshape(shp)


def null_basis(G):
    """Orthonormal basis of {c : G c = 0}."""
    _, sv, vt = np.linalg.svd(G)
    rank = int(np.sum(sv > 1e-10 * max(1.0, sv.max())))
    return vt[rank:].T


class Fit1D:
    def __init__(self, ku):
        self.ku = ku
        self.c = None

    def fit(self, u, val, w, lam, exact_ends=False):
        """exact_ends: df/du = 0 exactly at both ends of the knot domain (u0 and u1)."""
        A = basis(u, self.ku)
        D = d2mat(self.ku.n)
        N = None
        if exact_ends:
            G = np.vstack([dbasis([self.ku.u0], self.ku)[0], dbasis([self.ku.u1], self.ku)[0]])
            N = null_basis(G)
        Ae = A @ N if N is not None else A
        De = D @ N if N is not None else D
        M = Ae.T @ (Ae * w[:, None]) + lam * De.T @ De
        c = np.linalg.solve(M, Ae.T @ (w * val))
        self.c = N @ c if N is not None else c
        self.lam = lam
        return A @ self.c

    def du(self, u):
        return dbasis(np.atleast_1d(u), self.ku) @ self.c

    def __call__(self, u):
        return basis(np.atleast_1d(u), self.ku) @ self.c


def weighted_stats(r, w):
    m = w > 0
    rms = float(np.sqrt(np.sum(w[m] * r[m] ** 2) / np.sum(w[m])))
    p95 = float(np.percentile(np.abs(r[m]), 95))
    return rms, p95


FLOOR_FACTOR = 1.25  # BT1 deviation option "factor": budget = 1.25 x floor
FLOOR_RULE = "add"  # BT1 deviation: budget = floor + target when the target is below the achievable floor


def choose_lambda(fitobj, u, v, val, w, target_rms, constraint_rows=None, lo=-8.0, hi=6.0, iters=40):
    """Largest penalty (bisection on log10) with weighted RMS <= target. If even the smallest penalty
    misses the target (the floor is above it), the budget becomes FLOOR_FACTOR x floor.
    Returns lam, rms, p95, info."""
    fitobj.prepare(u, v, val, w, constraint_rows)

    def run(loglam):
        pred = fitobj.solve(10.0 ** loglam)
        return weighted_stats(pred - val, w)

    floor, _ = run(lo)
    budget = target_rms
    reached = floor <= target_rms
    if not reached:
        budget = floor + target_rms if FLOOR_RULE == "add" else FLOOR_FACTOR * floor
    rms_hi, _ = run(hi)
    if rms_hi <= budget:
        rms, p95 = run(hi)
        return 10.0 ** hi, rms, p95, {"reached": reached, "floor": floor, "budget": budget}
    a, b = lo, hi
    for _ in range(iters):
        mid = 0.5 * (a + b)
        r, _ = run(mid)
        if r <= budget:
            a = mid
        else:
            b = mid
        if b - a < 0.02:
            break
    rms, p95 = run(a)
    return 10.0 ** a, rms, p95, {"reached": reached, "floor": floor, "budget": budget}
