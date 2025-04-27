import tkinter as tk
from display import update_display, update_proc_display

def show_layer_controls(self):
    """Show the unified layer control frame after images are loaded"""
    if not self.controls_visible:
        # Pack the unified layer control frame
        self.unified_layer_frame.pack(pady=10, fill=tk.X)
        # Pack the save button frame
        self.save_frame.pack(pady=10, fill=tk.X)
        self.controls_visible = True
        
        # Update the layer rows to reflect the current order
        update_layer_rows(self)

def show_proc_layer_controls(self):
    """Show the processing tab layer control frame after images are loaded"""
    if not self.proc_controls_visible:
        # Pack the unified layer control frame
        self.proc_unified_layer_frame.pack(pady=10, fill=tk.X)
        # Pack the save button frame
        self.proc_save_frame.pack(pady=10, fill=tk.X)
        self.proc_controls_visible = True
        
        # Update the layer rows to reflect the current order
        update_proc_layer_rows(self)

def hide_layer_controls(self):
    """Hide the unified layer control frame"""
    if self.controls_visible:
        # Unpack the unified layer control frame
        self.unified_layer_frame.pack_forget()
        self.controls_visible = False

def hide_proc_layer_controls(self):
    """Hide the processing tab layer control frame"""
    if self.proc_controls_visible:
        # Unpack the unified layer control frame
        self.proc_unified_layer_frame.pack_forget()
        self.proc_save_frame.pack_forget()
        self.proc_controls_visible = False

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
            command=lambda idx=i: move_layer_up_by_index(self, idx)
        )
        self.layer_rows[i]['down_button'].config(
            command=lambda idx=i: move_layer_down_by_index(self, idx)
        )
        
        # Enable/disable up/down buttons based on position
        self.layer_rows[i]['up_button'].config(state=tk.NORMAL if i > 0 else tk.DISABLED)
        self.layer_rows[i]['down_button'].config(
            state=tk.NORMAL if i < len(self.layer_order) - 1 else tk.DISABLED
        )

def update_proc_layer_rows(self):
    """Update the processing tab layer rows to reflect the current layer order"""
    # Reorder the layer rows based on the current proc_layer_order
    for i, layer_idx in enumerate(self.proc_layer_order):
        # Update the label text
        self.proc_layer_rows[i]['label'].config(text=self.proc_layer_names[layer_idx])
        
        # Update the checkbutton variable
        self.proc_layer_rows[i]['visibility'].config(variable=self.proc_layer_visibility[layer_idx])
        
        # Update the up/down button commands
        self.proc_layer_rows[i]['up_button'].config(
            command=lambda idx=i: move_proc_layer_up_by_index(self, idx)
        )
        self.proc_layer_rows[i]['down_button'].config(
            command=lambda idx=i: move_proc_layer_down_by_index(self, idx)
        )
        
        # Enable/disable up/down buttons based on position
        self.proc_layer_rows[i]['up_button'].config(state=tk.NORMAL if i > 0 else tk.DISABLED)
        self.proc_layer_rows[i]['down_button'].config(
            state=tk.NORMAL if i < len(self.proc_layer_order) - 1 else tk.DISABLED
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
    update_layer_rows(self)
    
    # Update the display
    update_display(self)

def move_proc_layer_up_by_index(self, index):
    """Move a processing tab layer up in the order based on its current position"""
    if index <= 0 or index >= len(self.proc_layer_order):
        return
        
    # Get the layer indices at the current and target positions
    current_layer = self.proc_layer_order[index]
    target_layer = self.proc_layer_order[index - 1]
    
    # Swap them in the layer_order list
    self.proc_layer_order[index] = target_layer
    self.proc_layer_order[index - 1] = current_layer
    
    # Update the layer rows
    update_proc_layer_rows(self)
    
    # Update the display
    update_proc_display(self)

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
    update_layer_rows(self)
    
    # Update the display
    update_display(self)

def move_proc_layer_down_by_index(self, index):
    """Move a processing tab layer down in the order based on its current position"""
    if index < 0 or index >= len(self.proc_layer_order) - 1:
        return
        
    # Get the layer indices at the current and target positions
    current_layer = self.proc_layer_order[index]
    target_layer = self.proc_layer_order[index + 1]
    
    # Swap them in the layer_order list
    self.proc_layer_order[index] = target_layer
    self.proc_layer_order[index + 1] = current_layer
    
    # Update the layer rows
    update_proc_layer_rows(self)
    
    # Update the display
    update_proc_display(self)