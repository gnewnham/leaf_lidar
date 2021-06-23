import os
import sys
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from glob import glob

import LEAF_functions

BASEPATH = '/home/pi/dataLEAF/'
DATAFOLDER = BASEPATH + 'data/'                        # INPUT files. This is the folder location for LEAF data input files
OUTPUTFOLDER = BASEPATH + 'output/'                   # OUTPUT files. This is the folder location for procesed LEAF data files

InstParams = {'headerRows':17,
              'tripodHeight':1.1, 
              'instrumentHeight':0.33, 
              'incrScanEncoder':10000.0, 
              'incrRotEncoder':20000.0, 
              'rangeMin':0.3,
              'rangeMax':100.0,
              'maxRangeDelta':0.3}

profileParams = {'minZenithDeg':0, 
              'maxZenithDeg':90, 
              'nRings':9,
              'heightStep':0.1,
              'hingeWidthDeg':2.0,
              'smoothing':10}


#flist = glob(DATAFOLDER+'*.csv')
#inputFile = flist[0]
#print(inputFile)

flist = []															
for dirName, dirNames, fileNames in os.walk(DATAFOLDER):
	for fileName in fileNames:
		flist.append(os.path.join(dirName, fileName))
flist.sort()

profile = []

for index, inputFile in enumerate(flist):
	if os.path.isfile(inputFile):
		if('.csv' in inputFile.lower()):
			try:
				# import csv file into pandas dataframe (no header), skip metadata rows, drop bad lines that would otherwise raise an exception
				df = pd.read_csv(inputFile, header=None, skiprows=InstParams['headerRows'], error_bad_lines=False, warn_bad_lines=True)    
				df = df[:-6]          # drop the bottom six rows of the input datafile (metadata information)
				df.drop(df.columns[[0,6]], axis=1, inplace=True)    # delete the sample and millisec columnns
				df.columns = ['scanEnc','rotEnc','range1','intensity','range2']

				df = LEAF_functions.ConvertToXYZ(df, InstParams)

				shotCount = LEAF_functions.ShotsByZenithRing(df, InstParams, profileParams)
				# print(shotCount['nShots'])

				#Null any points that have a range of zero or an intensity of zero - have temporarily removed range2=0 and delta<0.3
				df = LEAF_functions.FilterPoints(df, InstParams['rangeMin'], InstParams['maxRangeDelta'])

				# If its a hinge scan do a hinge profile
				profile.append(LEAF_functions.hingeProfile(df, InstParams, profileParams))
				print(profile[index])
			except Exception as e:
				print('Error processing LEAF data: {}'.format(e))

print(len(profile))
# ----- plot  profiles to the screen -----
LEAF_functions.PlotProfile(profile, profileParams['smoothing'], flist, OUTPUTFOLDER)



# # # plt.scatter(df['zenithRad'], df['azimuthRad'], c='r')
# # plt.scatter(df['x1'], df['y1'], c='r')
# # plt.show()
