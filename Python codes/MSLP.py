import requests
import os
import cfgrib
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np
from scipy.ndimage import gaussian_filter, minimum_filter, maximum_filter
from PIL import Image
from datetime import datetime

def clear_folder(folder_path):
    """Deletes all files in the specified folder."""
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

def download_grib_files():
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    current_hour = today.hour
    run_hour = (current_hour // 6) * 6
    hour_str = f"{run_hour:02d}"
    forecast_steps = [f"f{str(i).zfill(3)}" for i in range(13)] + [f"f{str(i).zfill(3)}" for i in range(12, 97, 6)]
    
    output_folders = [
        os.path.join(os.getcwd(), 'public', 'mslet'),
        os.path.join(os.getcwd(), 'public', 'grib', 'surft')  # Added folder
    ]
    
    for folder in output_folders:
        os.makedirs(folder, exist_ok=True)
        clear_folder(folder)
    
    for step in forecast_steps:
        url = f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_1p00.pl?dir=%2Fgfs.{date_str}%2F{hour_str}%2Fatmos&file=gfs.t{hour_str}z.pgrb2.1p00.{step}&var_MSLET=on&var_PRMSL=on&lev_mean_sea_level=on"
        output_filename = os.path.join(output_folders[0], f"gfs_t{hour_str}z_pgrb2_1p00_{step}.grb2")
        response = requests.get(url)
        if response.status_code == 200:
            with open(output_filename, 'wb') as file:
                file.write(response.content)

def create_png_from_grib(file_path, output_folder):
    forecast_hour = file_path.split("_")[-1].replace(".grb2", "").replace("f", "")
    ds = cfgrib.open_dataset(file_path, filter_by_keys={'typeOfLevel': 'meanSea'})
    lons, lats = np.meshgrid(ds.longitude.values, ds.latitude.values)
    mslp = ds.prmsl.values / 100
    min_val, max_val = np.nanmin(mslp), np.nanmax(mslp)
    if np.isnan(min_val) or np.isnan(max_val) or min_val >= max_val:
        raise ValueError("Invalid data detected.")
    
    mslp_smoothed = gaussian_filter(mslp, sigma=2)
    lows = (mslp_smoothed == minimum_filter(mslp_smoothed, 10))
    highs = (mslp_smoothed == maximum_filter(mslp_smoothed, 10))
    
    plt.figure(figsize=(12, 8), dpi=120)
    m = Basemap(projection='lcc', resolution='i', lat_0=37.5, lon_0=-98.35, width=9e6, height=6e6)
    
    # Draw only the plot without borders, axes, or titles
    x, y = m(lons, lats)
    x_mask = (x >= 0) & (x <= m.urcrnrx) & (y >= 0) & (y <= m.urcrnry)
    mslp = np.where(x_mask, mslp, np.nan)
    contour_levels = np.arange(min_val, max_val, 4) if min_val < max_val else np.linspace(980, 1040, 20)
    contour_lows = m.contour(x, y, mslp, levels=contour_levels[contour_levels < 1019], colors="red", linewidths=1.2)
    contour_highs = m.contour(x, y, mslp, levels=contour_levels[contour_levels >= 1019], colors="blue", linewidths=1.2)
    plt.clabel(contour_lows, inline=True, fontsize=9, fmt="%1.0f", colors='red')
    plt.clabel(contour_highs, inline=True, fontsize=9, fmt="%1.0f", colors='blue')
    
    for i in range(mslp.shape[0]):
        for j in range(mslp.shape[1]):
            if x_mask[i, j]:
                if highs[i, j]:
                    plt.text(x[i, j], y[i, j], 'H', color='blue', fontsize=16, fontweight='bold', ha='center', va='center')
                elif lows[i, j]:
                    plt.text(x[i, j], y[i, j], 'L', color='red', fontsize=16, fontweight='bold', ha='center', va='center')
    
    # Remove all map features
    plt.axis('off')  # Turn off axes
    m.drawcoastlines(linewidth=0)  # Remove coastlines
    m.drawcountries(linewidth=0)  # Remove country borders
    m.drawstates(linewidth=0)  # Remove state borders
    m.drawcounties(linewidth=0)  # Remove county borders

    # Save the plot
    output_filename = os.path.join(output_folder, f"{os.path.basename(file_path)}.png")
    plt.savefig(output_filename, dpi=150, bbox_inches='tight', pad_inches=0)
    plt.close()

def create_gif_from_png(output_folder):
    png_files = sorted([f for f in os.listdir(output_folder) if f.endswith(".png")])
    images = [Image.open(os.path.join(output_folder, f)) for f in png_files]
    if images:
        gif_filename = os.path.join(os.getcwd(), 'public', 'HL', 'animation.gif')
        images[0].save(gif_filename, save_all=True, append_images=images[1:], duration=500, loop=0)

output_folder = os.path.join(os.getcwd(), 'public', 'HL')
os.makedirs(output_folder, exist_ok=True)
clear_folder(output_folder)
download_grib_files()
grib_folder = os.path.join(os.getcwd(), 'public', 'mslet')
for file_name in os.listdir(grib_folder):
    if file_name.endswith(".grb2"):
        create_png_from_grib(os.path.join(grib_folder, file_name), output_folder)
create_gif_from_png(output_folder)