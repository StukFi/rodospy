import argparse
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models


def setup_models(dbsession):
    """
    Add or update models / fixtures in the database.
    """

    """
    Create fresh users
    """
    editor = dbsession.query(models.User).filter_by(id=1).first()
    if not editor:
        editor = models.User(name='editor', role='editor')
        editor.set_password('editor')
        dbsession.add(editor)

    basic = dbsession.query(models.User).filter_by(id=2).first()
    if not basic:
        basic = models.User(name='basic', role='basic')
        basic.set_password('basic')
        dbsession.add(basic)

    """
    Retrieve 'editor'
    """
    scenario1 = dbsession.query(models.Scenario).filter_by(id=1).first()
    if not scenario1:
        scenario1 = models.Scenario(
            id=1,
            name='Scenario-1',
            data='This is Scenario 1',
            creator=editor,
        )
        dbsession.add(scenario1)

    item1 = dbsession.query(models.Item).filter_by(id=1).first()
    if not item1:
        item1 = models.Item(
            name="First Item",
            scenario_id=1,
            data="First Item Data",
            next=-1,
            previous=-1,
            creator=editor,
        )
        dbsession.add(item1)

    item1 = dbsession.query(models.Item).filter_by(id=1).first()
    item1.next = 2

    item2 = dbsession.query(models.Item).filter_by(id=2).first()
    if not item2:
        item2 = models.Item(
            name="Second Item",
            scenario_id=1,
            data="Second Item Data",
            next=3,
            previous=item1.id,
            creator=editor,
        )
        dbsession.add(item2)

    item3 = dbsession.query(models.Item).filter_by(id=3).first()
    if not item3:
        item3 = models.Item(
            name="Third Item",
            scenario_id=1,
            data="Third Item Data",
            next=4,
            previous=item2.id,
            creator=editor,
        )
        dbsession.add(item3)

    item4 = dbsession.query(models.Item).filter_by(id=4).first()
    if not item4:
        item4 = models.Item(
            name="Fourth Item",
            scenario_id=1,
            data="Fourth Item Data",
            next=-1,
            previous=item3.id,
            creator=editor,
        )
        dbsession.add(item4)


    scenario2 = dbsession.query(models.Scenario).filter_by(id=2).first()
    if not scenario2:
        scenario2 = models.Scenario(
            id=2,
            name='Scenario-2',
            data='This is Scenario 2',
            creator=editor,
        )
        dbsession.add(scenario2)

    item5 = dbsession.query(models.Item).filter_by(id=5).first()
    if not item5:
        item5 = models.Item(
            name="First Item of 2",
            scenario_id=2,
            data="First Item of 2",
            next=-1,
            previous=-1,
            creator=editor,
        )
        dbsession.add(item5)

def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., development.ini',
    )
    return parser.parse_args(argv[1:])


def main(argv=sys.argv):
    args = parse_args(argv)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)

    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            setup_models(dbsession)
    except OperationalError:
        print('''
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to initialize your database tables with `alembic`.
    Check your README.txt for description and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.
            ''')
