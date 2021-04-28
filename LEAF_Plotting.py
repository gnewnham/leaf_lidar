

import plotly.express as px
import plotly.graph_objects as go
from glob import glob
import pandas as pd

BASEPATH = 'C:/Users/new298/OneDrive - CSIRO/Projects/LEAF Laser Scanner/Tumbarumba 2019 LEAF scans/'
OUTPUTFOLDER = BASEPATH + 'output/'

# flist = glob(OUTPUTFOLDER+'*xyz.csv')
flist = glob(OUTPUTFOLDER+'*.xyz')
infile = flist[1]
subsample = 2

df = pd.read_csv(infile)
print(df.columns)

dfSmall = df.iloc[::subsample, :]

# fig = px.scatter_3d(dfSmall, x='x1', y='y1', z='z1', color='intensity', size_max=0.5)
# fig.show()

fig = go.Figure(data=[go.Scatter3d(x=dfSmall['x1'], y=dfSmall['y1'], z=dfSmall['z1'], mode='markers', 
    marker=dict(size=1, color=dfSmall['intensity'], colorscale='Viridis', opacity=0.8))])
fig.show()