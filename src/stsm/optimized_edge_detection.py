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

# Example usage in your processing function
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
    
    # Process contours as before...
    processed_contours = []
    
    for idx, (parent_idx, is_edge) in enumerate(zip(parent_indices, is_edge_contour)):
        # Rest of your processing code...
        parent = contours[parent_idx]
        
        # Calculate area, perimeter, find children, etc.
        # ...
        
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