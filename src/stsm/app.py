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

        #Setup the Processing tab
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
        self.canvas = tk.Canvas(self.binary_frame_images) #, bg="black"
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Add a label to show when no images are loaded
        self.no_image_label = ttk.Label(
            self.canvas, 
            text="No images loaded. Click 'Load Images' to begin.",
        ) #    background="black",             foreground="white"
        
        self.canvas.create_window(640, 360, window=self.no_image_label)


#Setup the Processing tab
    def processing_tab(self):
        # Create a frame for controls
        self.processing_frame_controls = ttk.Frame(self.processing_frame)
        self.processing_frame_controls.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)       

        # Add label and input for Image pixel calibration (but not yet implemented)
        self.pixel_cal_label = ttk.Label(
            self.processing_frame_controls,
            text='Pixel calibration (pixel/\u03bcm):',
        )
        self.pixel_cal_label.pack(pady=(0, 5))
        
        self.pixel_cal = tk.StringVar(value="0,3051")  
        self.pixel_cal_input = ttk.Entry(
            self.processing_frame_controls,
            textvariable=self.pixel_cal,
        )
        self.pixel_cal_input.pack(pady=(0, 5), fill=tk.X)  
        
        # Create a button to load the mosaic to be processed
        self.load_button = ttk.Button(
            self.processing_frame_controls, 
            text="Load Mosaic", 
            command=self.load_mosaic
        )
        self.load_button.pack(pady=5)
#ENDS THE TABS DEFINITIONS

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

    def hide_layer_controls(self):
        """Hide the unified layer control frame"""
        if self.controls_visible:
            # Unpack the unified layer control frame
            self.unified_layer_frame.pack_forget()
            self.controls_visible = False

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

    def load_mosaic(self):
        # Verify if pixel calibration is set
        if not self.pixel_cal_input.get():
            messagebox.showwarning("Warning", "Please set the pixel calibration value.")
            return
        # Clear previous images
        self.images = []
        # Open file dialog to select images
        file_paths = fd.askopenfilename(
            title="Select a Mosaic",
            filetypes=[("Image files", "*.tiff")]
        )
        
        if len(file_paths) < 1:
            messagebox.showwarning("Warning", "Please select at least one images.")
            return
            
        image = cv2.imread(file_paths)
        if image is not None:
            # Select ROI
            messagebox.showinfo("Select ROI", "Select the 'Region Of Interest' in the loaded mosaic.")
            #Here is need that the image be displayed in a canvas to select the ROI. 
            #But it is also needed that ROI refers to the original image, not the resized one.
            #Because calculus must be done in the original image.
            r = cv2.selectROI("Select ROI", image, fromCenter=False, showCrosshair=True)
            cv2.destroyWindow("Select ROI")
            image = cv2.cvtColor(image[int(r[1]):int(r[1]+r[3]), int(r[0]):int(r[0]+r[2])], cv2.COLOR_BGR2GRAY)
            self.images.append(image) #One of the stored image to be displayed in the Processing tab canvas.

            self.process_mosaic(image)
            
            
        else:
            messagebox.showerror("Error", f"Failed to load image.")
            return
    
    def process_mosaic(self, image):
        # Process the loaded mosaic image
        # Find contours
        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Calculate the area of each contour
        contours_by_area = [[contour, cv2.contourArea(contour)] for contour in contours]


        
        # Add the processed image to the images list
        #self.images.append()
        
        # Show the layer controls now that we have images
        self.show_layer_controls() #Define a function similar or modify to rehuse this in the Processing tab
            
            # Update the display with the processed image
        self.update_display() #Define a function similar or modify to rehuse this in the Processing tab
    

if __name__ == "__main__":
    root = tk.Tk()
    app = stsmApp(root)
    root.mainloop()