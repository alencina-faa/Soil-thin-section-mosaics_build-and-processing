import tkinter as tk
from tkinter import ttk
from load_save import load_image, save_image
from display import update_display

def binary_tab(self):
    # Create a frame for controls
    self.binary_frame_controls = ttk.Frame(self.binary_frame)
    self.binary_frame_controls.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

    # Create a button to load images        
    self.load_button = ttk.Button(
        self.binary_frame_controls, 
        text="Load Images", 
        command= lambda: load_image(self)
    )
    self.load_button.pack(pady=5, padx=60)
    
    # Create a unified layer control frame - but don't pack it yet
    self.unified_layer_frame = ttk.LabelFrame(self.binary_frame_controls, text="Layer Controls")
    # We'll pack this after images are loaded
    
    # Create individual layer control rows
    self.layer_rows = []
    for i, name in enumerate(self.layer_names):
        # Create a frame for this layer's controls
        layer_frame = ttk.Frame(self.unified_layer_frame)
        layer_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Add visibility checkbutton
        visibility_cb = ttk.Checkbutton(
            layer_frame,
            variable=self.layer_visibility[i],
            command= lambda: update_display(self)
        )
        visibility_cb.pack(side=tk.LEFT, padx=(0, 5))
        
        # Add layer name label
        layer_label = ttk.Label(layer_frame, text=name, width=15)
        layer_label.pack(side=tk.LEFT, padx=5)
        
        # Add move up button
        up_button = ttk.Button(
            layer_frame, 
            text="↑", 
            width=2,
            command=lambda idx=i: self.move_layer_up_by_index(idx)
        )
        up_button.pack(side=tk.LEFT, padx=2)
        
        # Add move down button
        down_button = ttk.Button(
            layer_frame, 
            text="↓", 
            width=2,
            command=lambda idx=i: self.move_layer_down_by_index(idx)
        )
        down_button.pack(side=tk.LEFT, padx=2)
        
        # Store references to this layer's controls
        self.layer_rows.append({
            'frame': layer_frame,
            'visibility': visibility_cb,
            'label': layer_label,
            'up_button': up_button,
            'down_button': down_button
        })

    # Create save button frame - but don't pack it yet
    self.save_frame = ttk.Frame(self.binary_frame_controls)
    
    # Add save button
    self.save_button = ttk.Button(
        self.save_frame,
        text="Save Binary mosaic",
        command= lambda: save_image(self)
    )
    self.save_button.pack(pady=5)
    
    # Create a frame for image display
    self.binary_frame_images = ttk.Frame(self.binary_frame)
    self.binary_frame_images.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    # Create a canvas for displaying images
    self.canvas = tk.Canvas(self.binary_frame_images)
    self.canvas.pack(fill=tk.BOTH, expand=True)
    
    # Add a label to show when no images are loaded
    self.no_image_label = ttk.Label(
        self.canvas, 
        text="No images loaded. Click 'Load Images' to begin.",
    )
    
    self.canvas.create_window(640, 360, window=self.no_image_label)