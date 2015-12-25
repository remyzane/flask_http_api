# -*- coding: utf-8 -*-

import peewee
import logging
import pkgutil
import datetime

from .utility import class_name_to_api_name

log = logging.getLogger(__name__)


def curd_setup(app, config):
    if config.get('databases'):
        setup_database(config['databases'])

    # configure flask app
    setup_app(app, config)
    # configure view
    setup_view(app, config['view_packages'])


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
        class_path = config.pop('class')
        exec('from %s import %s as plugin' % tuple(class_path.rsplit('.', 1)))
        plugin_class = locals()['plugin']
        plugin_class.reconstruct(config)
        app.config['plugins'][name]['class'] = plugin_class


# 设置view
def setup_view(app, config):
    """Configure view

    url route configure.

    :param app: Flask app object
    :param config: view's config
    :type  config: dict
    """
    from .view import CView
    app.view_packages = config
    for package_name in app.view_packages:
        exec('import %s as package' % package_name)
        for importer, modname, is_pkg in pkgutil.iter_modules(locals()['package'].__path__):
            if not is_pkg:
                exec('import %s.%s as package' % (package_name, modname))
                views = locals()['package']
                for item in dir(views):
                    # call [hasattr] function of flask's request and session(werkzeug.local.LocalProxy),
                    # will be raise "RuntimeError: working outside of request context".
                    if item in ['request', 'session'] and getattr(views, item).__class__.__name__ == 'LocalProxy':
                        continue
                    view = getattr(views, item)
                    if hasattr(view, 'parameters') and hasattr(view, 'requisite') and view != CView:
                        name = class_name_to_api_name(view.__name__)
                        uri = '/%s/%s' % (package_name, name)
                        endpoint = '%s.%s' % (package_name, name)
                        app.add_url_rule(uri, view_func=view.as_view(endpoint, app))
