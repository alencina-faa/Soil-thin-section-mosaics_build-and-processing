import tkinter as tk
from tkinter import ttk
from load_save import load_mosaic, save_proc_image, save_original_binary, save_mosaic_stats_data
from display import update_proc_display
from roi import confirm_roi

def processing_tab(self):
    # Create a frame for controls
    self.processing_frame_controls = ttk.Frame(self.processing_frame)
    self.processing_frame_controls.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)       

    # Add label and input for Image pixel calibration
    self.pixel_cal_label = ttk.Label(
        self.processing_frame_controls,
        text='Pixel calibration (pixel/\u03bcm):',
    )
    self.pixel_cal_label.pack(pady=(0, 5))
    
    self.pixel_cal = tk.StringVar(value="0.3051")  
    self.pixel_cal_input = ttk.Entry(
        self.processing_frame_controls,
        textvariable=self.pixel_cal,
        width=7,
        justify=tk.CENTER
    )
    self.pixel_cal_input.pack(pady=(0, 5))
    
    # Create a button to load the mosaic to be processed
    self.load_mosaic_button = ttk.Button(
        self.processing_frame_controls, 
        text="Load Image", 
        command= lambda: load_mosaic(self)
    )
    self.load_mosaic_button.pack(pady=5)
    
    # Create a button to confirm ROI selection
    self.confirm_roi_button = ttk.Button(
        self.processing_frame_controls,
        text="Confirm ROI",
        command= lambda: confirm_roi(self),
        state=tk.DISABLED  # Initially disabled
    )
    self.confirm_roi_button.pack(pady=5)
    
    # Create a unified layer control frame for processing tab - but don't pack it yet
    self.proc_unified_layer_frame = ttk.LabelFrame(self.processing_frame_controls, text="Layer Controls")
    
    # Create individual layer control rows for processing tab
    self.proc_layer_rows = []
    for i, name in enumerate(self.proc_layer_names):
        # Create a frame for this layer's controls
        layer_frame = ttk.Frame(self.proc_unified_layer_frame)
        layer_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Add visibility checkbutton
        visibility_cb = ttk.Checkbutton(
            layer_frame,
            variable=self.proc_layer_visibility[i],
            command= lambda: update_proc_display(self)
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
            command=lambda idx=i: self.move_proc_layer_up_by_index(idx)
        )
        up_button.pack(side=tk.LEFT, padx=2)
        
        # Add move down button
        down_button = ttk.Button(
            layer_frame, 
            text="↓", 
            width=2,
            command=lambda idx=i: self.move_proc_layer_down_by_index(idx)
        )
        down_button.pack(side=tk.LEFT, padx=2)
        
        # Store references to this layer's controls
        self.proc_layer_rows.append({
            'frame': layer_frame,
            'visibility': visibility_cb,
            'label': layer_label,
            'up_button': up_button,
            'down_button': down_button
        })
    
    # Create save buttons frame for processing tab - but don't pack it yet
    self.proc_save_frame = ttk.Frame(self.processing_frame_controls)
    
    # Add save buttons for each processed image
    self.save_small_contours_button = ttk.Button(
        self.proc_save_frame,
        text="Save Image of Pores \u2264 50μm",
        command=lambda: save_proc_image(self, 0)
    )
    self.save_small_contours_button.pack(pady=2)
    
    self.save_large_contours_button = ttk.Button(
        self.proc_save_frame,
        text="Save Image of Pores > 50μm",
        command=lambda: save_proc_image(self, 1)
    )
    self.save_large_contours_button.pack(pady=2)
    
    self.save_all_contours_button = ttk.Button(
        self.proc_save_frame,
        text="Save Image of All Contours",
        command=lambda: save_proc_image(self, 2)
    )
    self.save_all_contours_button.pack(pady=2)
    
    # Add a button to save the original binary image without contours
    # self.save_original_binary_button = ttk.Button(
    #     self.proc_save_frame,
    #     text="Save Original Binary",
    #     command= lambda: save_original_binary(self)
    # )
    # self.save_original_binary_button.pack(pady=2)

    # Create a buton to save Global Pore Stats
    self.save_mosaic_stats_data_button = ttk.Button(
        self.proc_save_frame,
        text="Save Stats & Data",
        command = lambda: save_mosaic_stats_data(self)
    )
    self.save_mosaic_stats_data_button.pack(pady=2)
    
    # Create a frame for image display in processing tab
    self.processing_frame_images = ttk.Frame(self.processing_frame)
    self.processing_frame_images.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    # Create a canvas for displaying images in processing tab
    self.proc_canvas = tk.Canvas(self.processing_frame_images)
    self.proc_canvas.pack(fill=tk.BOTH, expand=True)
    
    # Add a label to show when no images are loaded in processing tab
    self.proc_no_image_label = ttk.Label(
        self.proc_canvas, 
        text="No Image loaded. Click 'Load Image' to begin.",
    )
    
    self.proc_canvas.create_window(640, 360, window=self.proc_no_image_label)
    
    # Add ROI instruction label (initially hidden)
    self.roi_instruction_label = ttk.Label(
        self.proc_canvas,
        text="Click and drag to select ROI. Press Enter to confirm.",
        background="white",
        foreground="black",
        padding=5
    )
    self.roi_instruction_window = None