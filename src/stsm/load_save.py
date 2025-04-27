import tkinter as tk
import cv2
import tkinter.filedialog as fd
import tkinter.simpledialog as sd
import tkinter.messagebox as messagebox
import os
from layer_controls import show_layer_controls, hide_layer_controls, hide_proc_layer_controls
from display import update_display, update_proc_display
from roi import start_roi, update_roi, end_roi_drag, confirm_roi
import openpyxl as opxl

def load_image(self):
    # Clear previous images
    self.images = []
    self.tk_images = []
    
    # Hide controls if they were previously shown
    hide_layer_controls(self)
    
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
        show_layer_controls(self)
        
        # Update the display
        update_display(self)

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
    hide_proc_layer_controls(self)
    
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
    update_proc_display(self)
    
    # Bind mouse events for ROI selection
    self.proc_canvas.bind("<ButtonPress-1>", lambda event: start_roi(self, event))
    self.proc_canvas.bind("<B1-Motion>", lambda event: update_roi(self, event))
    self.proc_canvas.bind("<ButtonRelease-1>", lambda event: end_roi_drag(self, event))

    # Bind keyboard event for confirming ROI (only Enter key)
    self.root.bind("<Return>", lambda event: confirm_roi(self, event))

    
    # Enable the confirm ROI button
    self.confirm_roi_button.config(state=tk.NORMAL)
    
    # Show a message to the user
    messagebox.showinfo("Select ROI", "Click and drag to select a Region Of Interest. Press Enter or click 'Confirm ROI' button when done.")

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

def save_gpd_stats(self):
    """Save the global pore statistics to a file"""
    if not hasattr(self, 'summary') or self.summary is None:
        messagebox.showwarning("Warning", "No global pore statistics available.")
        return
        
    # Open dialog to select save location directory
    file_path = fd.askdirectory(
        title="Select Directory to Save Global Pore Stats"
    )
    
    if not file_path:
        messagebox.showwarning("Warning", "No directory selected.")
        return  # User cancelled
    file_path = os.path.abspath(file_path)  # Get absolute path
    print(file_path)    
    try:
        # Save the summary to a Excel file using openpyxl
        if not os.path.exists(file_path + "/Global_Pore_Stats.xlsx"):
            # If file does not exist, create a new workbook and worksheet
            wb = opxl.Workbook()
            ws = wb.active
            ws.title = "Global Pore Stats"
            
            # Write headers
            headers = ["Mosaic Name",
                "Number of parent contours",
                "Number of child contours",
                "Porosity",
                "Number of parent contours <= 50μm",
                "Number of child contours <= 50μm",
                "Percentage of pores <= 50μm",
                "Number of parent contours > 50μm",
                "Number of child contours > 50μm",
                "Percentage of pores > 50μm"
            ]
            ws.append(headers)
        else:
            # If file exists, load the existing workbook and worksheet
            wb = opxl.load_workbook(file_path + "/Global_Pore_Stats.xlsx")
            ws = wb.active
        
        # Enter the mosaic name to append the mosaic name to the summary
        mosaic_name = sd.askstring("Mosaic Name", "Enter the name of the mosaic:")
        if not mosaic_name:
            messagebox.showwarning("Warning", "No mosaic name provided.")
            return  # User cancelled
        self.summary = (mosaic_name, ) + self.summary

        # Append the summary to the worksheet
        ws.append(self.summary)
        wb.save(file_path + "/Global_Pore_Stats.xlsx")
        wb.close()
            
        messagebox.showinfo("Success", f"Global pore statistics saved to '{os.path.basename(file_path) + '/Global_Pore_Stats.xlsx'}'")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save statistics: {str(e)}")