rodospy_settings = {
    "wps": {
        # URL for Geoserver WPS service to retrieve JRodos runs etc
        # it's enough to change host and port
        # "url": "http://localhost:8080/geoserver/wps",
        "url": "http://jrodos.dev.cal-net.nl/geoserver/wps",
        # Local storage of GeoPackage files, must be writeable
        # The directory will be created if it does not exist.
        "file_storage": "/var/www/mapserver",
        # Local store of sld files, must be writable
        # Path will be extended with a 'scenario'-part (based on time etc)
        # Path should be part of webdir of a webserver so it can be retrieved over http
        "sld_storage": "/var/www/mapserver",
        # Base url to be used for the sld's (to be used by mapserver as custom sld)
        "sld_base_url": 'http://localhost/viewer',
        # FULL wms server url (mapfile-pathname will be appanded to this)
        # used in map items for WMS-T server
        "wms_server_url": 'http://localhost/mapserver/mapserv?map='
    },
    "rest": {
        # TOMCAT rest service URL
        # "url": "http://geoserver.dev.cal-net.nl/jrodos-rest-1.2-SNAPSHOT
        # /jrodos"
        "url": "http://jrodos.dev.cal-net.nl/rest-2.0/jrodos"
    }
}