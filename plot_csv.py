import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
from PIL.ImageChops import offset
from scipy.signal import savgol_filter
import os
import re
from datetime import datetime
#from scipy import signal

# Plot acceleration as well, low pass filter


# Initialize Folder where the image plots will be saved
plot_output_directory = "plot outputs"

def match_lengths(*arrays):
    """
    Trims all input arrays to the same minimum length.

    Args:
        *arrays: Variable number of lists or numpy arrays.

    Returns:
        Tuple of arrays, all trimmed to the same length.
    """
    min_len = min(len(arr) for arr in arrays)
    return tuple(arr[:min_len] for arr in arrays)


def remove_extension(filename):
    return os.path.splitext(filename)[0]



def make_plot_dir_if_doesnt_exist():
    global plot_output_directory
    # Create the folder to store plot capture  if it doesn't exist
    if not os.path.exists(plot_output_directory):
        os.makedirs(plot_output_directory)




def plot_encoders(filepath,base_name,timestamp,replotting_flag=0,filename = ""):
    #For window resizing
    screen_width = 1920  # change to your actual screen width
    screen_height = 1000  # change if needed : Actual is 1080 but removed some to show tools at the bottom

    # Width and height for half-screen windows
    half_width = screen_width // 2
    window_height = screen_height

    # Load CSV, skip the first row
    df = pd.read_csv(filepath, skiprows=1, header=None)

    # Find index change column
    col = df.iloc[:, 5]
    # Find where the value changes
    change_rows = col[col != col.shift()].index
    # Get the last index where it changed
    last_change_index = change_rows[-1]
    # Get the value at that index
    last_changed_value = col.iloc[last_change_index]
    fine_offset = df.iloc[last_change_index, 5]
    coarse_offset = df.iloc[last_change_index, 2]

    # Extract time and angle data
    time_ms = df.iloc[last_change_index:, 0].values
    time_s = time_ms / 1000.0
    # Get the full column as a NumPy array, starting from last_change_index
    y1 = df.iloc[last_change_index:, 2].values  # Coarse angle
    y2 = df.iloc[last_change_index:, 4].values  # Fine angle

    if coarse_offset < 0:coarse_offset += 360 # wraps to 360

    if fine_offset < 0:fine_offset +=360 # wraps to 360

    #print(angle_offset)

    c_cmd = df[6].values #Coarse Command Values
    f_cmd = df[7].values #Fine Command Values

    # Remove repeated time values
    dt = np.diff(time_s)
    dt = np.insert(dt, 0, 1e-6)
    valid_indices = dt != 0

    time_s = time_s[valid_indices]
    y1 = y1[valid_indices]
    y2 = y2[valid_indices]

    # Shift fine angle before unwrap
    #y2_shifted = y2 - angle_offset # shifts y2 values

    # Unwrap angles for derivative calc and offsets
    y1_unwrapped = np.rad2deg(np.unwrap(np.deg2rad(y1)))
    #y2_unwrapped = np.rad2deg(np.unwrap(np.deg2rad(y2_shifted))) #NEW
    y2_unwrapped = np.rad2deg(np.unwrap(np.deg2rad(y2))) #OLD

    y2_unwrapped -= fine_offset

    #needs to be unwrapped first
    y1_unwrapped -= coarse_offset  # to add offset the motor encoder angle values

    # Compute derivatives for Velocity
    dy1_dt = np.gradient(y1_unwrapped, time_s)
    dy2_dt = np.gradient(y2_unwrapped, time_s)

    # Compute 2nd derivatives for Acceleration
    d2y1_dt2 = np.gradient(dy1_dt, time_s)
    d2y2_dt2 = np.gradient(dy2_dt, time_s)

    # Wrap angles to -180 to 180 for plotting
    y1_wrapped = ((y1_unwrapped + 180) % 360) - 180
    y2_wrapped = ((y2_unwrapped + 180) % 360) - 180 # applies zeroing shift for angle y2 was y2_shifted

    #aligned_coarse, aligned_fine = align_by_zero_crossings(y1_wrapped, y2_wrapped) #to fix motor phase shift

    #Filtering for Values
    filtered_dy1_dt =  savgol_filter(dy1_dt, window_length=10001 ,  polyorder=3)
    filtered_dy2_dt =  savgol_filter(dy2_dt, window_length=10001 ,  polyorder=3)

    filtered_d2y1_dt2 = savgol_filter(d2y1_dt2, window_length=10001 ,  polyorder=3)
    filtered_d2y2_dt2 = savgol_filter(d2y2_dt2, window_length=10001 ,  polyorder=3)

    # Matches size of Shifted arrays to fix in time domain
    time_s, aligned_coarse, aligned_fine, dy1_dt, dy2_dt, c_cmd, f_cmd = match_lengths(time_s, y1_wrapped, y2_wrapped, dy1_dt, dy2_dt, c_cmd, f_cmd)

    # Print row numbers where the value changes
    print("Value changes at rows:", change_rows.tolist(), last_changed_value)
    # === Plotting ===
    # === Figure 1: Angle vs. Time ===
    fig1, ax1 = plt.subplots(figsize=(14, 6))
    ax1.plot(time_s, y1_wrapped, label='Motor Encoder Angle (Wrapped)')
    ax1.plot(time_s, y2_wrapped, label='Glass Encoder Angle (Wrapped)')
    ax1.set_ylabel("Angle (°)")
    ax1.set_title("Encoder Angle (Wrapped) vs. Time")
    ax1.legend()
    ax1.grid(True)
    fig1.canvas.manager.window.wm_geometry(f"{half_width}x{window_height}+0+0")  # Left half

    # === Figure 2: Angular Velocity vs. Wrapped Angle ===
    fig2, ax2 = plt.subplots(figsize=(14, 6))
    ax2.step(y1_wrapped, filtered_dy1_dt, where='mid', label='Motor Encoder dθ/dt vs Angle', color='tab:blue')
    ax2.step(y2_wrapped, filtered_dy2_dt, where='mid', label='Glass Encoder dθ/dt vs Angle', color='tab:orange')
    ax2.set_xlabel("Angle (wrapped, °)")
    ax2.set_ylabel("Angular Velocity (°/s)")
    ax2.set_title("Angular Velocity vs. Wrapped Angle (Step Plot)")
    ax2.legend()
    ax2.grid(True)
    fig2.canvas.manager.window.wm_geometry(f"{half_width}x{window_height}+{half_width}+0")  # Right half

    # === Stats Box in Figure 2 ===
    stats_text = (
        f"Coarse Slew:\n"
        f"  Max dθ/dt: {dy1_dt.max():.2f}°/s\n"
        f"  Min dθ/dt: {dy1_dt.min():.2f}°/s\n"
        f"  Avg dθ/dt: {dy1_dt.mean():.2f}°/s\n\n"
        f"Fine Slew:\n"
        f"  Max dθ/dt: {dy2_dt.max():.2f}°/s\n"
        f"  Min dθ/dt: {dy2_dt.min():.2f}°/s\n"
        f"  Avg dθ/dt: {dy2_dt.mean():.2f}°/s"
    )

    fig2.text(0.85, 0.5, stats_text, fontsize=10, bbox=dict(facecolor='white', edgecolor='gray'))

    # === Figure 3: Angular Acceleration vs. Wrapped Angle ===
    fig3, ax3 = plt.subplots(figsize=(14, 6))
    ax3.step(y1_wrapped, filtered_d2y1_dt2, where='mid', label='Motor Encoder dθ/dt vs Angle', color='tab:blue')
    ax3.step(y2_wrapped, filtered_d2y2_dt2, where='mid', label='Glass Encoder dθ/dt vs Angle', color='tab:orange')
    ax3.set_xlabel("Angle (wrapped, °)")
    ax3.set_ylabel("Angular Acceleration (°/s^2)")
    ax3.set_title("Angular Acceleration vs. Wrapped Angle (Step Plot)")
    ax3.legend()
    ax3.grid(True)

    # === Figure 3: Angular Velocity vs. Time ===
    #fig3, ax3 = plt.subplots(figsize=(14, 6))
    #ax3.step(time_s, dy1_dt, where='mid', label='Motor Encoder dθ/dt vs Angle', color='tab:blue')
    #ax3.step(time_s, dy2_dt, where='mid', label='Glass Encoder dθ/dt vs Angle', color='tab:orange')
    #ax3.set_xlabel("Time (s)")
    #ax3.set_ylabel("Angular Velocity (°/s)")
    #ax3.set_title("Angular Velocity vs. Wrapped Angle (Step Plot)")
    #ax3.legend()
    #ax3.grid(True)
    #fig3.canvas.manager.window.wm_geometry(f"{half_width}x{window_height}+{half_width}+0")  # Right half
    # Show both figures
    plt.show()

    #axs[2].plot(time_s, c_cmd, label='Coarse Command Value', color='tab:green')
    #axs[2].set_xlabel("Time (s)")
    #axs[2].set_ylabel("Coarse Command Values")
    #axs[2].set_title("Coarse Commands vs. Time")
    #axs[2].legend()
    #axs[2].grid(True)

    #axs[3].plot(time_s, y3, label='Test graph', color='tab:red')
    #axs[3].set_xlabel("Time (s)")
    #axs[3].set_ylabel("motor with offset")
    #axs[3].set_title("motor with offset vs. Time")
    #axs[3].legend()
    #axs[3].grid(True)

    # autosaving the plots 
    make_plot_dir_if_doesnt_exist() #as a redundancy to make sure that the directory exists before trying to save to it

    
    if replotting_flag == 0:
        # Save each figure & construct names for each plot from the user input
        fig1_path = os.path.join(plot_output_directory, base_name+"_"+timestamp+"_angle_vs_time.png")
        fig2_path = os.path.join(plot_output_directory, base_name+"_"+timestamp+"_angular_velocity_vs_angle.png")
        fig3_path = os.path.join(plot_output_directory, base_name+"_"+timestamp+"_angular_acceleration_vs_angle.png")

        fig1.savefig(fig1_path, bbox_inches='tight')
        fig2.savefig(fig2_path, bbox_inches='tight')
        fig3.savefig(fig3_path, bbox_inches='tight')

    if replotting_flag == 1:
        # Save each figure & construct names for each plot from the user input
        fig1_path = os.path.join(plot_output_directory, filename+"_angle_vs_time.png")
        fig2_path = os.path.join(plot_output_directory, filename+"_angular_velocity_vs_angle.png")
        fig3_path = os.path.join(plot_output_directory, filename+"_angular_acceleration_vs_angle.png")

        fig1.savefig(fig1_path, bbox_inches='tight')
        fig2.savefig(fig2_path, bbox_inches='tight')
        fig3.savefig(fig3_path, bbox_inches='tight')

    print(f"Saved figures to '{plot_output_directory}' directory.")






def replot_encoder_data(filename):
    print("running replot encode data running...")
    filepath = os.path.join("encoder_logs/"+filename)
    file_without_ext = remove_extension(filename)   # remove filename extension
    #recal the function with parmeters set and dummy arguments that will get ignored due to the flag passed in
    plot_encoders(filepath,'not_a_name','not_a_time', replotting_flag = 1,filename=file_without_ext)
    


    


# Call the function
#filepath = os.path.join("encoder_logs/616-00022_Slow_Right_20250416_162402.csv")
#plot_encoders(filepath,"616-00022_Slow_Right", "23456789" ) #Slow Left
#replot_encoder_data('616-00021_CCW_3.8V_20250425_142244.csv')
#plot_encoders(r'C:\Users\i2Tech\Desktop\I2EncoderDataInspectionTool_V2\encoder_logs\616-00022_Slow_Right_20250416_162402.csv') #Slow Right
#plot_encoders(r'C:\Users\i2Tech\PycharmProjects\I2EncoderInspectionTool\.venv\Scripts\encoder_logs\616-00022_Fast_Left_20250416_163143.csv') #Fast Left
#plot_encoders(r'C:\Users\i2Tech\PycharmProjects\I2EncoderInspectionTool\.venv\Scripts\encoder_logs\616-00022_Fast_Right_20250416_162950.csv') #Fast Right