# -*- coding: utf-8 -*-
from owslib.wps import WebProcessingService
import osr
import ogr
import os
from datetime import datetime, timedelta
from copy import copy
try: # python3
    from urllib.request import Request
    from urllib.request import urlopen
except ImportError: # python2
    from urllib2 import Request
    from urllib2 import urlopen
import json
import codecs
from xml.etree.ElementTree import XML, fromstring, tostring
# standard logging
import logging
logger = logging.getLogger('rodospy')
# set to INFO or WARNING in production environment
# set logging format
FORMAT = '%(asctime)-15s %(levelname)-6s %(message)s'
formatter = logging.Formatter(fmt=FORMAT)
# output to console
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

# URL fetching parameters
reader = codecs.getreader("utf-8")
xml_headers = { 'Content-Type': 'application/xml' }

owslib_log = logging.getLogger('owslib')
# Add formatting and handlers as needed
owslib_log.setLevel(logging.DEBUG)

# GDAL contants
wgs84_cs = osr.SpatialReference()
wgs84_cs.ImportFromEPSG(4326)
gml_driver = ogr.GetDriverByName('GML')

# META request XML content
meta_xml = """
<?xml version="1.0" encoding="UTF-8"?><wps:Execute version="1.0.0" service="WPS" 
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
xmlns="http://www.opengis.net/wps/1.0.0" xmlns:wfs="http://www.opengis.net/wfs" 
xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1" 
xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" 
xmlns:wcs="http://www.opengis.net/wcs/1.1.1" xmlns:xlink="http://www.w3.org/1999/xlink" 
xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
  <ows:Identifier>gs:JRodosMetadataWPS</ows:Identifier>
  <wps:DataInputs>
    <wps:Input>
      <ows:Identifier>projectArg</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>all</wps:LiteralData>
      </wps:Data>
    </wps:Input>
  </wps:DataInputs>
  <wps:ResponseForm>
    <wps:RawDataOutput mimeType="application/octet-stream">
      <ows:Identifier>result</ows:Identifier>
    </wps:RawDataOutput>
  </wps:ResponseForm>
</wps:Execute>
"""

def time_formatter(time_string):
    "format rodos strings to python datetime objects"
    # two possible time formats
    try:
        time_value = datetime.strptime( time_string.split(".")[0], \
            '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        time_value = datetime.strptime( time_string.split(".")[0], \
            '%Y-%m-%dT%H:%M:%SZ')
    return time_value

def to_rodos_nuclide(nuclide):
    "Convert nuclide string to Rodos format inherited from 80s"
    n = nuclide.split("-")
    element = n[0]
    mass = n[1]
    nuc_string = element
    if len(element)==1:
        nuc_string += " "
    nuc_string += "-"
    if len(mass)==2:
        nuc_string += " "
    elif len(mass)==1:
        nuc_string += "  "
    nuc_string += mass
    return nuc_string

def from_rodos_nuclide(nuclide):
    n = nuclide.split("-")
    n[0] = n[0].strip()
    n[1] = n[1].strip()
    return n[0] + "-" + n[1]

class RodosPyException(Exception):
    "Module specific exception"
    pass

class RodosConnection(object):
    """
    Setup JRodos database and Geoserver connection
    When initialized, connections are checked.
    The connection settings will be passed to other classes.
    """
    def __repr__(self):
        return ("<RodosConnection %s | %s>" % (self.wps))

    def __init__(self,settings=None):
        "Initialize RODOS DB and WPS connection"
        logger.debug("Read settings from file")
        if settings==None:
            # try to read from config file
            raise RodosPyException( "No settings defined" )
        self.w = settings["wps"]
        self.wps = WebProcessingService(self.w["url"], 
                                        verbose=False, # set this True when debugging
                                        skip_caps=True)
        self.storage = self.w["file_storage"]
        # check that connections are OK
        self.check_connections()
        self.projects = self.get_projects()

    def check_connections(self):
        "Check connections"
        logger.debug("Check DB and WPS connections")
        # listing of projects?
        self.db_alive = False
        # GetCapabilities
        try:
            capabilities = self.wps.getcapabilities()
            self.wps_alive = True
        except RodosPyException:
            raise RodosPyException( "WPS Service not available" )

    def refresh_projects():
        "get refreshed list of projects"
        self.projects = self.get_projects()

    def get_projects(self): # fetch the project list
        """
        Get listing of projects. 
        project_uid as parameter if only one project information wanted."
        """
        data_val = meta_xml.replace("\n","").encode("utf-8")
        req = Request ( self.w["url"],
                        data = data_val, 
                        headers = xml_headers)
        response = urlopen( req )
        proj_dict = json.load(reader(response))["rodos_projects"]
        projects = []
        for p in proj_dict:
            values = {
                "uid": p["project_uid"],
                "name": p["name"],
                "comment": p["comment"],
                "user": p["user"],
                "modelchainname": p["modelchainname"],
                "calculationDate": time_formatter(p["calculationDate"])
            }
            projects.append(Project(self,None,values))
        return projects

class Project(object):
    """
    Create Project instance.
    project must be tuple generated by RodosConnection 
    or project uid
    """
    def __repr__(self):
        return ("<Project %s | %s>" % (self.name, self.modelchainname))

    def __init__(self,rodos,project_uid=None,values=None):
        "Project must be initialized with RODOS db connection"
        if (project_uid==None and values==None):
            raise RodosPyException( 
                "Either project uid or velues dict must be defined" 
            )
        self.rodos = rodos
        if project_uid:
            for p in rodos.projects:
                if p.uid==project_uid:
                    self.uid = p.uid
                    self.name = p.name
                    self.comment = p.comment
                    self.user = p.user
                    self.modelchainname = p.modelchainname
                    self.calculationdate = p.calculationdate
        else:
            self.uid = values["uid"]
            self.name = values["name"]
            self.comment = values["comment"]
            self.user = values["user"]
            self.modelchainname = values["modelchainname"]
            self.calculationdate = values["calculationDate"]
        self.details = None

    def get_project_details(self):
        "get details of the project. fetch only when necessary"
        data_val = meta_xml.replace("\n","").replace\
                ("all","projectuid=" + self.uid).encode("utf-8")
        req = Request ( self.rodos.w["url"],
                        data = data_val, 
                        headers = xml_headers)
        response = urlopen( req )
        self.details = json.load( reader(response) )["rodos_results"]

    def tasks(self):
        "Get tasks in the project"
        if self.details==None:
            self.get_project_details()
        # read task id:s / names from db
        logger.debug( "Query project task list" )
        tasks = []
        for p in self.details["task"]:
            values = {
                "path": p["path"],
                "modelwrapper": p["modelwrapper"],
                "project_uid": self.uid,
                "name": p["name"]
            }
            tasks.append( Task( self,None, values ) )
        return tasks
 
class Task(object):
    """
    JRodos Task instance. Contains single model run.
    """
    def __repr__(self):
        return ("<Task %s | %s>" % (self.modelwrapper, self.name))

    def __init__(self,project,task_path=None,values=None):
        self.rodos = project.rodos
        self.project = project
        if self.project.details==None:
            self.project.get_project_details()
        if (task_path==None and values==None):
            raise RodosPyException( 
                "Either task uid or velues dict must be defined" 
            )
        if task_path:
            for t in project.tasks():
                if t.path==task_path:
                    self.path = t.path
                    self.modelwrapper = t.modelwrapper
                    self.project_uid = t.project_uid
                    self.name = t.name
        self.path = values["path"]
        self.modelwrapper = values["modelwrapper"]
        self.project_uid = values["project_uid"]
        self.name = values["name"]

    def datasets(self,filter_string=None):
        "list datasets available"
        logger.debug( "Get listing of Task datasets" )
        datasets = []
        for p in self.project.details["task"]:
            if p["path"]==self.path:
                for layer in p["layers"]:
                    params = []
                    try:
                        for f in layer["filters"]:
                            param = f["param"]
                            if not param in params:
                                params.append(param)
                    except KeyError:
                        pass
                    values = {
                        "path": layer["path"],
                        "unit": layer["unit"],
                        "name": layer["name"],
                        "params": params
                    }
                    datasets.append( Dataset( self,values ) )
        return datasets
        
class Dataset(object):
    """
    JRodos dataset instance.
    May contain several times and levels
    """
    def __repr__(self):
        return ("<Task %s | %s>" % (self.task.name, self.path))

    def __init__(self,task,values):
        self.rodos = task.rodos
        self.project = task.project
        self.task = task
        self.path = values["path"]
        self.unit = values["unit"]
        self.name = values["name"]
        self.params = values["params"]
        self.times = None
        self.nuclides = None
        self.levels = None
        self.default_time = None
        self.default_nuclide = None
        if "date" in self.params:
            self.get_times()
        if "nuclide" in self.params:
            self.get_nuclides()
        if "level" in self.params:
            self.get_levels()

    def get_times(self):
        "read timestamps as Python objects" 
        for p in self.project.details["task"]:
            if p["path"]==self.task.path:
                for layer in p["layers"]:
                    if layer["path"]==self.path:
                        for f in layer["filters"]:
                            if f["param"]=="date":
                                times = f["allowedValues"]
                            self.times = times
                            self.default_time = f["defaultValue"]
                            break
        self.default_time = time_formatter(self.default_time)
        self.times = list(map(time_formatter,self.times))

    def get_nuclides(self):
        "read nuclides"
        for p in self.project.details["task"]:
            if p["path"]==self.task.path:
                for layer in p["layers"]:
                    if layer["path"]==self.path:
                        for f in layer["filters"]:
                            if f["param"]=="nuclide":
                                nuclides = f["allowedValues"]
                                default = f["defaultValue"]
        self.nuclides = list(map(from_rodos_nuclide,nuclides))
        self.default_nuclide = from_rodos_nuclide(default)

    def get_levels(self):
        "read height values"
        return ["TODO"]
 
class DataItem(object):
    """ 
    Single 2D dataset.
    """
    def __init__(self,dataset,t_index=0,nuclide=None,z_index=0):
        self.dataset = dataset
        self.rodos = dataset.rodos
        self.t_index = t_index
        self.z_index = z_index
        self.nuclide = nuclide
        self.wps_input = [
            ('taskArg', 
             "taskuid='%s'" % self.dataset.task.path),
            ('dataitem',
             "path='%s'" % self.dataset.path),
            ('columns', str(t_index)), # only one column per data layer
            ('vertical', str(z_index)),
            ('threshold', str(0)) # TODO: add threshold support
        ]
        if nuclide!=None:
            # add nuclide to path parameter
            self.wps_input[1] = (self.wps_input[1][0],
                                 self.wps_input[1][1][:-1]\
                                 + to_rodos_nuclide(nuclide) + "'")
        self.gml = self.save_gml()
        #read projection from gml
        gml_data = open(self.gml).read()
        t = "epsg.xml#"
        ti = gml_data.find(t) + len(t)
        p = "epsg:"
        while gml_data[ti].isdigit():
            p += gml_data[ti]
            ti += 1
        self.projection = p # human readable
        # GDAL projection
        self.srs = osr.SpatialReference()
        try:
            self.srs.ImportFromEPSG( int(p.split(":")[-1]) )
        except ValueError:
            # no features, no projection
            self.srs = None
        # coordinate transfrom operator
        # store time value
        if self.dataset.times:
            self.timestamp = self.dataset.times[t_index]

    def save_gml(self,filename=None,force=False):
        if not filename:
            if self.nuclide:
                nuclide = self.nuclide
            else:
                nuclide = ""
            filename = self.rodos.storage + "/%s_%s_%02d_%01d%s.gml" % \
                (self.dataset.task.project.name,
                 self.dataset.name.replace(" ","_"),
                 self.t_index,
                 self.z_index,
                 nuclide)
        if (os.path.exists(filename) and force==False):
            return filename
        wps_run = self.rodos.wps.execute('gs:JRodosWPS',self.wps_input)

        logger.debug ( "Execute WPS with values %s" % (str(self.wps_input)) )
        wps_run.getOutput ( filename )
        return filename

    def envelope(self):
        gml_data = gml_driver.Open(self.gml)
        layer = gml_data.GetLayer()
        return layer.GetExtent()

    def valueAtLonLat(self,lon,lat):
        "read value at lon/lat point"
        if self.srs==None: # no features
            return None
        transform = osr.CoordinateTransformation(wgs84_cs,self.srs)
        x,y,dummy = transform.TransformPoint(lon,lat)
        gml_data = gml_driver.Open(self.gml)
        layer = gml_data.GetLayer()
        wkt = "POINT (%f %f)" % (x,y)
        layer.SetSpatialFilter(ogr.CreateGeometryFromWkt(wkt))
        for feature in layer:
            return float(feature.GetField("Value") )

    def areaExceeding(self,value):
        "calculate area where value is exceeded"
        gml_data = gml_driver.Open(self.gml)
        layer = gml_data.GetLayer()
        layer.SetAttributeFilter( "Value > %f" % value )
        area = 0
        for feature in layer:
            area += feature.GetGeometryRef().GetArea()
        return area

    def max(self):
        "Get max value and its lon/lat location"
        gml_data = gml_driver.Open(self.gml)
        layer = gml_data.GetLayer()
        max_value = 0
        geom_wkt = None
        for feature in layer:
            value = feature.GetField("Value")
            if value>max_value:
                max_value = value
                geom_wkt = feature.GetGeometryRef().ExportToWkt()
        if geom_wkt!=None:
            transform = osr.CoordinateTransformation(self.srs,wgs84_cs)
            polygon = ogr.CreateGeometryFromWkt(geom_wkt)
            # use point instead of polygon
            point = polygon.PointOnSurface()
            lon,lat,dummy = transform.TransformPoint(point.GetX(),point.GetY())
        else:
            lon,lat = None, None
        return (max_value,(lon,lat))
        
