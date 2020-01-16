from example import *
import csv
import pprint
pp = pprint.PrettyPrinter (indent=4)

# find olkiluoto coordinates
for npp in rodos.get_npps():
    if npp["block"]=="OLKILUOTO-1":
        print ( "Olkiluoto information available:" )
        pp.pprint ( npp )
        lon = npp["longitude"]
        lat = npp["latitude"]
        break

# extract all the max doses in the distances of 5, 10, ... , 100 km 
# and write them to csv file for further analysis

rows = [
    ["distance","dose_type","nuclide_or_type","value_mSv"]
]
for distance in (0.5,1,1.5,2,3,4,5,10,15,20,30,40,50):
    for key in task.cloud_dose.keys():
        rows.append([
            distance,
            "cloud",
            key,
            task.cloud_dose[key].maxAtDistance(lon,lat,distance),
        ])
    for key in task.ground_dose.keys():
        rows.append([
            distance,
            "ground",
            key,
            task.ground_dose[key].maxAtDistance(lon,lat,distance),
        ])
    for key in task.total_dose.keys():
        rows.append([
            distance,
            "total_effective",
            key,
            task.total_dose[key].maxAtDistance(lon,lat,distance),
        ])
    for key in task.inhalation_dose.keys():
        rows.append([
            distance,
            "inhalation",
            key,
            task.inhalation_dose[key].maxAtDistance(lon,lat,distance),
        ])
    for key in task.skin_dose.keys():
        rows.append([
            distance,
            "skin",
            key,
            task.skin_dose[key].maxAtDistance(lon,lat,distance),
        ])
    
with open('doses.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(rows)
