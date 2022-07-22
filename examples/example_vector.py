settings = {
    "wps": {
        # URL for Geoserver WPS service
        # it's enough to change host and port
        "url": "http://localhost:8080/geoserver/wps",
        # Local storage of GeoPackage files, must be writeable
        # The directory will be created if it does not exist.
        "file_storage": "/tmp/jrodoswps"
    },
    "rest": {
        # TOMCAT rest service URL
        "url": "http://localhost:8080/jrodos-rest-1.2-SNAPSHOT/jrodos"
    }
}

try:
    from rodospy import *
except ImportError: 
    import sys, os.path
    sys.path.append(os.path.abspath('../'))
    sys.path.append(os.path.abspath('.'))
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


# Choose the latest project where model chain is "LSMC+EMERSIM+DEPOM+FDMT"
project = rodos.get_projects(filters={"modelchainname":
                                      "Emergency"})[-1]

# Get the only task and also for wind series 24 first timestemps and 10 vertical levels
task = project.get_tasks({},24,10)[0]

# Print following wind field series is available
for wind_field in task.wind_field.keys():
    print ( wind_field )

if __name__=="__main__":
    print ( "Sample data loaded.")
