import tkinter as tk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import random # Used for generating dummy data

# Create a sample DataFrame to simulate initial data
initial_data = {
    'time': [datetime.datetime(2025, 1, 1), datetime.datetime(2025, 1, 2), datetime.datetime(2025, 1, 3)],
    'score': [75, 82, 65]
}
initial_df = pd.DataFrame(initial_data)
initial_df['time'] = pd.to_datetime(initial_df['time'])

# Global variables for the plot and canvas
fig, ax = plt.subplots(figsize=(8, 6))
canvas = None

def plot_data(df):
    """
    Plots data on the Matplotlib chart. Clears previous data if any.
    Args:
        df (pd.DataFrame): DataFrame containing 'time' and 'score' columns.
    """
    global fig, ax, canvas

    # Clear previous plot
    ax.clear()

    # Convert the time column to matplotlib's date format
    x = pd.to_datetime(df['time'])
    y = df['score']

    # Plot the data
    ax.scatter(x, y, color='blue', label='Score Data')
    ax.plot(x, y, color='blue', linestyle='--', linewidth=1)
    
    # Set the y-axis limits (flexible if not set)
    ax.set_ylim(50, 100)
    
    # Label axes and set title
    ax.set_xlabel('Time')
    ax.set_ylabel('Score')
    ax.set_title('Flexible Score Chart')
    ax.legend()
    
    # Format the x-axis to show dates nicely
    fig.autofmt_xdate()
    
    # Draw the canvas
    fig.tight_layout()
    canvas.draw()

def create_chart(parent, df):
    """
    Creates the initial Matplotlib chart canvas and embeds it in the Tkinter window.
    """
    global fig, ax, canvas

    # Create a canvas to hold the Matplotlib figure
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # Plot the initial data
    plot_data(df)

def reload_data():
    """
    Simulates loading new data and updates the chart.
    """
    print("Reloading data...")
    # Create new dummy data
    new_data = {
        'time': [datetime.datetime(2025, 2, 1), datetime.datetime(2025, 2, 2), datetime.datetime(2025, 2, 3), datetime.datetime(2025, 2, 4)],
        'score': [random.randint(60, 95) for _ in range(4)]
    }
    new_df = pd.DataFrame(new_data)
    
    # Update the chart with the new data
    plot_data(new_df)
    print("Chart updated!")

def main():
    root = tk.Tk()
    root.title("Dynamic Matplotlib Chart in Tkinter")
    root.geometry("900x700")

    # Frame to hold the chart
    chart_frame = ttk.Frame(root)
    chart_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=10, pady=10)

    # Create and display the initial chart
    create_chart(chart_frame, initial_df)

    # Button to reload the data and update the chart
    reload_button = ttk.Button(root, text="Reload Data", command=reload_data)
    reload_button.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()