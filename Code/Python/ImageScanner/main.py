import tkinter as tk
from tkinter import filedialog, messagebox
import pyautogui
from PIL import Image, ImageTk
import os
import time

class ScreenImageDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Image Detector")
        self.root.geometry("800x600") # Increased window size
        self.root.resizable(True, True)

        # Set default image folder
        self.image_folder = "images"
        self.target_images = {} # Stores {'image_name': PIL_Image_Object}
        self.scanning_active = False
        self.scan_job_id = None
        self.detection_results_widgets = {} # Stores {'image_name': {'label': tk.Label}}

        self.setup_ui()
        self.load_images_on_startup() # Load images automatically on startup

    def setup_ui(self):
        # --- Top Frame for Controls ---
        control_frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE, padx=10, pady=10)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        # Scan Controls
        self.start_button = tk.Button(control_frame, text="Start Scanning", command=self.start_scanning, state=tk.DISABLED)
        self.start_button.grid(row=0, column=0, padx=5, pady=5)
        self.stop_button = tk.Button(control_frame, text="Stop Scanning", command=self.stop_scanning, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)

        self.status_label = tk.Label(control_frame, text="Status: Initializing...", fg="blue")
        self.status_label.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # Scan Delay Slider
        tk.Label(control_frame, text="Scan Delay (ms):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.scan_delay_scale = tk.Scale(control_frame, from_=10, to=1000, orient=tk.HORIZONTAL,
                                         label="", length=200, resolution=10)
        self.scan_delay_scale.set(50) # Default to 50ms (20 FPS)
        self.scan_delay_scale.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")


        # Configure column weights for resizing
        control_frame.grid_columnconfigure(2, weight=1) # Make status label expand

        # --- Results Display Area ---
        results_frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE, padx=10, pady=10)
        results_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(results_frame, text="Detection Results:", font=("Arial", 12, "bold")).pack(pady=5)

        self.results_canvas = tk.Canvas(results_frame, bg="lightgray", bd=1, relief=tk.SUNKEN)
        self.results_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.results_scrollbar = tk.Scrollbar(results_frame, orient="vertical", command=self.results_canvas.yview)
        self.results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.results_canvas.configure(yscrollcommand=self.results_scrollbar.set)
        # Bind to <Configure> event of the canvas to update scrollregion when canvas size changes
        self.results_canvas.bind('<Configure>', self.on_canvas_configure)

        self.results_inner_frame = tk.Frame(self.results_canvas, bg="lightgray")
        # Create a window in the canvas to hold the inner frame
        self.results_canvas.create_window((0, 0), window=self.results_inner_frame, anchor="nw")

        # Bind to <Configure> event of the inner frame to update scrollregion when inner frame content changes
        self.results_inner_frame.bind('<Configure>', lambda e: self.results_canvas.configure(scrollregion = self.results_canvas.bbox("all")))

        self.root.update_idletasks() # Update to get initial size for scrollbar

    def on_canvas_configure(self, event):
        # Update the canvas scroll region to encompass the inner frame's content
        self.results_canvas.itemconfig(self.results_canvas.winfo_children()[0], width=event.width)
        self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))


    def load_images_on_startup(self):
        # Create the 'images' folder if it doesn't exist
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)
            messagebox.showinfo("Folder Created", f"The default image folder '{self.image_folder}' has been created. Please place your target images inside this folder.")

        self.target_images = {}
        self.clear_results_display() # Clear previous results display

        image_files = [f for f in os.listdir(self.image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]

        if not image_files:
            messagebox.showwarning("No Images Found", f"No supported image files found in '{self.image_folder}'. Please add images to this folder.")
            self.start_button.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Ready (No images loaded)", fg="orange")
            return

        for filename in image_files:
            try:
                filepath = os.path.join(self.image_folder, filename)
                img = Image.open(filepath)
                self.target_images[filename] = img

                # Create widgets for each image
                row_frame = tk.Frame(self.results_inner_frame, bg="lightgray", bd=1, relief=tk.RAISED)
                row_frame.pack(fill=tk.X, padx=5, pady=2)

                img_label = tk.Label(row_frame, text=f"{filename}: Not found", anchor="w", bg="lightgray")
                img_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)

                # Store references to widgets
                self.detection_results_widgets[filename] = {'label': img_label}

            except Exception as e:
                print(f"Error loading image {filename}: {e}")
                messagebox.showerror("Image Load Error", f"Could not load image '{filename}': {e}")

        if self.target_images:
            self.start_button.config(state=tk.NORMAL)
            self.status_label.config(text=f"Status: Loaded {len(self.target_images)} images. Ready to scan.", fg="green")
        else:
            self.start_button.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Ready (No images loaded)", fg="orange")

        self.results_canvas.update_idletasks()
        self.results_canvas.config(scrollregion=self.results_canvas.bbox("all"))


    def clear_results_display(self):
        for widget in self.results_inner_frame.winfo_children():
            widget.destroy()
        self.detection_results_widgets = {}
        self.results_canvas.update_idletasks()
        self.results_canvas.config(scrollregion=self.results_canvas.bbox("all"))

    def start_scanning(self):
        if not self.target_images:
            messagebox.showwarning("No Images", "No images loaded. Please ensure images are in the 'images' folder.")
            return

        self.scanning_active = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Status: Scanning...", fg="green")
        self.perform_scan()

    def stop_scanning(self):
        self.scanning_active = False
        if self.scan_job_id:
            self.root.after_cancel(self.scan_job_id)
            self.scan_job_id = None
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Stopped.", fg="red")

    def perform_scan(self):
        if not self.scanning_active:
            return

        try:
            # Take a screenshot of the entire screen
            # pyautogui.screenshot() can be slow, consider region if possible
            screenshot = pyautogui.screenshot()

            for filename, img_obj in self.target_images.items():
                # Use pyautogui.locateOnScreen for detection
                location = pyautogui.locateOnScreen(img_obj, grayscale=False, confidence=0.9)

                result_label = self.detection_results_widgets[filename]['label']

                if location:
                    # Found the image, display its coordinates
                    x, y, width, height = location
                    result_label.config(text=f"{filename}: Found at X:{x}, Y:{y}, W:{width}, H:{height}", fg="darkgreen")
                else:
                    # Image not found
                    result_label.config(text=f"{filename}: Not found", fg="gray")

        except pyautogui.PyAutoGUIException as e:
            self.status_label.config(text=f"Error during scan: {e}", fg="red")
            print(f"PyAutoGUI Error: {e}")
            self.stop_scanning() # Stop scanning on error
            messagebox.showerror("Scanning Error", f"An error occurred during screen scanning: {e}\nScanning stopped.")
        except Exception as e:
            self.status_label.config(text=f"An unexpected error occurred: {e}", fg="red")
            print(f"Unexpected Error: {e}")
            self.stop_scanning()
            messagebox.showerror("Unexpected Error", f"An unexpected error occurred: {e}\nScanning stopped.")

        # Schedule the next scan based on the slider value
        scan_delay_ms = self.scan_delay_scale.get()
        self.scan_job_id = self.root.after(scan_delay_ms, self.perform_scan)

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenImageDetectorApp(root)
    root.mainloop()
