import os
import shutil
import requests
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from datetime import datetime
from PIL import Image
import matplotlib.colors as mcolors  # Add this import for custom colormap

# Folder paths for GRIB data and image outputs
base_folder = "./public"
grib_folder = os.path.join(base_folder, "grib")
grib_folder_surft = os.path.join(grib_folder, "Gust")  # Add the 'surft' folder
images_folder = os.path.join(base_folder, "images")
temp_folder = os.path.join(base_folder, "GUST")

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
os.makedirs(images_folder, exist_ok=True)  # Ensure images folder exists

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
variable = "GUST"  # Wind Gust

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
               f"&file=gfs.t{hour}z.pgrb2.0p25.{step}&var_{variable}=on&lev_surface=on")

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
    exit()

# Function to create a gust plot for a given GRIB file
def create_gust_plot(grib_file_path, output_filename):
    ds = xr.open_dataset(grib_file_path, engine='cfgrib')
    gust = ds['gust']

    # Define the custom colormap and levels
    levels = [0, 5, 10, 20, 30, 40, 70]  # Define wind gust levels
    cmap = mcolors.ListedColormap(["lightblue", "blue", "green", "yellow", "orange", "red", "purple"])
    norm = mcolors.BoundaryNorm(levels, ncolors=cmap.N, extend='max')

    plt.figure(figsize=(12, 8), dpi=100)  # Increase figure size and DPI for better visualization
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Use imshow for rendering the data
    img = ax.imshow(
        gust.values,
        extent=[gust.longitude.min(), gust.longitude.max(), gust.latitude.min(), gust.latitude.max()],
        origin='upper',
        cmap=cmap,
        norm=norm,
        interpolation='bilinear'  # Smooth interpolation
    )

    # Set the extent to focus on the USA
    ax.set_extent([-125, -66.5, 24, 50], crs=ccrs.PlateCarree())  # Lower 48 states

    # Remove axes and title
    ax.axis('off')  # Turn off axes

    # Save the image
    plt.tight_layout()
    plt.savefig(output_filename, dpi=100, bbox_inches='tight', pad_inches=0)  # Save without extra padding
    plt.close()
    print(f"Plot saved to {output_filename}")

# Generate the plots for each forecast step
image_files = []
for hour in [hour_str, f"{(int(hour_str) - 6) % 24:02d}"]:  # Try current and past run
    for step in forecast_steps:
        grib_file_path = os.path.join(grib_folder_surft, f"gfs.t{hour}z.pgrb2.0p25.{step}.grib2")  # Use 'surft' folder
        if os.path.exists(grib_file_path):
            output_filename = os.path.join(temp_folder, f"gust_{hour}_{step}.png")
            create_gust_plot(grib_file_path, output_filename)
            image_files.append(output_filename)

# Create an animated GIF
plot_files = [os.path.join(temp_folder, f"gust_{hour}_{step}.png") for hour in [hour_str, f"{(int(hour_str) - 6) % 24:02d}"] for step in forecast_steps]
images = [Image.open(file) for file in plot_files if os.path.exists(file)]
animation_path = os.path.join(temp_folder, "gfs_gust_animation.gif")
if images:
    images[0].save(animation_path, save_all=True, append_images=images[1:], duration=500, loop=0)
    print(f"GIF created: {animation_path}")
else:
    print("No images found to create a GIF.")
