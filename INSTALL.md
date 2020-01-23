
# JRODOS Python module installation

## Ubuntu 16/18 Python virtual environment

Below is briefly described the installation for Ubuntu under Python3 virtual environment. Probably this also applies for Debian. For other Linux distros you have to at least replace apt commands.

### Required 

* Clone repository `git clone https://github.com/StukFi/rodospy.git'
* ´cd rodospy´
* Create virtual enviroment ´python3 -m venv venv´
* Activate it ´source venv/bin/activate´
* Install "easy" depencencies ´pip install wheel numpy python-dateutil owslib´
* Install GDAL build dependencies ´sudo apt install libgdal-dev python3-dev gdal-bin´
* Check GDAL version using command ´gdalinfo´
* Set necessary env variables:
´´´
export CPLUS_INCLUDE_PATH=/usr/include/gdal

export C_INCLUDE_PATH=/usr/include/gdal
´´´
* Install correspondent version using pip, probably ´pip install GDAL==2.2.3´

### Optional

* Some examples depend on matplotlib and mpl basemap
* Install matplotlib  ´pip install matplotlib´
* Install basemap ´pip install git+https://github.com/matplotlib/basemap.git´

