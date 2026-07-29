import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from serial_reader import read_mock, read_from_serial, SerialListener, list_ports

MOCK_MODE = True

WAVELENGTHS = [415, 445, 480, 515, 555, 590, 630, 680]

CMF = {
    415: (0.07058, 0.00200, 0.34230),
    445: (0.32000, 0.03400, 1.65750),
    480: (0.09564, 0.13902, 0.81295),
    515: (0.03341, 0.50800, 0.16120),
    555: (0.44420, 0.97500, 0.00200),
    590: (0.99200, 0.75700, 0.00010),
    630: (0.64870, 0.28000, 0.00000),
    680: (0.16490, 0.06100, 0.00000),
}

_Xn_raw = sum(CMF[wl][0] for wl in WAVELENGTHS)
_Yn_raw = sum(CMF[wl][1] for wl in WAVELENGTHS)
_Zn_raw = sum(CMF[wl][2] for wl in WAVELENGTHS)
Xn, Yn, Zn = 95.047, 100.0, 108.883


def compute_lab(tooth, white, dark):
    R = []
    for t, w, d in zip(tooth, white, dark):
        denom = w - d
        R.append(max(0.0, min((t - d) / denom, 1.0)) if denom > 0 else 0.0)

    X = sum(R[i] * CMF[WAVELENGTHS[i]][0] for i in range(8))
    Y = sum(R[i] * CMF[WAVELENGTHS[i]][1] for i in range(8))
    Z = sum(R[i] * CMF[WAVELENGTHS[i]][2] for i in range(8))
    X = (X / _Xn_raw) * Xn
    Y = (Y / _Yn_raw) * Yn
    Z = (Z / _Zn_raw) * Zn

    def f(t): return t ** (1/3)
    L = 116 * f(Y/Yn) - 16
    a = 500 * (f(X/Xn) - f(Y/Yn))
    b = 200 * (f(Y/Yn) - f(Z/Zn))
    return (L, a, b)


def delta_e(lab1, lab2):
    return math.sqrt(sum((c1-c2)**2 for c1, c2 in zip(lab1, lab2)))

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

VITA_SHADE_HEX = {
    "A1":    "#F5EDD4", "A2":    "#F2E5C0", "A3":    "#EDDB9F",
    "A3.5":  "#E8D18A", "A4":    "#DFC472", "B1":    "#F7EFD8",
    "B2":    "#F3E8C4", "B3":    "#EDE0A8", "B4":    "#E6D48E",
    "C1":    "#F0EAD5", "C2":    "#EAE0C0", "C3":    "#E2D5A8",
    "C4":    "#D8C88E", "D2":    "#F1E8C8", "D3":    "#EADFB0",
    "D4":    "#E1D49A", "1M1":   "#F8F2E2", "1M2":   "#F4EDD6",
    "2L1.5": "#F3EDD8", "2L2.5": "#EEE5C8", "2M1":   "#F0E8CC",
    "2M2":   "#EBDFB8", "2M3":   "#E5D5A4", "2R1.5": "#EFE6CA",
    "2R2.5": "#E9DDB4", "3L1.5": "#EBE0B8", "3L2.5": "#E4D5A4",
    "3M1":   "#E8DC9E", "3M2":   "#E2D090", "3M3":   "#D9C47C",
    "3R1.5": "#E5D898", "3R2.5": "#DDD088",
}

CHANNEL_LABELS = ["415\nViolet", "445\nIndigo", "480\nBlue",
                  "515\nCyan",   "555\nGreen",  "590\nYellow",
                  "630\nOrange", "680\nRed"]
CHANNEL_COLORS = ["#7B2FBE", "#4B56D2", "#2196F3",
                  "#00BCD4", "#4CAF50", "#CDDC39",
                  "#FF9800", "#F44336"]



class DentalShadeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dental Shade Matcher")
        self.root.geometry("860x660")
        self.root.configure(bg="#1A1A2E")

        self.dark_ref  = None
        self.white_ref = None
        self.step      = 0 
        self.listener  = None   

        self._build_ui()

        if not MOCK_MODE:
            self.listener = SerialListener(callback=self._on_serial_reading)
            self.listener.start()

    def _build_ui(self):
        self.font_title = ("Helvetica", 13, "bold")
        self.font_label = ("Helvetica", 10)
        self.font_shade = ("Helvetica", 52, "bold")
        self.font_small = ("Helvetica", 9)

        BG    = "#1A1A2E"
        PANEL = "#16213E"
        TEXT  = "#E0E0E0"

        self.colors = dict(BG=BG, PANEL=PANEL, TEXT=TEXT,
                           GREEN="#4CAF50", YELLOW="#FFC107", RED="#F44336")

        left   = tk.Frame(self.root, bg=PANEL, width=220)
        centre = tk.Frame(self.root, bg=BG)

        left.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 4), pady=8)
        centre.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        left.pack_propagate(False)

        self._build_left(left)
        self._build_centre(centre)

    def _build_left(self, parent):
        C = self.colors

        tk.Label(parent, text="CALIBRATION",
                 bg=parent["bg"], fg=C["TEXT"],
                 font=self.font_title).pack(pady=(16, 8))

        self.step_labels = []
        steps = ["Step 1 — Dark reading",
                 "Step 2 — White tile",
                 "Step 3 — Scan tooth"]
        for s in steps:
            lbl = tk.Label(parent, text=f"○  {s}",
                           bg=parent["bg"], fg="#666",
                           font=self.font_small, anchor="w")
            lbl.pack(fill=tk.X, padx=16, pady=2)
            self.step_labels.append(lbl)

        ttk.Separator(parent, orient="horizontal").pack(
            fill=tk.X, padx=12, pady=12)

        btn_style = dict(font=self.font_label, relief="flat",
                         cursor="hand2", padx=8, pady=6)

        self.btn_dark = tk.Button(
            parent, text="1 · Take Dark Reading",
            bg="#333355", fg=C["TEXT"],
            command=self.take_dark, **btn_style)
        self.btn_dark.pack(fill=tk.X, padx=12, pady=4)

        self.btn_white = tk.Button(
            parent, text="2 · Calibrate White Tile",
            bg="#333355", fg=C["TEXT"],
            command=self.calibrate_white,
            state=tk.DISABLED, **btn_style)
        self.btn_white.pack(fill=tk.X, padx=12, pady=4)

        self.btn_scan = tk.Button(
            parent, text="3 · Scan Tooth",
            bg="#0F3460", fg=C["TEXT"],
            command=self.scan_tooth,
            state=tk.DISABLED, **btn_style)
        self.btn_scan.pack(fill=tk.X, padx=12, pady=4)

        ttk.Separator(parent, orient="horizontal").pack(
            fill=tk.X, padx=12, pady=12)

        tk.Label(parent, text="MATCHED SHADE",
                 bg=parent["bg"], fg=C["TEXT"],
                 font=self.font_title).pack()

        self.swatch = tk.Label(parent, text="",
                               bg="#2A2A4A", width=12, height=2)
        self.swatch.pack(pady=(8, 2))

        self.shade_label = tk.Label(parent, text="--",
                                    bg=parent["bg"], fg="#4FC3F7",
                                    font=self.font_shade)
        self.shade_label.pack()

        self.status_label = tk.Label(
            parent, text="Complete calibration to begin",
            bg=parent["bg"], fg="#888",
            font=self.font_small, wraplength=200)
        self.status_label.pack(pady=4)

        ttk.Separator(parent, orient="horizontal").pack(
            fill=tk.X, padx=12, pady=12)

        tk.Label(parent, text="L*a*b* VALUES",
                 bg=parent["bg"], fg=C["TEXT"],
                 font=self.font_title).pack()

        lab_frame = tk.Frame(parent, bg="#0D1117", padx=12, pady=10)
        lab_frame.pack(fill=tk.X, padx=12, pady=(6, 0))

        self.lab_labels = {}
        for axis, colour in [("L*", "#FFFFFF"),
                              ("a*", "#F44336"),
                              ("b*", "#FFC107")]:
            row = tk.Frame(lab_frame, bg="#0D1117")
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=axis, bg="#0D1117", fg=colour,
                     font=("Helvetica", 11, "bold"), width=3).pack(side=tk.LEFT)
            val = tk.Label(row, text="--", bg="#0D1117",
                           fg=C["TEXT"], font=("Helvetica", 11))
            val.pack(side=tk.LEFT, padx=8)
            self.lab_labels[axis] = val

    def _build_centre(self, parent):
        C = self.colors

        tk.Label(parent, text="REFLECTANCE SPECTRUM",
                 bg=parent["bg"], fg=C["TEXT"],
                 font=self.font_title).pack(pady=(8, 4))

        self.fig, self.ax = plt.subplots(figsize=(5.8, 3.2), dpi=95)
        self.fig.patch.set_facecolor("#1A1A2E")
        self.ax.set_facecolor("#0D1117")
        self.ax.tick_params(colors=C["TEXT"])
        self.ax.spines[:].set_color("#333")
        self.ax.set_ylim(0, 100)
        self.ax.set_ylabel("Reflectance %", color=C["TEXT"], fontsize=9)
        self.ax.set_xticks(range(8))
        self.ax.set_xticklabels(CHANNEL_LABELS, fontsize=7, color=C["TEXT"])

        self.bars = self.ax.bar(range(8), [0]*8,
                                color=CHANNEL_COLORS, alpha=0.85,
                                width=0.6, edgecolor="#222")
        self.fig.tight_layout(pad=1.2)

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.X, padx=12)

        tk.Label(parent, text="TOP 3 CLOSEST MATCHES",
                 bg=parent["bg"], fg=C["TEXT"],
                 font=self.font_title).pack(pady=(12, 4))

        match_frame = tk.Frame(parent, bg=parent["bg"])
        match_frame.pack(fill=tk.X, padx=16)

        self.match_widgets = []
        for rank in range(3):
            row = tk.Frame(match_frame, bg="#16213E",
                           relief="flat", padx=10, pady=6)
            row.pack(fill=tk.X, pady=3)

            tk.Label(row, text=f"#{rank+1}",
                     bg="#16213E", fg="#555",
                     font=("Helvetica", 14, "bold"),
                     width=3).pack(side=tk.LEFT)

            swatch = tk.Label(row, text="  ", bg="#2A2A4A", width=3)
            swatch.pack(side=tk.LEFT, padx=(0, 8))

            shade_lbl = tk.Label(row, text="--",
                                 bg="#16213E", fg=C["TEXT"],
                                 font=("Helvetica", 13, "bold"),
                                 width=6, anchor="w")
            shade_lbl.pack(side=tk.LEFT)

            de_lbl = tk.Label(row, text="ΔE: --",
                              bg="#16213E", fg="#888",
                              font=self.font_small)
            de_lbl.pack(side=tk.LEFT, padx=8)

            q_lbl = tk.Label(row, text="",
                             bg="#16213E", fg=C["GREEN"],
                             font=self.font_small)
            q_lbl.pack(side=tk.RIGHT)

            self.match_widgets.append((swatch, shade_lbl, de_lbl, q_lbl))

    def take_dark(self):
        if MOCK_MODE:
            values = read_mock(shade="A2", step="dark")
            self._store_reading(values)
        else:
            self.status_label.config(
                text="Press the wand button\n(probe covered, LED off)",
                fg=self.colors["YELLOW"])
            self.step = 0

    def calibrate_white(self):
        if MOCK_MODE:
            values = read_mock(shade="A2", step="white")
            self._store_reading(values)
        else:
            self.status_label.config(
                text="Press the wand button\n(probe on white tile)",
                fg=self.colors["YELLOW"])
            self.step = 1

    def scan_tooth(self):
        """Step 3: Take tooth measurement and run shade matching."""
        if self.dark_ref is None or self.white_ref is None:
            messagebox.showerror("Not calibrated",
                                 "Complete dark and white calibration first.")
            return

        if MOCK_MODE:
            values = read_mock(shade="A2", step="tooth")
            self._store_reading(values)
        else:
            self.status_label.config(
                text="Press the wand button\n(probe on tooth)",
                fg=self.colors["YELLOW"])
            self.step = 2

    def _on_serial_reading(self, values):
        self.root.after(0, lambda: self._store_reading(values))

    def _store_reading(self, values):
        if self.step == 0:
            self.dark_ref = np.array(values)
            self._mark_step(0)
            self.btn_white.config(state=tk.NORMAL, bg="#0F4A2E")
            self.status_label.config(
                text="Dark reading done.\nNow place probe on white tile.",
                fg=self.colors["GREEN"])
            self.step = 1

        elif self.step == 1:
            self.white_ref = np.array(values)
            self._mark_step(1)
            self.btn_scan.config(state=tk.NORMAL, bg="#0F3460")
            self.status_label.config(
                text="White calibration done.\nReady to scan tooth.",
                fg=self.colors["GREEN"])
            self.step = 2

        elif self.step == 2:
            tooth_counts = np.array(values)

            pct = np.clip(
                (tooth_counts - self.dark_ref) /
                (self.white_ref - self.dark_ref) * 100,
                0, 100)

            lab = compute_lab(tooth_counts.tolist(),
                              self.white_ref.tolist(),
                              self.dark_ref.tolist())

            ranked = sorted(VITA_SHADE_LAB.items(),
                            key=lambda x: delta_e(lab, x[1]))
            top3       = ranked[:3]
            best_shade = top3[0][0]
            best_de    = delta_e(lab, top3[0][1])

            self._mark_step(2)
            self._update_graph(pct)
            self._update_result(best_shade, best_de, lab)
            self._update_top3(top3, lab)
            self.step = 2  

    def _mark_step(self, idx):
        self.step_labels[idx].config(
            text="●  " + self.step_labels[idx]["text"][3:],
            fg=self.colors["GREEN"])

    def _update_graph(self, pct):
        for bar, height in zip(self.bars, pct):
            bar.set_height(height)
        self.ax.set_ylim(0, 110)
        for txt in self.ax.texts:
            txt.remove()
        for bar, val in zip(self.bars, pct):
            self.ax.text(bar.get_x() + bar.get_width()/2,
                         bar.get_height() + 1.5,
                         f"{val:.0f}%", ha="center", va="bottom",
                         fontsize=7, color="#CCC")
        self.canvas.draw()

    def _update_result(self, shade, de, lab):
        self.shade_label.config(text=shade)
        self.swatch.config(bg=VITA_SHADE_HEX.get(shade, "#F5EDD4"))

        if de < 1.0:
            msg, fg = f"Excellent match  (ΔE = {de:.2f})", self.colors["GREEN"]
        elif de < 3.0:
            msg, fg = f"Acceptable match  (ΔE = {de:.2f})", self.colors["YELLOW"]
        else:
            msg, fg = f"Weak match  (ΔE = {de:.2f})", self.colors["RED"]

        self.status_label.config(text=msg, fg=fg)

        L, a, b = lab
        self.lab_labels["L*"].config(text=f"{L:.2f}")
        self.lab_labels["a*"].config(text=f"{a:.2f}")
        self.lab_labels["b*"].config(text=f"{b:.2f}")

    def _update_top3(self, top3, measured_lab):
        for (shade, ref_lab), (swatch, shade_lbl, de_lbl, q_lbl) \
                in zip(top3, self.match_widgets):
            de = delta_e(measured_lab, ref_lab)
            swatch.config(bg=VITA_SHADE_HEX.get(shade, "#F5EDD4"))
            shade_lbl.config(text=shade)
            de_lbl.config(text=f"ΔE = {de:.2f}")
            if de < 1.0:
                q_lbl.config(text="● Excellent", fg=self.colors["GREEN"])
            elif de < 3.0:
                q_lbl.config(text="● Acceptable", fg=self.colors["YELLOW"])
            else:
                q_lbl.config(text="● Weak", fg=self.colors["RED"])

if __name__ == "__main__":
    root = tk.Tk()
    app = DentalShadeApp(root)
    root.mainloop()
