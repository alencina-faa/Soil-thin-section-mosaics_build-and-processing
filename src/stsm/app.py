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
        self.pixel_cal_input.pack(pady=(0, 5))#, fill=tk.X)  
        
        # Create a button to load the mosaic to be processed
        self.load_mosaic_button = ttk.Button(
            self.processing_frame_controls, 
            text="Load Mosaic", 
            command=self.load_mosaic
        )
        self.load_mosaic_button.pack(pady=5)
        
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
        self.save_original_button = ttk.Button(
            self.proc_save_frame,
            text="Save Original ROI",
            command=lambda: self.save_proc_image(0)
        )
        self.save_original_button.pack(pady=2)
        
        self.save_small_contours_button = ttk.Button(
            self.proc_save_frame,
            text="Save Pores \u2264 50μm",
            command=lambda: self.save_proc_image(1)
        )
        self.save_small_contours_button.pack(pady=2)
        
        self.save_large_contours_button = ttk.Button(
            self.proc_save_frame,
            text="Save Pores > 50μm",
            command=lambda: self.save_proc_image(2)
        )
        self.save_large_contours_button.pack(pady=2)
        
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
        if not self.proc_images:
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
            
        # Calculate the scale factor to fit images in the canvas
        img_height, img_width = self.proc_images[0].shape
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        scale = min(scale_x, scale_y)
        
        # Calculate new dimensions
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Convert OpenCV images to PIL format and resize
        self.proc_tk_images = []
        for img in self.proc_images:
            # Convert to PIL Image
            pil_img = Image.fromarray(img)
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
        
        # Display the image for ROI selection
        self.select_roi_on_canvas(image)

    def select_roi_on_canvas(self, image):
        """Display the image on canvas and allow ROI selection"""
        # Convert BGR to RGB for display
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Create a new window for ROI selection
        roi_window = tk.Toplevel(self.root)
        roi_window.title("Select Region of Interest")
        roi_window.geometry("800x600")
        
        # Create a frame for the canvas
        frame = ttk.Frame(roi_window)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a canvas for displaying the image
        canvas = tk.Canvas(frame)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbars if the image is large
        h_scrollbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=canvas.xview)
        v_scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Convert to PIL Image
        pil_img = Image.fromarray(rgb_image)
        
        # Calculate scale factor to fit in window
        img_height, img_width = rgb_image.shape[:2]
        window_width = 800
        window_height = 600
        scale_x = window_width / img_width
        scale_y = window_height / img_height
        scale = min(scale_x, scale_y)
        
        # Calculate new dimensions
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Resize the image
        pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
        
        # Convert to PhotoImage
        tk_img = ImageTk.PhotoImage(pil_img)
        
        # Display the image on canvas
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
        canvas.image = tk_img  # Keep a reference to prevent garbage collection
        
        # Configure canvas scrolling region
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Variables for ROI selection
        roi_start_x = None
        roi_start_y = None
        roi_rect = None
        
        # Function to start ROI selection
        def start_roi(event):
            nonlocal roi_start_x, roi_start_y, roi_rect
            # Get canvas coordinates
            x = canvas.canvasx(event.x)
            y = canvas.canvasy(event.y)
            roi_start_x = x
            roi_start_y = y
            # Create a rectangle
            roi_rect = canvas.create_rectangle(
                x, y, x, y, outline="red", width=2
            )
        
        # Function to update ROI selection
        def update_roi(event):
            nonlocal roi_rect
            if roi_start_x is not None and roi_start_y is not None:
                # Get canvas coordinates
                x = canvas.canvasx(event.x)
                y = canvas.canvasy(event.y)
                # Update rectangle
                canvas.coords(roi_rect, roi_start_x, roi_start_y, x, y)
        
        # Function to end ROI selection
        def end_roi(event):
            nonlocal roi_start_x, roi_start_y, roi_rect
            if roi_start_x is not None and roi_start_y is not None:
                # Get canvas coordinates
                x = canvas.canvasx(event.x)
                y = canvas.canvasy(event.y)
                
                # Get the rectangle coordinates
                x1 = min(roi_start_x, x)
                y1 = min(roi_start_y, y)
                x2 = max(roi_start_x, x)
                y2 = max(roi_start_y, y)
                
                # Convert canvas coordinates to original image coordinates
                orig_x1 = int(x1 / scale)
                orig_y1 = int(y1 / scale)
                orig_x2 = int(x2 / scale)
                orig_y2 = int(y2 / scale)
                
                # Ensure coordinates are within image bounds
                orig_x1 = max(0, orig_x1)
                orig_y1 = max(0, orig_y1)
                orig_x2 = min(img_width, orig_x2)
                orig_y2 = min(img_height, orig_y2)
                
                # Close the ROI selection window
                roi_window.destroy()
                
                # Process the selected ROI
                self.process_selected_roi(orig_x1, orig_y1, orig_x2, orig_y2)
        
        # Bind mouse events
        canvas.bind("<ButtonPress-1>", start_roi)
        canvas.bind("<B1-Motion>", update_roi)
        canvas.bind("<ButtonRelease-1>", end_roi)
        
        # Add instructions
        instructions = ttk.Label(
            roi_window,
            text="Click and drag to select a region of interest, then release to process."
        )
        instructions.pack(side=tk.BOTTOM, pady=5)

    def process_selected_roi(self, x1, y1, x2, y2):
        """Process the selected ROI"""
        if self.original_image is None:
            return
            
        # Crop the original image to the selected ROI
        roi_image = self.original_image[y1:y2, x1:x2].copy()
        
        # Convert to grayscale for processing
        gray_roi = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to create a binary image
        _, binary_roi = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Store the original ROI as the first processed image
        self.proc_images.append(binary_roi)
        
        # Process the ROI to find contours
        self.process_mosaic(binary_roi)
        
        # Show the layer controls now that we have images
        self.show_proc_layer_controls()
        
        # Update the display
        self.update_proc_display()

    def process_mosaic(self, image):
        """Process the loaded mosaic image to find contours"""
        # Find contours
        contours, _ = cv2.findContours(image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

        # Calculate the area of each contour
        contours_by_area = [[contour, cv2.contourArea(contour)] for contour in contours]

        # Segmenting contours by diameter lesser than 50 micras
        # Converting diameter to pixels using the pixel calibration value
        D_pix = 50 * float(self.pixel_cal_input.get())

        # Calculate the area of the circle with diameter D_pix
        area_50 = round(np.pi * (D_pix/2)**2)

        # Create copies of the original image for drawing contours
        small_contours_image = image.copy()
        large_contours_image = image.copy()
        
        # Convert to BGR for colored contours
        small_contours_image = cv2.cvtColor(small_contours_image, cv2.COLOR_GRAY2BGR)
        large_contours_image = cv2.cvtColor(large_contours_image, cv2.COLOR_GRAY2BGR)

        # Filter contours with area less than the area of the circle with diameter D_pix
        contours_minor_50 = [contour for contour, area in contours_by_area if area <= area_50]

        # Draw the contours on the small contours image
        cv2.drawContours(small_contours_image, contours_minor_50, -1, (255, 0, 0), 3)
        
        # Convert back to grayscale for display
        #small_contours_image = cv2.cvtColor(small_contours_image, cv2.COLOR_BGR2GRAY)
        
        # Add the processed image to the images list
        self.proc_images.append(small_contours_image)

        # Filter contours with area major than the area of the circle with diameter D_pix
        contours_major_50 = [contour for contour, area in contours_by_area if area > area_50]

        # Draw the contours on the large contours image
        cv2.drawContours(large_contours_image, contours_major_50, -1, (0, 255, 0), 3)
        
        # Convert back to grayscale for display
        #large_contours_image = cv2.cvtColor(large_contours_image, cv2.COLOR_BGR2GRAY)
        
        # Add the processed image to the images list
        self.proc_images.append(large_contours_image)

if __name__ == "__main__":
    root = tk.Tk()
    app = stsmApp(root)
    root.mainloop()