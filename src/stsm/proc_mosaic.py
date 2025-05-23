import cv2
from tkinter import messagebox
import numpy as np
import math as m

def process_mosaic(self, image):
    # Store the image for further analysis
    self.image = image
    
    # Call the optimized contour processing function
    processed_contours = enhanced_process_mosaic_optimized(image)

    # Store the processed contours for further analysis
    self.processed_contours = processed_contours
    
    # Segmenting contours by diameter less than 50 micron
    # Converting diameter to pixels using the pixel calibration value
    self.calibration = float(self.pixel_cal_input.get())
    D_pix = 50 * self.calibration
    
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
    for idx, is_edge, parent, children, area, perimeter in processed_contours:
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
    proc_cont_great_50(self)

#Contour edge detection function
def detect_edge_contours_optimized(image, contours, border_size=1):
    """
    Efficiently identify which contours touch the edge of the image using optimized masks.
    
    Args:
        image: The original binary image
        contours: List of contours to check
        border_size: Size of the border to consider (default: 1 pixel)
        
    Returns:
        List of booleans indicating whether each contour touches the edge
    """
    height, width = image.shape[:2]
    is_edge_contour = []
    
    # Create a small border mask for each edge of the image
    left_edge = np.zeros((height, border_size), dtype=np.uint8)
    left_edge.fill(255)
    
    right_edge = np.zeros((height, border_size), dtype=np.uint8)
    right_edge.fill(255)
    
    top_edge = np.zeros((border_size, width), dtype=np.uint8)
    top_edge.fill(255)
    
    bottom_edge = np.zeros((border_size, width), dtype=np.uint8)
    bottom_edge.fill(255)
    
    for contour in contours:
        # Get bounding rectangle of contour
        x, y, w, h = cv2.boundingRect(contour)
        
        # Quick check if bounding box touches the edge
        if x <= border_size or y <= border_size or x + w >= width - border_size or y + h >= height - border_size:
            # Create a small mask just for the bounding rectangle (with padding)
            padding = border_size + 1
            x_start = max(0, x - padding)
            y_start = max(0, y - padding)
            x_end = min(width, x + w + padding)
            y_end = min(height, y + h + padding)
            
            # Create a small mask just for the bounding rectangle area
            small_mask = np.zeros((y_end - y_start, x_end - x_start), dtype=np.uint8)
            
            # Adjust contour coordinates for the smaller mask
            adjusted_contour = contour - np.array([[x_start, y_start]])
            cv2.drawContours(small_mask, [adjusted_contour], 0, 255, -1)
            
            # Check each edge that the bounding box might touch
            touches_edge = False
            
            if x_start == 0:  # Left edge
                edge_slice = left_edge[y_start:y_end, 0:min(border_size, small_mask.shape[1])]
                if edge_slice.shape[1] > 0:  # Ensure the slice is not empty
                    mask_slice = small_mask[:, 0:edge_slice.shape[1]]
                    if np.any(cv2.bitwise_and(mask_slice, edge_slice)):
                        touches_edge = True
            
            if not touches_edge and x_end == width:  # Right edge
                edge_slice = right_edge[y_start:y_end, 0:min(border_size, small_mask.shape[1])]
                if edge_slice.shape[1] > 0:
                    mask_slice = small_mask[:, -edge_slice.shape[1]:]
                    if np.any(cv2.bitwise_and(mask_slice, edge_slice)):
                        touches_edge = True
            
            if not touches_edge and y_start == 0:  # Top edge
                edge_slice = top_edge[0:min(border_size, small_mask.shape[0]), x_start:x_end]
                if edge_slice.shape[0] > 0:
                    mask_slice = small_mask[0:edge_slice.shape[0], :]
                    if np.any(cv2.bitwise_and(mask_slice, edge_slice)):
                        touches_edge = True
            
            if not touches_edge and y_end == height:  # Bottom edge
                edge_slice = bottom_edge[0:min(border_size, small_mask.shape[0]), x_start:x_end]
                if edge_slice.shape[0] > 0:
                    mask_slice = small_mask[-edge_slice.shape[0]:, :]
                    if np.any(cv2.bitwise_and(mask_slice, edge_slice)):
                        touches_edge = True
            
            is_edge_contour.append(touches_edge)
        else:
            # Bounding box doesn't touch the edge, so contour definitely doesn't
            is_edge_contour.append(False)
    
    return is_edge_contour

# Contour processing function with optimized edge detection and flags
def enhanced_process_mosaic_optimized(image):
    """Process the loaded mosaic image with optimized edge detection"""
    # Find contours with hierarchy
    contours, hierarchy = cv2.findContours(image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    
    # Check if contours were found
    if len(contours) == 0 or hierarchy is None:
        print("No contours found in the image.")
        return []
    
    # Flatten hierarchy array for easier access
    hierarchy = hierarchy[0]
    
    # Find all parent contours (those with no parent)
    parent_indices = [i for i, h in enumerate(hierarchy) if h[3] == -1]
    parent_contours = [contours[i] for i in parent_indices]
    
    # Detect which parent contours touch the edge using optimized method
    is_edge_contour = detect_edge_contours_optimized(image, parent_contours)
    
    # Create a list to store processed contours with their properties and hierarchy
    # Format: [idx, is_edge, parent_contour, [child_contours], final_area, final_perimeter]
    processed_contours = []

    for idx, (parent_idx, is_edge) in enumerate(zip(parent_indices, is_edge_contour)):
        # Take a parent contour
        parent = contours[parent_idx]
        
        # Calculate initial area and perimeter for the parent
        parent_area = cv2.contourArea(parent)
        parent_perimeter = cv2.arcLength(parent, True)
        
        # Find all children of this parent
        child_idx = hierarchy[parent_idx][2]  # First child #I THINK HERE IS MY ERROR!!!
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
        
        # Add to processed contours list
        processed_contours.append([
            idx,
            is_edge,  # Edge flag
            parent,
            child_contours,
            final_area,
            final_perimeter
        ])
        
    
    return processed_contours

def proc_cont_all(self):
    #TOTALS
    # Calculate the area of the image in pixels
    image_area = np.shape(self.image)[0] * np.shape(self.image)[1]
    
    # Calculate the number of parent contours (with or whitout children)
    num_parent_contours = len(self.processed_contours)

    # Calculate the number of child contours
    num_child_contours = sum([len(contour[3]) for contour in self.processed_contours])
    
    # Calculathe the total area of all contours
    cont_total_area = sum([contour[4] for contour in self.processed_contours])
 
    #LESS THAN 50 micron
    # Calculate the number of parent contours with area greater than 50 micron
    num_parent_contours_less_50 = sum([1 for contour in self.processed_contours if contour[4] <= self.area_50])

    # Calculate the number of child contours with area greater than 50 micron
    num_child_contours_less_50 = sum([len(contour[3]) for contour in self.processed_contours if contour[4] <= self.area_50])
    
    # Calculate the total area of contours with diameter less than 50 micron
    cont_total_area_less_50 = sum([contour[4] for contour in self.processed_contours if contour[4] <= self.area_50])
    
    #GREATHER THAN 50 micron
    # Calculate the number of parent contours with area greater than 50 micron
    num_parent_contours_great_50 = sum([1 for contour in self.processed_contours if contour[4] > self.area_50])

    # Calculate the number of child contours with area greater than 50 micron
    num_child_contours_great_50 = sum([len(contour[3]) for contour in self.processed_contours if contour[4] > self.area_50])
    
    # Calculate the total area of contours with diameter greather than 50 micron
    cont_total_area_great_50 = sum([contour[4] for contour in self.processed_contours if contour[4] > self.area_50])
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

    
    
def proc_cont_great_50(self):
    # Segment contours (pores from now on...) with an area greather than the area of a pore with a diameter of 50 micron
    processed_cont_great_50= [
        [
            cont[0], #id
            cont[1], #is_edge
            cont[4], #area
            cont[5], #perimeter
            S := 4 * m.pi * cont[4] / cont[5]**2, #Shape = 4 pi area / perimeter^2
            C := float(4 * m.pi * (cv2.contourArea(cv2.convexHull(cont[2])) -
                             np.sum([cv2.contourArea(cv2.convexHull(contch)) for contch in cont[3]]))/cont[5]**2), #Convex Shape = 4 pi Convex_area / perimeter^2
            m.sqrt(S**2 + C**2) , #Pore elongation
            m.atan(S/C)*180/m.pi, #Pore irragularity (deg)
            2 * m.sqrt(cont[4] / m.pi) / self.calibration, #Equivalent diameter = 2 sqrt(area / pi) / self.calibration
            cv2.fitEllipse(cont[2])[1][1], #Ellipse minor diameter
            cv2.fitEllipse(cont[2])[1][0], #Ellipse major diameter
            cv2.fitEllipse(cont[2])[2], # Ellipse angle
            cont[4] - m.sqrt(cont[5]**2 - 16 * cont[4]) if S < m.pi / 4 else None,  # Rectangle minor side
            cont[4] + m.sqrt(cont[5]**2 - 16 * cont[4]) if S < m.pi / 4 else None #Rectangle major side
            ] 
                for cont in self.processed_contours if cont[4] > self.area_50]
        
    # Shapes of interest are defined in a dictionary with min and max values
    self.shapes = [
        {"name": "circ", "min": 0.8, "max": 1}, # Circular
        {"name": "MLcirc", "min": 0.5, "max": 0.8}, # More or Less circular
        {"name": "shpless", "min": 0.2, "max": 0.5}, # Shapeless
        {"name": "elongated", "min": 0.0, "max": 0.2}, # Elongated 
    ]

    # Sizes of interest are defined in a dictionary with min and max values
    self.sizes = [
        {"name": "edS", "min": 0, "max": 50},           # ed -> Equivalent diameter;        S -> small
        {"name": "edM", "min": 50, "max": 300},         #                                   M -> medium
        {"name": "edL", "min": 300, "max": 1000},       #                                   L -> large
        {"name": "edXL", "min": 100, "max": 100000},    #                                   XL -> extra earge
        {"name": "emdS", "min": 0, "max": 50},          # emd -> Ellipse minor diameter;    S -> small
        {"name": "emdM", "min": 50, "max": 300},        #                                   M -> medium
        {"name": "emdL", "min": 300, "max": 1000},      #                                   L -> large
        {"name": "emdXL", "min": 100, "max": 100000},   #                                   XL -> extra earge   
        {"name": "rmsS", "min": 0, "max": 50},          # rms -> Rectangle minor side;         S -> small
        {"name": "rmsM", "min": 50, "max": 300},        #                                   M -> medium
        {"name": "rmsL", "min": 300, "max": 1000},      #                                   L -> large
        {"name": "rmsXL", "min": 100, "max": 100000},   #                                   XL -> extra earge
    ]                            

    # All the results segmented according shape an size are stored in a dict
    self.processed_cont_great_50_sz = {}

    # Pores are segmented according the defined shape-size combinations.
    for shape in self.shapes:
        for size in self.sizes:
            # Skip invalid shape-size combinations
            if (
                (shape["name"] != "elongated" and size["name"] in ["edS", "edM", "edL", "edXL"]) or
                (shape["name"] != "circ" and size["name"] in ["emdS", "emdM", "emdL", "emdXL"]) or
                ((shape["name"] not in ["circ", "MLcirc"]) and size["name"] in ["rmsS", "rmsM", "rmsL", "rmsXL"])
            ):
                for cont in processed_cont_great_50:
                    # Determine the size metric based on shape and size
                    size_metric = (
                        cont[8] if size["name"] in ["edS", "edM", "edL", "edXL"] else #Equivalent diameter
                        cont[9] if size["name"] in ["emdS", "emdM", "emdL", "emdXL"] else #Ellipse minor diameter
                        cont[12] #Rectangle minor side
                    )

                    # Check if the contour matches the shape and size criteria
                    if shape["min"] < cont[4] <= shape["max"] and size["min"] < size_metric <= size["max"]:
                        # Use (shape["name"], size["name"]) as the key in the dictionary
                        key = (shape["name"], size["name"])
                        if key not in self.processed_cont_great_50_sz:
                            self.processed_cont_great_50_sz[key] = []

                        # Append the processed contour data to the dictionary
                        self.processed_cont_great_50_sz[key].append([
                            cont[0],  # idx
                            str(cont[1]),  # is_edge
                            cont[2],  # area
                            cont[3],  # perimeter
                            cont[4],  # Shape
                            cont[5],  # Convex Shape
                            cont[6],  # Pore elongation
                            cont[7] if cont[7] <= 13.5 else None,  # Irregulars theta <= 13.5°
                            cont[7] if 13.5 < cont[7] <= 22.5 else None,  # Slightly irregulars
                            cont[7] if 22.5 < cont[7] <= 31.5 else None,  # Slightly regulars
                            cont[7] if 31.5 < cont[7] else "",  # Regulars
                            size_metric,  # Size metric (Equivalent diameter, Ellipse minor diameter, etc.)
                            None if size["name"] in ["edS", "edM", "edL", "edXL"] else #For circular shaped pores
                            cont[10] if size["name"] in ["emdS", "emdM", "emdL", "emdXL"] else #Ellipse major diameter
                            cont[13],  # Rectangle major side
                            cont[11] if shape["name"] == "elongated" else None,  # Ellipse angle
                        ])


    # Example: Accessing the processed data
    #print(self.processed_cont_great_50_sz.get(("circ", "edM"), []))

