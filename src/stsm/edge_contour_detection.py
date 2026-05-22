import cv2
import numpy as np
import h5py
import time

def detect_edge_contours(image, contours, border_size=1):
    """
    Efficiently identify which contours touch the edge of the image.
    
    Args:
        image: The original binary image
        contours: List of contours to check
        border_size: Size of the border to consider (default: 1 pixel)
        
    Returns:
        List of booleans indicating whether each contour touches the edge
    """
    height, width = image.shape[:2]
    
    # Create a mask for the image border
    border_mask = np.zeros_like(image, dtype=np.uint8)
    
    # Draw the border on the mask
    cv2.rectangle(border_mask, (0, 0), (width-1, height-1), 255, border_size)
    
    # Check each contour for intersection with the border
    is_edge_contour = []
    
    for contour in contours:
        # Create a mask for this contour
        contour_mask = np.zeros_like(image, dtype=np.uint8)
        cv2.drawContours(contour_mask, [contour], 0, 255, -1)
        
        # Check if there's any intersection between the contour and the border
        intersection = cv2.bitwise_and(contour_mask, border_mask)
        touches_edge = np.any(intersection > 0)
        
        is_edge_contour.append(touches_edge)
    
    return is_edge_contour

def enhanced_process_mosaic(image):
    """
    Process the loaded mosaic image to find contours with edge detection.
    
    Args:
        image: Binary image to process
        
    Returns:
        List of [index, is_edge, parent_contour, [child_contours], area, perimeter]
    """
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
    
    # Detect which parent contours touch the edge
    is_edge_contour = detect_edge_contours(image, parent_contours)
    
    # Create a list to store processed contours with their properties and hierarchy
    # Format: [index, is_edge, parent_contour, [child_contours], area, perimeter]
    processed_contours = []
    
    # Process each parent contour
    for idx, parent_idx in enumerate(parent_indices):
        parent = contours[parent_idx]
        is_edge = is_edge_contour[idx]
        
        # Calculate initial area and perimeter for the parent
        parent_area = cv2.contourArea(parent)
        parent_perimeter = cv2.arcLength(parent, True)
        
        # Find all children of this parent
        child_idx = hierarchy[parent_idx][2]  # First child
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
        
        # Add to processed contours list with all information
        processed_contours.append([
            idx,                # Index
            is_edge,           # Edge flag (True/False)
            parent,            # Parent contour
            child_contours,    # List of child contours
            final_area,        # Area (parent - children)
            final_perimeter    # Perimeter (parent + children)
        ])
    
    return processed_contours

def save_enhanced_contours_hdf5(contour_data, filename):
    """
    Save contours with edge information to HDF5 file.
    
    Args:
        contour_data: List of [index, is_edge, parent, [children], area, perimeter]
        filename: Output HDF5 filename
    """
    with h5py.File(filename, 'w') as f:
        # Create a group for all contours
        contours_group = f.create_group("contours")
        
        # Store metadata about the dataset
        f.attrs['num_contours'] = len(contour_data)
        f.attrs['creation_date'] = time.ctime()
        
        # Create groups for edge and interior contours for easy filtering
        edge_group = f.create_group("edge_contours")
        interior_group = f.create_group("interior_contours")
        
        # Create a group for each contour with its index as the name for direct access
        for idx, is_edge, parent, children, area, perimeter in contour_data:
            # Use the index as the group name for direct access
            contour_group = contours_group.create_group(f"{idx}")
            
            # Store the index and edge flag as attributes
            contour_group.attrs['index'] = idx
            contour_group.attrs['is_edge'] = is_edge
            contour_group.attrs['area'] = area
            contour_group.attrs['perimeter'] = perimeter
            
            # Save parent contour
            parent_dataset = contour_group.create_dataset('parent', data=parent)
            
            # Save metadata about children
            contour_group.attrs['num_children'] = len(children)
            
            # Create a group for children
            if children:
                children_group = contour_group.create_group('children')
                for j, child in enumerate(children):
                    child_dataset = children_group.create_dataset(f"{j}", data=child)
            
            # Add reference to edge or interior group
            if is_edge:
                edge_group[f"{idx}"] = contour_group.ref
            else:
                interior_group[f"{idx}"] = contour_group.ref
    
    print(f"Enhanced contours saved to {filename}")

def get_contours_by_location(filename, edge_only=False, interior_only=False):
    """
    Get contours filtered by their location (edge or interior).
    
    Args:
        filename: HDF5 file containing contours
        edge_only: If True, return only edge contours
        interior_only: If True, return only interior contours
        
    Returns:
        List of contours matching the criteria
    """
    results = []
    
    with h5py.File(filename, 'r') as f:
        # Determine which group to use for filtering
        if edge_only:
            if "edge_contours" not in f:
                return []
            indices = [k for k in f["edge_contours"].keys()]
        elif interior_only:
            if "interior_contours" not in f:
                return []
            indices = [k for k in f["interior_contours"].keys()]
        else:
            if "contours" not in f:
                return []
            indices = [k for k in f["contours"].keys()]
        
        # Get the contours
        for idx in indices:
            contour_group = f[f"contours/{idx}"]
            
            # Get attributes
            index = contour_group.attrs['index']
            is_edge = contour_group.attrs['is_edge']
            area = contour_group.attrs['area']
            perimeter = contour_group.attrs['perimeter']
            
            # Get the parent contour
            parent = contour_group['parent'][:]
            
            # Get the children contours
            children = []
            if 'children' in contour_group:
                children_group = contour_group['children']
                for child_name in sorted(children_group.keys(), key=int):
                    child = children_group[child_name][:]
                    children.append(child)
            
            # Add to results
            results.append([index, is_edge, parent, children, area, perimeter])
    
    return results

# Example usage
def demonstrate_edge_detection():
    # Create a sample binary image
    image = np.zeros((500, 500), dtype=np.uint8)
    
    # Draw some shapes - some touching the edge, some not
    # Interior shapes
    cv2.circle(image, (250, 250), 50, 255, -1)  # Interior circle
    cv2.rectangle(image, (150, 150), (200, 200), 255, -1)  # Interior rectangle
    
    # Edge shapes
    cv2.circle(image, (50, 50), 60, 255, -1)  # Circle touching edge
    cv2.rectangle(image, (400, 0), (500, 100), 255, -1)  # Rectangle on edge
    
    # Process the image
    processed_contours = enhanced_process_mosaic(image)
    
    # Print results
    print(f"Found {len(processed_contours)} contours")
    
    edge_count = sum(1 for _, is_edge, _, _, _, _ in processed_contours if is_edge)
    interior_count = len(processed_contours) - edge_count
    
    print(f"Edge contours: {edge_count}")
    print(f"Interior contours: {interior_count}")
    
    # Save to HDF5
    save_enhanced_contours_hdf5(processed_contours, "edge_contours.h5")
    
    # Retrieve filtered contours
    edge_contours = get_contours_by_location("edge_contours.h5", edge_only=True)
    interior_contours = get_contours_by_location("edge_contours.h5", interior_only=True)
    
    print(f"Retrieved {len(edge_contours)} edge contours")
    print(f"Retrieved {len(interior_contours)} interior contours")
    
    # Visualize the results
    visualization = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    
    # Draw edge contours in red
    for _, _, parent, children, _, _ in edge_contours:
        cv2.drawContours(visualization, [parent], -1, (0, 0, 255), 2)
        cv2.drawContours(visualization, children, -1, (0, 0, 255), 1)
    
    # Draw interior contours in green
    for _, _, parent, children, _, _ in interior_contours:
        cv2.drawContours(visualization, [parent], -1, (0, 255, 0), 2)
        cv2.drawContours(visualization, children, -1, (0, 255, 0), 1)
    
    # Save the visualization
    cv2.imwrite("edge_detection_result.png", visualization)
    print("Visualization saved to edge_detection_result.png")

# Run the demonstration
if __name__ == "__main__":
    demonstrate_edge_detection()