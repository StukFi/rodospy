from example import *

import matplotlib.pyplot as plt
from matplotlib import dates
from matplotlib.colors import LogNorm
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import numpy as np

# search for max value of gamma dose rate
gamma_max = gamma_dose_rate.max()
gamma_max_value = gamma_max[0]
lon = gamma_max[1][0]
lat = gamma_max[1][1]
time_value = gamma_dose_rate.times()[-1]
bbox = gamma_dose_rate.getLonLatBoundaries()

# Plot map
shapefile_path = gamma_dose_rate.save_as_shapefile( 
    "/tmp","out",time_value)

from mpl_toolkits.basemap import Basemap

fig = plt.figure()
ax = fig.add_subplot(111)

Map = Basemap(llcrnrlon=bbox[0]-0.5,
              llcrnrlat=bbox[1]-0.5,
              urcrnrlon=bbox[2]+0.5,
              urcrnrlat=bbox[3]+0.5,
              resolution='h', 
              projection='stere', 
              lat_0 = (bbox[3]-bbox[1]), 
              lon_0 = (bbox[2]-bbox[0]),
              )
Map.drawmapboundary(fill_color='aqua')
Map.fillcontinents(color='#ddaa66',lake_color='aqua')
Map.drawcoastlines()

s = shapefile_path.split(".")

Map.readshapefile(".".join(s[:-1]), 
                  os.path.basename(shapefile_path).split(".")[0],
                  linewidth=0.01
                    )
cmap = plt.cm.BuPu
#norm = plt.Normalize( 0, gamma_max_value)
norm = LogNorm( gamma_max_value/1e9, gamma_max_value)

patches = []
values = []

for info, shape in zip(Map.out_info, Map.out):
    value = info["Value"]
    values.append( value)
    color = cmap(norm(value))
    patches.append ( Polygon ( np.array(shape), True, color=color))

pc = PatchCollection(patches, 
                     match_original=True,
                     edgecolor="k",
                     linewidth=0,
                     zorder=2)
ax.add_collection(pc)
sm = plt.cm.ScalarMappable ( cmap=cmap, norm=norm)
sm.set_array( [0,gamma_max] )
fig.colorbar(sm,ax=ax)
plt.title(gamma_dose_rate.name + " (" +
          gamma_dose_rate.unit + ")")
plt.show()

# and more simple examples...

hfmt = dates.DateFormatter("%m/%d %H:%M")

# plot single dataset timestep
data = gamma_dose_rate.timeSeries(lon,lat)
fig = plt.figure()
ax =  fig.add_subplot (111)
plt.plot( data["times"], data["values"] )
plt.title ( data["title"] )
plt.ylabel ( data["unit"] )
#plt.gcf().autofmt_xdate()
ax.xaxis.set_major_formatter( hfmt )
plt.xticks( rotation="vertical")
unit = data["unit"]
fig.tight_layout()

# plot multiple datasets
# take one as an example
fig, ax = plt.subplots()
for nuclide in ("Cs-137", "I-131", "Xe-133"):
    grid = task.air_concentration[nuclide]
    data = grid.timeSeries( lon,lat )
    ax.plot( data["times"], data["values"], label=nuclide )
plt.title ( "Air concentrations" )
plt.ylabel ( data["unit"] )
plt.yscale ( "log" )
plt.ylabel ( data["unit"] )
ax.xaxis.set_major_formatter( hfmt )
plt.xticks( rotation="vertical")
fig.tight_layout()
leg = ax.legend()
fig.tight_layout()
plt.show()


