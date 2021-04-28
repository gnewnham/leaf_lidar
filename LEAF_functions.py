# -*- coding: utf-8 -*-
"""
Created on Sat Aug 22 14:04:01 2020

@author: new298
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

def ConvertToXYZ(df, InstParams):
    
     # ----- calculate xyz coords from range, azimuth and zenith -----
    df['zenithRad'] = ((df['scanEnc']/InstParams['incrScanEncoder'])*np.pi*2)    # zenith angle in radians
    df['azimuthRad'] = ((df['rotEnc']/InstParams['incrRotEncoder'])*np.pi*2)    # azimuth angle in radians
        
    df['x1'] = (np.sin(df['zenithRad']) * df['range1']) * np.sin(df['azimuthRad'])
    df['y1'] = (np.sin(df['zenithRad']) * df['range1']) * np.cos(df['azimuthRad'])
    df['z1'] = (-(np.cos(df['zenithRad']) * df['range1']) + InstParams['tripodHeight'] + InstParams['instrumentHeight'])
    
    df['x2'] = (np.sin(df['zenithRad']) * df['range2']) * np.sin(df['azimuthRad'])
    df['y2'] = (np.sin(df['zenithRad']) * df['range2']) * np.cos(df['azimuthRad'])
    df['z2'] = (-(np.cos(df['zenithRad']) * df['range2']) + InstParams['tripodHeight'] + InstParams['instrumentHeight'])
    
    #transform zenith=[0:pi] azimuth=[0:2pi] - *** check with Darius
    df['zenithRad'] = df['zenithRad'] - np.pi
    mask = df['zenithRad'] < 0.0
    df.loc[mask, 'zenithRad'] = (0.0 - df.loc[mask, 'zenithRad'])
    df.loc[mask, 'azimuthRad'] = (df.loc[mask, 'azimuthRad'] + np.pi)

    return df


def FilterPoints(df, minRange=0.0, maxDelta=0.3):
    
    # ----------- apply filtering to remove spurious/unreliable points ---------------
    # filtering is based mostly on an anlysis of the two range measurements that are
    # acquired in each pointing direction. The successive range measurements should be
    # very close. Filtering is an important process and some further investigation and 
    # --- optimisation may be worthwhile, including better use of intensity values ---
    
    #Glenn: is there a difference between a gap and an error? If so we shoudl remove error rows as well as set gap to zero
    
    mask = df['range1'] < minRange                                # replace any range 1 negative values (normally -1.00) with zero. These are non-hits (gaps).
    df.loc[mask, 'range1'] = 0    
    df.loc[mask, 'range2'] = 0    
    
    #mask = df['range2'] < minRange                                # replace any range 2 negative values (normally -1.00) with zero. These are non-hits (gaps).
    #df.loc[mask, 'range1'] = 0    
    #df.loc[mask, 'range2'] = 0
    
    mask = df['intensity'] == 0                            # nullify all ranges with raw intensity zero (there have been no 1/r2 corrections to intensity at this point, but there should be if an intensity threshold > 0 is applied)
    df.loc[mask, 'range1'] = 0    
    df.loc[mask, 'range2'] = 0    
    
    df['delta'] = np.sqrt(np.square(df['range1']-df['range2']))    # unsigned difference between range 1 ans 2 for each direction
    mask = df['delta'] > maxDelta                            # if distance between range 1 & 2 is > 0.3m then nullify the point
    df.loc[mask, 'range1'] = 0    
    df.loc[mask, 'range2'] = 0
    
    return df


def HingeProfile(df, InstParams, hingeWidthDeg, minRange):
    
#    hingeWidthDeg=1
#    minRange=0.3
    
    # -------------- calculate LAI profiles ---------------------
    
    dfZ = df[['x1','y1','z1','zenithRad','range1']].copy()
    dfZ.columns = ['x','y','z','zenithRad','Range']
    
    print('Total shots in file (before filtering):', np.size(dfZ, axis=0))    
    print('Min, Max Z: {:0.2f}, {:0.2f}'.format(dfZ['z'].min(), dfZ['z'].max()))

    hingeAngleRadians = np.arctan(np.pi/2.0)
    dtor = np.pi/180.0
    hingeWidth = hingeWidthDeg * dtor
    hinge = {'Min':hingeAngleRadians-hingeWidth, 'Max':hingeAngleRadians+hingeWidth}
 
    #not sure what happens when no points are found within the range
    dfZ['mask'] = (dfZ['zenithRad'] > hinge['Min']) & (dfZ['zenithRad'] < hinge['Max'])
    dfZ = dfZ[dfZ['mask']]

    # LEAF point of lidar rotation is treated as the origin (xyz = 0) for LAI calculation. Tripod and instruemnt height are added later.
    dfZ['z'] = (dfZ['z'] - InstParams['tripodHeight'] - InstParams['instrumentHeight'])    
    
    totalShots = np.size(dfZ, 0)
    print('There are {:0d} shots within hinge angle of +/- {:0.2f} deg.'.format(totalShots, hingeWidthDeg))

    #this is really filtering    
    dfZ = dfZ[(dfZ['Range'] > minRange)]

    hitCount = np.size(dfZ, 0)
    print('Number of hits:', hitCount)
    
    minZ = dfZ['z'].min()                                # calculate a few basic z-dimension stats from hinge angle data
    maxZ = dfZ['z'].max()
    pct001Z = dfZ['z'].quantile(0.001)                    # 0.10%
    pct999Z = dfZ['z'].quantile(0.999)                    # 99.9%
    
    print('Hinge angle shots Min, Max Z: {:0.2f}, {:0.2f}'.format(minZ,maxZ))
    print('Hinge angle 0.1%, 99.9% height: {:0.2f}, {:0.2f}'.format(pct001Z,pct999Z))
    
    binCount = int((pct999Z/InstParams['zIncr'])+1)
    pct999ZRounded = float('{:0.1f}'.format(binCount*InstParams['zIncr']))
    heightBin = np.linspace(0, pct999ZRounded, binCount+1)
    
    shotCountZ = dfZ['z'].groupby(pd.cut(dfZ['z'],heightBin)).count()
    hitCount = shotCountZ.sum()
    print('Number of hinge angle shots to 99.9% height:', hitCount)
    
    #check to make sure that height bin is the correct size, Darius removed one height in his code in the plot
    pf = {'Height':heightBin, 'Pgapz':heightBin*0.0, 'LAIz':heightBin*0.0, 'FAVD':heightBin*0.0, 'sumZStep':heightBin*0.0}
    Profile = pd.DataFrame(pf)

    sumZStep = 0
    for i in range(binCount):
        
        sumZStep += shotCountZ[i]                        # count the cumulative number of hits from the instrument height upwards...
        Pgapz = (1.0 - float(float(sumZStep)/float(totalShots)))
        LAIz = (-1.1 * np.log(Pgapz))
        if(i > 0): 
            FAVD = ((LAIz-Profile['LAIz'][i-1])/InstParams['zIncr']) 
        else: 
            FAVD = 0.0
        Profile.loc[i+1] = [heightBin[i], Pgapz, LAIz, FAVD, sumZStep]
        # print(Profile.loc[i])
        
    # heightBin += (InstParams['tripodHeight'] + InstParams['instrumentHeight'])        # add tripod and instrument height
    # print(heightBin[binCount-1], shotCountZ[binCount-1], sumZStep, 'Top of Canopy PGap {:0.3f} and LAI {:0.3f}'.format(Pgapz[binCount-1],LAIz[binCount-1]))
  
    return(Profile)

def PlotProfile(profile, smoothing, full_fname, OUTPUTFOLDER):
 
    FAVDsmooth = profile['FAVD'].rolling(smoothing).mean()                # applying moving average filter 1m high

    baseFilename = os.path.splitext(os.path.basename(full_fname))[0]
    legendText = baseFilename.split('Z')[0]

    #print(profile.describe())

    fig, (ax1, ax2) = plt.subplots(1, 2, sharey=True)
    fig.subplots_adjust(hspace=0.1, wspace=0.1)
    plt.rcParams.update({'font.size': 10})
    # set global tick label sizes for both axes
    plt.rc('xtick',labelsize=8)
    plt.rc('ytick',labelsize=8)

    ax1.plot(profile['LAIz'], profile['Height'], linewidth=1, label='{}, n={:f}'.format(legendText, max(profile['sumZStep'])))
    #ax1.legend(loc='lower right', shadow=False, ncol=1, prop={'size':8})
    ax1.legend(loc='upper left', shadow=False, ncol=1, prop={'size':8})
    ax1.set_xlabel('Leaf Area Index (LAI)', fontsize=12)
    ax1.set_ylabel('Height (m)', fontsize=12)
        
    ax2.plot(FAVDsmooth, profile['Height'], linewidth=1, label='{}, n={:f}'.format(legendText,max(profile['sumZStep'])))
    ax2.set_xlabel('Foliage Area Volume Density (FAVD)', fontsize=12)
        
    fig.set_size_inches(11.0, 8.5)
    fig.savefig(OUTPUTFOLDER + 'LAIz_FAVD.jpg', dpi=300, bbox_inches='tight')
    plt.show()

 
def ShotsByZenithRing(df, InstParams, nRings=9, minZen=0.0, maxZen=np.pi/2.0):

    # return the number of shots in each of nRings

    ringWidth = (maxZen-minZen) / nRings
    halfWidth = ringWidth/2.0
    ringCentres = np.arange(minZen+halfWidth, maxZen, ringWidth)
    ringCentresDeg = ringCentres / np.pi * 180
    nShots = np.zeros(nRings)

    for i in range(nRings):
        minZen = ringCentres[i]-halfWidth
        maxZen = ringCentres[i]+halfWidth
        mask = ((df['zenithRad'] > minZen) & (df['zenithRad'] < maxZen))
        nShots[i] = np.sum(mask)

    shotCount = {'ringCentresDeg':ringCentresDeg, 
                'ringCentres':ringCentres,
                'nShots':nShots}

    return shotCount


def getPgap():
    #return the Pgap profile by zenith ring, ie 2d array
    return 0


def hemiProfile():
    #return the vertial L and FAVD profile
    return 0
