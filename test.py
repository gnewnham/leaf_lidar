import os
import sys
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from glob import glob

import LEAF_functions

BASEPATH = 'C:/Users/new298/OneDrive - CSIRO/Projects/LEAF Laser Scanner/Tumbarumba 2019 LEAF scans/'
DATAFOLDER = BASEPATH + 'data/'                        # INPUT files. This is the folder location for LEAF data input files
OUTPUTFOLDER = BASEPATH + 'output/'                   # OUTPUT files. This is the folder location for procesed LEAF data files

InstParams = {'tripodHeight':1.1, 
              'instrumentHeight':0.33, 
              'incrScanEncoder':10000.0, 
              'incrRotEncoder':20000.0, 
              'zIncr':0.1}

flist = glob(DATAFOLDER+'*.csv')
inputFile = flist[0]

# import csv file into pandas dataframe (no header), skip metadata rows, drop bad lines that would otherwise raise an exception
df = pd.read_csv(inputFile, header=None, skiprows=15, error_bad_lines=False, warn_bad_lines=True)    
df = df[:-6]          # drop the bottom six rows of the input datafile (metadata information)
df.drop(df.columns[[0,6]], axis=1, inplace=True)    # delete the sample and millisec columnns
df.columns = ['scanEnc','rotEnc','range1','intensity','range2']


df = LEAF_functions.ConvertToXYZ(df, InstParams)

shotCount = LEAF_functions.ShotsByZenithRing(df, InstParams, nRings=9)
print(shotCount['nShots'])

# # plt.scatter(df['zenithRad'], df['azimuthRad'], c='r')
# plt.scatter(df['x1'], df['y1'], c='r')
# plt.show()
