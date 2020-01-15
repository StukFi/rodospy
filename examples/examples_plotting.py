from example import *

import matplotlib.pyplot as plt
from matplotlib import dates
import numpy as np

hfmt = dates.DateFormatter("%m/%d %H:%M")

# plot single dataset timestep
# search for max value of gamma dose rate
gamma_max_location = gamma_dose_rate.max()[1]
lon = gamma_max_location[0]
lat = gamma_max_location[1]
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


