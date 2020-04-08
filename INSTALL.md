
# JRODOS Python module installation

## Ubuntu 16/18 Python virtual environment
## Debian Testing virtual environment
## Centos virtual environment

Below is briefly described the installation for Ubuntu under Python3 virtual environment. Probably this also applies for Debian. For other Linux distros you have to at least replace apt commands.

### Required 

* Clone repository `git clone https://github.com/StukFi/rodospy.git`
* `cd rodospy`
* Create virtual enviroment `python3 -m venv venv`
* Activate it `source venv/bin/activate`
* Install "easy" depencencies 
    - `pip install wheel numpy python-dateutil owslib` 
* Install GDAL build dependencies 
    - `sudo apt install libgdal-dev python3-dev gdal-bin`  # on Debian/Ubuntu
    - `sudo yum install gdal gdal-devel python3-devel`  # CentOS7
* Check GDAL version using command `gdalinfo --version`
* Set necessary env variables:
```
export CPLUS_INCLUDE_PATH=/usr/include/gdal

export C_INCLUDE_PATH=/usr/include/gdal
```
* Install correspondent version using pip:
    - `pip install GDAL==2.2.3` # Ubuntu 16/18
    - `pip install GDAL==3.0.4` # Debian Testing/Bullseye
    - `pip install GDAL==2.2.4` # Centos7 (self compiled GDAL and mapserver)

### Optional

* Some examples depend on matplotlib and mpl basemap
* Install matplotlib  `pip install matplotlib`
* Install basemap `pip install git+https://github.com/matplotlib/basemap.git`


## Scenario reporter

Heavily based on: https://docs.pylonsproject.org/projects/pyramid/en/latest/tutorials/wiki2/

Development using PyCharmCE (Free Community Edition)

See: https://docs.pylonsproject.org/projects/pyramid-cookbook/en/latest/development_tools/pycharm.html#using-pycharm


* `cd src/`

* `pip install -e ".[testing]"`

From wiki docs:

    # Generate your first revision.
    env/bin/alembic -c development.ini revision --autogenerate -m "init"
    # Upgrade to that revision.
    env/bin/alembic -c development.ini upgrade head
    # Load default data.
    env/bin/initialize_scenarioreporter_db development.ini


Run project `pserve development.ini`

Development with PycharmCE from root dir

https://trac.osgeo.org/gdal/wiki/BuildingOnUnixGDAL25dev
https://trac.osgeo.org/gdal/wiki/BuildingOnUnix

yum install libsqlite3x-devel libsqlite3x automake libtool proj-epsg




