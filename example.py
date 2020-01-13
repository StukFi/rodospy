settings = {
    "wps": {
        # URL for Geoserver WPS service
        # it's enough to change host and port
        "url": "http://localhost:8080/geoserver/wps",
        # Local storage of GML files, must be writeable
        "file_storage": "/tmp/jrodoswps"
    },
    "rest": {
        # TOMCAT rest service URL
        "url": "http://localhost:8080/jrodos-rest-1.2-SNAPSHOT/jrodos"
    }
}

from rodospy import *
# set debug level logging
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.ERROR)

# create connection
rodos = RodosConnection( settings )
# list projects available
# filters can be used but they are not required
#projects = rodos.projects_old( )
projects = rodos.projects

print ( "Projects available:" )
for p in projects:
    print ( "* {}".format(p.name) )

# Choose the latest project
project = projects[-1]
print ("Got project " + project.name)
# load project metadata
project.load()
# get tasks
tasks = project.tasks
# Emergency project has only 1 task
task = tasks[0]

# iterate over timestamps
gamma_dose_rate  = task.total_gamma_dose_rate
time_values = gamma_dose_rate.times()

for timestamp in time_values:
    m = gamma_dose_rate.max(timestamp)
    if m[2]==None:
        continue
    max_value = m[0]
    max_location = m[1]
    print ( "Max gamma dose rate on {} is {} mSv/h at point {}.".format(
        timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
        max_value,
        str(max_location))
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
    print ( "Max deposition of {} is {} Bq/m2 at point {} and time {}".format(
        nuclide,
        max_value,
        str(max_location),
        max_tstamp)
    )

## print area where 0.001 mSv/h is exceeded
#for i in items:
#    a = i.areaExceeding( 0.001 ) 
#    print ( "Area at time index %i where 0.001 mSv/h is exceeded  is %f m2." % (i.t_index, a ) )
#
## see more methods from rodospy.py 
#"""
