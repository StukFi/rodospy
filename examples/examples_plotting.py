from example import *

import matplotlib.pyplot as plt
from matplotlib import dates
import numpy as np

# search for max value of gamma dose rate
gamma_max = gamma_dose_rate.max()
lon = gamma_max[1][0]
lat = gamma_max[1][1]
time_max = gamma_max[2]

# Plot map
shapefile_path = gamma_dose_rate.save_as_shapefile( 
    "/tmp","out",time_max)

print ( "joo" )
from mpl_toolkits.basemap import Basemap

map = Basemap(llcrnrlon=20,llcrnrlat=60,urcrnrlon=22,urcrnrlat=62.,
             resolution='i', projection='tmerc', lat_0 = 61, lon_0 = 21)

map.drawmapboundary(fill_color='aqua')
map.fillcontinents(color='#ddaa66',lake_color='aqua')
map.drawcoastlines()

s = shapefile_path.split(".")
print ( ".".join(s[:-1] ))

map.readshapefile(".".join(s[:-1]), 
                  os.path.basename(shapefile_path).split(".")[0] )

plt.show()


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


