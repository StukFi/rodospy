from pyramid.compat import escape
import re
from docutils.core import publish_parts

from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    )

from pyramid.view import view_config

from pyramid.renderers import render

from xml.dom.minidom import parse, getDOMImplementation

from rodospy import rodospy
from rodospy import settings
from datetime import datetime, timedelta
import os
import json

from .. import models

@view_config(route_name='scenarios', renderer='../templates/scenarios.jinja2')
def scenarios(request):
    scenarios = request.dbsession.query(models.Scenario)  # TODO sort by ??
    return dict(scenarios=scenarios)

@view_config(route_name='scenario', renderer='../templates/scenario.jinja2')
def scenario(request):
    scenario_id = request.matchdict['id']
    scenario = request.dbsession.query(models.Scenario).filter_by(id=scenario_id).first()
    if not scenario:
        raise HTTPNotFound('No such scenario: "{}"'.format(scenario_id))
    items = request.dbsession.query(models.Item).filter_by(scenario_id=scenario_id).order_by(models.Item.previous).all()  # all() returns as List
    item_dict = {x.id: x for x in items}
    # find start item
    sorted_items = []
    for item in items:
        if item.previous == -1:
            # start item!
            sorted_items.append(item)
            break
    # create the lineup
    for i in range(1, len(items)):
        sorted_items.append(item_dict[sorted_items[-1].next])
    return dict(scenario=scenario, items=sorted_items)

def getText(nodelist):
    """
    Util function to get the text from a nodelist (to get xml data)
    :param nodelist:
    :return:
    """
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def fix_and_save_sld(sld_path, new_sld_path):
    dom = parse(sld_path)
    cssparam_elements = dom.getElementsByTagName('CssParameter')
    # remove Literal Elements and set value from it to CssParameter
    # https://mapserver.org/development/rfc/ms-rfc-124.html Currently, MapServer only supports raw constants in <CssParameter> or <SvgParameter> tags, e.g.:
    for css in cssparam_elements:
        literal_elements = css.getElementsByTagName('Literal')
        for lit in literal_elements:
            value = getText(lit.childNodes)
            css.removeChild(lit)
            v = dom.createTextNode(value)
            css.appendChild(v)

    impl = getDOMImplementation()
    newdom = impl.createDocument(None, "StyledLayerDescriptor", None)
    namedLayer = newdom.createElement('NamedLayer')
    name = newdom.createElement('Name')
    n = newdom.createTextNode('jrodoslayer')  # <== YOU REALLY HAVE TO GIVE IT THE SAME NAME AS YOUR LAYER!
    newdom.childNodes[0].appendChild(namedLayer).appendChild(name).appendChild(n)
    namedLayer.appendChild(dom.childNodes[0])

    #print(newdom.toprettyxml(indent='  '))
    # directory will not be there yet, probably:
    # https://stackoverflow.com/questions/12517451/automatically-creating-directories-with-file-output
    if not os.path.exists(os.path.dirname(new_sld_path)):
        try:
            os.makedirs(os.path.dirname(new_sld_path))
        except OSError:  # Guard against race condition
            raise
    f = open(new_sld_path, 'w')
    newdom.writexml(f, indent='  ', addindent='  ', newl='\n')
    f.close()

@view_config(route_name='scenario_new', renderer='../templates/scenario.jinja2')
def scenario_new(request):
    ''' Show the model end points so the user can select one (for now) to save a first version '''
    project_url = request.params['project_url']
    datapath = request.params['datapath']
    task_name = request.params['task']
    project = get_project_via_rest(project_url)
    result = 'NOT OK'
    file = '-'

    for task in project.tasks:
        # is gridserie.datapath unique per task or overall ????
        for gridserie in task.gridseries:
            if datapath == gridserie.datapath and task_name == task.modelwrappername:

                # some modelchainnames have plus-signs in their name... remove them
                modelchainname = project.modelchainname.replace('+', '_')

                scenario_dir = '{}_{}_{}_{}'.format(datetime.now().strftime("%Y%m%d%H%M%f"), task_name,
                                                     project.projectId, modelchainname)
                file_names = gridserie.save_gpkg(output_dir=settings.rodospy_settings['wps']['file_storage']+os.path.sep+scenario_dir)

                # create a mapserver mapfile in the same dir
                # https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/templates.html
                # TODO check if prognosis params are really in seconds (s)
                prognosis_end = project.startOfPrognosis+timedelta(seconds=project.durationOfPrognosis)
                mapfile_content = render('scenarioreporter:templates/mapserver.map.jinja2',
                                {'mapname': project.name,
                                 'layername': 'jrodoslayer',
                                 'prognosis_start': project.startOfPrognosis.isoformat(), # prognosis start (not the release) ??
                                 'prognosis_end': prognosis_end.isoformat(),  # calculated prognosis end
                                 'gpkgname': file_names['gpkg']
                                 },
                                request=request)
                mapfile = open('{}/mapserver.map'.format(settings.rodospy_settings['wps']['file_storage']+os.path.sep+scenario_dir), 'w')
                mapfile.write(mapfile_content)
                mapfile.close()

                if file_names['sld']:
                    old_sld = '{}{}{}{}{}'.format(settings.rodospy_settings['wps']['file_storage'], os.path.sep, scenario_dir, os.path.sep, file_names['sld'])
                    new_sld = '{}{}{}{}{}'.format(settings.rodospy_settings['wps']['sld_storage'], os.path.sep, scenario_dir, os.path.sep, 'jrodos.sld')
                    fix_and_save_sld(old_sld, new_sld)

                # TODO get current editor from ... session?
                editor = request.dbsession.query(models.User).filter_by(id=1).first()
                scenario = models.Scenario(
                    name='name',
                    data='data',
                    creator=editor,
                )
                request.dbsession.add(scenario)
                # flush to be able to get the scenario.id
                request.dbsession.flush()
                scenario_id = scenario.id
                scenario.name = "Scenario created {} based on '{}' ({}) " \
                    .format(datetime.now().strftime("%d/%m/%y %H:%M"), project.name, project.projectId)

                scenario_data = []
                scenario_data.append('<ul>')
                scenario_data.append('<li> name: {} </li>'.format(project.name))
                scenario_data.append('<li> projectId: {}</li>'.format(project.projectId))
                scenario_data.append('<li> username: {}</li>'.format(project.username))
                scenario_data.append('<li> description: {}</li>'.format(project.description))
                scenario_data.append('<li> timestepOfPrognosis: {}</li>'.format(project.timestepOfPrognosis))
                scenario_data.append('<li> timestepOfPronosisUnit: {}</li>'.format(project.timestepOfPronosisUnit))
                scenario_data.append('<li> durationOfPrognosis: {}</li>'.format(project.durationOfPrognosis))
                scenario_data.append('<li> durationOfPronosisUnit: {}</li>'.format(project.durationOfPronosisUnit))
                scenario_data.append('<li> modelchainname: {}</li>'.format(project.modelchainname))
                # pointer to rodos connection... not to be shown
                # scenario_data.append('<li> rodos: {}</li>'.format(project.rodos))
                scenario_data.append('<li> sourcetermNuclides: {}</li>'.format(project.sourcetermNuclides))
                scenario_data.append('<li> startOfPrognosis: {}</li>'.format(project.startOfPrognosis))
                scenario_data.append('<li> startOfRelease: {}</li>'.format(project.startOfRelease))
                scenario_data.append('<li> systemOperationMode: {}</li>'.format(project.systemOperationMode))
                #scenario_data.append('<li> tasks: {}</li>'.format(project.tasks))
                #scenario_data.append('<li> uid: {}</li>'.format(project.uid))
                scenario_data.append('<li> weatherProvider: {}</li>'.format(project.weatherProvider))
                scenario_data.append('<li> links: {}</li>'.format(project.links[0]['href']))
                scenario_data.append('<li> dateTimeCreated: {}</li>'.format(project.dateTimeCreated))
                scenario_data.append('<li> dateTimeModified: {}</li>'.format(project.dateTimeModified))
                scenario_data.append('</ul>')
                scenario.data = ''.join(scenario_data)

                # adding TEXT item
                text_item = models.Item(
                    name='name',
                    scenario_id=scenario_id,
                    data='',
                    next=-1,
                    previous=-1,
                    creator=editor,
                )
                request.dbsession.add(text_item)

                # adding MAP item
                map_item = models.Item(
                    name='map',
                    scenario_id=scenario_id,
                    data='',
                    next=-1,
                    previous=-1,
                    creator=editor,
                )
                request.dbsession.add(map_item)

                # flush to be able to get the item.id's
                request.dbsession.flush()
                text_item_id = text_item.id
                map_item_id = map_item.id
                text_item.name = "This is name of item {}".format(text_item_id)
                text_item.data = "This is data of item {} <br/> {} <br/> {} <br/> {}".format(text_item_id, project_url, datapath, file)
                text_item.next = map_item_id
                map_item.previous = text_item_id
                map_data = {'div': map_item_id,
                            'wms_server_url': settings.rodospy_settings['wps']['wms_server_url'],
                            'map_file': '{}/mapserver.map'.format(scenario_dir),
                            'prognosis_start': project.startOfPrognosis.isoformat(),
                            'prognosis_end': prognosis_end.isoformat(),
                            'timestep_period': 'PT{}{}'.format(project.timestepOfPrognosis, project.durationOfPronosisUnit.upper()), # 'PT3600S' or 'PT60M'
                            'sld_url': settings.rodospy_settings['wps']['sld_base_url']+'/'+scenario_dir+'/jrodos.sld'}
                map_item.data = json.dumps(map_data)
                scenario_url = request.route_url('scenario', id=scenario_id)
                return HTTPFound(location=scenario_url)

@view_config(route_name='item', renderer='../templates/item.jinja2')
def item(request):
    item_id = request.matchdict['id']
    item = request.dbsession.query(models.Item).filter_by(id=item_id).first()
    scenario = request.dbsession.query(models.Scenario).filter_by(id=item.scenario_id).first()
    return dict(scenario=scenario, item=item)

@view_config(route_name='item_edit', renderer='../templates/item.jinja2')
def item_edit(request):
    item_id = request.matchdict['id']
    item = request.dbsession.query(models.Item).filter_by(id=item_id).first()
    scenario = request.dbsession.query(models.Scenario).filter_by(id=item.scenario_id).first()

    if 'form.submitted' in request.params:
        if request.params['form.submitted'] == 'Cancel-Edit-GoTo-Scenario':
            scenario_url = request.route_url('scenario', id=scenario.id)
            return HTTPFound(location=scenario_url)
        # else: save data
        item.data = request.params['body']
        if request.params['form.submitted'] == 'Save-Item':
            next_url = request.route_url('item', id=item.id)
            return HTTPFound(location=next_url)
        elif request.params['form.submitted'] == 'Save-Item-GoTo-Scenario':
            scenario_url = request.route_url('scenario', id=scenario.id)
            return HTTPFound(location=scenario_url)

    return dict(scenario=scenario, item=item, edit=True)

@view_config(route_name='item_down', renderer='../templates/scenario.jinja2')
def item_down(request):
    item_id = request.matchdict['id']
    this_item = request.dbsession.query(models.Item).filter_by(id=item_id).first()
    if this_item.next >= 0:  # last one has -1
        next_item = request.dbsession.query(models.Item).filter_by(id=this_item.next).first()
        # only if next item HAS a next one: change previous pointer to this id
        if next_item.next >= 0:
            next_next_item = request.dbsession.query(models.Item).filter_by(id=next_item.next).first()
            next_next_item.previous = this_item.id
        # only if this item as a previous one: change next pointer to new next
        if this_item.previous >= 0:
            previous_item = request.dbsession.query(models.Item).filter_by(id=this_item.previous).first()
            previous_item.next = next_item.id
        # ORDER OF THESE LINES MATTER!
        this_item.next = next_item.next
        next_item.next = this_item.id
        next_item.previous = this_item.previous
        this_item.previous = next_item.id
    scenario = request.dbsession.query(models.Scenario).filter_by(id=this_item.scenario_id).first()
    scenario_url = request.route_url('scenario', id=scenario.id)
    return HTTPFound(location=scenario_url)

@view_config(route_name='item_up', renderer='../templates/scenario.jinja2')
def item_up(request):
    item_id = request.matchdict['id']
    this_item = request.dbsession.query(models.Item).filter_by(id=item_id).first()
    if this_item.previous >= 0:  # first one has -1, so ignore
        previous_item = request.dbsession.query(models.Item).filter_by(id=this_item.previous).first()
        # only if the previous item as a previous one
        if previous_item.previous >= 0:
            previous_previous_item = request.dbsession.query(models.Item).filter_by(id=previous_item.previous).first()
            previous_previous_item.next = this_item.id
        # only if this was not the last one
        if this_item.next >= 0:
            next_item = request.dbsession.query(models.Item).filter_by(id=this_item.next).first()
            next_item.previous = previous_item.id
        # ORDER OF THESE LINES MATTER!
        this_item.previous = previous_item.previous
        previous_item.previous = this_item.id
        previous_item.next = this_item.next
        this_item.next = previous_item.id
    scenario = request.dbsession.query(models.Scenario).filter_by(id=this_item.scenario_id).first()
    scenario_url = request.route_url('scenario', id=scenario.id)
    return HTTPFound(location=scenario_url)

@view_config(route_name='item_new', renderer='../templates/scenario.jinja2')
def item_new(request):
    item_id = request.matchdict['id']
    previous_item = request.dbsession.query(models.Item).filter_by(id=item_id).first()
    # TODO ? request user from session ??
    editor = request.dbsession.query(models.User).filter_by(id=1).first()
    item = models.Item(
        name="NEW Item",
        scenario_id=previous_item.scenario_id,
        data="NEW Item Data",
        next=previous_item.next,
        previous=previous_item.id,
        creator=editor,
    )
    request.dbsession.add(item)
    request.dbsession.flush()  # we flush because we want to retrieve the id / primary key
    if previous_item.next >= 0:
        # meaning: after_items was NOT the last one; update the before_item
        before_item = request.dbsession.query(models.Item).filter_by(id=previous_item.next).first()
        before_item.previous = item.id
    previous_item.next = item.id
    item_url = request.route_url('item_edit', id=item.id)
    return HTTPFound(location=item_url)

# TODO confirmation and showing  again
@view_config(route_name='item_delete', renderer='../templates/item.jinja2')
def item_delete(request):
    item_id = request.matchdict['id']
    item = request.dbsession.query(models.Item).filter_by(id=item_id).first()
    # we have to fix the pointers of next and previous items (IF they are)
    if item.previous >= 0:
        previous_item = request.dbsession.query(models.Item).filter_by(id=item.previous).first()
        previous_item.next = item.next
    if item.next >= 0:
        next_item = request.dbsession.query(models.Item).filter_by(id=item.next).first()
        next_item.previous = item.previous
    request.dbsession.delete(item)
    scenario = request.dbsession.query(models.Scenario).filter_by(id=item.scenario_id).first()
    return dict(scenario=scenario, item=item)



# regular expression used to find WikiWords
# wikiwords = re.compile(r"\b([A-Z]\w+[A-Z]+\w+)")
#
# @view_config(route_name='view_wiki')
# def view_wiki(request):
#     next_url = request.route_url('view_page', pagename='FrontPage')
#     return HTTPFound(location=next_url)
#
# @view_config(route_name='view_page', renderer='../templates/scenario.jinja2')
# def view_page(request):
#     pagename = request.matchdict['pagename']
#     page = request.dbsession.query(models.Scenario).filter_by(name=pagename).first()
#     if page is None:
#         raise HTTPNotFound('No such page')
#
#     def add_link(match):
#         word = match.group(1)
#         exists = request.dbsession.query(models.Scenario).filter_by(name=word).all()
#         if exists:
#             view_url = request.route_url('view_page', pagename=word)
#             return '<a href="%s">%s</a>' % (view_url, escape(word))
#         else:
#             add_url = request.route_url('add_page', pagename=word)
#             return '<a href="%s">%s</a>' % (add_url, escape(word))
#
#     content = publish_parts(page.data, writer_name='html')['html_body']
#     content = wikiwords.sub(add_link, content)
#     edit_url = request.route_url('edit_page', pagename=page.name)
#     return dict(page=page, content=content, edit_url=edit_url)
#
# @view_config(route_name='edit_page', renderer='../templates/edit.jinja2')
# def edit_page(request):
#     pagename = request.matchdict['pagename']
#     page = request.dbsession.query(models.Scenario).filter_by(name=pagename).one()
#     if 'form.submitted' in request.params:
#         page.data = request.params['body']
#         next_url = request.route_url('view_page', pagename=page.name)
#         return HTTPFound(location=next_url)
#     return dict(
#         pagename=page.name,
#         pagedata=page.data,
#         save_url=request.route_url('edit_page', pagename=page.name),
#         )
#
# @view_config(route_name='add_page', renderer='../templates/edit.jinja2')
# def add_page(request):
#     pagename = request.matchdict['pagename']
#     if request.dbsession.query(models.Scenario).filter_by(name=pagename).count() > 0:
#         next_url = request.route_url('edit_page', pagename=pagename)
#         return HTTPFound(location=next_url)
#     if 'form.submitted' in request.params:
#         body = request.params['body']
#         page = models.Scenario(name=pagename, data=body)
#         page.creator = (
#             request.dbsession.query(models.User).filter_by(name='editor').one())
#         request.dbsession.add(page)
#         next_url = request.route_url('view_page', pagename=pagename)
#         return HTTPFound(location=next_url)
#     save_url = request.route_url('add_page', pagename=pagename)
#     return dict(pagename=pagename, pagedata='', save_url=save_url)


# JRodos Projects


@view_config(route_name='projects', renderer='../templates/projects.jinja2')
def projects(request):
    # rodospy_settings = {
    #     "wps": {
    #         # URL for Geoserver WPS service
    #         # it's enough to change host and port
    #         # "url": "http://localhost:8080/geoserver/wps",
    #         "url": "http://jrodos.dev.cal-net.nl/geoserver/wps",
    #         # Local storage of GeoPackage files, must be writeable
    #         # The directory will be created if it does not exist.
    #         "file_storage": "/tmp/jrodoswps"
    #     },
    #     "rest": {
    #         # TOMCAT rest service URL
    #         # "url": "http://geoserver.dev.cal-net.nl/jrodos-rest-1.2-SNAPSHOT/jrodos"
    #         "url": "http://jrodos.dev.cal-net.nl/rest-2.0/jrodos"
    #     }
    # }
    # create connection
    rodos = rodospy.RodosConnection(settings.rodospy_settings)
    # list projects available
    # filters can be used but they are not required
    # projects = rodos.projects_old( )
    # let's sort them on projectId to be able to show newest on top
    p = sorted(rodos.projects, key=lambda project: project.projectId, reverse=True)
    return {'projects': p}

# REST interface project url like
# http://jrodos.dev.cal-net.nl/rest-2.0/jrodos/projects/3149
def get_project_via_rest(rodos_rest_project_url):
    # rodospy_settings = {
    #     "wps": {
    #         # URL for Geoserver WPS service
    #         # it's enough to change host and port
    #         # "url": "http://localhost:8080/geoserver/wps",
    #         "url": "http://jrodos.dev.cal-net.nl/geoserver/wps",
    #         # Local storage of GeoPackage files, must be writeable
    #         # The directory will be created if it does not exist.
    #         "file_storage": "/tmp/jrodoswps"
    #     },
    #     "rest": {
    #         # TOMCAT rest service URL
    #         # "url": "http://geoserver.dev.cal-net.nl/jrodos-rest-1.2-SNAPSHOT/jrodos"
    #         "url": "http://jrodos.dev.cal-net.nl/rest-2.0/jrodos"
    #     }
    # }
    # create connection
    rodos = rodospy.RodosConnection(settings.rodospy_settings)
    p = rodospy.Project(None, {})
    p.rodos = rodos
    rodos_project = p.load(rodos_rest_project_url)
    return rodos_project

@view_config(route_name='grid_save', renderer='../templates/grid_save.jinja2')
def grid_save(request):

    # needed input:
    # project url or id (to be able to retrieve Tasks and GridSeries (again)
    # datapath to be able to run through Task/GridSeries to find the right GridSerie
    # call GridSeries.save_gpkg()

    project_url = request.params['project_url']
    datapath = request.params['datapath']
    task_name = request.params['task']
    project = get_project_via_rest(project_url)
    result = 'NOT OK'
    file = '-'

    for task in project.tasks:
        # is gridserie.datapath unique per task or overall ????
        for gridserie in task.gridseries:
            if datapath == gridserie.datapath and task_name == task.modelwrappername:
                final_dir = '{}{}{}_{}_{}_{}'.format(settings.rodospy_settings['wps']['file_storage'], os.path.sep,
                                                     datetime.now().strftime("%Y%m%d%H%M%f"), task_name,
                                                     project.projectId, project.modelchainname)
                file = gridserie.save_gpkg(output_dir=final_dir)
                result = 'OK'

    return {'result': result, 'project_url': project_url, 'datapath': datapath, 'file': file}

@view_config(route_name='project', renderer='../templates/project.jinja2')
def project(request):

    project = get_project_via_rest(request.params['project_url'])
    tasks_dataitems = []

    for task in project.tasks:
        # anytree is a simple way to create a Tree structure:
        # pip install anytree
        from anytree import AnyNode, RenderTree
        dataitems = {}
        dataitemtree = {}
        for item in task.dataitems:
            dataitems[item['dataitem_id']] = item

        # create a Tree of anytree-Anynodes
        dataitemtree[0] = AnyNode(id='Root', parent=None, dataitem=None)
        for i in sorted(
                dataitems.keys()):  # you really have to sort them because they come unordered from data !!
            if dataitems[i]['parent_dataitem_id'] is not None:
                #if 'Data for' in dataitems[i]['name']:
                    dataitemtree[i] = AnyNode(
                        id=dataitems[i]['name'],
                        parent=dataitemtree[dataitems[i]['parent_dataitem_id']],
                        dataitem=dataitems[i])
                #else:
                #    print(dataitems[i]['name'])
            else:
                dataitemtree[i] = AnyNode(id=dataitems[i]['name'], parent=None,
                                           dataitem=None)
        # mmm, pity, we cannot use anytree.RenderTree in Jinja2...
        # so cannot pass the actual Node's
        # we create a array of dataitems here
        dataitemnodes = []

        for pre, fill, node in RenderTree(dataitemtree[0]):
            unit = ''
            type = ''
            datapath = ''
            if node.dataitem is None:
                name = 'Root'
                node.dataitem = {'project': task.project.name}
            else:
                name = node.dataitem['name']
                type = node.dataitem['dataitem_type']
                datapath = node.dataitem['datapath']
                if node.dataitem['showunit']:
                    unit = '[{}]'.format(node.dataitem['unit'])
            print("{} {}{} {} {}".format(len(pre), pre, name, unit, type))
            #dataitemtreelines.append("{}{}{} {} {} - {}".format(fill, pre, name, unit, type, datapath))
            #dataitemtreelines.append("{}{} {} {} - {}".format(pre, name, unit, type, datapath))
            dataitemnodes.append((pre, node.dataitem))
        tasks_dataitems.append({'name':task.modelwrappername, 'description':task.description, 'dataitemnodes':dataitemnodes})
        #break  # every task in project contains ALL
    return {'project': project, 'tasks_dataitems': tasks_dataitems}


