import os
import shutil
import requests
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from PIL import Image

# Folder paths for GRIB data and image outputs
base_folder = "./public"
grib_folder = os.path.join(base_folder, "grib")
grib_folder_surft = os.path.join(grib_folder, "surft")  # Add the 'surft' folder
images_folder = os.path.join(base_folder, "images")
temp_folder = os.path.join(base_folder, "temp")

# Function to clear a folder
def clear_folder(folder_path):
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove file or symlink
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove directory and its contents
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")

# Clear the 'surft' and 'temp' folders before execution
clear_folder(grib_folder_surft)
clear_folder(temp_folder)

# Ensure the folders exist
os.makedirs(grib_folder, exist_ok=True)
os.makedirs(grib_folder_surft, exist_ok=True)  # Ensure 'surft' folder exists
os.makedirs(temp_folder, exist_ok=True)

# Get today's date and format it for the URL
today = datetime.now()
date_str = today.strftime("%Y%m%d")

# Determine the most recent GFS run based on the current hour
current_hour = today.hour
hour_str = f"{(current_hour // 6) * 6:02d}"  # Get the latest run in 6-hour intervals

# Forecast steps limited to f000 to f012 and then every 6 hours up to f096
forecast_steps = [f"f{str(i).zfill(3)}" for i in range(13)]  # Generates ['f000', ..., 'f012']
forecast_steps += [f"f{str(i).zfill(3)}" for i in range(12, 97, 6)]  # Adds ['f018', ..., 'f096']

# Variable to download
variable = "TMP"  # Temperature

# Function to check if the file exists on the server
def file_exists(url):
    response = requests.head(url)
    return response.status_code == 200

# Try the most recent GFS run and fall back if necessary
run_found = False
for hour in [hour_str, f"{(int(hour_str) - 6) % 24:02d}"]:  # Try current and past run
    for step in forecast_steps:
        # Build the URL with the specified variable
        url = (f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?dir=%2Fgfs.{date_str}%2F{hour}%2Fatmos"
               f"&file=gfs.t{hour}z.pgrb2.0p25.{step}&var_{variable}=on&lev_2_m_above_ground=on")

        # Check if the file exists
        if file_exists(url):
            filename = os.path.join(grib_folder_surft, f"gfs.t{hour}z.pgrb2.0p25.{step}.grib2")  # Save to 'surft' folder

            # Request the file from the URL
            response = requests.get(url)
            if response.status_code == 200:
                with open(filename, 'wb') as file:
                    file.write(response.content)
                print(f"Downloaded: {filename}")
                run_found = True
            else:
                print(f"Failed to download {filename}. Status code: {response.status_code}")

    # If files are found for this run, exit the loop
    if run_found:
        break

if not run_found:
    print("No valid GFS data was found for the specified runs.")

# Function to generate the plot
def create_temperature_plot(file_path, output_filename):
    try:
        # Open the GRIB2 file with xarray
        dataset = xr.open_dataset(file_path, engine="cfgrib")

        # Check if the 2-meter temperature ('t2m') is available
        if 't2m' in dataset.variables:
            temperature_k = dataset['t2m']  # Temperature in Kelvin at 2 meters
            temperature_f = (temperature_k - 273.15) * 9 / 5 + 32  # Convert to Fahrenheit
            lats = dataset['latitude'].values
            lons = dataset['longitude'].values

            # Convert longitude to match Basemap's format (-180 to 180)
            lons = np.where(lons > 180, lons - 360, lons)

            # Define the limits to zoom into the USA (approximate lat/lon for the US)
            lat_min, lat_max = 24.396308, 49.384358
            lon_min, lon_max = -125.0, -66.93457

            # Mask the temperature data to zoom into the USA
            lat_mask = (lats >= lat_min) & (lats <= lat_max)
            lon_mask = (lons >= lon_min) & (lons <= lon_max)
            temperature_f = temperature_f[lat_mask, :][:, lon_mask]
            lats = lats[lat_mask]
            lons = lons[lon_mask]

            # Create a meshgrid for plotting
            lon_grid, lat_grid = np.meshgrid(lons, lats)

            # Define temperature bounds and corresponding colors
            bounds = [-90, -70, -50, -40, -30, -20, 0, 10, 32, 40, 50, 60, 70, 80, 90, 100, 120]
            colors = [
                '#FFB6C1', '#FF69B4', '#D84C9A', '#9B36A2', '#6A0DAD', '#4B0082', '#8A2BE2', '#4169E1',
                '#90EE90', '#32CD32', '#228B22', '#FFFF00', '#FFA500', '#FF4500', '#B22222', '#000000'
            ]
            cmap = plt.cm.colors.ListedColormap(colors)
            norm = plt.cm.colors.BoundaryNorm(bounds, cmap.N)

            # Set up the plot without Basemap
            fig, ax = plt.subplots(figsize=(14, 10))
            ax.set_facecolor('black')  # Set background to black
            ax.set_xticks([])  # Hide x-ticks
            ax.set_yticks([])  # Hide y-ticks

            # Plot temperature data
            temp_contour = ax.contourf(lon_grid, lat_grid, temperature_f, levels=bounds, cmap=cmap, norm=norm)

            # Remove the color bar
            # cbar = plt.colorbar(temp_contour, ax=ax, location='right', pad=0)
            # cbar.set_label('Temperature (°F)', fontsize=12)
            # cbar.ax.tick_params(labelsize=10)

            # Remove the title
            plt.tight_layout()

            # Save the plot as a PNG file
            plt.savefig(output_filename, bbox_inches='tight', pad_inches=0, dpi=300)
            plt.close()
            print(f"Plot saved: {output_filename}")
        else:
            print("The dataset does not contain the 't2m' variable (2-meter temperature).")

    except Exception as e:
        print(f"Error opening the GRIB2 file: {e}")

# Generate the plots for each forecast step
image_files = []
for hour in [hour_str, f"{(int(hour_str) - 6) % 24:02d}"]:  # Try current and past run
    for step in forecast_steps:
        grib_file_path = os.path.join(grib_folder_surft, f"gfs.t{hour}z.pgrb2.0p25.{step}.grib2")  # Use 'surft' folder
        if os.path.exists(grib_file_path):
            output_filename = os.path.join(temp_folder, f"temperature_{hour}_{step}.png")
            create_temperature_plot(grib_file_path, output_filename)
            image_files.append(output_filename)

# Create an animated GIF
plot_files = [os.path.join(temp_folder, f"temperature_{hour}_{step}.png") for hour in [hour_str, f"{(int(hour_str) - 6) % 24:02d}"] for step in forecast_steps]
images = [Image.open(file) for file in plot_files if os.path.exists(file)]
animation_path = os.path.join(temp_folder, "gfs_animation.gif")
if images:
    images[0].save(animation_path, save_all=True, append_images=images[1:], duration=500, loop=0)
    print(f"GIF created: {animation_path}")
else:
    print("No images found to create a GIF.")
