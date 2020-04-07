from example import *

print ( "Projects available:" )
for p in projects:
    print ( "* {}".format(p.name) )
print ("Got project " + project.name)
time_values = gamma_dose_rate.times()
for timestamp in time_values:
    m = gamma_dose_rate.max(timestamp)
    if m[2]==None:
        continue
    max_value = m[0]
    gamma_max_location = m[1]
    print ( "Max gamma dose rate on {} is {} {} at point {}.".format(
        timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
        max_value,
        gamma_dose_rate.unit,
        str(gamma_max_location))
    )
# iterate over depositions
for nuclide in task.deposition.keys():
    grid = task.deposition[nuclide]
    m = grid.max()
    if m[2]==None:
        continue
    max_value = m[0]
    max_location = m[1]
    max_tstamp = m[2].strftime('%Y-%m-%dT%H:%M:%SZ')
    print ( "Max deposition of {} is {} {} at point {} and time {}".format(
        nuclide,
        max_value,
        grid.unit,
        str(max_location),
        max_tstamp)
    )


