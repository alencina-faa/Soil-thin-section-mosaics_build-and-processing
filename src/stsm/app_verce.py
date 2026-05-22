import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.filedialog as fd
import cv2
import numpy as np
from PIL import Image, ImageTk
import os

class stsmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Soil Thin Section Mosaics: build & analysis")
        self.root.geometry("1280x720")
        
        # Initialize image variables and control flags
        self.images = []
        self.tk_images = []
        self.layer_visibility = [tk.BooleanVar(value=True) for _ in range(3)]
        self.layer_order = [2, 0, 1]  # Default order: binary mosaic, mosaic 1, mosaic 2
        self.controls_visible = False
        self.layer_names = ["Mosaic 1", "Mosaic 2", "Binary mosaic"]
        
        # Initialize processing tab variables
        self.proc_images = []  # Original, contours < 50, contours > 50
        self.proc_tk_images = []
        self.proc_layer_visibility = [tk.BooleanVar(value=True) for _ in range(3)]
        self.proc_layer_order = [0, 1, 2]  # Default order: Original, pores <= 50, pores > 50
        self.proc_controls_visible = False
        self.proc_layer_names = ["Original", "Pore \u2264 50μm", "Pore > 50μm"]
        self.original_image = None  # Store the original image before ROI selection
        
        # ROI selection variables
        self.roi_mode = False
        self.roi_start_x = None
        self.roi_start_y = None
        self.roi_rect = None
        self.roi_image = None
        self.roi_scale = 1.0
        self.roi_tk_image = None  # Store reference to prevent garbage collection
        
        # Create notebook (tab container)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create the tabs
        self.acquire_frame = ttk.Frame(self.notebook)
        self.build_frame = ttk.Frame(self.notebook)
        self.align_frame = ttk.Frame(self.notebook)
        self.binary_frame = ttk.Frame(self.notebook)
        self.processing_frame = ttk.Frame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(self.acquire_frame, text="Acquire")
        self.notebook.add(self.build_frame, text="Build")
        self.notebook.add(self.align_frame, text="Align")
        self.notebook.add(self.binary_frame, text="Binary")
        self.notebook.add(self.processing_frame, text="Processing")
        
        # Setup the Binary tab
        self.binary_tab()

        # Setup the Processing tab
        self.processing_tab()
#Ends the mainwindow definitions

#STARTS THE TABS DEFINITIONS
# Setup the binary tab
    def binary_tab(self):
        # Create a frame for controls
        self.binary_frame_controls = ttk.Frame(self.binary_frame)
        self.binary_frame_controls.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Create a button to load images        
        self.load_button = ttk.Button(
            self.binary_frame_controls, 
            text="Load Images", 
            command=self.load_image
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
                command=self.update_display
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
            command=self.save_image
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
            text="Load Mosaic", 
            command=self.load_mosaic
        )
        self.load_mosaic_button.pack(pady=5)
        
        # Create a button to confirm ROI selection
        self.confirm_roi_button = ttk.Button(
            self.processing_frame_controls,
            text="Confirm ROI",
            command=self.confirm_roi,
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
                command=self.update_proc_display
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
            text="Save Pores \u2264 50μm",
            command=lambda: self.save_proc_image(0)
        )
        self.save_small_contours_button.pack(pady=2)
        
        self.save_large_contours_button = ttk.Button(
            self.proc_save_frame,
            text="Save Pores > 50μm",
            command=lambda: self.save_proc_image(1)
        )
        self.save_large_contours_button.pack(pady=2)
        
        self.save_all_contours_button = ttk.Button(
            self.proc_save_frame,
            text="Save All Contours",
            command=lambda: self.save_proc_image(2)
        )
        self.save_all_contours_button.pack(pady=2)
        
        # Add a button to save the original binary image without contours
        self.save_original_binary_button = ttk.Button(
            self.proc_save_frame,
            text="Save Original Binary",
            command=self.save_original_binary
        )
        self.save_original_binary_button.pack(pady=2)
        
        # Create a frame for image display in processing tab
        self.processing_frame_images = ttk.Frame(self.processing_frame)
        self.processing_frame_images.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Create a canvas for displaying images in processing tab
        self.proc_canvas = tk.Canvas(self.processing_frame_images)
        self.proc_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Add a label to show when no images are loaded in processing tab
        self.proc_no_image_label = ttk.Label(
            self.proc_canvas, 
            text="No mosaic loaded. Click 'Load Mosaic' to begin.",
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
        
    def show_layer_controls(self):
        """Show the unified layer control frame after images are loaded"""
        if not self.controls_visible:
            # Pack the unified layer control frame
            self.unified_layer_frame.pack(pady=10, fill=tk.X)
            # Pack the save button frame
            self.save_frame.pack(pady=10, fill=tk.X)
            self.controls_visible = True
            
            # Update the layer rows to reflect the current order
            self.update_layer_rows()

    def show_proc_layer_controls(self):
        """Show the processing tab layer control frame after images are loaded"""
        if not self.proc_controls_visible:
            # Pack the unified layer control frame
            self.proc_unified_layer_frame.pack(pady=10, fill=tk.X)
            # Pack the save button frame
            self.proc_save_frame.pack(pady=10, fill=tk.X)
            self.proc_controls_visible = True
            
            # Update the layer rows to reflect the current order
            self.update_proc_layer_rows()

    def hide_layer_controls(self):
        """Hide the unified layer control frame"""
        if self.controls_visible:
            # Unpack the unified layer control frame
            self.unified_layer_frame.pack_forget()
            self.controls_visible = False

    def hide_proc_layer_controls(self):
        """Hide the processing tab layer control frame"""
        if self.proc_controls_visible:
            # Unpack the unified layer control frame
            self.proc_unified_layer_frame.pack_forget()
            self.proc_save_frame.pack_forget()
            self.proc_controls_visible = False

    def update_layer_rows(self):
        """Update the layer rows to reflect the current layer order"""
        # Reorder the layer rows based on the current layer_order
        for i, layer_idx in enumerate(self.layer_order):
            # Update the label text
            self.layer_rows[i]['label'].config(text=self.layer_names[layer_idx])
            
            # Update the checkbutton variable
            self.layer_rows[i]['visibility'].config(variable=self.layer_visibility[layer_idx])
            
            # Update the up/down button commands
            self.layer_rows[i]['up_button'].config(
                command=lambda idx=i: self.move_layer_up_by_index(idx)
            )
            self.layer_rows[i]['down_button'].config(
                command=lambda idx=i: self.move_layer_down_by_index(idx)
            )
            
            # Enable/disable up/down buttons based on position
            self.layer_rows[i]['up_button'].config(state=tk.NORMAL if i > 0 else tk.DISABLED)
            self.layer_rows[i]['down_button'].config(
                state=tk.NORMAL if i < len(self.layer_order) - 1 else tk.DISABLED
            )

    def update_proc_layer_rows(self):
        """Update the processing tab layer rows to reflect the current layer order"""
        # Reorder the layer rows based on the current proc_layer_order
        for i, layer_idx in enumerate(self.proc_layer_order):
            # Update the label text
            self.proc_layer_rows[i]['label'].config(text=self.proc_layer_names[layer_idx])
            
            # Update the checkbutton variable
            self.proc_layer_rows[i]['visibility'].config(variable=self.proc_layer_visibility[layer_idx])
            
            # Update the up/down button commands
            self.proc_layer_rows[i]['up_button'].config(
                command=lambda idx=i: self.move_proc_layer_up_by_index(idx)
            )
            self.proc_layer_rows[i]['down_button'].config(
                command=lambda idx=i: self.move_proc_layer_down_by_index(idx)
            )
            
            # Enable/disable up/down buttons based on position
            self.proc_layer_rows[i]['up_button'].config(state=tk.NORMAL if i > 0 else tk.DISABLED)
            self.proc_layer_rows[i]['down_button'].config(
                state=tk.NORMAL if i < len(self.proc_layer_order) - 1 else tk.DISABLED
            )

    def move_layer_up_by_index(self, index):
        """Move a layer up in the order based on its current position"""
        if index <= 0 or index >= len(self.layer_order):
            return
            
        # Get the layer indices at the current and target positions
        current_layer = self.layer_order[index]
        target_layer = self.layer_order[index - 1]
        
        # Swap them in the layer_order list
        self.layer_order[index] = target_layer
        self.layer_order[index - 1] = current_layer
        
        # Update the layer rows
        self.update_layer_rows()
        
        # Update the display
        self.update_display()

    def move_proc_layer_up_by_index(self, index):
        """Move a processing tab layer up in the order based on its current position"""
        if index <= 0 or index >= len(self.proc_layer_order):
            return
            
        # Get the layer indices at the current and target positions
        current_layer = self.proc_layer_order[index]
        target_layer = self.proc_layer_order[index - 1]
        
        # Swap them in the layer_order list
        self.proc_layer_order[index] = target_layer
        self.proc_layer_order[index - 1] = current_layer
        
        # Update the layer rows
        self.update_proc_layer_rows()
        
        # Update the display
        self.update_proc_display()

    def move_layer_down_by_index(self, index):
        """Move a layer down in the order based on its current position"""
        if index < 0 or index >= len(self.layer_order) - 1:
            return
            
        # Get the layer indices at the current and target positions
        current_layer = self.layer_order[index]
        target_layer = self.layer_order[index + 1]
        
        # Swap them in the layer_order list
        self.layer_order[index] = target_layer
        self.layer_order[index + 1] = current_layer
        
        # Update the layer rows
        self.update_layer_rows()
        
        # Update the display
        self.update_display()

    def move_proc_layer_down_by_index(self, index):
        """Move a processing tab layer down in the order based on its current position"""
        if index < 0 or index >= len(self.proc_layer_order) - 1:
            return
            
        # Get the layer indices at the current and target positions
        current_layer = self.proc_layer_order[index]
        target_layer = self.proc_layer_order[index + 1]
        
        # Swap them in the layer_order list
        self.proc_layer_order[index] = target_layer
        self.proc_layer_order[index + 1] = current_layer
        
        # Update the layer rows
        self.update_proc_layer_rows()
        
        # Update the display
        self.update_proc_display()

    def load_image(self):
        # Clear previous images
        self.images = []
        self.tk_images = []
        
        # Hide controls if they were previously shown
        self.hide_layer_controls()
        
        # Open file dialog to select images
        file_paths = fd.askopenfilenames(
            title="Select Two Images",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.tif *.tiff")]
        )
        
        if len(file_paths) < 2:
            messagebox.showwarning("Warning", "Please select at least two images.")
            return
            
        # Load the first two selected images using OpenCV
        for i, file in enumerate(file_paths[:2]):
            image = cv2.imread(file)
            if image is not None:
                # Convert to grayscale
                gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                self.images.append(gray_image)
                self.layer_names[i] = os.path.basename(file)  # Use the file name as the layer name
            else:
                messagebox.showerror("Error", f"Failed to load image {i+1}.")
                return
        
        # Process the images to create the combined result
        if len(self.images) == 2:
            # Add the two images with equal weight (0.5 each)
            combined = cv2.add(
                cv2.divide(self.images[0], 2),
                cv2.divide(self.images[1], 2)
            )
            # Apply Gaussian blur
            combined = cv2.GaussianBlur(combined, (11, 11), 0)
            # Apply Otsu's thresholding
            _, combined = cv2.threshold(
                combined, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            self.images.append(combined)
            
            # Reset layer order to default
            self.layer_order = [2, 0, 1]
            
            # Show the layer controls now that we have images
            self.show_layer_controls()
            
            # Update the display
            self.update_display()
    
    def update_display(self):
        if not self.images:
            return
            
        # Hide the "no image" label
        self.no_image_label.place_forget()
        
        # Clear the canvas
        self.canvas.delete("all")
        
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # If canvas size is not yet determined, use default values
        if canvas_width <= 1:
            canvas_width = 800
        if canvas_height <= 1:
            canvas_height = 600
            
        # Calculate the scale factor to fit images in the canvas
        img_height, img_width = self.images[0].shape
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        scale = min(scale_x, scale_y)
        
        # Calculate new dimensions
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Convert OpenCV images to PIL format and resize
        self.tk_images = []
        for img in self.images:
            # Convert to PIL Image
            pil_img = Image.fromarray(img)
            # Resize to fit canvas
            pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
            # Convert to PhotoImage
            tk_img = ImageTk.PhotoImage(pil_img)
            self.tk_images.append(tk_img)
        
        # Calculate position to center the image
        x_pos = (canvas_width - new_width) // 2
        y_pos = (canvas_height - new_height) // 2
        
        # Display images in the specified order, respecting visibility
        for i in reversed(range(len(self.layer_order))):  # Reversed to draw bottom layer first
            layer_idx = self.layer_order[i]
            if self.layer_visibility[layer_idx].get():
                self.canvas.create_image(
                    x_pos, y_pos,
                    anchor=tk.NW,
                    image=self.tk_images[layer_idx]
                )

    def update_proc_display(self):
        """Update the display in the processing tab"""
        if not self.proc_images and not self.roi_mode:
            return
            
        # Hide the "no image" label
        self.proc_no_image_label.place_forget()
        
        # Clear the canvas
        self.proc_canvas.delete("all")
        
        # Get canvas dimensions
        canvas_width = self.proc_canvas.winfo_width()
        canvas_height = self.proc_canvas.winfo_height()
        
        # If canvas size is not yet determined, use default values
        if canvas_width <= 1:
            canvas_width = 800
        if canvas_height <= 1:
            canvas_height = 600
        
        # If in ROI selection mode, display the original image for ROI selection
        if self.roi_mode and self.roi_image is not None:
            # Calculate the scale factor to fit image in the canvas
            img_height, img_width = self.roi_image.shape[:2]
            scale_x = canvas_width / img_width
            scale_y = canvas_height / img_height
            scale = min(scale_x, scale_y)
            self.roi_scale = scale
            
            # Calculate new dimensions
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # Convert to PIL Image
            rgb_image = cv2.cvtColor(self.roi_image, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_image)
            
            # Resize to fit canvas
            pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage
            tk_img = ImageTk.PhotoImage(pil_img)
            self.roi_tk_image = tk_img  # Store reference to prevent garbage collection
            
            # Calculate position to center the image
            x_pos = (canvas_width - new_width) // 2
            y_pos = (canvas_height - new_height) // 2
            
            # Display the image
            self.proc_canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=tk_img, tags="roi_image")
            
            # Show ROI instruction label
            if self.roi_instruction_window is None:
                self.roi_instruction_window = self.proc_canvas.create_window(
                    canvas_width // 2, 
                    y_pos + new_height + 10,
                    window=self.roi_instruction_label
                )
            
            # Store the image position for ROI calculations
            self.roi_image_pos = (x_pos, y_pos)
            return
            
        # If we have processed images, display them
        if self.proc_images:
            # Calculate the scale factor to fit images in the canvas
            img_height, img_width = self.proc_images[0].shape[:2]
            scale_x = canvas_width / img_width
            scale_y = canvas_height / img_height
            scale = min(scale_x, scale_y)
            
            # Calculate new dimensions
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # Convert OpenCV images to PIL format and resize
            self.proc_tk_images = []
            for img in self.proc_images:
                # Convert to PIL Image (handle both grayscale and color images)
                if len(img.shape) == 2:  # Grayscale
                    pil_img = Image.fromarray(img)
                else:  # Color (BGR)
                    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                
                # Resize to fit canvas
                pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
                
                # Convert to PhotoImage
                tk_img = ImageTk.PhotoImage(pil_img)
                self.proc_tk_images.append(tk_img)
            
            # Calculate position to center the image
            x_pos = (canvas_width - new_width) // 2
            y_pos = (canvas_height - new_height) // 2
            
            # Display images in the specified order, respecting visibility
            for i in reversed(range(len(self.proc_layer_order))):  # Reversed to draw bottom layer first
                layer_idx = self.proc_layer_order[i]
                if self.proc_layer_visibility[layer_idx].get():
                    self.proc_canvas.create_image(
                        x_pos, y_pos,
                        anchor=tk.NW,
                        image=self.proc_tk_images[layer_idx]
                    )

    def save_image(self):
        """Save the combined result as a TIFF file"""
        if not self.images or len(self.images) < 3:
            messagebox.showwarning("Warning", "No Binary mosaic to save.")
            return
            
        # Open file dialog to select save location
        file_path = fd.asksaveasfilename(
            title="Save Binary mosaic",
            defaultextension=".tiff",
            filetypes=[("TIFF files", "*.tiff"), ("All files", "*.*")]
        )
        
        if not file_path:
            return  # User cancelled
            
        try:
            # Save the combined result image (original resolution)
            cv2.imwrite(file_path, self.images[2])
            messagebox.showinfo("Success", f"Binary mosaic saved to '{os.path.basename(file_path)}'")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {str(e)}")

    def save_proc_image(self, index):
        """Save the specified processed image as a TIFF file"""
        if not self.proc_images or index >= len(self.proc_images):
            messagebox.showwarning("Warning", f"No {self.proc_layer_names[index]} image to save.")
            return
            
        # Open file dialog to select save location
        file_path = fd.asksaveasfilename(
            title=f"Save {self.proc_layer_names[index]}",
            defaultextension=".tiff",
            filetypes=[("TIFF files", "*.tiff"), ("All files", "*.*")]
        )
        
        if not file_path:
            return  # User cancelled
            
        try:
            # Save the specified image (original resolution)
            cv2.imwrite(file_path, self.proc_images[index])
            messagebox.showinfo("Success", f"{self.proc_layer_names[index]} saved to '{os.path.basename(file_path)}'")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {str(e)}")

    def load_mosaic(self):
        """Load a mosaic image and display it for ROI selection"""
        # Verify if pixel calibration is set
        if not self.pixel_cal_input.get():
            messagebox.showwarning("Warning", "Please set the pixel calibration value.")
            return
            
        # Clear previous images
        self.proc_images = []
        self.proc_tk_images = []
        
        # Hide controls if they were previously shown
        self.hide_proc_layer_controls()
        
        # Open file dialog to select image
        file_path = fd.askopenfilename(
            title="Select a Mosaic",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.tif *.tiff")]
        )
        
        if not file_path:
            return  # User cancelled
            
        # Load the selected image using OpenCV
        image = cv2.imread(file_path)
        if image is None:
            messagebox.showerror("Error", "Failed to load image.")
            return
            
        # Store the original image
        self.original_image = image.copy()
        
        # Enter ROI selection mode
        self.roi_mode = True
        self.roi_image = image
        
        # Display the image for ROI selection
        self.update_proc_display()
        
        # Bind mouse events for ROI selection
        self.proc_canvas.bind("<ButtonPress-1>", self.start_roi)
        self.proc_canvas.bind("<B1-Motion>", self.update_roi)
        self.proc_canvas.bind("<ButtonRelease-1>", self.end_roi_drag)
        
        # Bind keyboard event for confirming ROI (only Enter key)
        self.root.bind("<Return>", self.confirm_roi)
        
        # Enable the confirm ROI button
        self.confirm_roi_button.config(state=tk.NORMAL)
        
        # Show a message to the user
        messagebox.showinfo("Select ROI", "Click and drag to select a Region Of Interest. Press Enter or click 'Confirm ROI' button when done.")

    def start_roi(self, event):
        """Start ROI selection"""
        if not self.roi_mode:
            return
            
        # Get canvas coordinates
        x = event.x
        y = event.y
        
        # Check if click is within the image
        img_x, img_y = self.roi_image_pos
        img_height, img_width = self.roi_image.shape[:2]
        img_width_scaled = int(img_width * self.roi_scale)
        img_height_scaled = int(img_height * self.roi_scale)
        
        if (x < img_x or x > img_x + img_width_scaled or 
            y < img_y or y > img_y + img_height_scaled):
            return
        
        # Delete any existing ROI rectangle
        if self.roi_rect is not None:
            self.proc_canvas.delete(self.roi_rect)
        
        self.roi_start_x = x
        self.roi_start_y = y
        
        # Create a rectangle
        self.roi_rect = self.proc_canvas.create_rectangle(
            x, y, x, y, outline="red", width=2
        )

    def update_roi(self, event):
        """Update ROI selection"""
        if not self.roi_mode or self.roi_start_x is None or self.roi_rect is None:
            return
            
        # Get canvas coordinates
        x = event.x
        y = event.y
        
        # Update rectangle
        self.proc_canvas.coords(self.roi_rect, self.roi_start_x, self.roi_start_y, x, y)

    def end_roi_drag(self, event):
        """End ROI drag (but don't confirm yet)"""
        # We don't process the ROI here, just finish the drag
        # The ROI will be confirmed with Enter key or Confirm ROI button
        pass

    def confirm_roi(self, event=None):
        """Confirm ROI selection with Enter key or button click"""
        if not self.roi_mode or self.roi_start_x is None or self.roi_rect is None:
            return
            
        # Get the rectangle coordinates
        coords = self.proc_canvas.coords(self.roi_rect)
        if len(coords) != 4:
            return
            
        x1, y1, x2, y2 = coords
        
        # Ensure x1,y1 is the top-left and x2,y2 is the bottom-right
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        # Convert canvas coordinates to original image coordinates
        img_x, img_y = self.roi_image_pos
        
        # Adjust coordinates relative to the image position
        x1 = x1 - img_x
        y1 = y1 - img_y
        x2 = x2 - img_x
        y2 = y2 - img_y
        
        # Convert from scaled to original image coordinates
        orig_x1 = int(x1 / self.roi_scale)
        orig_y1 = int(y1 / self.roi_scale)
        orig_x2 = int(x2 / self.roi_scale)
        orig_y2 = int(y2 / self.roi_scale)
        
        # Ensure coordinates are within image bounds
        img_height, img_width = self.roi_image.shape[:2]
        orig_x1 = max(0, orig_x1)
        orig_y1 = max(0, orig_y1)
        orig_x2 = min(img_width, orig_x2)
        orig_y2 = min(img_height, orig_y2)
        
        # Exit ROI selection mode
        self.exit_roi_mode()
        
        # Process the selected ROI
        self.process_selected_roi(orig_x1, orig_y1, orig_x2, orig_y2)

    def exit_roi_mode(self):
        """Exit ROI selection mode and clean up"""
        self.roi_mode = False
        
        # Unbind events
        self.proc_canvas.unbind("<ButtonPress-1>")
        self.proc_canvas.unbind("<B1-Motion>")
        self.proc_canvas.unbind("<ButtonRelease-1>")
        self.root.unbind("<Return>")
        
        # Clear ROI variables
        self.roi_start_x = None
        self.roi_start_y = None
        self.roi_rect = None
        
        # Hide instruction label
        if self.roi_instruction_window is not None:
            self.proc_canvas.delete(self.roi_instruction_window)
            self.roi_instruction_window = None
        
        # Disable the confirm ROI button
        self.confirm_roi_button.config(state=tk.DISABLED)

    def process_selected_roi(self, x1, y1, x2, y2):
        """Process the selected ROI"""
        if self.original_image is None:
            return
            
        # Crop the original image to the selected ROI
        roi_image = self.original_image[y1:y2, x1:x2].copy()
        
        # Check if the image is color (3 channels) or grayscale (1 channel)
        if len(roi_image.shape) == 3:
            # Convert to grayscale for processing
            gray_roi = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
            
            # Check if the image is already binary (only contains 0 and 255 values)
            unique_values = np.unique(gray_roi)
            if len(unique_values) <= 2 and np.all(np.isin(unique_values, [0, 255])):
                # Image is already binary, no need to threshold
                binary_roi = gray_roi
            else:
                # Apply thresholding to ensure binary image
                _, binary_roi = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            # Image is already grayscale
            gray_roi = roi_image
            
            # Check if the image is already binary (only contains 0 and 255 values)
            unique_values = np.unique(gray_roi)
            if len(unique_values) <= 2 and np.all(np.isin(unique_values, [0, 255])):
                # Image is already binary, no need to threshold
                binary_roi = gray_roi
            else:
                # Apply thresholding to ensure binary image
                _, binary_roi = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Store the original binary image for later use
        self.original_binary = binary_roi.copy()
        
        # Process the ROI to find contours
        self.process_mosaic(binary_roi)
        
        # Show the layer controls now that we have images
        self.show_proc_layer_controls()
        
        # Update the display
        self.update_proc_display()

    def save_original_binary(self):
        """Save the original binary image without contours"""
        if not hasattr(self, 'original_binary') or self.original_binary is None:
            messagebox.showwarning("Warning", "No original binary image available.")
            return
            
        # Open file dialog to select save location
        file_path = fd.asksaveasfilename(
            title="Save Original Binary",
            defaultextension=".tiff",
            filetypes=[("TIFF files", "*.tiff"), ("All files", "*.*")]
        )
        
        if not file_path:
            return  # User cancelled
            
        try:
            # Save the original binary image
            cv2.imwrite(file_path, self.original_binary)
            messagebox.showinfo("Success", f"Original binary image saved to '{os.path.basename(file_path)}'")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {str(e)}")
        
    def process_mosaic(self, image):
        """Process the loaded mosaic image to find contours"""
        # Find contours with hierarchy
        contours, hierarchy = cv2.findContours(image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        
        # Check if contours were found
        if len(contours) == 0 or hierarchy is None:
            messagebox.showwarning("Warning", "No contours found in the selected ROI.")
            return
        
        # Flatten hierarchy array for easier access
        hierarchy = hierarchy[0]
        
        # Create a list to store processed contours with their properties and hierarchy
        # Format: [parent_contour, [child_contours], area, perimeter]
        processed_contours = []
        
        # Process each contour
        for i, contour in enumerate(contours):
            # Check if this is a parent contour (no parent)
            if hierarchy[i][3] == -1:  # [Next, Previous, First_Child, Parent]
                # Calculate initial area and perimeter for the parent
                parent_area = cv2.contourArea(contour)
                parent_perimeter = cv2.arcLength(contour, True)
                
                # Find all children of this parent
                child_idx = hierarchy[i][2]  # First child
                children_area = 0
                children_perimeter = 0
                child_contours = []
                
                # Process all children
                while child_idx != -1:
                    child_contour = contours[child_idx]
                    child_contours.append(child_contour)
                    children_area += cv2.contourArea(child_contour)
                    children_perimeter += cv2.arcLength(child_contour, True)
                    
                    # Move to the next child at the same level
                    child_idx = hierarchy[child_idx][0]
                
                # Calculate final area and perimeter
                final_area = parent_area - children_area
                final_perimeter = parent_perimeter + children_perimeter
                
                # Add to processed contours list with parent, children, area, and perimeter
                processed_contours.append([contour, child_contours, final_area, final_perimeter])
        
        # Store the processed contours for further analysis
        self.processed_contours = processed_contours
        
        # Segmenting contours by diameter less than 50 micras
        # Converting diameter to pixels using the pixel calibration value
        D_pix = 50 * float(self.pixel_cal_input.get())
        
        # Calculate the area of the circle with diameter D_pix
        area_50 = round(np.pi * (D_pix/2)**2)
        
        # Create copies of the original image for drawing contours
        all_contours_image = image.copy()
        small_contours_image = image.copy()
        large_contours_image = image.copy()
        
        # Convert to BGR for colored contours
        all_contours_image = cv2.cvtColor(all_contours_image, cv2.COLOR_GRAY2BGR)
        small_contours_image = cv2.cvtColor(small_contours_image, cv2.COLOR_GRAY2BGR)
        large_contours_image = cv2.cvtColor(large_contours_image, cv2.COLOR_GRAY2BGR)
        
        # Prepare lists for small and large contours
        small_contours = []
        large_contours = []
        all_contours = []
        
        # Collect all contours (parents and children)
        for parent, children, area, perimeter in processed_contours:
            all_contours.append(parent)
            all_contours.extend(children)
            
            if area <= area_50:
                small_contours.append(parent)
                small_contours.extend(children)
            else:
                large_contours.append(parent)
                large_contours.extend(children)
        
        # Draw all contours on the original image
        cv2.drawContours(all_contours_image, all_contours, -1, (0, 0, 255), 2)  # Red color for all contours
        
        # Draw the contours on the small contours image
        cv2.drawContours(small_contours_image, small_contours, -1, (255, 0, 0), 2)  # Blue color
        
        # Draw the contours on the large contours image
        cv2.drawContours(large_contours_image, large_contours, -1, (0, 255, 0), 2)  # Green color
        
        # Clear previous images
        self.proc_images = []
        
        # Add the processed images to the images list in the desired order
        # First: Small contours
        self.proc_images.append(small_contours_image)
        # Second: Large contours
        self.proc_images.append(large_contours_image)
        # Third (last): Original with all contours
        self.proc_images.append(all_contours_image)
        
        # Update the layer names to reflect the new order
        self.proc_layer_names = ["Pore \u2264 50μm", "Pore > 50μm", "All Contours"]
        
        # Set the default layer order to show the original with all contours on top
        self.proc_layer_order = [0, 1, 2]  # This keeps the order as is, with all contours last/top
        
        
if __name__ == "__main__":
    root = tk.Tk()
    app = stsmApp(root)
    root.mainloop()

#RESERVED FOR FUTURE USE
# Add this method to visualize individual parent-child groups
def visualize_contour_group(self, index):
    """Visualize a specific parent contour with its children"""
    if not hasattr(self, 'processed_contours') or index >= len(self.processed_contours):
        messagebox.showwarning("Warning", "No contour group available at this index.")
        return
    
    # Get the parent and children contours
    parent, children, area, perimeter = self.processed_contours[index]
    
    # Create a copy of the original binary image
    if len(self.proc_images) > 0:
        # Use the first processed image (binary)
        if len(self.proc_images[0].shape) == 3:
            # If it's already a color image, convert to grayscale
            binary_image = cv2.cvtColor(self.proc_images[0], cv2.COLOR_BGR2GRAY)
        else:
            # If it's already grayscale, make a copy
            binary_image = self.proc_images[0].copy()
    else:
        messagebox.showwarning("Warning", "No processed image available.")
        return
    
    # Create a color image for visualization
    vis_image = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2BGR)
    
    # Draw the parent contour in blue
    cv2.drawContours(vis_image, [parent], -1, (255, 0, 0), 2)
    
    # Draw the children contours in green
    cv2.drawContours(vis_image, children, -1, (0, 255, 0), 2)
    
    # Add text with measurements
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(vis_image, f"Area: {area:.2f} px²", (10, 30), font, 0.7, (255, 255, 255), 2)
    cv2.putText(vis_image, f"Perimeter: {perimeter:.2f} px", (10, 60), font, 0.7, (255, 255, 255), 2)
    cv2.putText(vis_image, f"Children: {len(children)}", (10, 90), font, 0.7, (255, 255, 255), 2)
    
    # Display the image in a new window
    cv2.imshow(f"Contour Group {index+1}", vis_image)
    cv2.waitKey(0)
    cv2.destroyWindow(f"Contour Group {index+1}")
