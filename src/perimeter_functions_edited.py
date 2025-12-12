import geopandas as gpd
from pathlib import Path
import pandas as pd
import requests
import fiona
import re
import os
# from shapely.geometry import Polygon, MultiPolygon
# from shapely.ops import unary_union
import numpy as np
# from scipy.interpolate import splprep, splev



#Identifies geodatabases and merges layers based on name into singular geodataframes

def locate_string_gdb_to_concat_gdf(gdb_path_list,locater_string,coordinate_sys=None):
    gdb_quantity = len(gdb_path_list)
    
    if gdb_quantity == 0:
        print(f'cannot identify any {locater_string} from the path list provided')
        gdf_x = gpd.GeoDataFrame()
        gdf_x['geometry'] = None
        coord = coordinate_sys
    
    if gdb_quantity != 0:
        layers_list = fiona.listlayers(gdb_path_list[0])
        if locater_string in layers_list:
            gdf_x = gpd.read_file(gdb_path_list[0], layer=f"{locater_string}")
            coord = gdf_x.crs
            gdf_x['Source_Path'] = os.path.basename(gdb_path_list[0])
            if coordinate_sys!= None:
                coord = coordinate_sys
                gdf_x = gdf_x.to_crs(coord)
            else:
                pass
        else:
            gdf_x = gpd.GeoDataFrame()
            gdf_x['geometry'] = None
            coord = None
    
    if gdb_quantity > 1:
        for i in range(1,gdb_quantity):
            layers_list2 = fiona.listlayers(gdb_path_list[i])
            if locater_string in layers_list2:
                gdf_x2 = gpd.read_file(gdb_path_list[i], layer=f"{locater_string}")
                coord2 = gdf_x2.crs
                gdf_x2['Source_Path'] = os.path.basename(gdb_path_list[i])
                if coord == None:
                    coord = coord2
                if coord2 != coord:
                    print("\ncoordinate systems are not the same: will convert to match first gdb/gpkg in path list")
                    gdf_x2 = gdf_x2.to_crs(gdf_x.crs)
                gdf_x = pd.concat([gdf_x,gdf_x2])
                gdf_x.reset_index(drop=True, inplace=True)
            else:
                pass
    
    print(f'After searching through {gdb_quantity} geodatabases/geopackages, there are now {len(gdf_x)} \"{locater_string}\" features')
    return gdf_x


##Definition of Classes and functions

###Attaining all of the HUCs that potentially intersect the area where the junction lie

def retrieve_wbd_huc10_intersections(subbasins,outputs):
    print(f"Successfully loaded shapefile with {len(subbasins)} features")
    # Get the bounding box
    bbox = subbasins.total_bounds
    # Ensure the subbasins are in WGS84 (EPSG:4326) for the web service
    if subbasins.crs != 'EPSG:4326':
        print(f"Converting from {subbasins.crs} to EPSG:4326")
        subbasins = subbasins.to_crs('EPSG:4326')
        bbox = subbasins.total_bounds
        # subbasins.plot()
    # Format bbox for the web service
    bbox_string = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
    # Set up the request
    url = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/5/query"
    # print(bbox_string)
    params = {
        'where': '1=1',
        'outFields': '*',
        'geometry': bbox_string,
        'geometryType': 'esriGeometryEnvelope',
        'spatialRel': 'esriSpatialRelIntersects',
        'f': 'geojson',
        'inSR': '4326',
        'outSR': '4326',
        'returnGeometry': 'true'
    }
    try:
        # Make the request
        response = requests.get(url, params=params)  

        if response.status_code == 200:
            # Save the GeoJSON to a temporary file
            temp_geojson = "temp_hucs.geojson"
            with open(temp_geojson, 'w') as f:
                f.write(response.text)
            # Read the temporary file
            hucs = gpd.read_file(temp_geojson)
            print(f"Successfully loaded {len(hucs)} HUC features")
            hucs.to_file(outputs/"huc10s_to_compare.shp")
            print('exported hucs to folder designated')
            return hucs
        else:
            print(f"Error fetching data: {response.status_code}")
            return None

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print(f"Error type: {type(e)}")


#collects junctions upstream of the starting junction name - meant to be in a list. The next two variables are dictionaries
def move_up(in_junctions,junc_to_reach,reach_to_junc):
    starting_junctions = set()
    for junc in in_junctions:
        starting_junctions.add(junc)
    
    #from the starting in_table, filter reaches that connect to them going downstream
    us_reaches = [x for x,y in reach_to_junc.items() if y in starting_junctions]

    #from those us_reaches present we find the upstream junctions
    if len(us_reaches) != 0:
        us_junctions = [x for x,y in junc_to_reach.items() if y in us_reaches]
        return us_junctions
    else:
        # print("There are no upstream reaches to the given junctions")
        us_junctions = []
        return us_junctions
    
#returns the amount of junctions upstream of the starting one provided they're within the list (intended to be list of junctions within a HUC10)
#in_junctions is a list with the starting junction to count. Should be one, within_list is a list of permissible junctions allowed to be counted as upstream junctions, the last variables being dictionaries
def count_up_within_list_limiting(in_junction,within_list,junc_to_reach,reach_to_junc):
    us_count = 0
    temp_count = None
    in_junctions = []
    in_junctions.append(in_junction)
    
    while temp_count != 0:
        us_junctions = move_up(in_junctions,junc_to_reach,reach_to_junc)
        if len(us_junctions) != 0:
            allowed_junctions = [x for x in us_junctions if x in within_list]
            in_junctions = allowed_junctions
            temp_count = len(allowed_junctions)
        else:
            temp_count = 0
        us_count += temp_count
    return us_count

#similar counting as function above however the limitation is that it will remove values within the list provided. 
#This is intended to be used to limit counting upstream and limit networks at the next HUC10's "downstream junction"
def count_up_not_within_limiting(in_junction,terminate_list,junc_to_reach,reach_to_junc):
    us_count = 0
    temp_count = None
    in_junctions = []
    in_junctions.append(in_junction)
    
    while temp_count != 0:
        us_junctions = move_up(in_junctions,junc_to_reach,reach_to_junc)
        if len(us_junctions) != 0:
            allowed_junctions = [x for x in us_junctions if x not in terminate_list]
            in_junctions = allowed_junctions
            temp_count = len(allowed_junctions)
        else:
            temp_count = 0
        us_count += temp_count
    return us_count

#returns the downstream junctions from a starting junction. in junction should be a string of the singular junction
def move_down(in_junction,junc_to_reach,reach_to_junc):
    in_junctions = []
    in_junctions.append(in_junction)
    
    #from the starting in_table, filter reaches that connect to them going downstream
    ds_reaches = [y for x,y in junc_to_reach.items() if x in in_junctions]

    #from those us_reaches present we find the upstream junctions
    if len(ds_reaches) != 0:
        ds_junctions = [y for x,y in reach_to_junc.items() if x in ds_reaches]
    else:
        # print("There are no upstream reaches to the given junctions")
        ds_junctions = []
    
    return ds_junctions

#if all values in a list lie within the range
def all_in_range(val_list,min_val,max_val):

    for i in range(0,len(val_list)):
        if  min_val <= val_list[i] <= max_val:
            pass
        else:
            return False
    return True

#collects all the junctions upstream of designated ds junctions and makes their huc field the same as the downstream one. all junctions within network of a ds junction have the same huc10 value
def network_up(huc10s,junctions_df,junc_to_reach,reach_to_junc):
    ds_junctions_df = junctions_df.loc[junctions_df['ds_junc_status'] == True]
    ds_junctions_dict = ds_junctions_df.set_index('huc').to_dict()['name']
    
    # print(ds_junctions_dict.keys())
    
    for huc in huc10s:
        junc_set = set()
        in_junctions = []
        in_junctions.append(ds_junctions_dict[huc])
        temp_count_up = None
        
        while temp_count_up != 0:
            us_junctions = move_up(in_junctions,junc_to_reach,reach_to_junc)
            in_junctions = [x for x in us_junctions if x not in ds_junctions_dict.values()]
            temp_count_up = len(in_junctions)
            if temp_count_up != 0:
                junc_set.update(in_junctions)
        
        #once the network is complete, all junctions within the huc10 junction set should have their huc reassigned properly
        junctions_df.loc[junctions_df['name'].isin(junc_set), 'huc'] = huc
    return junctions_df

 

#########################################################################################################################################
#########################################################################################################################################
#########################################################################################################################################
#########################################################################################################################################
#########################################################################################################################################


#The following functions are mainly for the schematic to dictionary notebook

def singular_network(starter_list,connection_dictionary,restriction_str):
    total_connection = set()
    for i in starter_list:
        if i in connection_dictionary.keys():
            nextitem = connection_dictionary[i]
            reach_present = re.search(fr'(?i){restriction_str}', nextitem)
            while reach_present:
                nextitem = connection_dictionary[nextitem]
                reach_present = re.search(fr'(?i){restriction_str}', nextitem)
            total_connection.add(nextitem)
        else:
            pass
    return list(total_connection)


def single_dict_creator(gdf_list,identify_field,connection_field,supplemental_dicts):
    connection_dictionary = {}
    for gdf in gdf_list:
        temp_dict = gdf.set_index(identify_field).to_dict()[connection_field]
        connection_dictionary.update(temp_dict)
    for d in supplemental_dicts:
        connection_dictionary.update(d)
    return connection_dictionary



