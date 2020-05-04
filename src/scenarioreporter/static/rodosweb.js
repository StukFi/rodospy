// Shorthand for $( document ).ready()
function create_map_here(mapprops) {

    var MAP_DIV = 'map_'+mapprops.div;
    var MAP_FILE = mapprops.map_file;
    var WMS_SERVER_URL = mapprops.wms_server_url;
    var PROGNOSIS_START = mapprops.prognosis_start;
    var PROGNOSIS_END = mapprops.prognosis_end;
    var TIMESTEP_PERIOD = mapprops.timestep_period;
    var SLD_URL = '';
    if(typeof(mapprops.sld_url) !== "undefined"){
        SLD_URL = mapprops.sld_url;
    }

    // show the datapath, if defined
    if (mapprops.datapath){
        document.getElementById('datapath_'+mapprops.div).innerHTML = mapprops.datapath;
    }
    if (mapprops.map_file){
        document.getElementById('path_'+mapprops.div).innerHTML = 'cd /var/www/mapserver/'+mapprops.map_file.replace('/mapserver.map','');
    }
    var map = L.map(MAP_DIV, {});
    L.control.scale({position: 'topright', imperial: false, maxWidth: 200}).addTo(map);
    //L.control.mousePosition().addTo(map);

    // Reference layers, epsg:3857 == default Leaflet
    // OSM
    /*L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);*/
    // CALNET WMS
    var GEOSERVER_WMS = 'http://wms.cal-net.nl/geoserver/wms/';
    L.tileLayer.wms(
        GEOSERVER_WMS,
        {
          layers: 'rivm:OSM',
          attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
    // NPP's / Centrales
    L.tileLayer.wms(
        GEOSERVER_WMS,
        {
          layers: 'rivm:npp',
          attribution: '&copy; RIVM',
          transparent: 'true',
          format: 'image/png',
          //opacity: 1.0
        }).addTo(map);

    var layers = 'jrodoslayer';
    var styles = '';
    var WMS_TIME_SERVER = WMS_SERVER_URL+MAP_FILE;
    var wms_options = {
        layers: layers,
        styles: styles,
        format: 'image/png',
        transparent: true,
        attribution: 'RIVM',
        version: '1.3.0',
    }
    var legend_url = WMS_TIME_SERVER + '&version=1.1.1&service=WMS&request=GetLegendGraphic&format=image%2Fpng&layer=' +
        layers+'&style=' + styles +
        '&legend_options=fontName:Arial;fontAntiAliasing:true;fontColor:0x000033;fontSize:10;bgColor:0xEEEEEE;labelMargin:30';
    //console.log(legend_url);
    // TODO make this optional as sometimes there is no SLD (TODO 2: create one on the fly...)
    if (SLD_URL.length > 0){
        wms_options.SLD = SLD_URL;
        legend_url += '&SLD='+SLD_URL
    }
    var legend = L.wmsLegend(legend_url)
    legend.addTo(map);
    var wmsLayer = L.nonTiledLayer.wms(WMS_TIME_SERVER, wms_options);

    var timeDimension = new L.TimeDimension({
      timeInterval: PROGNOSIS_START+'/'+PROGNOSIS_END,  // '2019-09-02T05:00:00.000000Z/2019-09-02T06:00:00.000000Z'
      period: TIMESTEP_PERIOD, //'PT60M', // "PT10M",
      // validTimeRange: "00:00/24:00",
      // lowerLimitTime: "",
      // upperLimitTime: "",
      currentTime: new Date(PROGNOSIS_END), // new Date("2018-09-04T07:00:00Z")
    });
    var player = new L.TimeDimension.Player({
        transitionTime: 500,
        buffer: 0,
        loop: false,
        startOver: false
      },
      timeDimension
    );
    var timeDimensionControlOptions = {
        player:          player,
        timeDimension:   timeDimension,
        position:        'bottomleft',
        title:           'Time Control',
        backwardButton:  true,
        forwardButton:   true,
        autoPlay:        true,
        loopButton:      false,
        timeSteps:       1,
        playReverseButton: false,
        limitSliders:    false,
        speedSlider:     false,
        //minSpeed:      1,
        //speedStep:     0.5,
        //maxSpeed:      15,
        timeSliderDragUpdate: true,
        timeZones: ['Local', 'CET', 'UTC']
    };
    var timeDimensionControl = new L.Control.TimeDimension(timeDimensionControlOptions);
    map.addControl(timeDimensionControl);

    var tdWmsLayer = L.timeDimension.layer.wms(wmsLayer,
        {
            // either create a timeDimension object and use it:
            timeDimension: timeDimension

            // OR
            // use the getCapabilities of Geoserver
            // IMPORTANT: ONLY working if Geoserver is started with
            // -Dorg.geotools.shapefile.datetime=true
            // (else in case of a dataset which has time (instead of date only)
            // dimensions will not work because there will be no 'PT10M'
            // you should see:
            // 2018-11-12T00:00:00.000Z/2018-11-12T00:00:00.000Z/PT10M
            // cannot make this work with mapserver
            /*
            requestTimeFromCapabilities: true,
            updateTimeDimension: true,
            updateTimeDimensionMode: 'intersect'
            */
        }
    );
    tdWmsLayer.addTo(map);

    map.flyTo({lon:4.85, lat:51.70}, 8, {animate: false});

    // Add an event handler for the map "click" event
    // maybe to be able to retrieve all (time)values of one cell, to be able to
    // draw a time/value graph?
    map.on('click', function(e) {

      // Build the URL for a GetFeatureInfo
      var url = getFeatureInfoUrl(
                      map,
                      layers,
                      e.latlng,
                      {
                          'info_format': 'application/json',
                          //'propertyName': 'NAME,AREA_CODE,DESCRIPTIO'
                      }
                  );
      console.log(url)
      // Send the request and create a popup showing the response
      /*
      // https://javascript.info/fetch  ??
      request({
          url: url,
          type: 'json',
      }).then(function (data) {
          var feature = data.features[0];
          L.popup()
          .setLatLng(e.latlng)
          .setContent(L.Util.template("<h2>{NAME}</h2><p>{DESCRIPTIO}</p>", feature.properties))
          .openOn(map);
      });
      */
    });

    /**
     * Return the WMS GetFeatureInfo URL for the passed map, layer and coordinate.
     * Specific parameters can be passed as params which will override the
     * calculated parameters of the same name.
     */
    function getFeatureInfoUrl(map, layer, latlng, params) {

      var point = map.latLngToContainerPoint(latlng, map.getZoom()),
          size = map.getSize(),
          bounds = map.getBounds(),
          sw = bounds.getSouthWest(),
          ne = bounds.getNorthEast() ;
          //,
          //sw = crs.projection._proj.forward([sw.lng, sw.lat]),
          //ne = crs.projection._proj.forward([ne.lng, ne.lat]);

      var defaultParams = {
          request: 'GetFeatureInfo',
          service: 'WMS',
          crs: 'EPSG:4326',
          styles: '',
          version: '1.3.0',
          bbox: sw.lat+','+sw.lng+','+ne.lat+','+ne.lng, //[sw.join(','), ne.join(',')].join(','),
          height: size.y,
          width: size.x,
          layers: layers,
          query_layers: layers,
          info_format: 'geojson'
      };

      params = L.Util.extend(defaultParams, params || {});

      // not sure why, but I really have to SET it again:
      params['info_format'] = 'geojson';
      // AND if you want all features under your x,y you need:
      params['feature_count'] = '100';  // TODO: check if this is enough... or dynamicaly set it based on number of modelsteps


      params[params.version === '1.3.0' ? 'i' : 'x'] = point.x;
      params[params.version === '1.3.0' ? 'j' : 'y'] = point.y;

      var url = WMS_TIME_SERVER + L.Util.getParamString(params, WMS_TIME_SERVER, true);
      console.log(url);
      return url;
    }

}