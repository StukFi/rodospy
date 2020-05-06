settings = {
    "wps": {
        # URL for Geoserver WPS service
        # it's enough to change host and port
        "url": "http://jrodos.dev.cal-net.nl/geoserver/wps",
        # Local storage of GeoPackage files, must be writeable
        # The directory will be created if it does not exist.
        "file_storage": "/tmp/jrodoswps"
    },
    "rest": {
        # TOMCAT rest service URL
        "url": "http://jrodos.dev.cal-net.nl/rest-2.0/jrodos"
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
#logger.setLevel(logging.ERROR)

# create connection
rodos = RodosConnection( settings )
# list projects available
# filters can be used but they are not required
#projects = rodos.projects_old( )
#projects = rodos.projects


# Choose the latest project where model chain is "LSMC+EMERSIM+DEPOM+FDMT"
#project = rodos.get_projects(filters={"modelchainname":
#                                      "LSMC+EMERSIM+DEPOM+FDMT"})[-1]

projects = rodos.get_projects(filters={"projectId": 3149})

if len(projects) > 0:
    project = projects[-1]

    # Get LSMC task
    #tasks = project.get_tasks({"modelwrappername": "LSMC"})

    # Get tasks with selected gridseries?
    # get total gamma dose rate
    #tasks = project.get_tasks({'groupname': 'EffectedDoseRate_AllRelevant'})

    tasks = []
    # tasks = project.get_tasks({'datapath': 'Model data=;=Output=;=Prognostic Results=;=Dose rates=;=Total gamma dose rate'})
    # if len(tasks) > 0:
    #     print(tasks[0].total_gamma_dose_rate)
    #     gamma_dose_rate = tasks[0].total_gamma_dose_rate
    #     #print(gamma_dose_rate.max())
    #     print(gamma_dose_rate.data_extent())
    #
    # # try Potential doses Cloud gamma dose lung
    # tasks = project.get_tasks({'datapath': 'Model data=;=Output=;=Prognostic Results=;=Activity concentrations=;=Ground deposition wet+dry=;=Ba-140'})
    # if len(tasks) > 0:
    #     print(tasks[0].dep)
    #     ground_dep_ba140 = tasks[0].dep['Ba-140']
    #     print(ground_dep_ba140.data_extent())
    #
    # # Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=lung
    # tasks = project.get_tasks({'datapath': 'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=lung'})
    # if len(tasks) > 0:
    #     print(tasks[0].potential_dose)
    #     potential_dose_lung = tasks[0].potential_dose['lung']
    #     print(potential_dose_lung.data_extent())
    #
    # #  Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Ingestion dose=;=lung
    # tasks = project.get_tasks({'datapath': 'Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Ingestion dose=;=lung'})
    # if len(tasks) > 0:
    #     print(tasks[0].potential_dose_ingestion)
    #     potential_dose_ingestion_lung = tasks[0].potential_dose_ingestion['lung']
    #     print(potential_dose_ingestion_lung.data_extent())

    tasks = project.get_tasks({'datapath': 'Model data=;=Output=;=Prognostic Results=;=Cloud arrival time=;=Cloud arrival time'})
    if len(tasks) > 0:
        print(tasks[0].eta)
        eta_cloud_arrival_time = tasks[0].eta['Cloud arrival time']
        print(eta_cloud_arrival_time.data_extent())

    print('done')


if __name__=="__main__":
    print ( "Sample data loaded.")
