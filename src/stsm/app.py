import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from binary_tab import binary_tab
from processing_tab import processing_tab

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
        self.index = 0  # Index for the current image being processed
        
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
        binary_tab(self)

        # Setup the Processing tab
        processing_tab(self)
#Ends the mainwindow definitions

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
