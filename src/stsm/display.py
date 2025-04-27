from PIL import Image, ImageTk
import tkinter as tk
import cv2

def update_display(self):
    if not self.images:
        return
        
    # Hide the "no image" label
    self.no_image_label.place_forget()
    
    # Clear the canvas
    self.canvas.delete("all")
    
    # Get canvas dimensions
    canvas_width = self.canvas.winfo_width()
    canvas_height = self.canvas.winfo_height()
    
    # If canvas size is not yet determined, use default values
    if canvas_width <= 1:
        canvas_width = 800
    if canvas_height <= 1:
        canvas_height = 600
        
    # Calculate the scale factor to fit images in the canvas
    img_height, img_width = self.images[0].shape
    scale_x = canvas_width / img_width
    scale_y = canvas_height / img_height
    scale = min(scale_x, scale_y)
    
    # Calculate new dimensions
    new_width = int(img_width * scale)
    new_height = int(img_height * scale)
    
    # Convert OpenCV images to PIL format and resize
    self.tk_images = []
    for img in self.images:
        # Convert to PIL Image
        pil_img = Image.fromarray(img)
        # Resize to fit canvas
        pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
        # Convert to PhotoImage
        tk_img = ImageTk.PhotoImage(pil_img)
        self.tk_images.append(tk_img)
    
    # Calculate position to center the image
    x_pos = (canvas_width - new_width) // 2
    y_pos = (canvas_height - new_height) // 2
    
    # Display images in the specified order, respecting visibility
    for i in reversed(range(len(self.layer_order))):  # Reversed to draw bottom layer first
        layer_idx = self.layer_order[i]
        if self.layer_visibility[layer_idx].get():
            self.canvas.create_image(
                x_pos, y_pos,
                anchor=tk.NW,
                image=self.tk_images[layer_idx]
            )

def update_proc_display(self):
    """Update the display in the processing tab"""
    if not self.proc_images and not self.roi_mode:
        return
        
    # Hide the "no image" label
    self.proc_no_image_label.place_forget()
    
    # Clear the canvas
    self.proc_canvas.delete("all")
    
    # Get canvas dimensions
    canvas_width = self.proc_canvas.winfo_width()
    canvas_height = self.proc_canvas.winfo_height()
    
    # If canvas size is not yet determined, use default values
    if canvas_width <= 1:
        canvas_width = 800
    if canvas_height <= 1:
        canvas_height = 600
    
    # If in ROI selection mode, display the original image for ROI selection
    if self.roi_mode and self.roi_image is not None:
        # Calculate the scale factor to fit image in the canvas
        img_height, img_width = self.roi_image.shape[:2]
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        scale = min(scale_x, scale_y)
        self.roi_scale = scale
        
        # Calculate new dimensions
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Convert to PIL Image
        rgb_image = cv2.cvtColor(self.roi_image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_image)
        
        # Resize to fit canvas
        pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
        
        # Convert to PhotoImage
        tk_img = ImageTk.PhotoImage(pil_img)
        self.roi_tk_image = tk_img  # Store reference to prevent garbage collection
        
        # Calculate position to center the image
        x_pos = (canvas_width - new_width) // 2
        y_pos = (canvas_height - new_height) // 2
        
        # Display the image
        self.proc_canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=tk_img, tags="roi_image")
        
        # Show ROI instruction label
        if self.roi_instruction_window is None:
            self.roi_instruction_window = self.proc_canvas.create_window(
                canvas_width // 2, 
                y_pos + new_height + 10,
                window=self.roi_instruction_label
            )
        
        # Store the image position for ROI calculations
        self.roi_image_pos = (x_pos, y_pos)
        return
        
    # If we have processed images, display them
    if self.proc_images:
        # Calculate the scale factor to fit images in the canvas
        img_height, img_width = self.proc_images[0].shape[:2]
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        scale = min(scale_x, scale_y)
        
        # Calculate new dimensions
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Convert OpenCV images to PIL format and resize
        self.proc_tk_images = []
        for img in self.proc_images:
            # Convert to PIL Image (handle both grayscale and color images)
            if len(img.shape) == 2:  # Grayscale
                pil_img = Image.fromarray(img)
            else:  # Color (BGR)
                pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            
            # Resize to fit canvas
            pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage
            tk_img = ImageTk.PhotoImage(pil_img)
            self.proc_tk_images.append(tk_img)
        
        # Calculate position to center the image
        x_pos = (canvas_width - new_width) // 2
        y_pos = (canvas_height - new_height) // 2
        
        # Display images in the specified order, respecting visibility
        for i in reversed(range(len(self.proc_layer_order))):  # Reversed to draw bottom layer first
            layer_idx = self.proc_layer_order[i]
            if self.proc_layer_visibility[layer_idx].get():
                self.proc_canvas.create_image(
                    x_pos, y_pos,
                    anchor=tk.NW,
                    image=self.proc_tk_images[layer_idx]
                )
