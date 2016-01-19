# -*- coding: utf-8 -*-

import peewee
import logging
import datetime
from importlib import import_module

from .parameter import Param
from .utility import class_name_to_api_name, get_cls_with_path, iterate_package

log = logging.getLogger(__name__)


def curd_setup(app, config):
    if config.get('databases'):
        setup_database(config['databases'])

    # configure flask app
    setup_app(app, config)

    # parameter types
    parameter_types(app, config['app']['parameter_types'])

    # configure view
    setup_view(app, config['app']['view_packages'])


db_classes = {
    'mysql': peewee.MySQLDatabase,
    'pgsql': peewee.PostgresqlDatabase,
    'sqlite': peewee.SqliteDatabase
}
db = {}


def setup_database(config):
    """Configure database.

     cannot import view and model before call this function

    :param config: database's config
    :type  config: dict
    """
    global db
    for database in config:
        db[database['key']] = db_classes[database['type']](**config[0]['params'])
    # set default db
    peewee.Model._meta.database = db.get('default') or db[0]


# configure flask (app.config) defined in app section at project.yml
def setup_app(app, config):
    """Configure flask app.

    :param app: Flask app object
    :param config: api's config
    :type  config: dict
    """

    flask_config = config.get('flask') or {}
    for key, value in flask_config.items():
        # set the expiration date of a permanent session.
        if key == 'PERMANENT_SESSION_LIFETIME':
            app.config[key] = datetime.timedelta(days=int(value))
        else:
            app.config[key] = value

    app_config = config.get('app') or {}
    for key, value in app_config.items():
        app.config[key] = value

    app.config['plugins'] = app.config.get('plugins') or {}
    for name, config in app.config['plugins'].items():
        plugin_class = get_cls_with_path(config.pop('class'))
        plugin = plugin_class(config)
        app.config['plugins'][name] = plugin

    default_class_sign = ''
    app.config['responses'] = app.config.get('responses') or {}
    for name, class_path in app.config['responses'].items():
        if name == 'default':
            default_class_sign = class_path
        else:
            response_class = get_cls_with_path(class_path)
            app.config['responses'][name] = response_class
    app.config['responses']['default'] = app.config['responses'][default_class_sign]


def parameter_types(app, config):
    types = {}
    for package_name in config:
        exec('import %s as package' % package_name)
        parameter_package = locals()['package']
        for item in dir(parameter_package):
            # flask's request and session(werkzeug.local.LocalProxy) raise RuntimeError
            if item in ['request', 'session']:
                continue
            parameter = getattr(parameter_package, item)
            try:
                if issubclass(parameter, Param):
                    if parameter.__name__ not in types:
                        types[parameter.__name__] = parameter

            except TypeError:
                pass    # Some object throw TypeError in issubclass
    app.config['parameter_types'] = types


# setup view url rule
def setup_view(app, config):
    """Configure view

    url route configure.

    :param app: Flask app object
    :param config: view's config
    :type  config: dict
    """
    from .view import CView

    for package_path in config:
        iterate_package(import_module(package_path))

    for view in CView.__subclasses__():
        name = class_name_to_api_name(view.__name__)
        uri = '/%s/%s' % (package_path, name)
        endpoint = '%s.%s' % (package_path, name)
        app.add_url_rule(uri, view_func=view.as_view(endpoint, uri, app))
