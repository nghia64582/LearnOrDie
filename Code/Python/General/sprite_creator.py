import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageDraw, ImageTk
import requests
from io import BytesIO
import os

class UIGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("UI Element Generator")
        
        # Set default font
        default_font = ("Times New Roman", 13)
        style = ttk.Style()
        style.configure(".", font=default_font)
        
        # Common variables
        self.target_dir = tk.StringVar()
        self.image_name = tk.StringVar()
        
        # Create main frames
        left_frame = ttk.Frame(root)
        left_frame.pack(side=tk.LEFT, padx=5, pady=5, fill="both", expand=True)
        
        right_frame = ttk.Frame(root)
        right_frame.pack(side=tk.RIGHT, padx=5, pady=5, fill="both", expand=True)
        
        self.create_common_frame(left_frame)
        self.create_button_frame(left_frame)
        self.create_container_frame(right_frame)
        self.create_sprite_frame(right_frame)
        
    def create_common_frame(self, parent):
        common_frame = ttk.LabelFrame(parent, text="Common Settings")
        common_frame.pack(padx=5, pady=5, fill="x")
        
        ttk.Label(common_frame, text="Target Directory:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(common_frame, textvariable=self.target_dir).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(common_frame, text="Browse", command=self.browse_directory).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(common_frame, text="Image Name:").grid(row=1, column=0, padx=5, pady=5)
        ttk.Entry(common_frame, textvariable=self.image_name).grid(row=1, column=1, padx=5, pady=5)
    
    def create_button_frame(self, parent):
        button_frame = ttk.LabelFrame(parent, text="Button Generator")
        button_frame.pack(padx=5, pady=5, fill="x")
        
        self.button_width = tk.IntVar(value=100)
        self.button_height = tk.IntVar(value=40)
        self.border_color = tk.StringVar(value="#000000")
        self.border_width = tk.IntVar(value=2)
        self.button_bg = tk.StringVar(value="#FFFFFF")
        self.button_radius = tk.IntVar(value=10)  # New radius variable
        
        ttk.Label(button_frame, text="Width:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(button_frame, textvariable=self.button_width).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(button_frame, text="Height:").grid(row=1, column=0, padx=5, pady=5)
        ttk.Entry(button_frame, textvariable=self.button_height).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(button_frame, text="Border Color:").grid(row=2, column=0, padx=5, pady=5)
        color_frame = ttk.Frame(button_frame)
        color_frame.grid(row=2, column=1, padx=5, pady=5)
        ttk.Entry(color_frame, textvariable=self.border_color).pack(side=tk.LEFT)
        ttk.Button(color_frame, text="Pick", command=lambda: self.pick_color(self.border_color)).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(button_frame, text="Border Width:").grid(row=3, column=0, padx=5, pady=5)
        ttk.Entry(button_frame, textvariable=self.border_width).grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(button_frame, text="Border Radius:").grid(row=4, column=0, padx=5, pady=5)  # New radius input
        ttk.Entry(button_frame, textvariable=self.button_radius).grid(row=4, column=1, padx=5, pady=5)
        
        ttk.Label(button_frame, text="Background:").grid(row=5, column=0, padx=5, pady=5)
        bg_frame = ttk.Frame(button_frame)
        bg_frame.grid(row=5, column=1, padx=5, pady=5)
        ttk.Entry(bg_frame, textvariable=self.button_bg).pack(side=tk.LEFT)
        ttk.Button(bg_frame, text="Pick", command=lambda: self.pick_color(self.button_bg)).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(button_frame, text="Generate Button", command=self.generate_button).grid(row=6, column=0, columnspan=2, pady=10)
    
    def create_container_frame(self, parent):
        container_frame = ttk.LabelFrame(parent, text="Container Generator")
        container_frame.pack(padx=5, pady=5, fill="x")
        
        self.container_width = tk.IntVar(value=200)
        self.container_height = tk.IntVar(value=150)
        self.container_border = tk.IntVar(value=2)
        self.title_height = tk.IntVar(value=30)
        self.container_radius = tk.IntVar(value=15)  # New radius variable
        
        ttk.Label(container_frame, text="Width:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(container_frame, textvariable=self.container_width).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(container_frame, text="Height:").grid(row=1, column=0, padx=5, pady=5)
        ttk.Entry(container_frame, textvariable=self.container_height).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(container_frame, text="Border Width:").grid(row=2, column=0, padx=5, pady=5)
        ttk.Entry(container_frame, textvariable=self.container_border).grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(container_frame, text="Border Radius:").grid(row=3, column=0, padx=5, pady=5)  # New radius input
        ttk.Entry(container_frame, textvariable=self.container_radius).grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(container_frame, text="Title Height:").grid(row=4, column=0, padx=5, pady=5)
        ttk.Entry(container_frame, textvariable=self.title_height).grid(row=4, column=1, padx=5, pady=5)
        
        ttk.Button(container_frame, text="Generate Container", command=self.generate_container).grid(row=5, column=0, columnspan=2, pady=10)
    
    def generate_button(self):
        try:
            width = self.button_width.get()
            height = self.button_height.get()
            border_width = self.border_width.get()
            radius = self.button_radius.get()
            
            # Create image with transparent background
            img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw rounded rectangle
            draw.rounded_rectangle([0, 0, width-1, height-1], radius=radius, 
                                 fill=self.button_bg.get(),
                                 outline=self.border_color.get(),
                                 width=border_width)
            
            self.save_image(img)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def generate_container(self):
        try:
            width = self.container_width.get()
            height = self.container_height.get()
            border = self.container_border.get()
            title_height = self.title_height.get()
            radius = self.container_radius.get()
            
            img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw main rounded rectangle
            draw.rounded_rectangle([0, 0, width-1, height-1], radius=radius,
                                 fill='#FFFFFF', outline='#000000', width=border)
            
            # Draw title separator
            draw.line([(0, title_height), (width, title_height)], fill='#000000', width=border)
            
            self.save_image(img)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def create_sprite_frame(self, parent):
        sprite_frame = ttk.LabelFrame(parent, text="Sprite Generator")
        sprite_frame.pack(padx=5, pady=5, fill="x")
        
        self.sprite_url = tk.StringVar()
        self.sprite_width = tk.IntVar(value=64)
        self.sprite_height = tk.IntVar(value=64)
        
        ttk.Label(sprite_frame, text="Image URL:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(sprite_frame, textvariable=self.sprite_url).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(sprite_frame, text="Target Width:").grid(row=1, column=0, padx=5, pady=5)
        ttk.Entry(sprite_frame, textvariable=self.sprite_width).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(sprite_frame, text="Target Height:").grid(row=2, column=0, padx=5, pady=5)
        ttk.Entry(sprite_frame, textvariable=self.sprite_height).grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Button(sprite_frame, text="Generate Sprite", command=self.generate_sprite).grid(row=3, column=0, columnspan=2, pady=10)
    
    def pick_color(self, color_var):
        color = colorchooser.askcolor(color_var.get())
        if color[1]:
            color_var.set(color[1])
    
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.target_dir.set(directory)
    
    def generate_sprite(self):
        try:
            # Download image from URL
            response = requests.get(self.sprite_url.get())
            img = Image.open(BytesIO(response.content))
            
            # Resize image
            img = img.resize((self.sprite_width.get(), self.sprite_height.get()), Image.Resampling.LANCZOS)
            
            self.save_image(img)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def save_image(self, img):
        if not self.target_dir.get() or not self.image_name.get():
            messagebox.showerror("Error", "Please specify target directory and image name")
            return
        
        # Ensure directory exists
        os.makedirs(self.target_dir.get(), exist_ok=True)
        
        # Save image
        filename = os.path.join(self.target_dir.get(), self.image_name.get())
        if not filename.lower().endswith('.png'):
            filename += '.png'
        
        img.save(filename)
        messagebox.showinfo("Success", f"Image saved as {filename}")

if __name__ == '__main__':
    root = tk.Tk()
    app = UIGenerator(root)
    root.mainloop()