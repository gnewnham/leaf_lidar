# -*- coding: utf-8 -*-
"""
Created on Sat Aug 22 14:04:01 2020

@author: new298
"""
import numpy as np
from numpy.lib.shape_base import column_stack
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


def hingeProfile(df, InstParams, profileParams):
        
    # -------------- calculate LAI hinge profiles ---------------------
    
    dfZ = df[['x1','y1','z1','zenithRad','range1']].copy()
    dfZ.columns = ['x','y','z','zenithRad','Range']
    
    # print('Total shots in file (before filtering):', np.size(dfZ, axis=0))    
    # print('Min, Max Z: {:0.2f}, {:0.2f}'.format(dfZ['z'].min(), dfZ['z'].max()))

    hingeAngleRadians = np.arctan(np.pi/2.0)
    dtor = np.pi/180.0
    hingeWidth = profileParams['hingeWidthDeg'] * dtor
    hinge = {'Min':hingeAngleRadians-hingeWidth, 'Max':hingeAngleRadians+hingeWidth}
 
    #### we should handle the exception where no points are found within the range
    dfZ['mask'] = (dfZ['zenithRad'] > hinge['Min']) & (dfZ['zenithRad'] < hinge['Max'])
    dfZ = dfZ[dfZ['mask']]

    # LEAF point of lidar rotation is treated as the origin (xyz = 0) for LAI calculation. Tripod and instruemnt height are added later.
    dfZ['z'] = (dfZ['z'] - InstParams['tripodHeight'] - InstParams['instrumentHeight'])    
    
    totalShots = np.size(dfZ, 0)
    # print('There are {:0d} shots within hinge angle of +/- {:0.2f} deg.'.format(totalShots, profileParams['hingeWidthDeg']))

    ### Darius - is this really filtering???
    dfZ = dfZ[(dfZ['Range'] > InstParams['rangeMin'])]

    hitCount = np.size(dfZ, 0)
    # print('Number of hits:', hitCount)
    
    minZ = dfZ['z'].min()                                # calculate a few basic z-dimension stats from hinge angle data
    maxZ = dfZ['z'].max()
    pct001Z = dfZ['z'].quantile(0.001)                    # 0.10%
    pct999Z = dfZ['z'].quantile(0.999)                    # 99.9%
    
    # print('Hinge angle shots Min, Max Z: {:0.2f}, {:0.2f}'.format(minZ,maxZ))
    # print('Hinge angle 0.1%, 99.9% height: {:0.2f}, {:0.2f}'.format(pct001Z,pct999Z))
    
    binCount = int((pct999Z/profileParams['heightStep'])+1)
    pct999ZRounded = float('{:0.1f}'.format(binCount*profileParams['heightStep']))
    heightBin = np.linspace(0, pct999ZRounded, binCount+1)
    
    shotCountZ = dfZ['z'].groupby(pd.cut(dfZ['z'],heightBin)).count().to_numpy()
    hitCount = shotCountZ.sum()
    # print('Number of hinge angle shots to 99.9% height:', hitCount)

    # Glenn reworked this section to remove the loop and if statements
    CumCountZ = np.concatenate(([0], np.cumsum(shotCountZ).astype(float)))
    Pgapz = (1.0 - CumCountZ/float(totalShots))
    Pgapz_gtZero = np.clip(Pgapz, 1.0E-100, None)  #set all zero or negative Pgap values to a small number
    LAIz = (-1.1 * np.log(Pgapz_gtZero))

    LAIshift = np.concatenate(([0], LAIz[:-1]))
    FAVD = ((LAIz-LAIshift)/profileParams['heightStep'])

    #check to make sure that height bin is the correct size, Darius removed one height in his code in the plot
    pf = {'Height':heightBin, 'Pgapz':Pgapz, 'LAIz':LAIz, 'FAVD':FAVD, 'sumZStep':CumCountZ}
    Profile = pd.DataFrame(pf)
    
    # heightBin += (InstParams['tripodHeight'] + InstParams['instrumentHeight'])        # add tripod and instrument height
    # print(heightBin[binCount-1], shotCountZ[binCount-1], sumZStep, 'Top of Canopy PGap {:0.3f} and LAI {:0.3f}'.format(Pgapz[binCount-1],LAIz[binCount-1]))
  
    return(Profile)


def PlotProfile(profile, smoothing, full_fname, OUTPUTFOLDER):
    
    fig, (ax1, ax2) = plt.subplots(1, 2, sharey=True)
    
    for i in range(len(profile)):
        
        #print(profile[i].describe())
        FAVDsmooth = profile[i]['FAVD'].rolling(smoothing).mean()      # applying moving average filter
        baseFilename = os.path.splitext(os.path.basename(full_fname[i]))[0]
        legendText = baseFilename.split('Z')[0]
        ax1.plot(profile[i]['LAIz'], profile[i]['Height'], linewidth=1, label='{}, n={:d}'.format(legendText, int(max(profile[i]['sumZStep']))))
        ax2.plot(FAVDsmooth, profile[i]['Height'], linewidth=1)
    
    fig.subplots_adjust(hspace=0.1, wspace=0.1)
    plt.rcParams.update({'font.size': 10})
    plt.rc('xtick',labelsize=8)
    plt.rc('ytick',labelsize=8)
    
    #ax1.legend(loc='lower right', shadow=False, ncol=1, prop={'size':8})
    ax1.legend(loc='upper left', shadow=False, ncol=1, prop={'size':8})
    ax1.set_xlabel('Leaf Area Index (LAI)', fontsize=12)
    ax1.set_ylabel('Height (m)', fontsize=12)
    ax2.set_xlabel('Foliage Area Volume Density (FAVD)', fontsize=12)
    
    fig.set_size_inches(11.0, 8.5)
    fig.savefig(OUTPUTFOLDER + 'LAIz_FAVD.pdf', dpi=300, bbox_inches='tight')
    plt.show()

 
def ShotsByZenithRing(df, InstParams, profileParams):

    # return the number of shots in each of nRings

    minZen = profileParams['minZenithDeg']  * np.pi / 180
    maxZen = profileParams['maxZenithDeg'] * np.pi / 180
    nRings = profileParams['nRings']

    ringWidth = (maxZen-minZen) / nRings
    halfWidth = ringWidth/2.0
    ringCentres = np.arange(minZen+halfWidth, maxZen, ringWidth)
    ringCentresDeg = ringCentres / np.pi * 180
    nShots = np.zeros(nRings)

    for i in range(nRings):
        ringMin = ringCentres[i]-halfWidth
        ringMax = ringCentres[i]+halfWidth
        mask = ((df['zenithRad'] > ringMin) & (df['zenithRad'] < ringMax))
        nShots[i] = np.sum(mask)

    shotCount = {'ringCentresDeg':ringCentresDeg, 
                'ringCentres':ringCentres,
                'nShots':nShots}

    return shotCount


def getPgap(df, InstParams, profileParams):

    #returns a Pgap profile by zenith ring, ie 2d array

    minZen = profileParams['minZenithDeg']  * np.pi / 180
    maxZen = profileParams['maxZenithDeg'] * np.pi / 180
    nRings = profileParams['nRings']

    heightMax = df['z1'].quantile(0.999)           # 99.9%
    dZ = profileParams['heightStep']
    heights = np.round(np.arange(dZ, heightMax+dZ, dZ),2)
    nHeights = heights.size

    rangeMin = InstParams['rangeMin']
    rangeMax = InstParams['rangeMax']
    # ranges = np.round(np.arange(dR, rangeMax+dR, dR),2)
    # nRanges =ranges.size

    ringWidth = (maxZen-minZen) / nRings
    halfWidth = ringWidth/2.0
    ringCentres = np.arange(minZen+halfWidth, maxZen, ringWidth)
    ringCentresDeg = np.round(ringCentres / np.pi * 180)

    PgapDF = pd.DataFrame(index=heights, columns=ringCentresDeg)

    for ringNum in range(0,nRings):
        ringMin = ringCentres[ringNum]-halfWidth
        ringMax = ringCentres[ringNum]+halfWidth
        #shots within the ring
        mask = ((df['zenithRad'] > ringMin) & (df['zenithRad'] < ringMax))        
        #number of shots within the zenith ring
        nRingShots = np.sum(mask)
        
        if (nRingShots > 0):
            dfRing = df[mask]
            for zNum in range(0,nHeights):
                z = heights[zNum]
                zLow = z - dZ
                zHigh = z
                #zenith ring shots returned below z layer
                mask = ((dfRing['range1'] > rangeMin) & (dfRing['range1'] < rangeMax) & (dfRing['z1'] < zHigh))
                nHits = np.sum(mask)

                # test if beam exits top of height layer
                if (rangeMax*np.cos(ringCentres[ringNum]) > zHigh):
                    PgapDF.iloc[zNum, ringNum] = 1.0 - nHits / nRingShots

    return PgapDF


def hemiProfile(PgapDF, profileParams):
    #return the vertial L and FAVD profile
    size = PgapDF.size
    shape = PgapDF.shape
    heights = PgapDF.index.to_numpy(dtype=float)
    zeniths = PgapDF.columns.to_numpy(dtype=float)

    #flatten the Pgap array
    Fz = np.array(shape[0])
    for z in range(0,1):#range(0,shape[0]):
        Y = PgapDF.iloc[z,:].to_numpy(dtype=float)

        X = np.ones((shape[1], 2))
        X[:,1] = 2.0 / np.pi * np.tan(zeniths*np.pi/180)

        mask = np.isfinite(Y)
        Y = Y[mask]
        X = X[mask,:]
        print('Shape : ', Y.shape, X.shape)
        mod = np.linalg.lstsq(X, Y, rcond=None)[0]
        print('Mod: ', mod)

    # print(X.shape, Y.shape)
    # mod = np.linalg.lstsq(X, Y, rcond=None)
    # print(mod)

    return 0
