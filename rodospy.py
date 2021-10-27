# -*- coding: utf-8 -*-
from owslib.wps import WebProcessingService
try:
    import osr
    import ogr
except ImportError:
    from osgeo import osr
    from osgeo import ogr
import os
from datetime import datetime, timedelta
from urllib.request import Request
from urllib.request import urlopen
import json
import codecs
import tempfile
import zipfile
from dateutil.parser import parse
from xml.etree.ElementTree import XML, fromstring, tostring
from pathlib import Path
import numpy as n
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

# Add formatting and handlers as needed
owslib_log = logging.getLogger('owslib')
owslib_log.setLevel(logging.DEBUG)

# GDAL constants
wgs84_cs = osr.SpatialReference()
#wgs84_cs.ImportFromEPSG(4326)
wgs84_cs.ImportFromProj4("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
gml_driver = ogr.GetDriverByName('GML')
gpkg_driver = ogr.GetDriverByName('GPKG')
shapefile_driver = ogr.GetDriverByName('ESRI Shapefile')

request_template = """<?xml version="1.0" encoding="UTF-8"?>
        <wps:Execute version="1.0.0" service="WPS" 
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xmlns="http://www.opengis.net/wps/1.0.0" 
          xmlns:wfs="http://www.opengis.net/wfs"
          xmlns:wps="http://www.opengis.net/wps/1.0.0" 
          xmlns:ows="http://www.opengis.net/ows/1.1"
          xmlns:gml="http://www.opengis.net/gml" 
          xmlns:ogc="http://www.opengis.net/ogc"
          xmlns:wcs="http://www.opengis.net/wcs/1.1.1" 
          xmlns:xlink="http://www.w3.org/1999/xlink"
          xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 
          http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
          <ows:Identifier>gs:JRodosGeopkgWPS</ows:Identifier>
          <wps:DataInputs>
            <wps:Input>
              <ows:Identifier>taskArg</ows:Identifier>
              <wps:Data>
                <wps:LiteralData>TASKARG</wps:LiteralData>
              </wps:Data>
            </wps:Input>
            <wps:Input>
              <ows:Identifier>dataitem</ows:Identifier>
              <wps:Data>
                <wps:LiteralData>DATAITEM</wps:LiteralData>
              </wps:Data>
            </wps:Input>
            <wps:Input>
              <ows:Identifier>columns</ows:Identifier>
              <wps:Data>
                <wps:LiteralData>COLUMNS</wps:LiteralData>
              </wps:Data>
            </wps:Input>
            <wps:Input>
              <ows:Identifier>vertical</ows:Identifier>
              <wps:Data>
                <wps:LiteralData>0</wps:LiteralData>
              </wps:Data>
            </wps:Input>
            <wps:Input>
              <ows:Identifier>threshold</ows:Identifier>
              <wps:Data>
                <wps:LiteralData>THRESHOLD</wps:LiteralData>
              </wps:Data>
            </wps:Input>
            <wps:Input>
              <ows:Identifier>includeSLD</ows:Identifier>
              <wps:Data>
                <wps:LiteralData>1</wps:LiteralData>
              </wps:Data>
            </wps:Input>     
          </wps:DataInputs>
          <wps:ResponseForm>
            <wps:RawDataOutput mimeType="application/zip">
              <ows:Identifier>result</ows:Identifier>
            </wps:RawDataOutput>
          </wps:ResponseForm>
        </wps:Execute>
"""

def datetime_parser(value):
    "datetime parser for json document"
    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = datetime_parser(v)
    elif isinstance(value, list):
        for index, row in enumerate(value):
            value[index] = datetime_parser(row)
    elif isinstance(value, str) and value:
        try:
            value = parse(value)
        except (ValueError, AttributeError):
            pass
    return value

def from_rodos_nuclide(nuclide):
    "rodos nuclide has fixed string lenght"
    n = nuclide.split("-")
    n[0] = n[0].strip()
    n[1] = n[1].strip()
    return n[0] + "-" + n[1]

class RodosPyException(Exception):
    "Module specific exception"
    def __init(self,message):
        raise NameError ( message )

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
        self.r = settings["rest"]
        self.rest_url = self.r["url"]
        # check that connections are OK
        self.wps_capabilities = self.wps.getcapabilities()
        self.projects = self.get_projects()

    def refresh_projects():
        "get refreshed list of projects"
        self.projects = self.get_projects()

    def get_projects(self,
                     filters={}): # fetch the project list
        """
        Get listing of projects.
        Filters is a dictionary of project parameters.
        Possible dict values are: projectId, uid, name,
        description, username, modelchainname, extendedProjectInfo, 
        dateTimeCreated, dateTimeModified
        """
        # rest request
        response = urlopen( self.rest_url + "/projects" )
        proj_dict = json.load(reader(response),
                              object_hook=datetime_parser)["content"]
        # create list of project classes
        projects = []
        for p in proj_dict:
            if filters.items()<=p.items():
                projects.append(Project(self,p))
        return projects

    def get_npps(self):
        """
        Get listing of Nuclear Power plants
        """
        response = urlopen( self.rest_url + "/npps" )
        npp_dict = json.load(reader(response),
                             object_hook=datetime_parser)["content"]
        return npp_dict

class Project(object):
    """
    Create Project instance.
    project must be tuple generated by RodosConnection 
    or project uid
    """
    def __repr__(self):
        return ("<Project %s | %s>" % (self.name, self.modelchainname))

    def __init__(self,rodos,values):
        """
        Project class is created based on project id fetch from REST service
        project_id is integer
        """
        self.rodos = rodos
        for key in values:
            setattr(self,key,values[key])
        # load details only when necessary
        self.details_dict = None

    def load(self):
        """Load project metadata"""
        # request project details from rest service
        response = urlopen( self.rodos.rest_url + "/projects/{:d}".format(
            self.projectId))
        details_dict = json.load(reader(response),
                                 object_hook=datetime_parser)
        self.details_dict = details_dict
        # set metadata as attributes
        for key in details_dict:
            if (key not in ("tasks","extendedProjectInfo")):
                setattr(self,key,details_dict[key])
            elif key=="extendedProjectInfo":
                for key2 in details_dict[key]:
                    setattr(self,key2,details_dict[key][key2])
        # set source term nuclides as list
        try:
            self.sourcetermNuclides = self.sourcetermNuclides.split(",")
        except:
            logger.debug( "Source term info is missuing" )
            self.sourcetermNuclides = []
        for t in details_dict["tasks"]:
            self.tasks.append ( Task(self,t) )

    def get_tasks(self, filters={}):
        "Get tasks and filter by dictionary."
        if self.details_dict==None:
            self.load()
        tasks = []
        for t in self.details_dict["tasks"]:
            if filters.items()<=t.items():
                tasks.append ( Task(self,t) )
        return tasks
        

class Task(object):
    """
    JRodos Task instance. Contains single model run.
    """
    def __repr__(self):
        return ("<Task %s | %s>" % (self.modelwrappername, self.description))

    def __init__(self,project,tdict):
        self.rodos = project.rodos
        self.project = project
        self.dataitems = []
        for key in tdict:
            if key!="dataitems":
                setattr(self,key,tdict[key])
        self.dataitems_json = tdict["dataitems"] # use this for searchs?
        self.gridseries = []
        for d in tdict["dataitems"]:
            if d["dataitem_type"]=="GridSeries":
                self.gridseries.append( GridSeries(self,d) )
        self.deposition = {}
        self.wet_deposition = {}
        self.dry_deposition = {}
        self.air_concentration = {}
        self.time_integrated_air_concentration = {}
        self.total_deposition = {}
        self.ground_gamma_dose_rate = {}
        self.total_dose = {}
        self.cloud_dose = {}
        self.ground_dose = {}
        self.inhalation_dose = {}
        self.skin_dose = {}
        
        # classify grid series to dictionaries
        # TODO: some items still missing (FDMT, Emersim, DEPOM etc.)
        for i in self.gridseries:
            try:
                i.nuclide = from_rodos_nuclide(i.name)
            except IndexError: # not nuclide dependent
                i.nuclide = None
            if i.groupname=="ground.contamination":
                self.deposition[i.nuclide] = i
            elif i.groupname=="ground.contamination.wet":
                self.wet_deposition[i.nuclide] = i
            elif i.groupname=="ground.contamination.dry":
                self.dry_deposition[i.nuclide] = i
            elif i.groupname=="air.concentration.near.ground.surface":
                self.air_concentration[i.nuclide] = i
            elif i.groupname==\
                "air.concentration.time.integrated.near.ground.surface":
                self.time_integrated_air_concentration[i.nuclide] = i
            elif i.groupname=="air.concentration.instantaneous.exceeded":
                self.concentration_exceeded = i
            elif i.groupname=="Graphical_Aerosol":
                self.total_deposition["aerosol"] = i
            elif i.groupname=="Graphical_Iodine":
                self.total_deposition["iodine"] = i
            elif i.groupname=="total.gamma.dose.rate":
                self.total_gamma_dose_rate = i
            elif i.groupname=="DOSRCL":
                self.cloud_total_gamma_dose_rate = i
            elif i.groupname=="DRNUGR":
                self.ground_gamma_dose_rate[i.nuclide] = i
            elif i.groupname=="total.dose":
                self.total_dose[i.name] = i
            elif i.groupname=="cloud.dose":
                self.cloud_dose[i.name] = i
            elif i.groupname=="ground.dose":
                self.ground_dose[i.name] = i
            elif i.groupname=="inhalation.dose":
                self.inhalation_dose[i.name] = i
            elif i.groupname=="skin.dose":
                self.skin_dose[i.name] = i
            elif i.groupname=="cloud.arrival.time":
                self.cloud_arrival_time = i
            elif i.groupname=="cloud.arrival.living.time":
                self.cloud_leaving_time = i
            elif i.groupname=="total.dose.nuclide.specific":
                try:
                    key = from_rodos_nuclide(i.name)
                except IndexError: # not nuclide 
                    key = i.name
                self.total_dose[key] = i

class GridSeries(object):
    "Series of grid results"
    def __repr__(self):
        return ("<GridSeries %s | %s>" % (self.groupname, self.name))

    def __init__(self,task,ddict):
        self.task = task
        self.project = task.project
        self.rodos = task.rodos
        self.gpkgfile = None
        for key in ddict:
            setattr(self,key,ddict[key])
        self.output_dir = "{}/{}/{}/{}".format(self.rodos.storage,
                                               self.task.project.name,
                                               self.task.project.modelchainname,
                                               self.datapath.replace(" ","_"))

    def times(self):
        "Read timestamps of data"
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(1) # data layer
        times = []
        for feature in layer:
            time_value = feature.GetField ( "Time" )
            #unique times
            if not time_value in times:
                times.append(time_value)
        times.sort()
        # convert epoch times to datetime objects
        return list(map(datetime.fromtimestamp,times))

    def levels(self):
        "TODO"
        return []

    def get_filepath(self):
        "generate filepath if check if it does exists"
        if not os.path.isdir(self.output_dir):
            self.save_gpkg()
        return self.output_dir
    
    def gpkg_file(self):
        "get full path of gpkg file"
        filelist = os.listdir( self.get_filepath() ) 
        for filename in filelist:
            if filename.split(".")[-1]=="gpkg":
                break
        return self.get_filepath() + "/" + filename

    def sld_file(self):
        "get full path of sld file"
        filelist = os.listdir( self.get_filepath() ) 
        for filename in filelist:
            if filename.split(".")[-1]=="sld":
                break
        return self.get_filepath() + "/" + filename
    
    def save_gpkg(self,output_dir=None,force=True):
        "Read and save GeoPackage file from WPS service"
        if output_dir==None:
            output_dir = self.output_dir
        wps_input = [
                ('taskArg', 
                 "project='{}'&amp;model='{}'".format(self.task.project.name,\
                                                      self.task.modelwrappername)),
                ('dataitem',
                 "path='%s'" % self.datapath),
                ('columns', "0-"), # get the whole dataset
                ('vertical', "0"), # TODO: think!
                ('includeSLD', "1"),
                ('threshold', "1e-15") # TODO: add threshold support
            ]
        x = "{}".format(request_template)
        x = x.replace("TASKARG",wps_input[0][1])
        x = x.replace("DATAITEM",wps_input[1][1])
        x = x.replace("COLUMNS",wps_input[2][1])
        x = x.replace("THRESHOLD",wps_input[5][1])
        #wps_run = self.rodos.wps.execute('gs:JRodosGeopkgWPS',wps_input)
        req = Request ( self.rodos.w["url"],
                        data = x.encode(), 
                        headers = xml_headers)
        logger.debug ( "Execute WPS with values %s" % (str(wps_input)) )
        response = urlopen( req )
        temp = tempfile.NamedTemporaryFile() #2
        try:
            resp_file = open(temp.name, "wb")
            resp_file.write( response.read() )
            resp_file.close()
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            try:
                with zipfile.ZipFile(temp.name, 'r') as zip_ref:
                    zip_ref.extractall(output_dir)
            except zipfile.BadZipFile:
                logger.error ( "Something went wrong" )
                os.rmdir ( output_dir )
                raise RodosPyException ( open(temp.name).read()  )
        finally:
            temp.close() 
        self.filepath = output_dir
        return self.filepath

    def envelope(self):
        "Get the bbox of data"
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(0) # grid
        return layer.GetExtent()    

    def max(self,time_value=None):
        """
        Get max value and its lon/lat location
        Filter by time value is supported.
        """
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(2) # view
        if time_value!=None:
            epoch_time = int(time_value.timestamp())
            layer.SetAttributeFilter( "Time={:d}".format(epoch_time) )
        max_value = 0
        geom_wkt = None
        timestamp = None
        for feature in layer:
            value = feature.GetField("Value")
            if value>max_value:
                max_value = value
                geom_wkt = feature.GetGeometryRef().ExportToWkt()
                timestamp = feature.GetField("Time")
        if geom_wkt!=None:
            transform = osr.CoordinateTransformation(layer.GetSpatialRef(),wgs84_cs)
            polygon = ogr.CreateGeometryFromWkt(geom_wkt)
            # use point instead of polygon
            point = polygon.PointOnSurface()
            lon,lat,dummy = transform.TransformPoint(point.GetX(),point.GetY())
        else:
            lon,lat = None, None
        if max_value>0:
            timestamp = datetime.fromtimestamp(timestamp)
        return (max_value,(lon,lat),timestamp)

    def areaExceeding(self,value,time_value):
        "calculate area where value is exceeded"
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(2) # view
        if time_value!=None:
            epoch_time = int(time_value.timestamp())
            layer.SetAttributeFilter( "Time={:d}".format(epoch_time) )
        layer.SetAttributeFilter( "Value > %f" % value )
        area = 0
        for feature in layer:
            area += feature.GetGeometryRef().GetArea()
        return area

    def timeSeries(self,lon,lat):
        "extract time series in singe point"
        times = self.times
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint( lon,lat )
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(0) # grid
        transform = osr.CoordinateTransformation(wgs84_cs,layer.GetSpatialRef())
        point.Transform( transform )
        found = False
        for feature in layer:
            data_geom = feature.GetGeometryRef()
            if data_geom.Intersects( point ):
                cell = float(feature.GetField("Cell"))
                found = True
                break
        if not found:
            return None
        layer = gis_data.GetLayer(2) # view
        layer.SetAttributeFilter( "cell={:d}".format(int(cell)) )
        values = {}
        for feature in layer:
            value = feature.GetField("Value")
            t_value = feature.GetField("Time")
            values[t_value] = value
        # sort by time
        x = []
        y = []
        for key in sorted(values.keys()):
            x.append(key)
            y.append(values[key])
        return {"times": list(map(datetime.fromtimestamp,x)), 
                "values": y, 
                "unit": self.unit, 
                "title": "{} at point ({},{})".format(self.name,
                                                      "{0:.3f}".format(lon),
                                                      "{0:.3f}".format(lat))
                }

    def getBbox(self):
        "Get bounding box of data"
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(0) # grid
        e = layer.GetExtent()
        return (e[0],e[2],e[1],e[3])

    def getLonLatBoundaries(self):
        "get data boundaries"
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(0) # grid
        e = layer.GetExtent()
        transform = osr.CoordinateTransformation(layer.GetSpatialRef(),wgs84_cs)
        ll = ogr.Geometry(ogr.wkbPoint)
        ll.AddPoint( e[0],e[2] )
        ur = ogr.Geometry(ogr.wkbPoint)
        ur.AddPoint ( e[1], e[3] )
        ll.Transform( transform )
        ur.Transform( transform )
        return (ll.GetX(),ll.GetY(),ur.GetX(),ur.GetY())
    
    def getCentroid(self):
        "Get data bounding box centroid"
        bbox = self.getBbox()
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint( bbox[0], bbox[1] ) 
        ring.AddPoint( bbox[0], bbox[3] )
        ring.AddPoint( bbox[2], bbox[3] )
        ring.AddPoint( bbox[2], bbox[1] )
        ring.AddPoint( bbox[0], bbox[1] ) 
        polygon = ogr.Geometry( ogr.wkbPolygon )
        polygon.addGeometry (ring )
        return polygon.Centroid()

    def valueAtDistance(self,center_lon,center_lat,distance_in_km):
        "get maximum value in the distance of X meters. Center must be given also."
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(2) # view
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint( center_lon,center_lat )
        transform = osr.CoordinateTransformation(wgs84_cs,layer.GetSpatialRef())
        point.Transform( transform) 
        x = point.GetX()
        y = point.GetY()
        ring = ogr.Geometry(ogr.wkbLineString)
        for i in range(0,720): # circle line forms of 720 points
            x_coord = x + ( n.cos (n.radians(i/2.0) ) * distance_in_km/2.0 * 1000 *2 )
            y_coord = y + ( n.sin (n.radians(i/2.0) ) * distance_in_km/2.0 * 1000 *2 )
            ring.AddPoint( x_coord, y_coord )
        values = []
        for feature in layer:
            data_geom = feature.GetGeometryRef()
            if data_geom.Intersects ( ring ):
                values.append( feature.GetField("Value") )
        if values==[]:
            return {"max": None,
                    "average": None,
                    "min": None,
                    "median": None,
                    "percentile_90": None,
                    "percentile_95": None,
                    "percentile_80": None
                    }
        else:
            V = n.asarray(values)
            return {"max": n.amax(V),
                    "average": n.average(V),
                    "min": n.amin(V),
                    "median": n.percentile(V,50),
                    "percentile_90": n.percentile(V,90),
                    "percentile_95": n.percentile(V,95),
                    "percentile_80": n.percentile(V,80)
                    }


    def save_as_shapefile(self,output_dir=None, file_prefix="out", timestamp=None):
        "Save as shape file. Can be used in map plotting etc"
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(2) # view
        if timestamp!=None:
            epoch_time = int(timestamp.timestamp())
            layer.SetAttributeFilter( "Time={:d}".format(epoch_time) )
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        shapefile_path = "{}/{}.shp".format(
            output_dir,file_prefix)
        # delete existing dataset
        if os.path.exists(shapefile_path):
            shapefile_driver.DeleteDataSource(shapefile_path)
        data_source = shapefile_driver.CreateDataSource( shapefile_path)
        srs = layer.GetSpatialRef()
        shapefile_layer = data_source.CreateLayer( "jrodosexport",wgs84_cs,ogr.wkbPolygon)
        fields = ( 
            ("fid", ogr.OFTInteger64),
            ("Cell", ogr.OFTInteger64),
            ("Time", ogr.OFTInteger64),
            ("Value", ogr.OFTReal)
        )

        for f in fields:
            field_def = ogr.FieldDefn(f[0],f[1])
            shapefile_layer.CreateField(field_def)

        transform = osr.CoordinateTransformation(layer.GetSpatialRef(),wgs84_cs)
        for feature in layer:
            geom = feature.GetGeometryRef()
            geom.Transform ( transform )
            shapefile_layer.CreateFeature( feature )
        data_source = None
        return shapefile_path

