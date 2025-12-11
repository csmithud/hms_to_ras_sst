#### This file holds all the manually defined variables for the code. No other variable will require changes within the notebook. Only manual inputs will be requested as typed entries

import os
import pathlib as pl

######### manual inputs 

home = pl.Path(os.getcwd())

#creation of folders as needed for inputs, outputs and working_outputs
inputs = home/'inputs'/'mt_powdert_perim'
outputs = home/'outputs'/'mt_powdert_perim'
working_outputs = home/'outputs'/'mt_powdert_perim'/'working_outputs'
#review if input data in geopackage or geodatabase format
input_file_type = '/*.gpkg'

#if the input/output folders do not exist, create said folders
if not os.path.exists(inputs):
    os.makedirs(inputs)
if not os.path.exists(outputs):
    os.makedirs(outputs)
if not os.path.exists(working_outputs):
    os.makedirs(working_outputs)