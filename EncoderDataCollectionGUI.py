import tkinter as tk
from tkinter import ttk
import os
import subprocess
from plot_csv import plot_encoders, replot_encoder_data
from EncoderDataCollector import EncoderDataCollector


# Instruction text
instructions = [
    "For data collection:",
    "1. Enter a name for your data coollection in the text box.",
    "   Use this convention:",
    "                      'Serial-Number_direction_Voltage'",
        "                      Example: 616-00021_CCW_3.8V",
    "2. Click 'Collect Data' to begin logging encoder data.",
    "3. Wait for the data collection to complete.",
    "           This should take a few minutes",
    "           The plots will appear when done",
    "           Close the plots, they will auto save",
    "  When done Click 'Quit Program' to close the application safely.",
    "","For plotting of data: ",
    "Unless replotting, no need for these steps, data collection collects plots.",
    "1. Select a log file from the dropdown menu.",
    "2. Click 'Plot data' to visualize the encoder readings.",
    "3. The plots will populate when done. ",
    "           You can close the plots, they will autosave",
    "       Click 'Quit Program' to close the application safely."
]




# Directory containing log files
LOG_DIR = "encoder_logs"

# Ensure the directory exists
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Function to get file names from encoder_logs directory
def get_log_files():
    return sorted([f for f in os.listdir(LOG_DIR) if os.path.isfile(os.path.join(LOG_DIR, f))])

# Callback functions for buttons
def on_collect_data_button_click():
    input_text = entry_box.get()
    print(f"Collect Data clicked with input: {input_text}")
    EncoderDataCollector(input_text)




def on_plot_data_button_click():
    selected = dropdown_var.get()
    print(f"Plot data clicked for: {selected}")
    replot_encoder_data(selected)

def on_quit_button_click():
    print("Quit Program clicked")
    root.destroy()

def on_dropdown_select(event):
    selected = dropdown_var.get()
    print(f"Selected log file: {selected}")

# Create the main application window
root = tk.Tk()
root.title("I2 Encoder Inspection Tool")
root.geometry("800x550")
root.configure(bg="#1e1e1e")  # Dark background

# Style for dark-themed ttk widgets
style = ttk.Style()
style.theme_use("default")
style.configure("TCombobox",
                fieldbackground="#2e2e2e",
                background="#2e2e2e",
                foreground="white")

# Dropdown menu
dropdown_var = tk.StringVar()
log_files = get_log_files()
dropdown = ttk.Combobox(root, textvariable=dropdown_var, values=log_files, state="readonly", width=20)
dropdown.bind("<<ComboboxSelected>>", on_dropdown_select)
dropdown.place(x=30, y=80)

# "Plot data" button
plot_data_button = tk.Button(root, text="Plot data", command=on_plot_data_button_click,
                    bg="#333333", fg="white", activebackground="#444444")
plot_data_button.place(x=220, y=78)

# Entry box to the left of "Collect Data"
entry_box = tk.Entry(root, width=20, bg="#2e2e2e", fg="white", insertbackground="white")
entry_box.place(x=30, y=30)

# "Collect Data" button
collect_data_button = tk.Button(root, text="Collect Data", command=on_collect_data_button_click,
                    bg="#333333", fg="white", activebackground="#444444")
collect_data_button.place(x=220, y=28)

# "Quit Program" button
quit_button = tk.Button(root, text="Quit Program", command=on_quit_button_click,
                    bg="#333333", fg="white", activebackground="#aa0000")
quit_button.place(x=140, y=130)


# Place instructions on the right side
for i, line in enumerate(instructions):
    label = tk.Label(root, text=line, bg="#1e1e1e", fg="white", anchor="w", justify="left")
    label.place(x=360, y=30 + i*25)

# Start the main event loop
root.mainloop()
