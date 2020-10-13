
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
OUTPUTFOLDER = BASEPATH + '/output/'                   # OUTPUT files. This is the folder location for procesed LEAF data files

print('Processing LEAF data...')
    
pd.options.mode.chained_assignment = None                            # turn off pandas warning about replacing elements in dataframe 'Setting with Copy...'
np.set_printoptions(threshold=sys.maxsize)

InstParams = {'tripodHeight':1.1, 
              'instrumentHeight':0.33, 
              'incrScanEncoder':10000.0, 
              'incrRotEncoder':20000.0, 
              'zIncr':0.1}

                
flist = glob(DATAFOLDER+'*hemi*.csv')
full_fname = flist[1]
print("%s %s" % ('\nProcessing ', full_fname))

# import csv file into pandas dataframe (no header), skip metadata rows, drop bad lines that would otherwise raise an exception
df = pd.read_csv(full_fname, header=None, skiprows=15, error_bad_lines=False, warn_bad_lines=True)    
numCols = len(df.columns)
print('num cols: {:d}'.format(numCols))

df = df[:-6]                                        # drop the bottom six rows of the input datafile (metadata information)

df.drop(df.columns[[0,6]], axis=1, inplace=True)    # delete the sample and millisec columnns
df.columns = ['scanEnc','rotEnc','range1','intensity','range2']
df.index.name = 'sample'


LEAF_functions.ConvertToXYZ(df, InstParams)

LEAF_functions.FilterPoints(df)

hingeWidthDeg = 1.0
minRange = 0.3
profile = LEAF_functions.CalcHingeProfile(df, InstParams, hingeWidthDeg, minRange)
    
# ----- Write output files -----

# output all processed data as comprehensive *.csv file (good for detailed analysis and checking calculations)
df.to_csv(path_or_buf=OUTPUTFOLDER + os.path.splitext(os.path.basename(full_fname))[0] + '_xyz.csv', float_format='%.3f')

# output subset of columns as *.xyz file (mainly used for visualising point clouds)
xyzCols = ['x1','y1','z1','x2','y2','z2','intensity','delta']
df.to_csv(path_or_buf=OUTPUTFOLDER + os.path.splitext(os.path.basename(full_fname))[0] + '.xyz', columns=xyzCols, index=False, float_format='%.2f')                        


FAVDsmooth = profile['FAVD'].rolling(10).mean()                # applying moving average filter 1m high

baseFilename = os.path.splitext(os.path.basename(full_fname))[0]
legendText = baseFilename.split('Z')[0]


#Glenn: probably best if put plotting in a separate function even if it requires re-reading the data
fig, (ax1, ax2) = plt.subplots(1, 2, sharey=True)
fig.subplots_adjust(hspace=0.1, wspace=0.1)
plt.rcParams.update({'font.size': 10})
# set global tick label sizes for both axes
plt.rc('xtick',labelsize=8)
plt.rc('ytick',labelsize=8)

ax1.plot(profile['LAIz'], profile['heightBin'], linewidth=1, label='{}, n={:d}'.format(legendText, max(profile['sumAStep'])))
#ax1.legend(loc='lower right', shadow=False, ncol=1, prop={'size':8})
ax1.legend(loc='upper left', shadow=False, ncol=1, prop={'size':8})
ax1.set_xlabel('Leaf Area Index (LAI)', fontsize=12)
ax1.set_ylabel('Height (m)', fontsize=12)
    
ax2.plot(FAVDsmooth, profile['heightBin'], linewidth=1, label='{}, n={:d}'.format(legendText,max(profile['sumAStep'])))
ax2.set_xlabel('Foliage Area Volume Density (FAVD)', fontsize=12)
    
fig.set_size_inches(11.0, 8.5)
fig.savefig(OUTPUTFOLDER + 'LAIz_FAVD.jpg', dpi=300, bbox_inches='tight')
plt.show()        
    
    

