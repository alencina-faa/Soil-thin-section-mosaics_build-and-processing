import cv2
from tkinter import messagebox
import numpy as np

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
