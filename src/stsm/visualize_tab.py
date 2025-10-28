import tkinter as tk
from tkinter import ttk
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import h5py
import threading
import os


def visualize_tab(self):
    # State variables for this tab
    self.vis_binary_image = None  # numpy grayscale image
    self.vis_display_image = None  # color image for drawing overlays
    self.vis_tk_image = None
    self.vis_scale = 1.0  # base scale to fit canvas (updated per render)
    self.vis_zoom = 1.0   # user zoom multiplier
    self.vis_pan_x = 0    # pan in screen pixels
    self.vis_pan_y = 0
    self.vis_image_pos = (0, 0)
    self.vis_h5_path = None
    self.vis_pore_ids = []
    self.vis_loading_var = tk.StringVar(value="")
    self.vis_line_thickness_var = tk.IntVar(value=2)
    # Contours currently selected (original image coordinates)
    self._vis_parent_contour = None
    self._vis_children_contours = []
    # Render throttle state
    self._vis_render_scheduled = False
    self._vis_render_after_id = None

    # Left controls
    self.visualize_frame_controls = ttk.Frame(self.visualize_frame)
    self.visualize_frame_controls.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

    # Load HDF5 button
    self.vis_load_h5_btn = ttk.Button(
        self.visualize_frame_controls,
        text="Load .h5",
        command=lambda: _vis_load_h5(self)
    )
    self.vis_load_h5_btn.pack(pady=4, fill=tk.X)

    # Load Binary Image button
    self.vis_load_img_btn = ttk.Button(
        self.visualize_frame_controls,
        text="Load Binary Image",
        command=lambda: _vis_load_binary(self)
    )
    self.vis_load_img_btn.pack(pady=4, fill=tk.X)

    # Pore id selection
    ttk.Label(self.visualize_frame_controls, text="Pore_id:").pack(pady=(12, 2))
    self.vis_pore_id_var = tk.StringVar()
    # Allow typing for large datasets; we'll populate values only up to a threshold
    self.vis_pore_id_combo = ttk.Combobox(
        self.visualize_frame_controls,
        textvariable=self.vis_pore_id_var,
        values=[],
        state="normal"
    )
    self.vis_pore_id_combo.pack(pady=2, fill=tk.X)
    # Trigger show on Enter
    self.vis_pore_id_combo.bind("<Return>", lambda e: _vis_show_contour(self))

    self.vis_show_btn = ttk.Button(
        self.visualize_frame_controls,
        text="Show Contour",
        command=lambda: _vis_show_contour(self)
    )
    self.vis_show_btn.pack(pady=8, fill=tk.X)

    # Line thickness control
    row_lt = ttk.Frame(self.visualize_frame_controls)
    row_lt.pack(fill=tk.X, pady=(6, 2))
    ttk.Label(row_lt, text="Line width:", width=12).pack(side=tk.LEFT)
    self.vis_line_thickness_spin = ttk.Spinbox(
        row_lt,
        from_=1,
        to=10,
        textvariable=self.vis_line_thickness_var,
        width=5,
        command=lambda: _vis_update_display(self)
    )
    self.vis_line_thickness_spin.pack(side=tk.LEFT)
    self.vis_line_thickness_spin.bind("<Return>", lambda e: _vis_update_display(self))

    # Loading indicator
    self.vis_loading_label = ttk.Label(self.visualize_frame_controls, textvariable=self.vis_loading_var, foreground="gray")
    self.vis_loading_label.pack(pady=(8, 0), fill=tk.X)

    # View controls: Fit and Reset
    vc = ttk.Frame(self.visualize_frame_controls)
    vc.pack(fill=tk.X, pady=(10, 0))
    ttk.Button(vc, text="Fit", command=lambda: _vis_fit(self)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
    ttk.Button(vc, text="Reset", command=lambda: _vis_reset(self)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

    # Right area: canvas + stats panel
    self.visualize_frame_images = ttk.Frame(self.visualize_frame)
    self.visualize_frame_images.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # Split right area into canvas (left) and stats (right)
    self.vis_right_container = ttk.Frame(self.visualize_frame_images)
    self.vis_right_container.pack(fill=tk.BOTH, expand=True)
    self.vis_right_container.columnconfigure(0, weight=1)
    self.vis_right_container.rowconfigure(0, weight=1)

    # Canvas for image
    self.vis_canvas = tk.Canvas(self.vis_right_container, background="black")
    self.vis_canvas.grid(row=0, column=0, sticky="nsew")

    self.vis_no_image_label = ttk.Label(
        self.vis_canvas,
        text="No image loaded. Load .h5 and its binary image.",
        background="white"
    )
    self.vis_canvas.create_window(400, 300, window=self.vis_no_image_label)

    # Bind zoom and pan
    self.vis_canvas.bind("<MouseWheel>", lambda e: _vis_on_wheel(self, e))  # Windows
    # Pan with right mouse button (existing)
    self.vis_canvas.bind("<ButtonPress-3>", lambda e: _vis_pan_start(self, e))
    self.vis_canvas.bind("<B3-Motion>", lambda e: _vis_pan_move(self, e))
    self.vis_canvas.bind("<ButtonRelease-3>", lambda e: _vis_pan_end(self, e))
    # Also pan with left mouse button
    self.vis_canvas.bind("<ButtonPress-1>", lambda e: _vis_pan_start(self, e))
    self.vis_canvas.bind("<B1-Motion>", lambda e: _vis_pan_move(self, e))
    self.vis_canvas.bind("<ButtonRelease-1>", lambda e: _vis_pan_end(self, e))

    # Stats panel
    self.vis_stats = ttk.LabelFrame(self.vis_right_container, text="Stats")
    self.vis_stats.grid(row=0, column=1, sticky="ns", padx=(8, 0), pady=4)

    # Stats labels
    self._vis_stat_vars = {
        "index": tk.StringVar(value="-"),
        "is_edge": tk.StringVar(value="-"),
        "area": tk.StringVar(value="-"),
        "perimeter": tk.StringVar(value="-"),
        "num_children": tk.StringVar(value="-"),
    }

    for key, label in [
        ("index", "Pore_id"),
        ("is_edge", "Is Edge"),
        ("area", "Area (px^2)"),
        ("perimeter", "Perimeter (px)"),
        ("num_children", "# Children"),
    ]:
        row = ttk.Frame(self.vis_stats)
        row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(row, text=f"{label}:", width=16).pack(side=tk.LEFT)
        ttk.Label(row, textvariable=self._vis_stat_vars[key]).pack(side=tk.LEFT)


def _vis_load_h5(self):
    path = fd.askopenfilename(title="Select HDF5 file", filetypes=[("HDF5 files", "*.h5"), ("All files", "*.*")])
    if not path:
        return

    # Disable controls and show loading text
    _vis_set_controls_state(self, tk.DISABLED)
    self.vis_loading_var.set("Loading HDF5...")

    def worker():
        try:
            with h5py.File(path, 'r') as f:
                if "contours" not in f:
                    raise RuntimeError("Invalid H5: 'contours' group not found.")
                ids = list(f["contours"].keys())
        except Exception as e:
            self.root.after(0, lambda: [
                messagebox.showerror("Error", f"Failed to load H5: {e}"),
                self.vis_loading_var.set(""),
                _vis_set_controls_state(self, tk.NORMAL)
            ])
            return

        def on_done():
            self.vis_h5_path = path
            # If huge, avoid populating combobox values to keep UI responsive
            self.vis_pore_ids = sorted(ids, key=lambda s: int(s) if str(s).isdigit() else s)
            if len(self.vis_pore_ids) <= 500:
                self.vis_pore_id_combo["values"] = self.vis_pore_ids
                if self.vis_pore_ids:
                    self.vis_pore_id_combo.current(0)
            else:
                self.vis_pore_id_combo["values"] = []  # act as free-entry
                self.vis_pore_id_combo.set("")
            _vis_try_autoload_binary(self)
            self.vis_loading_var.set("")
            _vis_set_controls_state(self, tk.NORMAL)

        self.root.after(0, on_done)

    threading.Thread(target=worker, daemon=True).start()


def _vis_try_autoload_binary(self):
    if not self.vis_h5_path:
        return
    base, _ = os.path.splitext(self.vis_h5_path)
    for ext in [".tiff", ".tif", ".png", ".bmp", ".jpg", ".jpeg"]:
        cand = base + ext
        if os.path.exists(cand):
            img = cv2.imread(cand, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                self.vis_binary_image = img
                _vis_update_display(self)
            return


def _vis_load_binary(self):
    path = fd.askopenfilename(title="Select binary image", filetypes=[
        ("Image files", "*.tiff *.tif *.png *.bmp *.jpg *.jpeg"),
        ("All files", "*.*")
    ])
    if not path:
        return
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        messagebox.showerror("Error", "Failed to load image.")
        return
    self.vis_binary_image = img
    _vis_update_display(self)


def _vis_show_contour(self):
    if self.vis_h5_path is None:
        messagebox.showwarning("Warning", "Load the .h5 file first.")
        return
    if self.vis_binary_image is None:
        messagebox.showwarning("Warning", "Load the binary image.")
        return
    pore_id = self.vis_pore_id_var.get()
    if not pore_id:
        messagebox.showwarning("Warning", "Select a Pore_id.")
        return
    try:
        with h5py.File(self.vis_h5_path, 'r') as f:
            if "contours" not in f or pore_id not in f["contours"]:
                raise KeyError(f"Pore_id '{pore_id}' not found in H5")
            cg = f["contours"][pore_id]
            # Read stats
            idx = int(cg.attrs.get('index', int(pore_id)))
            is_edge = bool(cg.attrs.get('is_edge', False))
            area = float(cg.attrs.get('area', 0.0))
            perimeter = float(cg.attrs.get('perimeter', 0.0))
            num_children = int(cg.attrs.get('num_children', 0))

            # Read parent contour points
            parent = np.array(cg['parent'][:]) if 'parent' in cg else None
            # Read children
            children = []
            if 'children' in cg:
                chg = cg['children']
                for key in chg.keys():
                    children.append(np.array(chg[key][:]))

        # Ensure correct contour shapes and dtypes
        def _as_contour(arr):
            if arr is None:
                return None
            c = np.asarray(arr)
            if c.ndim == 2 and c.shape[1] == 2:
                c = c.reshape(-1, 1, 2)
            c = c.astype(np.int32)
            return c

        p_contour = _as_contour(parent)
        ch_contours = [_as_contour(c) for c in children]

        # Store contours for viewport rendering
        self._vis_parent_contour = p_contour
        self._vis_children_contours = [c for c in ch_contours if c is not None]
        # Discard any precomposed display image to avoid stale state
        self.vis_display_image = None

        # Update stats panel
        self._vis_stat_vars['index'].set(str(idx))
        self._vis_stat_vars['is_edge'].set("Yes" if is_edge else "No")
        self._vis_stat_vars['area'].set(f"{area:.2f}")
        self._vis_stat_vars['perimeter'].set(f"{perimeter:.2f}")
        self._vis_stat_vars['num_children'].set(str(num_children))

        # Auto-zoom to pore with 20% padding
        bbox = _vis_compute_bbox(p_contour, ch_contours)
        if bbox is not None:
            _vis_focus_bbox(self, bbox, padding=0.2)
        _vis_update_display(self)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to show contour: {e}")


def _vis_update_display(self):
    # We always render from the binary image and draw contours for the visible viewport only
    if self.vis_binary_image is None:
        return

    # Hide no-image label and clear canvas
    try:
        self.vis_no_image_label.place_forget()
    except Exception:
        pass
    self.vis_canvas.delete("all")

    # Canvas size (fallback if not ready)
    cw = self.vis_canvas.winfo_width() or 800
    ch = self.vis_canvas.winfo_height() or 600
    if cw <= 1:
        cw = 800
    if ch <= 1:
        ch = 600

    h, w = self.vis_binary_image.shape[:2]
    base_scale = min(cw / w, ch / h)
    self.vis_scale = base_scale
    scale = base_scale * max(0.1, min(self.vis_zoom, 20.0))

    # Image position in canvas (top-left of the full image if fully drawn)
    x_pos = (cw - w * scale) / 2 + self.vis_pan_x
    y_pos = (ch - h * scale) / 2 + self.vis_pan_y
    self.vis_image_pos = (int(x_pos), int(y_pos))

    # Compute visible image rectangle in image coords
    x1_img = int(max(0, (0 - x_pos) / scale))
    y1_img = int(max(0, (0 - y_pos) / scale))
    x2_img = int(min(w, (cw - x_pos) / scale))
    y2_img = int(min(h, (ch - y_pos) / scale))

    if x2_img <= x1_img or y2_img <= y1_img:
        return

    # Destination rectangle in canvas coords
    dest_x1 = int(max(0, x_pos))
    dest_y1 = int(max(0, y_pos))
    dest_w = int((x2_img - x1_img) * scale)
    dest_h = int((y2_img - y1_img) * scale)
    # Clip to canvas
    dest_w = max(1, min(dest_w, cw - dest_x1))
    dest_h = max(1, min(dest_h, ch - dest_y1))

    # Prepare resized crop
    crop = self.vis_binary_image[y1_img:y2_img, x1_img:x2_img]
    # Resize to destination size
    resized = cv2.resize(crop, (dest_w, dest_h), interpolation=cv2.INTER_NEAREST)
    dest_bgr = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)

    # Draw contours transformed into the cropped-resized space
    thickness = int(self.vis_line_thickness_var.get() or 2)
    sx = scale
    sy = scale
    # Because we've resized the crop to (dest_w,dest_h) using scale sx/sy, each image point (x,y)
    # maps to ((x - x1_img)*sx, (y - y1_img)*sy) in dest_bgr coords.
    def _transform_contour(cont):
        if cont is None:
            return None
        pts = cont.reshape(-1, 2).astype(np.float64)
        pts[:, 0] = (pts[:, 0] - x1_img) * sx
        pts[:, 1] = (pts[:, 1] - y1_img) * sy
        pts = np.round(pts).astype(np.int32).reshape(-1, 1, 2)
        return pts

    pc = _transform_contour(self._vis_parent_contour)
    chs = [c for c in ([_transform_contour(c) for c in self._vis_children_contours] if self._vis_children_contours else []) if c is not None]

    if pc is not None and len(pc) >= 2:
        cv2.drawContours(dest_bgr, [pc], -1, (255, 0, 0), thickness)
    for ch in chs:
        if len(ch) >= 2:
            cv2.drawContours(dest_bgr, [ch], -1, (0, 255, 0), thickness)

    # Convert to Tk image and draw at destination position
    pil = Image.fromarray(cv2.cvtColor(dest_bgr, cv2.COLOR_BGR2RGB))
    tkimg = ImageTk.PhotoImage(pil)
    self.vis_tk_image = tkimg
    self.vis_canvas.create_image(dest_x1, dest_y1, anchor=tk.NW, image=tkimg)


def _vis_schedule_render(self, delay_ms=50):
    # Throttle rendering to avoid excessive redraws during wheel/pan
    if self._vis_render_scheduled:
        # Already scheduled; no need to schedule another
        return
    self._vis_render_scheduled = True
    def _do():
        self._vis_render_scheduled = False
        _vis_update_display(self)
    # Cancel previous after if any
    try:
        if self._vis_render_after_id is not None:
            self.root.after_cancel(self._vis_render_after_id)
    except Exception:
        pass
    self._vis_render_after_id = self.root.after(delay_ms, _do)


def _vis_compute_bbox(parent_contour, children_contours):
    # parent_contour shape: (N,1,2); children list of same
    points = []
    if parent_contour is not None:
        points.append(parent_contour.reshape(-1, 2))
    for ch in children_contours or []:
        if ch is not None:
            points.append(ch.reshape(-1, 2))
    if not points:
        return None
    all_pts = np.vstack(points)
    x_min, y_min = np.min(all_pts[:, 0]), np.min(all_pts[:, 1])
    x_max, y_max = np.max(all_pts[:, 0]), np.max(all_pts[:, 1])
    return (int(x_min), int(y_min), int(x_max), int(y_max))


def _vis_focus_bbox(self, bbox, padding=0.2):
    # bbox: (x1,y1,x2,y2) in image coords
    if self.vis_binary_image is None:
        return
    cw = self.vis_canvas.winfo_width() or 800
    ch = self.vis_canvas.winfo_height() or 600
    if cw <= 1:
        cw = 800
    if ch <= 1:
        ch = 600

    x1, y1, x2, y2 = bbox
    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)
    # Apply padding
    pad_x = int(bw * padding)
    pad_y = int(bh * padding)
    bw_p = bw + 2 * pad_x
    bh_p = bh + 2 * pad_y

    h, w = self.vis_binary_image.shape[:2]
    # Compute base scale
    base_scale = min(cw / w, ch / h)
    # Desired scale so bbox fits
    desired_scale = min(cw / bw_p, ch / bh_p)
    # Convert to zoom multiplier (clamped)
    self.vis_zoom = max(0.1, min(20.0, desired_scale / base_scale))

    # Center bbox center
    cx = x1 + bw / 2
    cy = y1 + bh / 2
    scale = base_scale * self.vis_zoom
    nw, nh = w * scale, h * scale
    x_pos = (cw - nw) / 2
    y_pos = (ch - nh) / 2
    # Current screen position of bbox center without pan
    screen_cx = x_pos + cx * scale
    screen_cy = y_pos + cy * scale
    # Set pan so that center goes to canvas center (reset, not incremental)
    self.vis_pan_x = (cw / 2 - screen_cx)
    self.vis_pan_y = (ch / 2 - screen_cy)


def _vis_on_wheel(self, event):
    if self.vis_binary_image is None:
        return
    # Zoom towards mouse position
    delta = 1.1 if event.delta > 0 else 1/1.1
    old_zoom = self.vis_zoom
    new_zoom = min(20.0, max(0.1, self.vis_zoom * delta))
    if abs(new_zoom - old_zoom) < 1e-6:
        return

    # Compute base values
    cw = self.vis_canvas.winfo_width() or 800
    ch = self.vis_canvas.winfo_height() or 600
    h, w = self.vis_binary_image.shape[:2]
    base_scale = min(cw / w, ch / h)
    old_scale = base_scale * old_zoom
    new_scale = base_scale * new_zoom

    # Anchor zoom at mouse (keep point under cursor stable)
    # Compute image coords under cursor
    x_pos = (cw - w * old_scale) / 2 + self.vis_pan_x
    y_pos = (ch - h * old_scale) / 2 + self.vis_pan_y
    if old_scale > 0:
        img_x = (event.x - x_pos) / old_scale
        img_y = (event.y - y_pos) / old_scale
    else:
        img_x = w / 2
        img_y = h / 2

    # After zoom, compute where that image point would land, adjust pan to keep it
    x_pos_new = (cw - w * new_scale) / 2 + self.vis_pan_x
    y_pos_new = (ch - h * new_scale) / 2 + self.vis_pan_y
    screen_x_new = x_pos_new + img_x * new_scale
    screen_y_new = y_pos_new + img_y * new_scale
    self.vis_pan_x += (event.x - screen_x_new)
    self.vis_pan_y += (event.y - screen_y_new)

    self.vis_zoom = new_zoom
    _vis_schedule_render(self)


def _vis_pan_start(self, event):
    self._vis_dragging = True
    self._vis_last_x = event.x
    self._vis_last_y = event.y


def _vis_pan_move(self, event):
    if not getattr(self, '_vis_dragging', False):
        return
    dx = event.x - self._vis_last_x
    dy = event.y - self._vis_last_y
    self._vis_last_x = event.x
    self._vis_last_y = event.y
    self.vis_pan_x += dx
    self.vis_pan_y += dy
    _vis_schedule_render(self)


def _vis_pan_end(self, event):
    self._vis_dragging = False


def _vis_fit(self):
    # Fit whole image to canvas
    self.vis_zoom = 1.0
    self.vis_pan_x = 0
    self.vis_pan_y = 0
    _vis_update_display(self)


def _vis_reset(self):
    # Reset zoom/pan to default fit and clear any selection centering
    _vis_fit(self)


def _vis_set_controls_state(self, state):
    for w in [self.vis_load_h5_btn, self.vis_load_img_btn, self.vis_pore_id_combo, self.vis_show_btn]:
        try:
            w.config(state=state)
        except Exception:
            pass
