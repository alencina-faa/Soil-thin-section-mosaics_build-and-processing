import math
import os
import threading
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox
from tkinter import ttk

import h5py
import openpyxl as opxl
from PIL import Image

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

# Shapes/sizes used to segment pores (see proc_mosaic.py). Per user decision, the
# ellipse minor diameter ("emd") sheets are used as the single size metric for all shapes.
SHAPES = ["circ", "MLcirc", "shpless", "elongated"]
SIZES = ["S", "M", "L", "XL"]
SIZE_SHEET_PREFIX = "emd"
ROW_HEIGHT = 28

# Normalization constants for average pore area by size (Point 5)
NORM_AREA = {
    "S": (math.pi * (50**2)),
    "M": (math.pi * (300**2) / 4),
    "L": (math.pi * (1000**2) / 4),
    "XL": (math.pi * (10000**2) / 4),
}


def spectrum_tab(self):
    # State
    self.spectrum_stats_path = None
    self.spectrum_mosaics = []  # list of dicts, order defines plot/list order
    self.spectrum_aspect = 1.0 / 6.0
    self.spectrum_loading_var = tk.StringVar(value="")
    self._spectrum_drag_index = None
    self._spectrum_redraw_after_id = None

    # Left controls
    self.spectrum_frame_controls = ttk.Frame(self.spectrum_frame)
    self.spectrum_frame_controls.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

    self.spectrum_load_btn = ttk.Button(
        self.spectrum_frame_controls,
        text="Load Global_Pore_Stats.xlsx",
        command=lambda: _spectrum_load_stats(self),
    )
    self.spectrum_load_btn.pack(pady=(0, 8), fill=tk.X)

    # Aspect ratio control (V/H of each individual chart)
    aspect_frame = ttk.Frame(self.spectrum_frame_controls)
    aspect_frame.pack(pady=(0, 8), fill=tk.X)
    self.spectrum_aspect_var = tk.StringVar(value=_format_aspect(self.spectrum_aspect))
    ttk.Button(
        aspect_frame, text="-", width=2, command=lambda: _spectrum_adjust_aspect(self, 1 / 1.25)
    ).pack(side=tk.LEFT)
    ttk.Label(
        aspect_frame, textvariable=self.spectrum_aspect_var, anchor="center", width=10
    ).pack(side=tk.LEFT, expand=True, fill=tk.X)
    ttk.Button(
        aspect_frame, text="+", width=2, command=lambda: _spectrum_adjust_aspect(self, 1.25)
    ).pack(side=tk.LEFT)

    self.spectrum_loading_label = ttk.Label(
        self.spectrum_frame_controls, textvariable=self.spectrum_loading_var, foreground="gray"
    )
    self.spectrum_loading_label.pack(pady=(0, 4), fill=tk.X)

    # Point 9: Color code legend placed on left panel above "Mosaics"
    legend_frame = ttk.LabelFrame(self.spectrum_frame_controls, text="Legend")
    legend_frame.pack(pady=(0, 8), fill=tk.X)

    legend_items = [
        ("General Stats", "#1f77b4"),
        ("Area Fraction (Σ=100%)", "#2ca02c"),
        ("Avg Area (norm. size)", "#ff7f0e"),
        ("Pore Count (/parents >50μm)", "#9467bd"),
    ]

    for label_text, color_hex in legend_items:
        row = ttk.Frame(legend_frame)
        row.pack(fill=tk.X, padx=4, pady=1)
        color_box = tk.Canvas(
            row, width=12, height=12, bg=color_hex, highlightthickness=1, highlightbackground="gray"
        )
        color_box.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Label(row, text=label_text, font=("Arial", 8)).pack(side=tk.LEFT, anchor="w")

    ttk.Label(self.spectrum_frame_controls, text="Mosaics:").pack(anchor="w")

    # Scrollable, re-orderable list of mosaics
    list_container = ttk.Frame(self.spectrum_frame_controls)
    list_container.pack(fill=tk.BOTH, expand=True)

    self.spectrum_list_canvas = tk.Canvas(list_container, width=220, highlightthickness=0)
    list_scroll = ttk.Scrollbar(
        list_container, orient="vertical", command=self.spectrum_list_canvas.yview
    )
    self.spectrum_list_canvas.configure(yscrollcommand=list_scroll.set)
    self.spectrum_list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    self.spectrum_list_frame = ttk.Frame(self.spectrum_list_canvas)
    self.spectrum_list_window = self.spectrum_list_canvas.create_window(
        (0, 0), window=self.spectrum_list_frame, anchor="nw"
    )
    self.spectrum_list_frame.bind(
        "<Configure>",
        lambda e: self.spectrum_list_canvas.configure(
            scrollregion=self.spectrum_list_canvas.bbox("all")
        ),
    )
    self.spectrum_list_canvas.bind(
        "<Configure>",
        lambda e: self.spectrum_list_canvas.itemconfigure(self.spectrum_list_window, width=e.width),
    )

    # Right side: stacked column charts
    self.spectrum_frame_display = ttk.Frame(self.spectrum_frame)
    self.spectrum_frame_display.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    self.spectrum_canvas_holder = tk.Canvas(
        self.spectrum_frame_display, background="white", highlightthickness=0
    )
    display_v_scroll = ttk.Scrollbar(
        self.spectrum_frame_display, orient="vertical", command=self.spectrum_canvas_holder.yview
    )
    self.spectrum_canvas_holder.configure(yscrollcommand=display_v_scroll.set)
    self.spectrum_canvas_holder.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    display_v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    self.spectrum_figure = Figure(figsize=(8, 4), dpi=100)
    self.spectrum_canvas_agg = FigureCanvasTkAgg(
        self.spectrum_figure, master=self.spectrum_canvas_holder
    )
    self.spectrum_canvas_widget = self.spectrum_canvas_agg.get_tk_widget()
    self.spectrum_canvas_window = self.spectrum_canvas_holder.create_window(
        (0, 0), window=self.spectrum_canvas_widget, anchor="nw"
    )

    self.spectrum_canvas_holder.bind("<Configure>", lambda e: _spectrum_on_holder_resize(self))

    # Point 11: Enable mouse wheel scrolling on charts
    def _on_mousewheel(event):
        if event.num == 4:
            self.spectrum_canvas_holder.yview_scroll(-3, "units")
        elif event.num == 5:
            self.spectrum_canvas_holder.yview_scroll(3, "units")
        elif hasattr(event, "delta") and event.delta:
            amount = int(-1 * (event.delta / 120))
            if amount == 0:
                amount = -1 if event.delta > 0 else 1
            self.spectrum_canvas_holder.yview_scroll(amount * 3, "units")

    for widget in (self.spectrum_canvas_holder, self.spectrum_canvas_widget):
        widget.bind("<MouseWheel>", _on_mousewheel)
        widget.bind("<Button-4>", _on_mousewheel)
        widget.bind("<Button-5>", _on_mousewheel)

    _spectrum_redraw(self)


# --------------------------------------------------------------------------------------
# Aspect ratio controls
# --------------------------------------------------------------------------------------
def _format_aspect(value):
    if value <= 0:
        return "V/H = 0"
    return f"V/H = 1/{1.0 / value:.1f}"


def _spectrum_adjust_aspect(self, factor):
    new_value = self.spectrum_aspect * factor
    new_value = max(1.0 / 30.0, min(1.0, new_value))
    self.spectrum_aspect = new_value
    self.spectrum_aspect_var.set(_format_aspect(new_value))
    _spectrum_redraw(self)


# --------------------------------------------------------------------------------------
# Loading Global_Pore_Stats.xlsx and per-mosaic shape/size spreadsheets
# --------------------------------------------------------------------------------------
def _spectrum_load_stats(self):
    path = fd.askopenfilename(
        title="Select Global_Pore_Stats.xlsx",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
    )
    if not path:
        return

    self.spectrum_load_btn.config(state=tk.DISABLED)
    self.spectrum_loading_var.set("Loading...")

    def worker():
        try:
            entries = _spectrum_read_global_stats(path)
            base_dir = os.path.dirname(path)
            for entry in entries:
                entry.update(_spectrum_compute_mosaic_metrics(base_dir, entry["name"]))
        except Exception as e:
            self.root.after(0, lambda: _spectrum_load_failed(self, str(e)))
            return
        self.root.after(0, lambda: _spectrum_load_done(self, path, entries))

    threading.Thread(target=worker, daemon=True).start()


def _spectrum_load_failed(self, message):
    self.spectrum_load_btn.config(state=tk.NORMAL)
    self.spectrum_loading_var.set("")
    messagebox.showerror("Error", f"Failed to load Global_Pore_Stats.xlsx: {message}")


def _spectrum_load_done(self, path, entries):
    self.spectrum_stats_path = path
    self.spectrum_mosaics = [
        {**entry, "enabled": tk.BooleanVar(value=True)} for entry in entries
    ]
    self.spectrum_load_btn.config(state=tk.NORMAL)
    self.spectrum_loading_var.set(f"Loaded {len(self.spectrum_mosaics)} mosaic(s).")
    _spectrum_rebuild_list_ui(self)
    _spectrum_redraw(self)

def clean_float(value, default=0.0):
    """Convierte de forma segura textos con comas o puntos a float."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        val_str = str(value).strip().replace(",", ".")
        return float(val_str)
    except (ValueError, TypeError):
        return default


def _spectrum_read_global_stats(path):
    """Read mosaic names and global stats from Global_Pore_Stats.xlsx."""
    wb = opxl.load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()

    if not rows:
        return []

    header = [str(h).strip().lower() if h is not None else "" for h in rows[0]]

    def find_col(keywords, avoid=None):
        for i, h in enumerate(header):
            if avoid and any(a in h for a in avoid):
                continue
            if all(k in h for k in keywords):
                return i
        return None

    idx_name = find_col(["mosaic"]) or find_col(["name"])
    idx_porosity = find_col(["porosity"])
    idx_pct_gt50 = find_col([">", "50"], avoid=["number", "num", "count", "parent", "child"]) or find_col(
        ["percentage", "50"], avoid=["<"]
    )

    # Búsqueda específica para "Number of parent contours > 50μm"
    idx_parents_gt50 = (
        find_col(["parent", ">", "50"])
        or find_col(["parent", "50"], avoid=["<", "percentage", "%", "child"])
        or find_col(["parent"], avoid=["%", "<", "child"])
    )

    entries = []
    for row in rows[1:]:
        if not row or idx_name is None or idx_name >= len(row) or row[idx_name] is None:
            continue
        m_name = str(row[idx_name]).strip()
        if not m_name:
            continue

        porosity = clean_float(row[idx_porosity]) if (idx_porosity is not None and idx_porosity < len(row)) else 0.0
        pct_gt50 = clean_float(row[idx_pct_gt50]) if (idx_pct_gt50 is not None and idx_pct_gt50 < len(row)) else 0.0

        parents_val = 1.0
        if idx_parents_gt50 is not None and idx_parents_gt50 < len(row):
            parents_val = clean_float(row[idx_parents_gt50], default=1.0)

        entries.append(
            {
                "name": m_name,
                "porosity": porosity,
                "pct_gt50": pct_gt50,
                "parents_gt50": parents_val if parents_val > 0 else 1.0,
            }
        )
    return entries


def _spectrum_compute_mosaic_metrics(base_dir, name):
    """Compute area-fraction / average-area / count raw metrics for a single mosaic."""
    mosaic_dir = os.path.join(base_dir, name)
    tiff_path = os.path.join(mosaic_dir, name + ".tiff")
    h5_path = os.path.join(mosaic_dir, name + ".h5")

    image_area_um2 = None
    if os.path.exists(tiff_path):
        try:
            with Image.open(tiff_path) as img:
                width_px, height_px = img.size
            calibration = None
            if os.path.exists(h5_path):
                with h5py.File(h5_path, "r") as f:
                    calibration = f.attrs.get("pixel_calibration_px_per_um")
            if calibration:
                cal_val = clean_float(calibration, default=0.0)
                if cal_val > 0:
                    image_area_um2 = (width_px * height_px) / (cal_val**2)
        except Exception:
            image_area_um2 = None

    area_fraction_raw = {}
    avg_area_raw = {}
    count_raw = {}

    for shape in SHAPES:
        shape_path = os.path.join(mosaic_dir, f"{name}_{shape}.xlsx")
        if not os.path.exists(shape_path):
            for size in SIZES:
                area_fraction_raw[(shape, size)] = 0.0
                avg_area_raw[(shape, size)] = 0.0
                count_raw[(shape, size)] = 0.0
            continue

        wb = opxl.load_workbook(shape_path, data_only=True, read_only=True)
        try:
            for size in SIZES:
                sheet_name = f"{SIZE_SHEET_PREFIX}{size}"
                key = (shape, size)
                if sheet_name not in wb.sheetnames:
                    area_fraction_raw[key] = 0.0
                    avg_area_raw[key] = 0.0
                    count_raw[key] = 0.0
                    continue

                ws = wb[sheet_name]
                total_area = 0.0
                non_edge_areas = []
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row or row[0] is None:
                        continue
                    
                    # Uso de clean_float para manejar comas decimales
                    area = clean_float(row[2])
                    total_area += area
                    
                    is_edge = str(row[1]).strip().lower() in ("true", "1", "1.0", "yes", "si", "verdadero")
                    if not is_edge:
                        non_edge_areas.append(area)

                area_fraction_raw[key] = (total_area / image_area_um2) if image_area_um2 else 0.0
                avg_area_raw[key] = (
                    sum(non_edge_areas) / len(non_edge_areas) if non_edge_areas else 0.0
                )
                count_raw[key] = float(len(non_edge_areas))
        finally:
            wb.close()

    return {
        "area_fraction_raw": area_fraction_raw,
        "avg_area_raw": avg_area_raw,
        "count_raw": count_raw,
    }

# --------------------------------------------------------------------------------------
# Re-orderable / checkable mosaic list
# --------------------------------------------------------------------------------------
def _spectrum_rebuild_list_ui(self):
    for child in self.spectrum_list_frame.winfo_children():
        child.destroy()

    for index, entry in enumerate(self.spectrum_mosaics):
        row = tk.Frame(self.spectrum_list_frame, height=ROW_HEIGHT)
        row.pack(fill=tk.X)
        row.pack_propagate(False)

        handle = ttk.Label(row, text="⋮⋮", cursor="fleur")
        handle.pack(side=tk.LEFT, padx=(2, 6))
        handle.bind("<ButtonPress-1>", lambda e, i=index: _spectrum_start_drag(self, i))
        handle.bind("<B1-Motion>", lambda e: _spectrum_drag_motion(self, e))
        handle.bind("<ButtonRelease-1>", lambda e: _spectrum_end_drag(self, e))

        check = ttk.Checkbutton(
            row, variable=entry["enabled"], command=lambda: _spectrum_redraw(self)
        )
        check.pack(side=tk.LEFT, padx=(0, 4))

        ttk.Label(row, text=entry["name"]).pack(side=tk.LEFT, fill=tk.X, expand=True)

    self.spectrum_list_canvas.update_idletasks()
    self.spectrum_list_canvas.configure(scrollregion=self.spectrum_list_canvas.bbox("all"))


def _spectrum_start_drag(self, index):
    self._spectrum_drag_index = index


def _spectrum_drag_motion(self, event):
    if self._spectrum_drag_index is None:
        return
    rel_y = event.y_root - self.spectrum_list_frame.winfo_rooty()
    target = max(0, min(len(self.spectrum_mosaics) - 1, int(rel_y // ROW_HEIGHT)))
    if target != self._spectrum_drag_index:
        entry = self.spectrum_mosaics.pop(self._spectrum_drag_index)
        self.spectrum_mosaics.insert(target, entry)
        self._spectrum_drag_index = target
        _spectrum_rebuild_list_ui(self)


def _spectrum_end_drag(self, event):
    if self._spectrum_drag_index is not None:
        self._spectrum_drag_index = None
        _spectrum_redraw(self)


# --------------------------------------------------------------------------------------
# Data Preparation & Chart Rendering (1 Chart per Mosaic)
# --------------------------------------------------------------------------------------
def _spectrum_prepare_data(mosaics):
    """
    Builds the array of 50 column labels and calculated values rescaled to [0, 100].
    Categories:
      1. General stats (2 values: Porosity, % > 50μm)
      2. Area fraction (16 values: sum normalized to 1, then x100 -> sum=100%)
      3. Average pore area (16 values: normalized by size area, then x100)
      4. Pore count (16 values: divided by parents > 50μm, then x100)
    """
    combos = [(shape, size) for shape in SHAPES for size in SIZES]

    labels = []
    # 1. General stats (2)
    labels.extend(["Porosity", "% > 50μm"])

    # 2. Area fraction (16)
    for shape, size in combos:
        labels.append(f"AF {shape}-{size}")

    # 3. Avg area (16)
    for shape, size in combos:
        labels.append(f"AvgA {shape}-{size}")

    # 4. Count (16)
    for shape, size in combos:
        labels.append(f"Cnt {shape}-{size}")

    data_by_mosaic = {}
    for m in mosaics:
        vals = []

        # 1. General stats (Point 1 & 7)
        p = m["porosity"]
        p = p * 100.0 if p <= 1.0 else p
        gt = m["pct_gt50"]
        gt = gt * 100.0 if gt <= 1.0 else gt
        vals.extend([p, gt])

        # 2. Area fraction (Point 4 & 7: sum = 1, rescaled to 100%)
        sum_af = sum(m["area_fraction_raw"].get(c, 0.0) for c in combos)
        for c in combos:
            af_norm = (m["area_fraction_raw"].get(c, 0.0) / sum_af) if sum_af > 0 else 0.0
            vals.append(af_norm * 100.0)

        # 3. Avg area (Point 5 : normalized by size formula, rescaled to 100%)
        for shape, size in combos:
            avg_a = m["avg_area_raw"].get((shape, size), 0.0)
            norm_factor = NORM_AREA[size]
            a_norm = avg_a / norm_factor
            vals.append(a_norm * 100.0) 

        # 4. Pore count (Point 6 & 7: divided by parents > 50μm, rescaled to 100%)
        parents = m.get("parents_gt50", 1.0)
        parents = parents if parents > 0 else 1.0
        for c in combos:
            cnt = m["count_raw"].get(c, 0.0)
            cnt_norm = cnt / parents
            vals.append(cnt_norm * 100.0)

        data_by_mosaic[m["name"]] = vals

    return labels, data_by_mosaic


def _spectrum_on_holder_resize(self):
    if self._spectrum_redraw_after_id is not None:
        self.root.after_cancel(self._spectrum_redraw_after_id)
    self._spectrum_redraw_after_id = self.root.after(150, lambda: _spectrum_redraw(self))


def _spectrum_apply_figure_size(self, rows):
    self.spectrum_canvas_holder.update_idletasks()
    width_px = self.spectrum_canvas_holder.winfo_width()
    if width_px <= 1:
        width_px = 800
    dpi = self.spectrum_figure.get_dpi()
    width_in = width_px / dpi

    # Asegura un mínimo de 1.5 pulgadas por cada subplot (rows)
    min_height_per_row = 1.5
    height_in = max(width_in * self.spectrum_aspect * rows, min_height_per_row * rows)

    self.spectrum_figure.set_size_inches(width_in, height_in, forward=True)
    self.spectrum_canvas_widget.configure(width=width_px, height=int(height_in * dpi))


def _spectrum_update_scrollregion(self):
    self.spectrum_canvas_holder.update_idletasks()
    self.spectrum_canvas_holder.itemconfigure(
        self.spectrum_canvas_window, width=self.spectrum_canvas_holder.winfo_width()
    )
    self.spectrum_canvas_holder.configure(
        scrollregion=self.spectrum_canvas_holder.bbox(self.spectrum_canvas_window)
    )


def _spectrum_show_message(self, message):
    fig = self.spectrum_figure
    ax = fig.add_subplot(111)
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=10)
    ax.axis("off")
    _spectrum_apply_figure_size(self, 1)
    self.spectrum_canvas_agg.draw()
    _spectrum_update_scrollregion(self)


def _spectrum_redraw(self):
    if self._spectrum_redraw_after_id is not None:
        self.root.after_cancel(self._spectrum_redraw_after_id)
        self._spectrum_redraw_after_id = None

    self.spectrum_figure.clear()

    if not self.spectrum_mosaics:
        _spectrum_show_message(self, "Load Global_Pore_Stats.xlsx to begin.")
        return

    visible_mosaics = [m for m in self.spectrum_mosaics if m["enabled"].get()]
    if not visible_mosaics:
        _spectrum_show_message(self, "No mosaics selected for display.")
        return

    labels, data_by_mosaic = _spectrum_prepare_data(self.spectrum_mosaics)
    n_mosaics = len(visible_mosaics)

    axes = self.spectrum_figure.subplots(n_mosaics, 1, sharex=True)
    if n_mosaics == 1:
        axes = [axes]

    # Category bar colors: Blue (General), Green (Area Fraction), Orange (Avg Area), Purple (Count)
    bar_colors = ["#1f77b4"] * 2 + ["#2ca02c"] * 16 + ["#ff7f0e"] * 16 + ["#9467bd"] * 16
    x = list(range(len(labels)))

    for idx, m in enumerate(visible_mosaics):
        ax = axes[idx]
        vals = data_by_mosaic.get(m["name"], [0.0] * len(labels))
        bars = ax.bar(x, vals, color=bar_colors, width=0.8)

        max_v = max(vals) if vals else 0.0
        top_limit = max(100.0, max_v * 1.30)
        ax.set_ylim(0, top_limit)

        # Point 10: Show only mosaic name in subplot title
        ax.set_title(m["name"], fontsize=9, loc="left", fontweight="bold")
        ax.tick_params(axis="y", labelsize=7)
        ax.margins(x=0.01)

        # Point 8: Value label above each bar
        bar_text_labels = [f"{v:.1f}" if v >= 0.05 else "" for v in vals]
        ax.bar_label(bars, labels=bar_text_labels, padding=2, fontsize=9, rotation=0)

        # Point 2: Group separators & dotted lines separating XL from S
        # Major group separators (dashed)
        ax.axvline(1.5, color="black", linestyle="--", linewidth=1.0, alpha=0.7)
        ax.axvline(17.5, color="black", linestyle="--", linewidth=1.0, alpha=0.7)
        ax.axvline(33.5, color="black", linestyle="--", linewidth=1.0, alpha=0.7)

        # Subgroup separators between XL and S of next shape (dotted)
        sub_lines = [5.5, 9.5, 13.5, 21.5, 25.5, 29.5, 37.5, 41.5, 45.5]
        for sx in sub_lines:
            ax.axvline(sx, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)

        # Tick labels on bottom axis
        if idx == n_mosaics - 1:
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=90, ha="center", fontsize=9)
            ax.tick_params(axis="x", labelbottom=True)
        else:
            ax.set_xticks(x)
            ax.tick_params(axis="x", labelbottom=False)

    self.spectrum_figure.subplots_adjust(
    left=0.05,    # Margen izquierdo (para valores del eje Y)
    right=0.98,   # Margen derecho
    top=0.97,     # Margen superior
    bottom=0.18,  # Margen inferior (espacio para las 50 etiquetas rotadas a 90°)
    hspace=0.15   # Separación vertical entre subplots (valores menores = más juntos)
)

    _spectrum_apply_figure_size(self, n_mosaics)
    self.spectrum_canvas_agg.draw()
    _spectrum_update_scrollregion(self)