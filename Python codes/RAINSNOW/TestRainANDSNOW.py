import os
import requests
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from datetime import datetime
from PIL import Image

# Folder paths for GRIB data and image outputs
base_folder = "./public"
grib_folder = os.path.join(base_folder, "grib")
grib_folder_temp = os.path.join(grib_folder, "temp")
grib_folder_refc = os.path.join(grib_folder, "refc")
rs_folder = os.path.join(base_folder, "RS")

os.makedirs(grib_folder_temp, exist_ok=True)
os.makedirs(grib_folder_refc, exist_ok=True)
os.makedirs(rs_folder, exist_ok=True)

def delete_all_files_in_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

def run_task():
    delete_all_files_in_folder(grib_folder_temp)
    delete_all_files_in_folder(grib_folder_refc)
    delete_all_files_in_folder(rs_folder)

    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    current_hour = today.hour
    hour_str = f"{(current_hour // 6) * 6:02d}"

    forecast_steps = [f"f{str(i).zfill(3)}" for i in range(13)]
    forecast_steps += [f"f{str(i).zfill(3)}" for i in range(12, 97, 6)]

    variable_temp = "TMP"
    variable_refc = "REFC"

    def file_exists(url):
        response = requests.head(url)
        return response.status_code == 200

    run_found = False
    for hour in [hour_str, f"{(int(hour_str) - 6) % 24:02d}"]:
        for step in forecast_steps:
            url_temp = (
                f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?dir=%2Fgfs.{date_str}%2F{hour}%2Fatmos"
                f"&file=gfs.t{hour}z.pgrb2.0p25.{step}&var_{variable_temp}=on&lev_2_m_above_ground=on"
            )
            url_refc = (
                f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?dir=%2Fgfs.{date_str}%2F{hour}%2Fatmos"
                f"&file=gfs.t{hour}z.pgrb2.0p25.{step}&var_{variable_refc}=on&lev_entire_atmosphere=on"
            )

            if file_exists(url_temp) and file_exists(url_refc):
                filename_temp = os.path.join(grib_folder_temp, f"gfs.t{hour}z.pgrb2.0p25.{step}.grib2")
                filename_refc = os.path.join(grib_folder_refc, f"gfs.t{hour}z.pgrb2.0p25.{step}.grib2")

                r1 = requests.get(url_temp)
                r2 = requests.get(url_refc)
                if r1.status_code == 200 and r2.status_code == 200:
                    with open(filename_temp, 'wb') as f:
                        f.write(r1.content)
                    with open(filename_refc, 'wb') as f:
                        f.write(r2.content)
                    print(f"Downloaded: {step}")
                    run_found = True
        if run_found:
            break

    if not run_found:
        print("No valid GFS data found.")
        return

    rain_levels = [10, 20, 30, 40, 50, 60, 75]
    rain_colors = ['#b2ff59', '#66bb6a', '#006400', '#ffff00', '#ff8c00', '#ff0000']
    cmap_refc_rain = plt.cm.colors.ListedColormap(rain_colors)
    norm_refc_rain = plt.cm.colors.BoundaryNorm(rain_levels, cmap_refc_rain.N)

    snow_levels = [0, 5, 10, 15, 20, 25, 30, 35, 40]
    snow_colors = ['#e0f7fa', '#b3e5fc', '#81d4fa', '#4fc3f7', '#29b6f6', '#039be5',
                   '#0288d1', '#0277bd', '#01579b']
    cmap_refc_snow = plt.cm.colors.ListedColormap(snow_colors)
    norm_refc_snow = plt.cm.colors.BoundaryNorm(snow_levels, cmap_refc_snow.N)

    def create_combined_reflectivity_plot(file_path_temp, file_path_refc, output_filename):
        try:
            ds_temp = xr.open_dataset(file_path_temp, engine="cfgrib")
            ds_refc = xr.open_dataset(file_path_refc, engine="cfgrib")

            if 't2m' in ds_temp.variables and 'refc' in ds_refc.variables:
                temperature_k = ds_temp['t2m']
                temperature_f = (temperature_k - 273.15) * 9 / 5 + 32
                lats = ds_temp['latitude'].values
                lons = ds_temp['longitude'].values
                refc = ds_refc['refc']

                lons = np.where(lons > 180, lons - 360, lons)
                lon_grid, lat_grid = np.meshgrid(lons, lats)

                plt.figure(figsize=(16, 8), dpi=120)
                m = Basemap(projection='cyl', resolution='c')
                m.drawcoastlines(color='gray', linewidth=0)

                snow_mask = temperature_f < 32.5
                refc_snow = np.ma.masked_where(~snow_mask, refc)
                rain_mask = temperature_f >= 31.5
                refc_rain = np.ma.masked_where(~rain_mask, refc)

                m.contourf(lon_grid, lat_grid, refc_snow, levels=snow_levels, cmap=cmap_refc_snow, norm=norm_refc_snow, latlon=True)
                m.contourf(lon_grid, lat_grid, refc_rain, levels=rain_levels, cmap=cmap_refc_rain, norm=norm_refc_rain, latlon=True)

                plt.axis('off')  # Hide axes
                plt.savefig(output_filename, dpi=150, bbox_inches='tight', pad_inches=0)
                plt.close()
                print(f"Saved plot: {output_filename}")
        except Exception as e:
            print(f"Error generating plot: {e}")

    image_paths = []
    for step in forecast_steps:
        temp_fp = os.path.join(grib_folder_temp, f"gfs.t{hour_str}z.pgrb2.0p25.{step}.grib2")
        refc_fp = os.path.join(grib_folder_refc, f"gfs.t{hour_str}z.pgrb2.0p25.{step}.grib2")
        out_img = os.path.join(rs_folder, f"Rain_Snow_Global_{date_str}_{hour_str}_{step}.png")
        create_combined_reflectivity_plot(temp_fp, refc_fp, out_img)
        image_paths.append(out_img)

    gif_filename = os.path.join(rs_folder, "GIF_reflectivity_global.gif")
    images = [Image.open(img) for img in image_paths if os.path.exists(img)]
    if images:
        images[0].save(gif_filename, save_all=True, append_images=images[1:], duration=1000, loop=0)
        print(f"GIF saved: {gif_filename}")
    else:
        print("No images to create a GIF.")

# Run it
run_task()
