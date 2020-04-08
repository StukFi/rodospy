
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

    # note that the 'alembic' and 'initialize_scenarioreporter_db' are added to the bin PATH of your venv
    # if NOT in src dir:
    cd src
    # Generate your first revision.
    alembic -c development.ini revision --autogenerate -m "init"
    # Upgrade to that revision.
    alembic -c development.ini upgrade head
    # Load default data.
    initialize_scenarioreporter_db development.ini


Run project `pserve development.ini`

## Development with PycharmCE

Open project (at this moment the branch 'scenarioreporter') in PyCharmCE so you have src and venv (created as show above in the root dir)

Now SET the python interpreter for the project:
Go to project settings: File/Setting/Project: scenarioreporter
Point the 'Project Interpreter' to the venv/bin/python in the venv
If all goes ok, you will see all modules that you added earlier there in the list.

Now to be able to debug: in upper right corner of PycharmCE, click 'Add Configuration'

Create a NEW configuration by either clicking the plus sign or the Python template and then 'save configuration'

Fill in the right values: 
Name: pserve development
Script path: browse to the pserve binary in your venv/bin directory (FULL PATH)
Parameters: development.ini --reload
Working directory: browse to the src dir
Click OK
Debug by selecting this configuration and clicking the little 'bug' button
You should now point your browser to http://localhost:6543

Alternative (without debugging), is to type in the terminal-panel of Pycharm:
- `source venv/bin/activate` # to activate your virtual env AND make 'pserve' appear in your PATH
- `pserve development.ini --reload` 
You should now point your browser to http://localhost:6543 


## CentOS7

CentOS7 does NOT have a recent GDAL (not even in 'epel'), so compile/install GDAL first: 
https://trac.osgeo.org/gdal/wiki/BuildingOnUnix

Then compile Mapserver (to have it use the same GDAL)

yum install libsqlite3x-devel libsqlite3x automake libtool proj-epsg




