"""Rotating stepped disk, plane stress, elastic (step 5c analytic disk check) [G].

The disk is a chain of annular segments of constant axial thickness h_i. In each segment the classical rotating
disk solution holds (e.g. Timoshenko, Theory of Elasticity, rotating disks) [G]:
    sigma_r  = A + B / r^2 - (3 + nu) / 8 rho omega^2 r^2
    sigma_th = A - B / r^2 - (1 + 3 nu) / 8 rho omega^2 r^2
At a thickness step the radial force per radian (sigma_r h r) and the radial displacement u = r (sigma_th - nu
sigma_r) / E are continuous (stepped-disk method, abrupt steps, no stress concentration) [G].
Boundary conditions: free bore (sigma_r = 0, no shaft fit) and the rim load at the outer radius (dead load of the
slotted rim, blades and their hardware spread over the live rim face) [G].
"""

import numpy as np


def solve(segments: list[tuple[float, float, float]], rho: float, omega: float, E: float, nu: float,
          sigma_outer: float, sigma_bore: float = 0.0) -> dict:
    """segments: (r_in, r_out, h) from the bore outward, contiguous. Returns per-segment A, B and a stress field
    function; stresses in Pa."""
    n = len(segments)
    for (a, b, _), (c, _, _) in zip(segments, segments[1:]):
        if abs(b - c) > 1e-12:
            raise ValueError("segments are not contiguous")
    k_r, k_t = (3 + nu) / 8 * rho * omega ** 2, (1 + 3 * nu) / 8 * rho * omega ** 2
    M, rhs = np.zeros((2 * n, 2 * n)), np.zeros(2 * n)

    def sr_row(i, r):  # sigma_r = A + B/r^2 - k_r r^2
        row = np.zeros(2 * n)
        row[2 * i], row[2 * i + 1] = 1.0, 1.0 / r ** 2
        return row, k_r * r * r

    def u_row(i, r):  # E u / r = sigma_th - nu sigma_r = (1 - nu) A - (1 + nu) B / r^2 - (k_t - nu k_r) r^2
        row = np.zeros(2 * n)
        row[2 * i], row[2 * i + 1] = 1 - nu, -(1 + nu) / r ** 2
        return row, (k_t - nu * k_r) * r * r

    row, c = sr_row(0, segments[0][0])
    M[0], rhs[0] = row, sigma_bore + c
    eq = 1
    for i in range(n - 1):
        r, h0, h1 = segments[i][1], segments[i][2], segments[i + 1][2]
        a, ca = sr_row(i, r)
        b, cb = sr_row(i + 1, r)
        M[eq], rhs[eq] = h0 * a - h1 * b, h0 * ca - h1 * cb
        a, ca = u_row(i, r)
        b, cb = u_row(i + 1, r)
        M[eq + 1], rhs[eq + 1] = a - b, ca - cb
        eq += 2
    row, c = sr_row(n - 1, segments[-1][1])
    M[eq], rhs[eq] = row, sigma_outer + c
    coef = np.linalg.solve(M, rhs)

    def field(i: int, r: float) -> dict:
        A, B = coef[2 * i], coef[2 * i + 1]
        sr = A + B / r ** 2 - k_r * r * r
        st = A - B / r ** 2 - k_t * r * r
        return {"r": r, "sigma_r": sr, "sigma_t": st, "von_mises": float(np.sqrt(sr * sr - sr * st + st * st)),
                "u": r * (st - nu * sr) / E}

    pts = []
    for i, (a, b, _) in enumerate(segments):
        for r in np.linspace(a, b, 41):
            pts.append(dict(field(i, float(r)), segment=i))
    peak = max(pts, key=lambda p: p["von_mises"])
    return {"coefficients": coef.tolist(), "points": pts, "bore": pts[0], "peak": peak, "field": field}


def mean_hoop_stress(segments, rho, omega, rim_force_total: float) -> float:
    """Average hoop stress over the meridional section of the live disk from the global force balance of a
    half disk [G]: (rim dead load / (2 pi) + rho omega^2 int h r^2 dr) / int h dr."""
    num = rim_force_total / (2 * np.pi) + sum(rho * omega ** 2 * h * (b ** 3 - a ** 3) / 3 for a, b, h in segments)
    return float(num / sum(h * (b - a) for a, b, h in segments))
