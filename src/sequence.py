import pathlib as pl
import os
import pandas as pd
import geopandas as gpd
import fiona
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import json
import numpy as np

#counter and trace function from upstreamt to downstream
#chooses the longest flowpath if there is more than one huc4 that flows into a downstream huc4
def ds_count(df,start_col,ds_col, huc,to_huc, to_huc_list,from_huc_list):
    ds_list = []
    count = 0
    while to_huc in from_huc_list:
        ds_list.append(to_huc)
        count+=1
        huc = to_huc
        if df.loc[df[start_col] == to_huc,ds_col].count() > 1:
            to_hucs = df.loc[df[start_col] == to_huc,ds_col].to_list()
            ds_counts = []
            for to_huc in to_hucs:
                ds_counts.append(ds_count(df,start_col,ds_col,huc,to_huc, to_huc_list,from_huc_list)[0])
            to_huc = to_hucs[ds_counts.index(max(ds_counts))]
        else:
            to_huc = df.loc[df[start_col] == to_huc,ds_col].iloc[0]    
    return count, ds_list

#counter and trace function from upstream to downstream
#chooses the longest flowpath 
def us_count(df,start_col,ds_col,huc,to_huc, to_huc_list,from_huc_list):
    us_list = []
    count = 0
    while huc in to_huc_list:
        count+=1
        to_huc = huc
        if df.loc[df[ds_col] == huc,start_col].count() > 1:
            from_hucs = df.loc[df[ds_col] == huc,start_col].to_list()
            us_counts = []
            for huc in from_hucs:
                us_counts.append(us_count(df,start_col,ds_col,huc,to_huc, to_huc_list,from_huc_list)[0])
            huc = from_hucs[us_counts.index(max(us_counts))]
        else:
            huc = df.loc[df[ds_col] == huc,start_col].iloc[0]
        us_list.append(huc)
    return count, us_list

def rule(df,cycle,cycles_left):
    already_studied = list(df.loc[df['sequence'].isna() == False].index)
    not_studied_hucs = df.loc[~df.index.isin(already_studied)]
    not_ready = []
    ready_hucs = []
    if len(not_studied_hucs.index) == 0:
        return ready_hucs
    fy_list = list(not_studied_hucs.index)
    for huc in fy_list:
        if not df.loc[huc]['ds_sequence']:
            #print(huc,'1st round, no downstream!')
            df.loc[huc,'sequence'] = cycle
            ready_hucs.append(huc)
        elif df.loc[huc]['ds_sequence'][0] in already_studied:
            #print(huc,'downstaream huc is studied. time to study!')
            df.loc[huc,'sequence'] = cycle
            ready_hucs.append(huc)
        else:
            #print(huc, 'not ready for sequencing', 'ds_huc=',df.loc[huc]['ds_sequence'][0])
            not_ready.append(huc)

    already_studied = list(df.loc[df['sequence'].isna() == False].index)
    not_studied_hucs = df.loc[~df.index.isin(already_studied)]
    #ready_hucs = not_studied_hucs.loc[~not_studied_hucs.index.isin(not_ready)]
    print(ready_hucs)
    return(ready_hucs)
    if cycles_left == 0:
        return ready_hucs