settings = {
    "postgres": {
        "host": "navetta.stuk.fi",
        "port": 5433,
        "user": "jrodos",
        "password": "jrodos"
    },
    "wps": {
        "url": "http://vmkevubu2.stuk.fi:8080/geoserver/ows",
        "file_storage": "/tmp"
    }
}

from rodospy import *
logger.setLevel(logging.DEBUG)
import random

# create connection
rodos = RodosConnection( settings )
# list projects available
#projects = rodos.projects({"modelchainname": "LSMC"})
projects = rodos.projects({"name": "geoserver"})

print projects

# Choose random project
project = projects[random.randint( 0, len(projects)-1 )]
# print name
print ("Got project " + project.name)
# get project tasks
tasks = project.tasks()
print ("Project '%s' has tasks %s" % (project.name,tasks))
# connection settings inherited
# get task
task = tasks[random.randint( 0, len(tasks)-1 )]
# get products (filter to LSMC
products = task.datasets()
print ("Task '%s' has following products:" % task.task_uid)
for p in products:
    print (p)
#product = Product(task,"gamma_dose_rate")

# TODO. read from products...
path = "'Model data=;=Output=;=Prognostic Results=;=Dose rates=;=Total gamma dose rate'"
dataset = Dataset(rodos,task,path)

items = []
for i in range(24):
    items.append(DataItem(dataset,i,0))

# iterate over items
for i in items:
    m = i.max()
    print ( "Max value at time index %i is %f at point %s" % (i.t_index, m[0], m[1] ) )

