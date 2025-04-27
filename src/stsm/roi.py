import tkinter as tk
import cv2
import numpy as np
from layer_controls import show_proc_layer_controls
from display import update_proc_display
from proc_mosaic import process_mosaic

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
    exit_roi_mode(self)
    
    # Process the selected ROI
    process_selected_roi(self, orig_x1, orig_y1, orig_x2, orig_y2)

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
    process_mosaic(self, binary_roi)
    
    # Show the layer controls now that we have images
    show_proc_layer_controls(self)
    
    # Update the display
    update_proc_display(self)