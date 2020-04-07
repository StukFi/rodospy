def includeme(config):
    # https://restfulapi.net/resource-naming/
    config.add_static_view('static', 'static', cache_max_age=3600)
    # ScenarioReporter Scenario's
    config.add_route('scenarios', '/')
    config.add_route('scenario_new', '/scenario/new')
    config.add_route('scenario', '/scenario/{id}')
    # Scenarion Items
    config.add_route('item_edit', '/item/{id}/edit')
    config.add_route('item_down', '/item/{id}/down')
    config.add_route('item_up', '/item/{id}/up')
    config.add_route('item_new', '/item/new/after/{id}')
    config.add_route('item_delete', '/item/delete/{id}')
    config.add_route('item', '/item/{id}')
    # JRodos Projects
    config.add_route('projects', '/projects')
    config.add_route('project', '/project')
    config.add_route('grid_save', '/grid_save')

    #config.add_route('view_wiki', '/')
    #config.add_route('view_page', '/{pagename}')
    #config.add_route('add_page', '/add_page/{pagename}')
    #config.add_route('edit_page', '/{pagename}/edit_page')

