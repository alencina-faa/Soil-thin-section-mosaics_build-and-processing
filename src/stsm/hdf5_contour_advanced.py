import h5py
import numpy as np
import cv2
import time

# Function to add a new contour to an existing HDF5 file
def add_contour_to_hdf5(filename, index, parent, children):
    with h5py.File(filename, 'a') as f:  # 'a' mode for append
        # Check if the contour already exists
        contour_path = f"contours/{index}"
        if contour_path in f:
            print(f"Contour with index {index} already exists. Use update_contour instead.")
            return False
        
        # Get the contours group or create it if it doesn't exist
        if 'contours' not in f:
            contours_group = f.create_group("contours")
            f.attrs['num_contours'] = 0
        else:
            contours_group = f['contours']
        
        # Create a new group for this contour
        contour_group = contours_group.create_group(f"{index}")
        contour_group.attrs['index'] = index
        
        # Save parent contour
        parent_dataset = contour_group.create_dataset('parent', data=parent)
        parent_dataset.attrs['shape'] = parent.shape
        parent_dataset.attrs['dtype'] = str(parent.dtype)
        
        # Save children
        contour_group.attrs['num_children'] = len(children)
        if children:
            children_group = contour_group.create_group('children')
            for j, child in enumerate(children):
                child_dataset = children_group.create_dataset(f"{j}", data=child)
                child_dataset.attrs['shape'] = child.shape
                child_dataset.attrs['dtype'] = str(child.dtype)
        
        # Update metadata
        f.attrs['num_contours'] = f.attrs['num_contours'] + 1
        f.attrs['last_modified'] = time.ctime()
        
        return True

# Function to update an existing contour
def update_contour_in_hdf5(filename, index, parent, children):
    with h5py.File(filename, 'a') as f:
        # Check if the contour exists
        contour_path = f"contours/{index}"
        if contour_path not in f:
            print(f"Contour with index {index} not found. Use add_contour instead.")
            return False
        
        # Delete the existing contour group
        del f[contour_path]
        
        # Create a new group for this contour
        contour_group = f['contours'].create_group(f"{index}")
        contour_group.attrs['index'] = index
        
        # Save parent contour
        parent_dataset = contour_group.create_dataset('parent', data=parent)
        parent_dataset.attrs['shape'] = parent.shape
        parent_dataset.attrs['dtype'] = str(parent.dtype)
        
        # Save children
        contour_group.attrs['num_children'] = len(children)
        if children:
            children_group = contour_group.create_group('children')
            for j, child in enumerate(children):
                child_dataset = children_group.create_dataset(f"{j}", data=child)
                child_dataset.attrs['shape'] = child.shape
                child_dataset.attrs['dtype'] = str(child.dtype)
        
        # Update metadata
        f.attrs['last_modified'] = time.ctime()
        
        return True

# Function to delete a contour
def delete_contour_from_hdf5(filename, index):
    with h5py.File(filename, 'a') as f:
        # Check if the contour exists
        contour_path = f"contours/{index}"
        if contour_path not in f:
            print(f"Contour with index {index} not found.")
            return False
        
        # Delete the contour group
        del f[contour_path]
        
        # Update metadata
        f.attrs['num_contours'] = f.attrs['num_contours'] - 1
        f.attrs['last_modified'] = time.ctime()
        
        return True

# Function to search for contours by properties
def search_contours_by_area(filename, min_area=None, max_area=None, limit=10):
    results = []
    
    with h5py.File(filename, 'r') as f:
        if 'contours' not in f:
            return results
        
        contours_group = f['contours']
        
        # Iterate through contours
        for idx_str in contours_group:
            contour_group = contours_group[idx_str]
            
            # Get the parent contour
            parent = contour_group['parent'][:]
            
            # Calculate area
            area = cv2.contourArea(parent)
            
            # Check if it meets the criteria
            if (min_area is None or area >= min_area) and (max_area is None or area <= max_area):
                # Get the children if needed
                children = []
                if 'children' in contour_group:
                    children_group = contour_group['children']
                    for child_name in sorted(children_group.keys(), key=int):
                        child = children_group[child_name][:]
                        children.append(child)
                
                # Add to results
                results.append([int(idx_str), parent, children, area])
                
                # Check limit
                if limit is not None and len(results) >= limit:
                    break
    
    # Sort by area
    results.sort(key=lambda x: x[3])
    
    # Remove the area from the results to match the original format
    return [[idx, parent, children] for idx, parent, children, _ in results]

# Example usage of advanced features
def demonstrate_advanced_features():
    # Create a new HDF5 file with some initial contours
    contour_data = create_sample_contours(10)
    save_contours_hdf5_optimized(contour_data, "contours_advanced.h5")
    
    # Add a new contour
    new_index = 100
    new_parent = np.array([[[100, 100]], [[150, 100]], [[150, 150]], [[100, 150]]], dtype=np.int32)
    new_children = [np.array([[[110, 110]], [[140, 110]], [[140, 140]], [[110, 140]]], dtype=np.int32)]
    
    print(f"Adding new contour with index {new_index}")
    add_contour_to_hdf5("contours_advanced.h5", new_index, new_parent, new_children)
    
    # Verify the new contour was added
    contour = get_contour_by_index("contours_advanced.h5", new_index)
    print(f"Retrieved contour {new_index}: Parent shape: {contour[1].shape}, Children: {len(contour[2])}")
    
    # Update the contour
    updated_parent = np.array([[[100, 100]], [[200, 100]], [[200, 200]], [[100, 200]]], dtype=np.int32)
    print(f"Updating contour {new_index}")
    update_contour_in_hdf5("contours_advanced.h5", new_index, updated_parent, new_children)
    
    # Verify the update
    contour = get_contour_by_index("contours_advanced.h5", new_index)
    print(f"Updated contour {new_index}: Parent shape: {contour[1].shape}")
    
    # Search for contours by area
    print("Searching for contours with area between 1000 and 5000")
    matching_contours = search_contours_by_area("contours_advanced.h5", min_area=1000, max_area=5000)
    print(f"Found {len(matching_contours)} matching contours")
    
    # Delete a contour
    print(f"Deleting contour {new_index}")
    delete_contour_from_hdf5("contours_advanced.h5", new_index)
    
    # Verify deletion
    indices = list_contour_indices("contours_advanced.h5")
    print(f"Remaining contour indices: {indices}")
    if str(new_index) not in indices:
        print(f"Contour {new_index} successfully deleted")

# Run the demonstration
if __name__ == "__main__":
    demonstrate_advanced_features()