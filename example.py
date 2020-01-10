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
import random

# create connection
rodos = RodosConnection( settings )
# list projects available
# filters can be used but they are not required
#projects = rodos.projects_old( )
projects = rodos.projects

print ( projects )

# Choose random project
project = projects[random.randint( 0, len(projects)-1 )]
# Choose the latest project
project = projects[2]
# print name
print ("Got project " + project.name)
project.load()
tasks = project.tasks
#print ("Project '%s' has tasks %s" % (project.name,tasks))
task = tasks[0]
# save gamma dose rates at timestep 2
gpkg_path = task.total_gamma_dose_rate.gpkg_file()

# iterate over depositions
for nuclide in task.deposition.keys():
    grid = task.deposition[nuclide]
    max_value = grid.max()
    print (nuclide)
    print (max_value)
    
## TODO: Products is not implemented yet
#datasets = task.datasets()
#print ("Task '%s' has following products:" % task.path)
#for d in datasets:
#    print (d)
##choose random dataset
#dataset = datasets[random.randint( 0, len(datasets)-1 )]
#
## iterate over timestep indices, from 0 to 23
## first iteration is slow because results are not cached
#items = []
#if dataset.times:
#    for i in range(len(dataset.times)):
#        items.append(DataItem(dataset,i,0))
#else:
#    items.append( DataItem(dataset,0,0) )
#"""
## iterate over items and read max values
## this is fast because results already exist on disk
#for i in items:
#    m = i.max()
#    print ( "Max value at time index %i is %f at point %s" % (i.t_index, m[0], m[1] ) )
#
## print area where 0.001 mSv/h is exceeded
#for i in items:
#    a = i.areaExceeding( 0.001 ) 
#    print ( "Area at time index %i where 0.001 mSv/h is exceeded  is %f m2." % (i.t_index, a ) )
#
## see more methods from rodospy.py 
#"""
