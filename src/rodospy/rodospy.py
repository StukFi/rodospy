# -*- coding: utf-8 -*-
from owslib.wps import WebProcessingService
import osr
import ogr
import os
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError
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
xml_headers = {'Content-Type': 'application/xml'}

# Add formatting and handlers as needed
owslib_log = logging.getLogger('owslib')
owslib_log.setLevel(logging.DEBUG)

# GDAL constants
wgs84_cs = osr.SpatialReference()
wgs84_cs.ImportFromEPSG(4326)
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

    def __init(self, message):
        raise NameError(message)


class RodosConnection(object):
    """
    Setup JRodos database and Geoserver connection
    When initialized, connections are checked.
    The connection settings will be passed to other classes.
    """

    def __repr__(self):
        return ("<RodosConnection %s>" % (self.wps))

    def __init__(self, settings=None):
        "Initialize RODOS DB and WPS connection"
        logger.debug("Read settings from file")
        if settings == None:
            # try to read from config file
            raise RodosPyException("No settings defined")
        self.w = settings["wps"]
        self.wps = WebProcessingService(self.w["url"],
                                        verbose=False,  # set this True when debugging
                                        skip_caps=True)
        self.storage = self.w["file_storage"]
        self.r = settings["rest"]
        self.rest_url = self.r["url"]
        # Richard: is this needed?
        # check that connections are OK
        self.wps_capabilities = self.wps.getcapabilities()
        self.projects = self.get_projects()

    def refresh_projects(self):
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
            if len(filters.keys()) == 0:
                projects.append(Project(self, p))
            else:
                # below does not work in Python3 ?
                # https://stackoverflow.com/questions/54691491/how-is-the-less-than-operator-for-dictionaries-defined-in-python-2
                #if filters.items() <= p.items():
                #    projects.append(Project(self, p))
                for key in filters.keys():
                    # 'casting' values to strings here, because it is not always clear if values are txt or integers
                    if key in filters.keys() and f'{p.get(key)}' == f'{filters[key]}':
                        projects.append(Project(self, p))
        return projects

    def get_npps(self):
        """
        Get listing of Nuclear Power plants
        """
        response = urlopen(self.rest_url + "/npps")
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

    def __init__(self, rodos, values):
        """
        Project class is created based on project id fetch from REST service
        project_id is integer
        """
        self.rodos = rodos
        for key in values:
            setattr(self,key,values[key])
        # load details only when necessary
        self.details_dict = None
        self.tasks = []

    # def load(self, project_rest_url=None):
    #     """Load project metadata"""
    #     # request project details from rest service
    #     if project_rest_url is not None:
    #         url = project_rest_url
    #     else:
    #         url = self.rodos.rest_url + "/projects/{:d}".format(self.projectId)
    #     response = urlopen(url)
    #     details_dict = json.load(reader(response),
    #                              object_hook=datetime_parser)
    #     # set metadata as attributes
    #     for key in details_dict:
    #         if (key not in ("tasks", "extendedProjectInfo")):
    #             setattr(self, key, details_dict[key])
    #         elif key == "extendedProjectInfo":
    #             for key2 in details_dict[key]:
    #                 setattr(self, key2, details_dict[key][key2])
    #     # set source term nuclides as list, or empty list as None
    #     if self.sourcetermNuclides:
    #         self.sourcetermNuclides = self.sourcetermNuclides.split(",")
    #     else:
    #         self.sourcetermNuclides = []
    #     for t in details_dict["tasks"]:
    #         self.tasks.append(Task(self, t))
    #     return self

    def load(self, project_rest_url=None):
        """Load project metadata"""
        # request project details from rest service
        if project_rest_url is not None:
            url = project_rest_url
        else:
            url = self.rodos.rest_url + "/projects/{:d}".format(self.projectId)
        try:
            response = urlopen(url)
        except URLError as e:
            # non excisting project throw a 500...
            # while url is actually pretty descriptive: http://jrodos.dev.cal-net.nl/rest-2.0/jrodos/projects/665
            # urllib does NOT provide any response object...
            # TODO add some exception
            print(e.reason)
            return
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
        if self.sourcetermNuclides:
            self.sourcetermNuclides = self.sourcetermNuclides.split(",")
        else:
            self.sourcetermNuclides = []
        for t in details_dict["tasks"]:
            self.tasks.append(Task(self, t))

    def get_tasks(self, filters={}):
        """Get tasks and filter by dictionary."""
        if self.details_dict==None:
            self.load()
        tasks = []
        for t in self.details_dict["tasks"]:
            if len(filters.keys()) == 0:
                tasks.append(Project(self, t))
            else:
                # below does not work in Python3 ?
                # https://stackoverflow.com/questions/54691491/how-is-the-less-than-operator-for-dictionaries-defined-in-python-2
                # if filters.items()<=t.items():
                #     tasks.append ( Task(self,t) )
                for key in filters.keys():
                    # 'casting' values to strings here, because it is not always clear if values are txt or integers
                    data_items = t.get('dataitems')
                    for data_item in data_items:
                        if key in data_item.keys() and f'{data_item.get(key)}' == f'{filters[key]}':
                            tasks.append(Task(self, t))
        return tasks

class Task(object):
    """
    JRodos Task instance. Contains single model run.
    """

    def __repr__(self):
        return ("<Task %s | %s>" % (self.modelwrappername, self.description))

    def __init__(self, project, tdict):
        self.rodos = project.rodos
        self.project = project
        self.dataitems = []
        for key in tdict:
            if key != "dataitems":
                setattr(self, key, tdict[key])
        self.dataitems_json = tdict["dataitems"]  # use this for searches?
        self.gridseries = []
        for d in tdict["dataitems"]:
            self.dataitems.append(d)
            if d["dataitem_type"] == "GridSeries":
                self.gridseries.append(GridSeries(self, d))
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
        self.groupnames = []
        # Richard
        self.dep = {}
        self.eta = {}
        self.potential_dose = {}
        self.potential_dose_ingestion = {}

        # classify grid series to dictionaries
        # TODO: some items still missing (FDMT, Emersim, DEPOM etc.)

        # NPKPUFF:
        # ['Dep', 'AtmResist', 'DEPOS', 'WDep', 'DDep', 'iDep', 'MaxDep',
        #  'MomWDep', 'MomDDep', 'Con', 'iCon', 'MaxCon', 'Column', 'AccRain',
        #  'CumulRain', 'MixLayer', 'EffectedDoseRate_AllRelevant',
        #  'EffectedDoseRate_ExtCloud', 'EffectedDoseRate_ExtGround',
        #  'DoseRate_ExtCloudNuclSpec', 'PotentialDose_AllRelevant',
        #  'PotentialDose_ExtCloud', 'PotentialDose_ExtGround',
        #  'PotentialDose_FInhalation', 'PotentialDose_Ingestion',
        #  'PotentialDose_SkinAllRelevant', 'Eta', 'Eta.Hemisphere', 'DEPOSW',
        #  'ACAIR', 'DOSRACL', 'IodineFrac', 'ResistAtm', 'RERAF']

        # LSMC:
        # ['ground.contamination', 'MPPtoADM_istabG', 'MPPtoADM_hmixG',
        # 'cloud.arrival.living.time', 'ground.contamination.wet', 'DBIHEFF',
        # 'DBIHJTHY', 'DBSOEFF', 'DBSOWEFF', 'ground.contamination.dry',
        # 'DBCLDET', 'DBGRDET', 'DBIHDET', 'DBAUCL',
        # 'air.concentration.near.ground.surface',
        # 'air.concentration.time.integrated.near.ground.surface',
        # 'air.concentration.instantaneous.exceeded', 'precipitation',
        # 'MPPtoADM_preciG', 'MPPtoADM_smoliG', 'MPPtoADM_UstarG',
        # 'MPPtoADM_LevelHght', 'total.gamma.dose.rate', 'DOSRCL', 'DOSRGR',
        # 'DRNUGR', 'total.dose', 'cloud.dose', 'ground.dose',
        # 'inhalation.dose', 'skin.dose', 'total.dose.nuclide.specific',
        # 'cloud.arrival.time', 'DINTGR7S', 'DBCLEFF', 'DBGREFF', 'DBAUGR',
        # 'DBAUIH', 'DBAUJT', 'DBAUSL', 'DBAUSLW', 'DBAUSO', 'DBAUSOW',
        # 'DOFFCL', 'DOFFGR', 'DOFFIH', 'DOFFJT', 'DOFFSL', 'DOFFSLW',
        # 'DOFFSO', 'DOFFSOW', 'DINTGR', 'ACAIR', 'DEPOS', 'DEPOSW', 'DOSRACL',
        # 'RERAF', 'ResistAtm', 'IodineFrac', 'Environmental_Region',
        # 'Environmental_Uniform_Elevation', 'Environmental_Uniform_Landuse']

        # LSMC / CETs:
        # ['ground.contamination', 'DBGREFF', 'DBIHEFF', 'DBIHJTHY', 'DBSOEFF',
        # 'DBSOWEFF', 'DBCLDET', 'ground.contamination.wet', 'DBGRDET',
        # 'DBIHDET', 'DOFFIH', 'DOFFSL', 'DOFFSLW', 'ground.contamination.dry',
        # 'DOFFSO', 'DOFFSOW', 'DINTGR', 'ACAIR',
        # 'air.concentration.near.ground.surface',
        # 'air.concentration.time.integrated.near.ground.surface',
        # 'air.concentration.instantaneous.exceeded', 'precipitation',
        # 'MPPtoADM_istabG', 'MPPtoADM_hmixG', 'MPPtoADM_preciG',
        # 'MPPtoADM_smoliG', 'MPPtoADM_UstarG', 'MPPtoADM_LevelHght',
        # 'total.gamma.dose.rate', 'DOSRCL', 'DOSRGR', 'DRNUGR', 'total.dose',
        # 'cloud.dose', 'ground.dose', 'cloud.arrival.time', 'inhalation.dose',
        # 'skin.dose', 'total.dose.nuclide.specific', 'cloud.arrival.living.time',
        # 'DBCLEFF', 'DINTGR7S', 'DBAUCL', 'DBAUGR', 'DBAUIH', 'DBAUJT',
        # 'DBAUSL', 'DBAUSLW', 'DBAUSO', 'DBAUSOW', 'DOFFCL', 'DOFFGR',
        # 'DOFFJT', 'DEPOS', 'DEPOSW', 'DOSRACL', 'IodineFrac', 'RERAF',
        # 'ResistAtm', 'Environmental_Region',
        # 'Environmental_Uniform_Elevation', 'Environmental_Uniform_Landuse']

        # DEPOM:
        # ['Graphical_Rainfall', 'Graphical_Aerosol', 'Graphical_Iodine',
        # 'Environmental_Region', 'Environmental_Landuse']

        # EMERSIM:
        # ['ARFLAG_KENDET', 'ARFLAG_KENNSH', 'ARFLAG_KENNEV',
        # 'ARFLAG_KENIAD', 'ARFLAG_KENICH', 'ARFLAG_KENUMT', 'ARFLAG_KENUMP',
        # 'ARFLAG_KIMMEV', 'ARFLAG_KENNSK', 'ARFLAG_KENSKM', 'ARFLAG_TAGSH',
        # 'ARFLAG_TAGEV', 'ARFLAG_TAGIAD', 'ARFLAG_TAGICH',
        # 'DOSFELAC_DGRAC_bone_marrow', 'DOSFELAC_DGRAC_bone_marrow_30',
        # 'DOSFELAC_DGRAC_thyroid', 'DOSFELAC_DGRAC_thyroid_30',
        # 'DOSFELAC_DGRAC_effective', 'DOSFELAC_DGRAC_effective_30',
        # 'DOSFELAC_DCLAC_bone_marrow', 'DOSFELAC_DCLAC_thyroid',
        # 'DOSFELAC_DCLAC_effective', 'DOSFELAC_DICTAC',
        # 'DOSFELAC_DIHAC_thyroid', 'DOSFELAC_DOSUAC_bone_marrow',
        # 'DOSFELAC_DOSUAC_thyroid', 'DOSFELAC_DOSUAC_effective',
        # 'DOSFELAC_DSLAC', 'DOSFELNO_DGRNO1_bone_marrow',
        # 'DOSFELNO_DGRNO2_bone_marrow', 'DOSFELNO_DGRNO1_bone_marrow_30',
        # 'DOSFELNO_DGRNO2_bone_marrow_30', 'DOSFELNO_DGRNO1_thyroid',
        # 'DOSFELNO_DGRNO2_thyroid', 'DOSFELNO_DGRNO1_thyroid_30',
        # 'DOSFELNO_DGRNO2_thyroid_30', 'DOSFELNO_DGRNO1_effective',
        # 'DOSFELNO_DGRNO2_effective', 'DOSFELNO_DGRNO1_effective_30',
        # 'DOSFELNO_DGRNO2_effective_30', 'DOSFELNO_DCLNO1_bone_marrow',
        # 'DOSFELNO_DCLNO2_bone_marrow', 'DOSFELNO_DCLNO1_thyroid',
        # 'DOSFELNO_DCLNO2_thyroid', 'DOSFELNO_DCLNO1_effective',
        # 'DOSFELNO_DCLNO2_effective', 'DOSFELNO_DICTNO1', 'DOSFELNO_DICTNO2',
        # 'DOSFELNO_DIHNO1_thyroid', 'DOSFELNO_DIHNO2_thyroid',
        # 'DOSFELNO_DOSUNO1_bone_marrow', 'DOSFELNO_DOSUNO2_bone_marrow',
        # 'DOSFELNO_DOSUNO1_thyroid', 'DOSFELNO_DOSUNO2_thyroid',
        # 'DOSFELNO_DOSUNO1_effective', 'DOSFELNO_DOSUNO2_effective',
        # 'DOSFELNO_DSLNO1', 'DOSFELNO_DSLNO2', 'DOSFELNO_GDOSE',
        # 'DOSFELNO_GRATE', 'INTER_DOKATS', 'INTER_DOKATSEV',
        # 'INTER_IODINE_CHILDREN', 'INTER_IODINE_ADULTS',
        # 'INTER_RELOCATION_30d', 'INTER_RELOCATION_1y', 'Popula_RBEV',
        # 'Environmental_Region', 'Environmental_Cloudshine',
        # 'Environmental_Groundshine_S', 'Environmental_Inhalation_S',
        # 'Environmental_Cloudshine.Sheltering',
        # 'Environmental_Groundshine_S.Sheltering',
        # 'Environmental_Inhalation_S.Sheltering',
        # 'Environmental_Occupancy', 'Environmental_HouseType']

        # FDMT:
        # ['cfee->niodfgri', 'cfee->ncesfgri', 'cfoo->niodfvel',
        # 'cfoo->niodfmil', 'cfoo->ncesfvel', 'cfoo->ncesfmil', 'cscr',
        # 'cgrl', 'cinh', 'cing->nsumfsum', 'csum->nsumfsum',
        # 'Environmental_Inhalation_S',
        # 'csum->csumgmapiintt01yepotnsumlallaaduoefffsumvnin',
        # 'Environmental_Region', 'Environmental_Landuse', 'Environmental_Soil',
        # 'Environmental_Cloudshine', 'Environmental_Groundshine_L',
        # 'Environmental_Groundshine_S', 'Environmental_Inhalation_L',
        # 'Environmental_Skin', 'Environmental_Occupancy',
        # 'Environmental_HouseType', 'Environmental_Food']

        for i in self.gridseries:

            if not i.groupname in self.groupnames:
                self.groupnames.append(i.groupname)

            try:
                i.nuclide = from_rodos_nuclide(i.name)
            except IndexError:  # not nuclide dependent
                i.nuclide = None
            # print(i.groupname)
            if i.groupname == "ground.contamination":
                self.deposition[i.nuclide] = i
            elif i.groupname == "ground.contamination.wet":
                self.wet_deposition[i.nuclide] = i
            elif i.groupname == "ground.contamination.dry":
                self.wet_deposition[i.nuclide] = i
            elif i.groupname == "air.concentration.near.ground.surface":
                self.air_concentration[i.nuclide] = i
            elif i.groupname == \
                    "air.concentration.time.integrated.near.ground.surface":
                self.time_integrated_air_concentration[i.nuclide] = i
            elif i.groupname == "air.concentration.instantaneous.exceeded":
                self.concentration_exceeded = i
            elif i.groupname == "Graphical_Aerosol":
                self.total_deposition["aerosol"] = i
            elif i.groupname == "Graphical_Iodine":
                self.total_deposition["iodine"] = i
            elif i.groupname == "EffectedDoseRate_AllRelevant":  # "total.gamma.dose.rate":
                self.total_gamma_dose_rate = i
            elif i.groupname == "DOSRCL":
                self.cloud_total_gamma_dose_rate = i
            elif i.groupname == "DRNUGR":
                self.ground_gamma_dose_rate[i.nuclide] = i
            elif i.groupname == "total.dose":
                self.total_dose[i.name] = i
            elif i.groupname == "total.dose.nuclide.specific":
                try:
                    key = from_rodos_nuclide(i.name)
                except IndexError:  # not nuclide
                    key = i.name
                self.total_dose[key] = i
            elif i.groupname == "cloud.dose":
                self.cloud_dose[i.name] = i
            elif i.groupname == "ground.dose":
                self.ground_dose[i.name] = i
            elif i.groupname == "inhalation.dose":
                self.inhalation_dose[i.name] = i
            elif i.groupname == "skin.dose":
                self.skin_dose[i.name] = i
            # Richard
            elif i.groupname == 'Dep':
                self.dep[i.name] = i
            elif i.groupname == 'PotentialDose_AllRelevant':
                self.potential_dose[i.name] = i
            elif i.groupname == 'PotentialDose_Ingestion':
                self.potential_dose_ingestion[i.name] = i
            elif i.groupname == 'Eta' or i.groupname == 'Eta.Hemisphere':
                self.eta[i.name] = i
            # TODO: handle all groupnames and names !!
            # else:
            #    print(f'group: {i.groupname} name: {i.name}')


class GridSeries(object):
    """Series of grid results"""

    def __repr__(self):
        return ("<GridSeries %s | %s>" % (self.groupname, self.name))

    def __init__(self, task, ddict):
        self.task = task
        self.project = task.project
        self.rodos = task.rodos
        self.gpkgfile = None
        for key in ddict:
            setattr(self, key, ddict[key])
        self.output_dir = "{}/{}/{}/{}".format("/tmp/jrodoswps",  # self.rodos.storage,
                                               self.task.project.name,
                                               self.task.project.modelchainname,
                                               self.datapath.replace(" ", "_"))

    def times(self):
        "Read timestamps of data"
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(1)  # data layer
        times = []
        for feature in layer:
            time_value = feature.GetField("Time")
            # unique times
            if not time_value in times:
                times.append(time_value)
        times.sort()
        # convert epoch times to datetime objects
        return list(map(datetime.fromtimestamp, times))

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
        filelist = os.listdir(self.get_filepath())
        for filename in filelist:
            if filename.split(".")[-1] == "gpkg":
                break
        return self.get_filepath() + "/" + filename

    def sld_file(self):
        "get full path of sld file"
        filelist = os.listdir(self.get_filepath())
        for filename in filelist:
            if filename.split(".")[-1] == "sld":
                break
        return self.get_filepath() + "/" + filename

    def save_gpkg(self, output_dir=None, force=True):
        "Read and save GeoPackage file from WPS service"
        if output_dir == None:
            output_dir = self.output_dir
        wps_input = [
            ('taskArg',
             "project='{}'&amp;model='{}'".format(self.task.project.name, \
                                                  self.task.modelwrappername)),
            ('dataitem',
             "path='%s'" % self.datapath),
            ('columns', "0-"),  # get the whole dataset
            ('vertical', "0"),  # TODO: think!
            ('includeSLD', "1"),
            ('threshold', "1e-15")  # TODO: add threshold support
        ]
        x = "{}".format(request_template)
        x = x.replace("TASKARG", wps_input[0][1])
        x = x.replace("DATAITEM", wps_input[1][1])
        x = x.replace("COLUMNS", wps_input[2][1])
        x = x.replace("THRESHOLD", wps_input[5][1])
        # wps_run = self.rodos.wps.execute('gs:JRodosGeopkgWPS',wps_input)
        req = Request(self.rodos.w["url"],
                      data=x.encode(),
                      headers=xml_headers)
        logger.debug("Execute WPS with values %s" % (str(wps_input)))
        response = urlopen(req)
        temp = tempfile.NamedTemporaryFile()  # 2
        gpkg_name = None
        sld_name = None
        try:
            resp_file = open(temp.name, "wb")
            resp_file.write(response.read())
            resp_file.close()
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            try:
                with zipfile.ZipFile(temp.name, 'r') as zip_ref:
                    zip_ref.extractall(output_dir)
                # extract name of gpkg and optionally the name of an sld
                for f in zip_ref.namelist():
                    if f.upper().endswith('GPKG'):
                        gpkg_name = f
                    elif f.upper().endswith('SLD'):
                        sld_name = f
            except zipfile.BadZipFile:
                logger.error("Something went wrong")
                os.rmdir(output_dir)
                raise RodosPyException(open(temp.name).read())
        finally:
            temp.close()
        self.filepath = output_dir
        return {'gpkg': gpkg_name, 'sld': sld_name}

    def envelope(self):
        "Get the bbox of data"
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(0)  # grid
        return layer.GetExtent()

    def data_extent(self, time_value=None):
        """
        Get min and max value and their lon/lat locations
        Returned as tuple [(min_value, (lon, lat), timestamp), (max_value, (lon, lat), timestamp)]
        Filter by time value is supported.
        """
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(2)  # view
        if time_value != None:
            epoch_time = int(time_value.timestamp())
            layer.SetAttributeFilter("Time={:d}".format(epoch_time))
        max_value = 0
        max_timestamp = None
        max_lon = None
        max_lat = None

        min_value = 1e99
        min_timestamp = None
        min_lon = None
        min_lat = None

        for feature in layer:
            value = feature.GetField("Value")
            if value > max_value:
                max_value = value
                max_geom_wkt = feature.GetGeometryRef().ExportToWkt()
                max_timestamp = feature.GetField("Time")
                if max_geom_wkt != None:
                    transform = osr.CoordinateTransformation(layer.GetSpatialRef(), wgs84_cs)
                    polygon = ogr.CreateGeometryFromWkt(max_geom_wkt)
                    # use point instead of polygon
                    point = polygon.PointOnSurface()
                    max_lon, max_lat, dummy = transform.TransformPoint(point.GetX(), point.GetY())
            if value < min_value:
                min_value = value
                min_geom_wkt = feature.GetGeometryRef().ExportToWkt()
                min_timestamp = feature.GetField("Time")
                if min_geom_wkt != None:
                    transform = osr.CoordinateTransformation(layer.GetSpatialRef(), wgs84_cs)
                    polygon = ogr.CreateGeometryFromWkt(min_geom_wkt)
                    # use point instead of polygon
                    point = polygon.PointOnSurface()
                    min_lon, min_lat, dummy = transform.TransformPoint(point.GetX(), point.GetY())
        if max_value > 0:
            max_timestamp = datetime.fromtimestamp(max_timestamp)
        if min_value < 1e99:
            min_timestamp = datetime.fromtimestamp(min_timestamp)
        return [(min_value, (min_lon, min_lat), min_timestamp), (max_value, (max_lon, max_lat), max_timestamp)]

    def max(self, time_value=None):
        """
        Get max value and its lon/lat location
        Filter by time value is supported.
        """
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(2)  # view
        if time_value != None:
            epoch_time = int(time_value.timestamp())
            layer.SetAttributeFilter("Time={:d}".format(epoch_time))
        max_value = 0
        geom_wkt = None
        timestamp = None
        for feature in layer:
            value = feature.GetField("Value")
            if value > max_value:
                max_value = value
                geom_wkt = feature.GetGeometryRef().ExportToWkt()
                timestamp = feature.GetField("Time")
        if geom_wkt != None:
            transform = osr.CoordinateTransformation(layer.GetSpatialRef(), wgs84_cs)
            polygon = ogr.CreateGeometryFromWkt(geom_wkt)
            # use point instead of polygon
            point = polygon.PointOnSurface()
            lon, lat, dummy = transform.TransformPoint(point.GetX(), point.GetY())
        else:
            lon, lat = None, None
        if max_value > 0:
            timestamp = datetime.fromtimestamp(timestamp)
        return (max_value, (lon, lat), timestamp)

    def areaExceeding(self, value, time_value):
        "calculate area where value is exceeded"
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(2)  # view
        if time_value != None:
            epoch_time = int(time_value.timestamp())
            layer.SetAttributeFilter("Time={:d}".format(epoch_time))
        layer.SetAttributeFilter("Value > %f" % value)
        area = 0
        for feature in layer:
            area += feature.GetGeometryRef().GetArea()
        return area

    def timeSeries(self, lon, lat):
        "extract time series in singe point"
        times = self.times
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(lon, lat)
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(0)  # grid
        transform = osr.CoordinateTransformation(wgs84_cs, layer.GetSpatialRef())
        point.Transform(transform)
        found = False
        for feature in layer:
            data_geom = feature.GetGeometryRef()
            if data_geom.Intersects(point):
                cell = float(feature.GetField("Cell"))
                found = True
                break
        if not found:
            return None
        layer = gis_data.GetLayer(2)  # view
        layer.SetAttributeFilter("cell={:d}".format(int(cell)))
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
        return {"times": list(map(datetime.fromtimestamp, x)),
                "values": y,
                "unit": self.unit,
                "title": "{} at point ({},{})".format(self.name,
                                                      "{0:.3f}".format(lon),
                                                      "{0:.3f}".format(lat))
                }

    def getBbox(self):
        "Get bounding box of data"
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(0)  # grid
        e = layer.GetExtent()
        return (e[0], e[2], e[1], e[3])

    def getLonLatBoundaries(self):
        "get data boundaries"
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(0)  # grid
        e = layer.GetExtent()
        transform = osr.CoordinateTransformation(layer.GetSpatialRef(), wgs84_cs)
        ll = ogr.Geometry(ogr.wkbPoint)
        ll.AddPoint(e[0], e[2])
        ur = ogr.Geometry(ogr.wkbPoint)
        ur.AddPoint(e[1], e[3])
        ll.Transform(transform)
        ur.Transform(transform)
        return (ll.GetX(), ll.GetY(), ur.GetX(), ur.GetY())

    def getCentroid(self):
        "Get data bounding box centroid"
        bbox = self.getBbox()
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(bbox[0], bbox[1])
        ring.AddPoint(bbox[0], bbox[3])
        ring.AddPoint(bbox[2], bbox[3])
        ring.AddPoint(bbox[2], bbox[1])
        ring.AddPoint(bbox[0], bbox[1])
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.addGeometry(ring)
        return polygon.Centroid()

    def maxAtDistance(self, center_lon, center_lat, distance_in_km):
        "get maximum value in the distance of X meters. Center must be given also."
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(2)  # view
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(center_lon, center_lat)
        transform = osr.CoordinateTransformation(wgs84_cs, layer.GetSpatialRef())
        point.Transform(transform)
        x = point.GetX()
        y = point.GetY()
        ring = ogr.Geometry(ogr.wkbLineString)
        for i in range(0, 720):  # circle line forms of 720 points
            x_coord = x + (n.cos(n.radians(i / 2.0)) * distance_in_km / 2.0 * 1000 * 2)
            y_coord = y + (n.sin(n.radians(i / 2.0)) * distance_in_km / 2.0 * 1000 * 2)
            ring.AddPoint(x_coord, y_coord)
        values = []
        for feature in layer:
            data_geom = feature.GetGeometryRef()
            if data_geom.Intersects(ring):
                values.append(feature.GetField("Value"))
        if values == []:
            return None
        else:
            return max(values)

    def save_as_shapefile(self, output_dir=None, file_prefix="out", timestamp=None):
        "Save as shape file. Can be used in map plotting etc"
        gis_data = gpkg_driver.Open(self.gpkg_file())
        layer = gis_data.GetLayer(2)  # view
        if timestamp != None:
            epoch_time = int(timestamp.timestamp())
            layer.SetAttributeFilter("Time={:d}".format(epoch_time))
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        shapefile_path = "{}/{}.shp".format(
            output_dir, file_prefix)
        data_source = shapefile_driver.CreateDataSource(shapefile_path)
        srs = layer.GetSpatialRef()
        shapefile_layer = data_source.CreateLayer("jrodosexport", wgs84_cs, ogr.wkbPolygon)
        fields = (
            ("fid", ogr.OFTInteger64),
            ("Cell", ogr.OFTInteger64),
            ("Time", ogr.OFTInteger64),
            ("Value", ogr.OFTReal)
        )

        for f in fields:
            field_def = ogr.FieldDefn(f[0], f[1])
            shapefile_layer.CreateField(field_def)

        transform = osr.CoordinateTransformation(layer.GetSpatialRef(), wgs84_cs)
        for feature in layer:
            geom = feature.GetGeometryRef()
            geom.Transform(transform)
            shapefile_layer.CreateFeature(feature)
        data_source = None
        return shapefile_path
