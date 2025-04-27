import cv2
from tkinter import messagebox
import numpy as np

def process_mosaic(self, image):
    # Store the image for further analysis
    self.image = image
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
    
    # Segmenting contours by diameter less than 50 micron
    # Converting diameter to pixels using the pixel calibration value
    D_pix = 50 * float(self.pixel_cal_input.get())
    
    # Calculate the area of the circle with diameter D_pix
    self.area_50 = round(np.pi * (D_pix/2)**2)
    
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
        
        if area <= self.area_50:
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

    proc_cont_all(self)

def proc_cont_all(self):
    #TOTALS
    # Calculate the area of the image in pixels
    image_area = np.shape(self.image)[0] * np.shape(self.image)[1]
    
    # Calculate the number of parent contours (with or whitout children)
    num_parent_contours = len(self.processed_contours)

    # Calculate the number of child contours
    num_child_contours = sum([len(contour[1]) for contour in self.processed_contours])
    
    # Calculathe the total area of all contours
    cont_total_area = sum([contour[2] for contour in self.processed_contours])
 
    #LESS THAN 50 micron
    # Calculate the number of parent contours with area greater than 50 micron
    num_parent_contours_less_50 = sum([1 for contour in self.processed_contours if contour[2] <= self.area_50])

    # Calculate the number of child contours with area greater than 50 micron
    num_child_contours_less_50 = sum([len(contour[1]) for contour in self.processed_contours if contour[2] <= self.area_50])
    
    # Calculate the total area of contours with diameter less than 50 micron
    cont_total_area_less_50 = sum([contour[2] for contour in self.processed_contours if contour[2] <= self.area_50])
    
    #GREATHER THAN 50 micron
    # Calculate the number of parent contours with area greater than 50 micron
    num_parent_contours_great_50 = sum([1 for contour in self.processed_contours if contour[2] > self.area_50])

    # Calculate the number of child contours with area greater than 50 micron
    num_child_contours_great_50 = sum([len(contour[1]) for contour in self.processed_contours if contour[2] > self.area_50])
    
    # Calculate the total area of contours with diameter greather than 50 micron
    cont_total_area_great_50 = sum([contour[2] for contour in self.processed_contours if contour[2] > self.area_50])
    #------------------------------------------------

    #Summary of the results to be appended as a new row to a Excel file (using openpyxl)
    self.summary = (
        num_parent_contours,  # Number of parent contours
        num_child_contours,  # Number of child contours
        cont_total_area / image_area,  # Porosity
        num_parent_contours_less_50,  # Number of parent contours less than 50 micron
        num_child_contours_less_50,  # Number of child contours less than 50 micron
        cont_total_area_less_50 / cont_total_area,  # Percentage of pores less than 50 micron
        num_parent_contours_great_50,  # Number of parent contours greather than 50 micron
        num_child_contours_great_50,  # Number of child contours greather than 50 micorn
        cont_total_area_great_50 / cont_total_area,  # Percentage of pores less than 50 micron
    )
    

