import math
WAVELENGTHS = [415, 445, 480, 515, 555, 590, 630, 680]
CMF = {
    415:        (0.07058,  0.00200,  0.34230),
    445:        (0.32000,  0.03400,  1.65750),
    480:        (0.09564,  0.13902,  0.81295),
    515:        (0.03341,  0.50800,  0.16120),
    555:        (0.44420,  0.97500,  0.00200),
    590:        (0.99200,  0.75700,  0.00010),
    630:        (0.64870,  0.28000,  0.00000),
    680:        (0.16490,  0.06100,  0.00000),
}

_Xn_raw = sum(CMF[wl][0] for wl in WAVELENGTHS)
_Yn_raw = sum(CMF[wl][1] for wl in WAVELENGTHS)
_Zn_raw = sum(CMF[wl][2] for wl in WAVELENGTHS)

Xn, Yn, Zn = 95.047, 100.0, 108.883

VITA_SHADE_LAB = {
    "A1":    (74.45,  1.91, 16.96),
    "A2":    (71.50,  2.40, 19.34),
    "A3":    (68.92,  3.71, 21.95),
    "A3.5":  (65.74,  4.06, 22.83),
    "A4":    (61.49,  4.74, 22.91),
    "B1":    (76.96,  0.62, 15.46),
    "B2":    (73.91,  1.55, 18.20),
    "B3":    (70.74,  2.34, 22.07),
    "B4":    (67.49,  3.39, 23.99),
    "C1":    (71.78, -0.34, 13.49),
    "C2":    (67.93,  0.34, 14.78),
    "C3":    (64.42,  1.21, 15.95),
    "C4":    (60.52,  1.96, 16.46),
    "D2":    (71.42,  0.98, 15.49),
    "D3":    (68.31,  1.78, 17.18),
    "D4":    (64.96,  2.45, 17.96),
    "1M1":   (78.50, -0.20, 11.20),
    "1M2":   (76.80,  0.30, 13.10),
    "2L1.5": (74.10,  0.10, 12.40),
    "2L2.5": (72.30,  0.80, 14.60),
    "2M1":   (73.50,  0.90, 14.90),
    "2M2":   (71.90,  1.40, 16.30),
    "2M3":   (70.20,  1.90, 17.80),
    "2R1.5": (72.80,  1.10, 15.20),
    "2R2.5": (70.60,  1.70, 17.10),
    "3L1.5": (69.90,  1.30, 16.00),
    "3L2.5": (67.80,  2.00, 18.20),
    "3M1":   (68.70,  1.80, 17.50),
    "3M2":   (66.90,  2.50, 19.40),
    "3M3":   (65.10,  3.10, 20.90),
    "3R1.5": (67.40,  2.20, 18.60),
    "3R2.5": (65.30,  2.90, 20.50),
}

def normalize_reflectance(tooth_counts, white_counts, dark_counts):
    if not (len(tooth_counts) == len(white_counts) == len(dark_counts) == 8):
        raise ValueError("All three inputs must have exactly 8 values")

    R = []
    for tooth, white, dark in zip(tooth_counts, white_counts, dark_counts):
        denominator = white - dark
        if denominator <= 0:
            R.append(0.0)   # avoid division by zero
        else:
            r = (tooth - dark) / denominator
            R.append(max(0.0, min(r, 1.0)))  # clamp to [0.0, 1.0]
    return R

def reflectance_to_xyz(R):
    X_raw = sum(R[i] * CMF[WAVELENGTHS[i]][0] for i in range(8))
    Y_raw = sum(R[i] * CMF[WAVELENGTHS[i]][1] for i in range(8))
    Z_raw = sum(R[i] * CMF[WAVELENGTHS[i]][2] for i in range(8))

    
    X = (X_raw / _Xn_raw) * Xn
    Y = (Y_raw / _Yn_raw) * Yn
    Z = (Z_raw / _Zn_raw) * Zn

    return (X, Y, Z)


def xyz_to_lab(X, Y, Z):
    def f(t):
        return t ** (1/3)   # as specified in project doc

    L = 116 * f(Y / Yn) - 16
    a = 500 * (f(X / Xn) - f(Y / Yn))
    b = 200 * (f(Y / Yn) - f(Z / Zn))

    return (L, a, b)


def compute_lab(tooth_counts, white_counts, dark_counts):
    R = normalize_reflectance(tooth_counts, white_counts, dark_counts)
    X, Y, Z = reflectance_to_xyz(R)
    L, a, b = xyz_to_lab(X, Y, Z)

    return [L, a, b]


def delta_e(lab1, lab2):
    return math.sqrt(sum((c1 - c2)**2 for c1, c2 in zip(lab1, lab2)))


def find_closest_shades(lab, top_n=3):
    results = [(name, delta_e(lab, ref)) for name, ref in VITA_SHADE_LAB.items()]
    results.sort(key=lambda x: x[1])
    return results[:top_n]

if __name__ == "__main__":
    fake_dark  = [120, 130, 115, 125, 118, 122, 119, 128]
    fake_white = [4000, 4200, 4500, 4600, 4700, 4550, 4300, 4100]  

    demo_teeth = {
        "A1 shade": [1762, 1535, 1306, 2625, 2108, 2353, 2337, 3702],
        "A2 shade": [1896, 1274, 1115, 1867, 2272, 2093, 1971, 3766],
        "B1 shade": [2024, 1534, 1893, 2713, 2271, 2651, 2307, 3855],
    }

    print("=== Dental Shade Matcher v2 — Demo Run ===")
    print("Implementing exact 3-step pipeline from project spec\n")

    for label, tooth in demo_teeth.items():
        print(f"--- {label} ---")
        R = normalize_reflectance(tooth, fake_white, fake_dark)
        print(f"  Step 1 (Reflectance R): {[round(r, 3) for r in R]}")
        X, Y, Z = reflectance_to_xyz(R)
        print(f"  Step 2 (XYZ)         : X={X:.2f}, Y={Y:.2f}, Z={Z:.2f}")
        L, a, b = xyz_to_lab(X, Y, Z)
        print(f"  Step 3 (L*a*b*)      : L={L:.2f}, a={a:.2f}, b={b:.2f}")
        ok_L = 70.0 <= L <= 85.0
        ok_a = 0.0 <= a <= 6.0
        ok_b = 10.0 <= b <= 25.0
        print(f"  Spec range check     : L={'✓' if ok_L else '✗'}  a={'✓' if ok_a else '✗'}  b={'✓' if ok_b else '✗'}")
        output_vector = compute_lab(tooth, fake_white, fake_dark)
        print(f"  Output → Member 4    : {[round(v, 2) for v in output_vector]}")
        matches = find_closest_shades(output_vector)
        print(f"  Closest shades:")
        for shade, de in matches:
            tag = "✓ Strong" if de < 1.0 else ("~ Acceptable" if de < 3.0 else "✗ Weak")
            print(f"    {shade}: ΔE={de:.3f} ({tag})")
        print()
