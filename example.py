settings = {
    "postgres": {
        # Postgres host
        "host": "navetta.stuk.fi",
        # Postgres port, probably 5432 
        "port": 5433,
        # Postgres username
        "user": "jrodos",
        # Postgres password
        "password": "jrodos"
    },
    "wps": {
        # URL for Geoserver WPS service
        # it's enough to change host and port
        "url": "http://vmkevubu2.stuk.fi:8080/geoserver/ows",
        # Local storage of GML files, must be writeable
        "file_storage": "/tmp"
    }
}

from rodospy import *
# set debug level logging
logger.setLevel(logging.DEBUG)
import random

# create connection
rodos = RodosConnection( settings )
# list projects available
# filters can be used but they are not required
projects = rodos.projects({"modelchainname": "Emergency"})
#projects = rodos.projects({"name": "geoserver"})

print projects

# Choose random project
#project = projects[random.randint( 0, len(projects)-1 )]
# Choose the latest project
project = projects[-1]
# print name
print ("Got project " + project.name)
# get project tasks
tasks = project.tasks()
print ("Project '%s' has tasks %s" % (project.name,tasks))
# get random task
task = tasks[random.randint( 0, len(tasks)-1 )]
# TODO: Products is not implemented yet
#products = task.datasets()
#print ("Task '%s' has following products:" % task.task_uid)
#for p in products:
#    print (p)
#product = Product(task,"gamma_dose_rate")

# choose the product by name
path = "'Model data=;=Output=;=Prognostic Results=;=Dose rates=;=Total gamma dose rate'"
dataset = Dataset(rodos,task,path)

# iterate over timestep indices, from 0 to 23
# TODO: times should be read from WPS or DB
# first iteration is slow because results are not cached
items = []
for i in range(24):
    items.append(DataItem(dataset,i,0))

# iterate over items and read max values
# this is fast because results already exist on disk
for i in items:
    m = i.max()
    print ( "Max value at time index %i is %f at point %s" % (i.t_index, m[0], m[1] ) )

# print area where 0.001 mSv/h is exceeded
for i in items:
    a = i.areaExceeding( 0.001 ) 
    print ( "Area at time index %i where 0.001 mSv/h is exceeded  is %f m2." % (i.t_index, a ) )

# see more methods from rodospy.py 
