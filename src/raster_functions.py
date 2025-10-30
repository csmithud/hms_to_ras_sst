import re
import os
import pathlib as pl
import pandas as pd
import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import rasterio
import rioxarray as rxr
import xarray as xr
from rasterio.crs import CRS
# https://stackoverflow.com/questions/47163728/how-to-add-legend-gradient-in-folium-heat-map
# del m
from collections import defaultdict
import branca.colormap as cm
import webbrowser
from folium.plugins import HeatMap 
import matplotlib.colors as colors
import sklearn
from sklearn import metrics
import shutil
from rasterio.warp import calculate_default_transform, reproject, Resampling
from osgeo import gdal
import glob
from collections import Counter
import concurrent.futures
import multiprocessing
import threading
from rasterio.windows import Window


def get_filenames_keyword(file_list,keywords,and_or = 'and'):
    """test
    """
    if and_or == 'or':
        re_str = '|'.join(keywords)
        re_str = '('+re_str+')'
    else:
        re_str = '[\s\S]+'.join(keywords)
    r = re.compile('(?i)([\s\S])*?('+re_str+')([\s\S])*?(.tif)$')
    matches = list(filter(r.match, file_list))
    return matches

def list_files(path: str, file_type: str):
    """Create a list in the directory given by the path string"""
    li_files = [
        file for file in os.listdir(path) if os.path.splitext(file)[-1] == file_type
    ]
    li_all_files = list()
    for file in li_files:
        li_all_files.append(os.path.join(path, file))
    return li_all_files


def colorize(array, cmap="terrain"):
    normed_data = (array - array.min()) / (array.max() - array.min())
    cm = plt.cm.get_cmap(cmap)
    return cm(normed_data)

# def resample_raster(raster,shrink):
#     from rasterio.enums import Resampling
#     with rxr.open_rasterio(raster) as xds:
#         # resample data to target shape

#         new_width = int(xds.rio.width / shrink)
#         new_height = int(xds.rio.width / shrink)

#     xds_upsampled = xds.rio.reproject(
#             xds.rio.crs,
#             shape=(new_height, new_width),
#             resampling=Resampling.bilinear,
#         )
#     return xds_upsampled
    

def colorize_percentile(array, cmap="terrain"):
    q1 = np.percentile(array, 0.1)
    q99 = np.percentile(array, 99.9)
    print(q1)
    print(q99)

    array[array < q1] = q1
    array[array > q99] = q99
    c_min = array.min()
    c_max = array.max()
    normed_data = mcolors.CenteredNorm(vcenter = 0)
    color = plt.cm.get_cmap(cmap)
    return color(normed_data(array)), c_min, c_max

def get_tifs_and_profile(area_name,list_of_tifs):
    true_tifs = []
    for tif in list_of_tifs:
        if tif.find(area_name)>=0:
            true_tifs.append(tif)
    #first tif for shape
    with rasterio.open(true_tifs[0]) as image:
        profile = image.profile
    return true_tifs, profile

def window_scaler(profile,target_block_size=2560):
    avg_block_size = (profile['blockxsize']+profile['blockysize'])/2
    return target_block_size//avg_block_size

def create_max_raster_by_block_wy(out_path,name,tifs,profile,force=False):
    t = 20
    name_parts = name.split('_')
    huc = name_parts[0]
    type = name_parts[1]
    ri = name_parts[2]
    frp_dict_ri = {'0.1':'10pct','0.04':'04pct','0.02':'02pct','0.01':'01pct','0.01p':'01plus','0.01m':'01minus','0.002':'0_2pct'}
    frp_dict_type = {'wse':'WSE','depth':'Depth','velocity':'Vel'}
    # if len(tifs) == 1:
    #     shutil.copy(tifs[0],pl.Path(out_path)/'{}_max.tif'.format(name))
    # else:
    if os.path.exists(pl.Path(out_path)/'{}.tif'.format('_'.join([huc,frp_dict_type[type],frp_dict_ri[ri]]))):
        return pl.Path(out_path)/'{}.tif'.format('_'.join([huc,frp_dict_type[type],frp_dict_ri[ri]]))
    with rasterio.Env():
        with rasterio.open(pl.Path(out_path)/'{}.tif'.format('_'.join([huc,frp_dict_type[type],frp_dict_ri[ri]])), 'w', **profile) as dst:
            first_rast = tifs[0]
            with rasterio.open(first_rast) as src:
                for ji, window in src.block_windows(1):
                    if ji[0]%t == 0 and ji[1]%t == 0:
                        window_co = window.col_off
                        window_ro = window.row_off
                        window_w = window.width*t if window_co+window.width*t <= src.width else (src.width - window_co)
                        window_h = window.height*t if window_ro+window.height*t <= src.height else (src.height - window_ro)
                        max_array = src.read(1,window=Window(window_co,window_ro,window_w,window_h))
                        for in_tif in tifs[1:]:
                            with rasterio.open(in_tif) as image:
                                area_array = image.read(1,window=Window(window_co,window_ro,window_w,window_h))
                                max_array = np.maximum(max_array,area_array)
                        max_array_rnd = np.round(max_array,decimals=1)
                        dst.write(max_array_rnd, 1, window = Window(window_co,window_ro,window_w,window_h))
    return pl.Path(out_path)/'{}.tif'.format('_'.join([huc,frp_dict_type[type],frp_dict_ri[ri]]))

# def create_max_raster_by_block_workers(out_path,name,tifs,profile,force=False):
#     def compute(tifs,window,read_lock):
#         first_rast = tifs[0]
#         with read_lock:
#             with rasterio.open(first_rast) as src:
#                 max_array = src.read(1,window=window)
#                 for in_tif in tifs[1:]:
#                     with rasterio.open(in_tif) as image:
#                         area_array = image.read(1,window=window)
#                         max_array = np.maximum(max_array,area_array)
#         max_array_rnd = np.round(max_array,decimals=1)
#         return max_array_rnd

#     name_parts = name.split('_')
#     huc = name_parts[0]
#     type = name_parts[1]
#     ri = name_parts[2]
#     frp_dict_ri = {'0.1':'10pct','0.04':'04pct','0.02':'02pct','0.01':'01pct','0.01p':'01plus','0.01m':'01minus','0.002':'0_2pct'}
#     frp_dict_type = {'wse':'WSE','depth':'Depth','velocity':'Vel'}
#     if os.path.exists(pl.Path(out_path)/'{}.tif'.format('_'.join([huc,frp_dict_type[type],frp_dict_ri[ri]]))):
#         return pl.Path(out_path)/'{}.tif'.format('_'.join([huc,frp_dict_type[type],frp_dict_ri[ri]]))
#     with rasterio.Env():
#         with rasterio.open(pl.Path(out_path)/'{}.tif'.format('_'.join([huc,frp_dict_type[type],frp_dict_ri[ri]])), 'w', **profile) as dst:
#             windows = [window for ij, window in dst.block_windows()]
#             read_lock = threading.Lock()
#             write_lock = threading.Lock()
#             def process(window):
#                 max_array_rnd = compute(tifs,window,read_lock)
#                 with write_lock:
#                     dst.write(max_array_rnd,1,window=window)
                
#             with concurrent.futures.ThreadPoolExecutor(max_workers = 4) as executor:
#                 executor.map(process,windows)
#     return pl.Path(out_path)/'{}.tif'.format('_'.join([huc,frp_dict_type[type],frp_dict_ri[ri]]))


def create_aep_raster_by_block(out_path,name,weights:pd.DataFrame,tifs,profile,threshold = 0.5):
    with rasterio.Env():
        with rasterio.open(pl.Path(out_path)/'{}_aep.tif'.format(name), 'w', **profile) as dst:
            first_rast = tifs[0]
            with rasterio.open(first_rast) as src:
                for ji, window in src.block_windows(1):
                    for in_tif in tifs:
                        with rasterio.open(in_tif) as image:
                            area_array = image.read(1,window=window)
                            #update to handle thresholds better
                            norm_array = area_array*(1/threshold)
                            thresholded_array = np.clip(norm_array,0,1)
                            area_array = np.where(thresholded_array==1,1,0)
                            runoff_str = re.findall('[runoff,coastal]_\d{1,4}_',in_tif)[0]
                            runoff_amount = re.findall('\d{1,4}',runoff_str)[0]
                            col_name = weights.columns.to_list()[0]
                            prob = weights.loc[int(runoff_amount)][col_name]
                            if in_tif == tifs[0]:
                                if np.isnan(area_array) is False:
                                    print(runoff_amount,prob,area_array)
                                block_risk = area_array*prob
                            else:
                                block_risk = np.add(block_risk,area_array*prob)
                    dst.write(block_risk, 1, window = window)
    return pl.Path(out_path)/'{}_aep.tif'.format(name)

def create_joined_prob_aep_raster_by_block(out_path,name,tif1,tif2,aoi_overlap):
    # clip the rasters
    with rasterio.open(tif1) as rast1:
        out_crs = rast1.profile['crs'].to_epsg()

    overlap = gpd.read_file(aoi_overlap)
    overlap_sr = overlap.to_crs(epsg=out_crs)
    geoms = [overlap_sr['geometry'].iloc[0].__geo_interface__]

    clip_tif_1 = str(tif1)[:str(tif1).find('.tif')]+'_clipped.tif'
    clip_tif_2 = str(tif2)[:str(tif2).find('.tif')]+'_clipped.tif'

    with rasterio.open(tif1) as rast1:
        out_image1, out_transform1 = rasterio.mask.mask(rast1,geoms,crop=True)
        out_meta = rast1.meta
        out_meta.update({"driver": "GTiff",
                     "height": out_image1.shape[1],
                     "width": out_image1.shape[2],
                     "transform": out_transform1})
        out_profile = rast1.profile

    with rasterio.open(clip_tif_1, "w", **out_meta) as clipped1:
        clipped1.write(out_image1)

    with rasterio.open(tif2) as rast2:
        out_image2, out_transform2 = rasterio.mask.mask(rast2,geoms,crop=True)
        out_meta = rast2.meta
        out_meta.update({"driver": "GTiff",
                     "height": out_image2.shape[1],
                     "width": out_image2.shape[2],
                     "transform": out_transform2})

    with rasterio.open(clip_tif_2, "w", **out_meta) as clipped2:
        clipped2.write(out_image2)

    with rasterio.Env():
        with rasterio.open(pl.Path(out_path)/'{}_aep.tif'.format(name), 'w', **out_meta) as dst:
            with rasterio.open(clip_tif_1) as image1:
                for ji, window in image1.block_windows(1):
                    with rasterio.open(clip_tif_2) as image2:
                        area_array1 = np.ma.masked_values(image1.read(1,window=window,masked=True),np.nan)
                        area_array2 = np.ma.masked_values(image2.read(1,window=window,masked=True),np.nan)
                        block_risk = np.nansum([np.nansum([area_array1,area_array2],axis=0),np.negative(np.prod([area_array1,area_array2],axis=0))],axis=0)
                        block_risk_out = np.where(block_risk == -1,out_meta['nodata'],block_risk)
                    dst.write(block_risk_out, 1, window = window)
                    
# def read_reformat_raster_as_array(raster,desired_crs,shrink = 4):
#     with rasterio.open(raster) as image:
#         nrows, ncols = np.shape(myarray)
#         shape = image.shape
#         transform = image.transform
#         xmin, ymin, xmax, ymax = image.bounds
#         crs = str(image.crs)
#         profile = image.profile
#     stored_array = np.empty([shape[0]//shrink,shape[1]//shrink])
#     env = rasterio.Env(
#         GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
#         CPL_VSIL_CURL_USE_HEAD=False,
#         CPL_VSIL_CURL_ALLOWED_EXTENSIONS="TIF",)

#     with env:
#         with rasterio.open(raster) as src:
#             with rasterio.vrt.WarpedVRT(src, crs="EPSG:4326") as vrt:
#                 for ji, window in src.block_windows(1):
                    
            
            
#     array_wgs84 = array.rio.reproject(crs_wgs84)
#     del array
#     array_reproject = np.squeeze(np.ma.getdata(array_wgs84.to_masked_array()))
#     array_reproject[array_reproject == -9999] = 0
#     array_reproject = array_reproject[::shrink, ::shrink]
#     return array_reproject

def align_clip_reproject(ref_tif,tif, aoi=None):
    '''
    Parameters:
    ref_tif = tif to align to
    tif = tif to be converted
    aoi = set to None in case no clip is required. Otherwise will be the geojson file of interest
    '''

    #open ref
    xds = xr.open_dataarray(tif)
    xds_match = xr.open_dataarray(ref_tif)

    #align
    xds_repr_match = xds.rio.reproject_match(xds_match)
    #assign coords to be safe from float issues
    xds_repr_match = xds_repr_match.assign_coords({
    "x": xds_match.x,
    "y": xds_match.y,
    })

    #clip
    if aoi:
        with rasterio.open(ref_tif) as rt:
            sr = rt.crs 
        overlap_sr = gpd.read_file(aoi).to_crs(crs=sr).dissolve()
        geoms = [overlap_sr['geometry'].iloc[0].__geo_interface__]
        xds_repr_match = xds_repr_match.rio.clip(geoms)
    #write to file
    name = tif.split('.tif')[0]+'_car.tif'
    xds_repr_match.rio.to_raster(name,tiled=True,windowed=True)
    return name

# def align_raster_cells(ref,target):
#     opt = gdal.WarpOptions(targetAlignedPixels=True)


# def align_extent_raster(raster_reference, tiff_to_be_aligned, output_path):
#     with rasterio.open(raster_reference) as src1:
#         data1 = src1.read(1)
#         profile1 = src1.profile
#         bounds1 = src1.bounds
#         transform_1 = src1.transform
#         no_data_1 = src1.nodata
        

#     with rasterio.open(tiff_to_be_aligned) as src2:
#         data2 = src2.read(1)
#         profile2 = src2.profile
#         bounds2 = src2.bounds
#         transform_2 = src2.transform

#     window = rasterio.windows.from_bounds(*bounds1, transform=transform_2)

#     with rasterio.open(tiff_to_be_aligned) as src2:
#         smaller_array = src2.read(window=window, boundless=True) 

#     profile1.update(nodata= no_data_1)
    
#     # Export it to another image 
#     with rasterio.open(output_path, 'w', **profile1) as dst:
#         dst.write(smaller_array)

def create_difference_raster_by_block(benchmark_tif,test_tifs):
    diff_data = {}
    with rasterio.open(benchmark_tif) as image:
        b_profile = image.profile
    #compression
    b_profile['compress'] = 'LZW'
    for in_tif in test_tifs:
        precision = 0
        recall =  0
        f1 = 0
        name = pl.Path(in_tif).stem
        with rasterio.Env():
            with rasterio.open(pl.Path(in_tif).parent/'{}_difference_abs.tif'.format(name), 'w', **b_profile) as dst_abs:
                with rasterio.open(pl.Path(in_tif).parent/'{}_difference.tif'.format(name), 'w', **b_profile) as dst:
                    with rasterio.open(benchmark_tif) as src:
                        b_profile = src.profile
                        total_cells = src.width*src.height
                        for ji, window in src.block_windows(1):
                            first_array = src.read(1,window=window)
                            with rasterio.open(in_tif) as image:
                                t_profile = image.profile
                                second_array = image.read(1,window=window)
                                f_no = np.array(first_array,copy=True)
                                s_no = np.array(second_array,copy=True)
                                f_no[f_no==b_profile['nodata']] = np.nan
                                s_no[s_no==t_profile['nodata']] = np.nan
                                #remove negative depths
                                f_no[f_no<0] = np.nan
                                s_no[s_no<0] = np.nan
                                minus_array = np.absolute(f_no - s_no)
                                dif_array = np.add(np.negative(f_no),s_no)

                                #convert to binary for metrics
                                f_no[f_no > 0] = 1
                                f_no[f_no <= 0] = 0
                                s_no[s_no > 0] = 1
                                s_no[s_no <= 0] = 0
                                np.nan_to_num(f_no,copy=False,nan=0)
                                np.nan_to_num(s_no,copy=False,nan=0)

                                precision += (metrics.precision_score(f_no.flatten(), s_no.flatten(),average='binary',zero_division=1.0)*len(f_no.flatten()))/total_cells
                                recall +=  (metrics.recall_score(f_no.flatten(), s_no.flatten(),average='binary',zero_division=1.0)*len(f_no.flatten()))/total_cells
                                f1 +=  (metrics.f1_score(f_no.flatten(), s_no.flatten(),average='binary',zero_division=1.0)*len(f_no.flatten()))/total_cells        
                            dst_abs.write(minus_array, 1, window = window)
                            dst.write(dif_array, 1, window = window)
        diff_data[name] = {'precision':precision,'recall':recall,'f1':f1,'diff_tif':pl.Path(in_tif).parent/'{}_difference_abs.tif'.format(name)}
    return diff_data


# def create_difference_raster_by_block_working(benchmark_tif,test_tifs):
#     diff_data = {}
#     with rasterio.open(benchmark_tif) as image:
#         b_profile = image.profile
#     t = window_scaler(b_profile,target_block_size=2560)
#     #compression
#     #b_profile['compress'] = 'LZW'
#     for in_tif in test_tifs:
#         precision = 0
#         recall =  0
#         f1 = 0
#         name = pl.Path(in_tif).stem
#         with rasterio.Env():
#             with rasterio.open(pl.Path(in_tif).parent/'{}_difference_abs.tif'.format(name), 'w', **b_profile) as dst_abs:
#                 with rasterio.open(pl.Path(in_tif).parent/'{}_difference.tif'.format(name), 'w', **b_profile) as dst:
#                     with rasterio.open(benchmark_tif) as src:
#                         b_profile = src.profile
#                         total_cells = src.width*src.height
#                         for ji, window in src.block_windows(1):
#                             if ji[0]%t == 0 and ji[1]%t == 0:
#                                 window_co = window.col_off
#                                 window_ro = window.row_off
#                                 window_w = window.width*t if window_co+window.width*t <= src.width else src.width%t
#                                 window_h = window.height*t if window_ro+window.height*t <= src.height else src.height%t
#                                 first_array = src.read(1,window=Window(window_co,window_ro,window_w,window_h))
#                                 with rasterio.open(in_tif) as image:
#                                     t_profile = image.profile
#                                     second_array = image.read(1,window=Window(window_co,window_ro,window_w,window_h))
#                                 #math
#                                 f_no = np.array(first_array,copy=True)
#                                 s_no = np.array(second_array,copy=True)
#                                 f_no[f_no==b_profile['nodata']] = np.nan
#                                 s_no[s_no==t_profile['nodata']] = np.nan
#                                 #remove negative depths
#                                 f_no[f_no<0] = np.nan
#                                 s_no[s_no<0] = np.nan
#                                 minus_array = np.absolute(f_no - s_no)
#                                 dif_array = np.add(np.negative(f_no),s_no)

#                                 #convert to binary for metrics
#                                 f_no[f_no > 0] = 1
#                                 f_no[f_no <= 0] = 0
#                                 s_no[s_no > 0] = 1
#                                 s_no[s_no <= 0] = 0
#                                 np.nan_to_num(f_no,copy=False,nan=0)
#                                 np.nan_to_num(s_no,copy=False,nan=0)

#                                 precision += (metrics.precision_score(f_no.flatten(), s_no.flatten(),average='binary',zero_division=1.0)*len(f_no.flatten()))/total_cells
#                                 recall +=  (metrics.recall_score(f_no.flatten(), s_no.flatten(),average='binary',zero_division=1.0)*len(f_no.flatten()))/total_cells
#                                 f1 +=  (metrics.f1_score(f_no.flatten(), s_no.flatten(),average='binary',zero_division=1.0)*len(f_no.flatten()))/total_cells        
#                             dst_abs.write(minus_array, 1, window = Window(window_co,window_ro,window_w,window_h))
#                             dst.write(dif_array, 1, window = Window(window_co,window_ro,window_w,window_h))
#         diff_data[name] = {'precision':precision,'recall':recall,'f1':f1,'diff_tif':pl.Path(in_tif).parent/'{}_difference_abs.tif'.format(name)}
#     return diff_data

# def create_max_raster(out_path,area_name,list_of_tifs,save_as_raster = True):
#     true_tifs = []
#     for tif in list_of_tifs:
#         if tif.find(area_name)>=0:
#             true_tifs.append(list_of_tifs.index(tif))
#     #first tif for shape
#     with rasterio.open(list_of_tifs[true_tifs[0]]) as image:
#         first_array = image.read(1)
#         profile = image.profile
#     max_array = first_array
#     if len(true_tifs) > 1:
#         for results_index in true_tifs:
#             with rasterio.open(list_of_tifs[results_index]) as image:
#                 area_array = image.read(1)
#             max_array = np.maximum(max_array,area_array)
#     if save_as_raster:
#         create_new_rast(out_path,area_name+'_max.tif',profile,max_array)
#     return max_array

def create_new_rast(out_path,name,profile,array):
    with rasterio.Env():
        with rasterio.open(pl.Path(out_path)/name, 'w', **profile) as dst:
            dst.write(array, 1)
            
def import_basemaps():
    # Add custom basemaps to folium
    basemaps = {
    "Google Maps": folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Maps",
        overlay=True,
        control=True,
    ),
    "Google Satellite": folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Satellite",
        overlay=True,
        control=True,
    ),
    "Google Terrain": folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Terrain",
        overlay=True,
        control=True,
    ),
    "Google Satellite Hybrid": folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Satellite",
        overlay=True,
        control=True,
    ),
    "Esri Satellite": folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Esri Satellite",
        overlay=True,
        control=True,
    ),
    }
    return basemaps


def reproj_match(infile, match):
    """Reproject a file to match the shape and projection of existing raster. 
    
    Parameters
    ----------
    infile : (string) path to input file to reproject
    match : (string) path to raster with desired shape and projection 
    outfile : (string) path to output file tif
    """
    # open input
    with rasterio.open(infile) as src:
        src_transform = src.transform
        
        # open input to match
        with rasterio.open(match) as match:
            dst_crs = match.crs
            
            # calculate the output transform matrix
            dst_transform, dst_width, dst_height = calculate_default_transform(
                src.crs,     # input CRS
                dst_crs,     # output CRS
                match.width,   # input width
                match.height,  # input height 
                *match.bounds,  # unpacks input outer boundaries (left, bottom, right, top)
            )

        # set properties for output
        dst_kwargs = src.meta.copy()
        dst_kwargs.update({"crs": dst_crs,
                           "transform": dst_transform,
                           "width": dst_width,
                           "height": dst_height,
                           "nodata": 0})
        # open output
        outfile = str(infile).replace('.tif','_aligned.tif')
        with rasterio.open(outfile, "w", **dst_kwargs) as dst:
            # iterate through bands and write using reproject function
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest)
    return outfile

def crop_tif(tif,shp):
    with rasterio.open(tif) as image:
        profile = image.profile
    out_crs = profile['crs']
    overlap_sr = gpd.read_file(shp).to_crs(crs=out_crs).dissolve()
    geoms = [overlap_sr['geometry'].iloc[0].__geo_interface__]
    with rasterio.open(tif) as rast:
        out_image, out_transform = rasterio.mask.mask(rast,geoms,crop=True)
        clip_tif = str(tif)[:str(tif).find('.tif')]+'_cropped.tif'
        out_meta = rast.meta
        out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform})

        with rasterio.open(clip_tif, "w", **out_meta) as clipped:
            clipped.write(out_image)
    return clip_tif

def crop_tif_rast(tif,target_tif):
    with rasterio.open(tif) as src:
        with rasterio.open(target_tif) as mask_image:
            profile = mask_image.profile
            mask_data = mask_raster.read(1)
            mask = mask_data != profile.no_data
        
            out_image, out_transform = rasterio.mask.mask(src,[mask],crop=True)
            clip_tif = str(tif)[:str(tif).find('.tif')]+'_cropped.tif'
            out_meta = rast.meta
            out_meta.update({"driver": "GTiff",
                        "height": out_image.shape[1],
                        "width": out_image.shape[2],
                        "transform": out_transform})

        with rasterio.open(clip_tif, "w", **out_meta) as clipped:
            clipped.write(out_image)
    return clip_tif

def mask_tif(tif,shps,action='mask'):
    action_d = {'mask':True,'clip':False}
    with rasterio.open(tif) as image:
        profile = image.profile
    out_crs = profile['crs']
    mask = gpd.read_file(shps[0]).to_crs(crs=out_crs)
    if len(shps) > 1:
        for shp in shps[1:]:
            mask_add = gpd.read_file(shp).to_crs(crs=out_crs)
            mask = pd.concat([mask,mask_add])
    mask_sr = mask.dissolve()
    geoms = [mask_sr['geometry'].iloc[0].__geo_interface__]
    with rasterio.open(tif) as rast:
        out_image, out_transform = rasterio.mask.mask(rast,geoms,invert=action_d[action])
        mask_tif = str(tif)[:str(tif).find('.tif')]+'_masked.tif'
        out_meta = rast.meta
        with rasterio.open(mask_tif, "w", **out_meta) as masked:
            masked.write(out_image)
    return mask_tif

def get_sst_storms_by_recurrence_underscore(huc,hms_shps):
    events_dict = {huc:{}}
    unique_events = []
    short_ids_dict = {}
    for ri_shp in hms_shps:
        f = re.search('_\d+.\d+[pm]*_',ri_shp)
        ri = f.group()[1:-1]
        events_dict[huc][ri] = []
        gdf = gpd.read_file(ri_shp)
        cols = list(gdf.columns.to_list())
        r = re.compile('R\d+-Y\d+-E\d+')
        col_matches = list(filter(r.match, cols))
        col_matches_ = []
        for col in col_matches:
            col_matches_.append(col.replace('-','_'))
        col_matches = col_matches_

        if col_matches:
            events_dict[huc][ri] = col_matches
            unique_events+= col_matches
            for col in col_matches:
                r_short = re.search('Y\d+_E\d+',col)
                short_ids_dict[col] = r_short.group()
        else:
            events_dict[huc][ri] = []

    counts = Counter(unique_events)
    if counts.most_common()[0][1] <= 1:
        print(f"Note that the same storm event {counts.most_common()[0][0]} is used for more than recurrence interval")
    #short_counts = Counter(list(short_ids_dict.values()))
    #assert short_counts.most_common()[0][1] <= 1, f"the same storm event number and year number {short_counts.most_common()[0][0]} is used for more than one realization. Discuss with Matt D about adding the RX to the dss file names"
    return events_dict