
# LEAF processing script (Version 5, November 2019)
# Written by Darius Culvenor (darius.culvenor@sensingsystems.com.au)
# This script is provided "as-is". It may be used and/or modified freely.
# Please let the author know of any coding mistakes or significant improvements.

# Dependencies: processing is mostly dependent on pandas, numpy and matplotlib libraries for Python3
# Known working versions: Pandas (0.16.2), Numpy (1.9.2), Matplotlib (1.1.1rc2)

# ---------------------------------------------------------------------------------------------
# Define a function to import a LEAF data file and calculate XYZ from azimuth, zenith and range
# ---------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------
# main thread
# ----------------------------------------------------------------------

import os
import sys
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from glob import glob

BASEPATH = 'C:/Users/new298/OneDrive - CSIRO/Projects/LEAF Laser Scanner/Tumbarumba 2019 LEAF scans/'

os.chdir(BASEPATH)
import LEAF_functions

DATAFOLDER = BASEPATH + 'data/'                        # INPUT files. This is the folder location for LEAF data input files
OUTPUTFOLDER = BASEPATH + 'output/'                   # OUTPUT files. This is the folder location for procesed LEAF data files

print('Processing LEAF data...')
    
pd.options.mode.chained_assignment = None              # turn off pandas warning about replacing elements in dataframe 'Setting with Copy...'
np.set_printoptions(threshold=sys.maxsize)

InstParams = {'tripodHeight':1.1, 
              'instrumentHeight':0.33, 
              'incrScanEncoder':10000.0, 
              'incrRotEncoder':20000.0, 
              'rangeMin':0.3,
              'rangeMax':100.0,
              'maxRangeDelta':0.3}

profileParams = {'minZenithDeg':0, 
              'maxZenithDeg':90, 
              'nRings':9,
              'heightStep':5.0,
              'hingeWidthDeg':2.0,
              'smoothing':10}

# flist = glob(DATAFOLDER+'*hemi*.csv')
flist = glob(DATAFOLDER+'*.csv')
inputFile = flist[1]
print("%s %s" % ('\nProcessing ', inputFile))

# import csv file into pandas dataframe (no header), skip metadata rows, drop bad lines that would otherwise raise an exception
df = pd.read_csv(inputFile, header=None, skiprows=15, error_bad_lines=False, warn_bad_lines=True)    
numCols = len(df.columns)
print('num cols: {:d}'.format(numCols))

df = df[:-6]          # drop the bottom six rows of the input datafile (metadata information)

df.drop(df.columns[[0,6]], axis=1, inplace=True)    # delete the sample and millisec columnns
df.columns = ['scanEnc','rotEnc','range1','intensity','range2']
df.index.name = 'sample'

# Add the following columns to the dataframe: 'zenithRad','azimuthRad', 'x1', 'y1', 'z1', 'x2', 'y2', 'z2
df = LEAF_functions.ConvertToXYZ(df, InstParams)

#Null any points that have a range of zero or an intensity of zero - have temporarily removed range2=0 and delta<0.3
df = LEAF_functions.FilterPoints(df, InstParams['rangeMin'], InstParams['maxRangeDelta'])

# If its a hinge scan do a hinge profile
profile = LEAF_functions.hingeProfile(df, InstParams, profileParams)

# If it's a hemispherical scan then use all the data to do a full hemi profile
########## work on this with Darius ###########

# Work out what scan configuration was used
shotCount = LEAF_functions.ShotsByZenithRing(df, InstParams, profileParams)
print(shotCount['nShots'])

PgapDF = LEAF_functions.getPgap(df, InstParams, profileParams)
print('Pgap Array = ', PgapDF)

# zero = LEAF_functions.hemiProfile()
# print(temp)

# # ----- plot  profiles to the screen -----
# LEAF_functions.PlotProfile(profile, profileParams['smoothing'], inputFile, OUTPUTFOLDER)


# ----- Write output point cloud files -----

# # output all processed data as comprehensive *.csv file (good for detailed analysis and checking calculations)
# df.to_csv(path_or_buf=OUTPUTFOLDER + os.path.splitext(os.path.basename(inputFile))[0] + '_xyz.csv', float_format='%.3f')

# # output subset of columns as *.xyz file (mainly used for visualising point clouds)
# xyzCols = ['x1','y1','z1','x2','y2','z2','intensity','delta']
# df.to_csv(path_or_buf=OUTPUTFOLDER + os.path.splitext(os.path.basename(inputFile))[0] + '.xyz', columns=xyzCols, index=False, float_format='%.2f')                        


