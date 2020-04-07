from scenarioreporter import models
#from scenarioreporter.views.default import my_view
from scenarioreporter.views.notfound import notfound_view
from pyramid.renderers import render


# def test_my_view_failure(app_request):
#     info = my_view(app_request)
#     assert info.status_int == 500
#
# def test_my_view_success(app_request, dbsession):
#     model = models.MyModel(name='one', value=55)
#     dbsession.add(model)
#     dbsession.flush()
#
#     info = my_view(app_request)
#     assert app_request.response.status_int == 200
#     assert info['one'].name == 'one'
#     assert info['project'] == 'scenarioreporter'

def test_notfound_view(app_request):
    info = notfound_view(app_request)
    assert app_request.response.status_int == 404
    assert info == {}

# pytest --capture=no tests/test_views.py
def test_mapserver_map(app_request):
    # https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/templates.html
    result = render('scenarioreporter:templates/mapserver.map.jinja2',
                    {'mapname': 'mapname',
                     'layername': 'layername',
                     'timeextentstart': '2019-09-01T06:00:00.000Z',
                     'timeextentend': '2019-09-02T06:00:00.000Z',
                     'gpkgname': 'gpkgname.gpkg',
                     'bar': 2
                     },
                    request=app_request)
    print(result)
    assert True
