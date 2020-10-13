# -*- coding: utf-8 -*-
"""
Created on Sat Aug 22 14:04:01 2020

@author: new298
"""



def FilterPoints(df):
    
    import numpy as np

    df['delta'] = np.sqrt(np.square(df['range1']-df['range2']))    # unsigned difference between first and second range measurements for each pointing direction

    # ----------- apply filtering to remove spurious/unreliable points ---------------
    # filtering is based mostly on an anlysis of the two range measurements that are
    # acquired in each pointing direction. The successive range measurements should be
    # very close. Filtering is an important process and some further investigation and 
    # --- optimisation may be worthwhile, including better use of intensity values ---
    
    #Glenn: is there a difference between a gap and an error? If so we shoudl remove error rows as well as set gap to zero
    
    mask = df['range1'] < 0                                # replace any range 1 negative values (normally -1.00) with zero. These are non-hits (gaps).
    df.loc[mask, 'range1'] = 0    
    df.loc[mask, 'range2'] = 0    
    
    #mask = df['range2'] < 0                                # replace any range 2 negative values (normally -1.00) with zero. These are non-hits (gaps).
    #df.loc[mask, 'range1'] = 0    
    #df.loc[mask, 'range2'] = 0
    
    mask = df['intensity'] == 0                            # nullify all ranges with raw intensity zero (there have been no 1/r2 corrections to intensity at this point, but there should be if an intensity threshold > 0 is applied)
    df.loc[mask, 'range1'] = 0    
    df.loc[mask, 'range2'] = 0    
    
    #mask = df['delta'] > 0.3                            # if distance between range 1 & 2 is > 0.3m then nullify the point
    #df.loc[mask, 'range1'] = 0    
    #df.loc[mask, 'range2'] = 0
    
    return


def ConvertToXYZ(df, InstParams):
    
    import numpy as np
    
     # ----- calculate xyz coords from range, azimuth and zenith -----
    df['zenithRad'] = ((df['scanEnc']/InstParams['incrScanEncoder'])*np.pi*2)    # zenith angle in radians
    df['azimuthRad'] = ((df['rotEnc']/InstParams['incrRotEncoder'])*np.pi*2)    # azimuth angle in radians
    
    #transform all zenith angles into 1-180 degree range
    mask = df['zenithRad'] > np.pi
    df.loc[mask, 'zenithRad'] = (2*np.pi - df.loc[mask, 'zenithRad'])
    
    df['x1'] = (np.sin(df['zenithRad']) * df['range1']) * np.sin(df['azimuthRad'])
    df['y1'] = (np.sin(df['zenithRad']) * df['range1']) * np.cos(df['azimuthRad'])
    df['z1'] = (-(np.cos(df['zenithRad']) * df['range1']) + InstParams['tripodHeight'] + InstParams['instrumentHeight'])
    
    df['x2'] = (np.sin(df['zenithRad']) * df['range2']) * np.sin(df['azimuthRad'])
    df['y2'] = (np.sin(df['zenithRad']) * df['range2']) * np.cos(df['azimuthRad'])
    df['z2'] = (-(np.cos(df['zenithRad']) * df['range2']) + InstParams['tripodHeight'] + InstParams['instrumentHeight'])
    
    return


def CalcHingeProfile(df, InstParams, hingeWidthDeg, minRange):
    
    import numpy as np
    import pandas as pd
#    hingeWidthDeg=1
#    minRange=0.3
    
        # -------------- calculate LAI profiles ---------------------
    
    dfZ = df[['x1','y1','z1','zenithRad','range1']].copy()
    dfZ.columns = ['x','y','z','zenithRad','Range']
    
    print('Total shots in file (before filtering):', np.size(dfZ, axis=0))
    
    hingeAngleRadians = np.arctan(np.pi/2)
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
    
    #check to make sure that height bin is the correct size, Daris removed one height in his code in the plot
    pf = {'Height':heightBin, 'Pgapz':heightBin*0.0, 'LAIz':heightBin*0.0, 'FAVD':heightBin*0.0, 'sumZStep':heightBin*0.0}
    Profile = pd.DataFrame(pf)

    sumZStep = 0
    for i in range(binCount):
        
        sumZStep += shotCountZ[i]                        # count the cumulative number of hits from the instrument height upwards...
        Pgapz = (1.0 - float(float(sumZStep)/float(totalShots)))
        LAIz = (-1.1 * np.log(Pgapz[i]))
        if(i > 0): 
            FAVD = ((LAIz[i]-LAIz[i-1])/InstParams['zIncr']) 
        else: 
            FAVD = 0.0
        Profile.loc[i] = [heightBin[i], Pgapz, LAIz, FAVD, sumZStep]
        
    heightBin += (InstParams['tripodHeight'] + InstParams['instrumentHeight'])        # add tripod and instrument height
    print(heightBin[binCount-1], shotCountZ[binCount-1], sumZStep, 'Top of Canopy PGap {:0.3f} and LAI {:0.3f}'.format(Pgapz[binCount-1],LAIz[binCount-1]))
  
    return(Profile)

