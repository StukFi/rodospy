settings = {
    "wps": {
        "url": "http://vmkevubu2.stuk.fi:8080/geoserver/wps",
        "file_storage": "/tmp"
    }
}
casenames = ("AutorunLOVIISA-1","AutorunOLKILUOTO-1")
time_indices = [2,5,8,11] # 3,6,9,12 hours after start of release
dataset_name = "Total gamma dose rate"

cases = {}
for casename in casenames:
    cases[casename] = {}

from rodospy import *
logger.setLevel(logging.INFO)

# create connection
rodos = RodosConnection( settings )

# list projects available
projects = rodos.projects

# find datasets
found = 0
for p in projects:
    for c in cases.keys():
        if p.name.startswith ( c ):
            found +=1
            cases[c]["project"] = p
            # Emergency model chain has only one task
            cases[c]["task"] = p.tasks()[0]
            for dataset in cases[c]["task"].datasets():
                if dataset.name==dataset_name:
                    cases[c]["dataset"] = dataset
                    break
            # save gml files
            cases[c]["files"] = []
            cases[c]["times"] = []
            for ti in time_indices:
                dataitem = DataItem(dataset,ti)
                cases[c]["files"].append ( dataitem.gml )
                cases[c]["projection"] = dataitem.projection
                cases[c]["times"].append ( dataitem.timestamp )
    if found>=len(cases):
        break
    else:
        continue
print ( cases )

# Jatko:
# 1. Tee mapnik-pohjalle kartat 2x2 jossa molemmat tapaukset
# 2. Käytä siinä pohjakarttaa jossa projektion on cases[".."]["projection"] ja rajat GML-tiedoston cases[".."]["files"][N] BBOX
# 3. Kirjoita lisäksi johonkin alkuaika ja kuvien alle tarkasteluajat cases["..."][times][N]
