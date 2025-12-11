#### This file holds all the manually defined variables for the code. No other variable will require changes within the notebook. Only manual inputs will be requested as typed entries

import os
import pathlib as pl

######### manual inputs 

home = pl.Path(os.getcwd())

#creation of folders as needed for inputs, outputs and working_outputs
inputs = home/'inputs'/'wy22_dictionary_updates'/'HEC-HMS Models SST Schematics'
outputs = home/'outputs'/'wy22_dictionary_updates'
working_outputs = home/'outputs'/'wy22_dictionary_updates'/'working_outputs_dictionary'

if not os.path.exists(inputs):
    os.makedirs(inputs)
if not os.path.exists(outputs):
    os.makedirs(outputs)
if not os.path.exists(working_outputs):
    os.makedirs(working_outputs)
#Ensure that all input geodatabases/geopackages are in the inputs folder as defined


#Are inputs in geodatabase or geopackage form. Altar based on format of files. "*.gdb" if geodatabases, "*.gpkg" if geopackages. All inputs must be the same format otherwise they will not be merged all at once.
schematic_input_type = '/*.gdb'

#Paths to expected shapefiles
sub_path = inputs/"bighorn_subbasins_merged_250721.shp" #path to the assigned subbasins shapefile.
subb_field = "huc_mod" #huc10 assignment field name within the shapefile

dsj_path = inputs/"bighorn_draft_ds_junctions_250721.shp"#path to the downstream junctions
dsj_field = "huc" #huc10 assignment field within shapefile

perim_path = inputs/"bighorn_perimeters_draft_ver2_clean_250721.shp" #path to the perimeter shapefile
perim_field = "huc_mod" #huc10 assignment field within the shapefile
