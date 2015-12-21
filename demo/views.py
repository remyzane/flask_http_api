# -*- coding: utf-8 -*-

import os
import logging
from peewee import CharField, Model

from api import app, session, Api, Int, Str, Mail
from api.plugin import Token
from demo import SimpleAes

log = logging.getLogger(__name__)


class GetArea(Api):
    description = '''Get the area information through it's id.'''
    parameters = {'id': Int}
    requisite = ('id',)
    json_p = 'callback'
    plugins_exclude = (Token,)
    codes = {
        'id_not_exist': 'Record does not exist.'
    }

    def get(self, params):
        user_id = params['id']
        if user_id > 100:
            return self.result('id_not_exist')
        else:
            return self.result('success', {'id': user_id,
                                           'name': 'area_%d' % user_id,
                                           'superior': 0})


class GetUser(Api):
    description = '''Get the user information through his/hers id.'''
    parameters = {'identity': Str, 'token': Str, 'id': Int}
    requisite = ('identity', 'token', 'id',)
    json_p = 'callback'
    codes = {
        'id_not_exist': 'Record does not exist.'
    }

    def get(self, params):
        user_id = params['id']
        if user_id > 100:
            return self.result('id_not_exist')
        else:
            return self.result('success', {'id': user_id,
                                           'name': 'user_%d' % user_id,
                                           'email': 'user_%s@yourself.com' % user_id})


class GetUserForExternal(Api):
    description = '''Get the user information through his/hers encrypted id.'''
    parameters = {'id': Str}
    requisite = ('id',)
    plugins_exclude = (Token,)
    codes = {
        'id_invalid': 'Id is invalid.',
        'id_not_exist': 'Record does not exist.'
    }

    def get(self, params):
        user_id = params['id']
        user_id = SimpleAes.decrypt(user_id)
        if not user_id:
            return self.result('id_invalid', {'error': 'Unable to decrypt'})
        try:
            user_id = int(user_id)
        except ValueError:
            return self.result('id_invalid', {'error': 'id must be integer', 'id': user_id})

        if user_id > 100:
            return self.result('id_not_exist')
        else:
            return self.result('success', {'id': user_id,
                                           'name': 'user_%d' % user_id,
                                           'email': 'user_%s@yourself.com' % user_id})


class SetUser(Api):
    description = '''User setting'''
    parameters = {'identity': Str, 'token': Str, 'username': Str, 'nickname': Str,
                  'password': Str, 'email': Mail, 'address': Str, 'mobile': Str, 'zipcode': Str}
    requisite = ('identity', 'token', 'username', 'password', 'email')
    codes = {
        'mobile_existent': 'Mobile number already exists.',
        'email_existent': 'Email address already exists.'
    }

    def post(self, params):
        self.process_log += 'do job 1' + os.linesep
        self.process_log += 'do job 2' + os.linesep
        self.process_log += 'do job 3'
        return self.result('success', {'id': 1})


class Session(Api):
    description = '''Session testing.'''
    plugins_exclude = (Token,)
    codes = {
        'not_configured': 'Session is not configured, Please setting SECRET_KEY in api.yml.',
        'not_login': 'Not logged in'
    }

    def get(self, params):
        if not app.config.get('SECRET_KEY'):
            return self.result('not_configured')
        if not session.get('user'):
            return self.result('not_login')

        return self.result('success', {'key': session['user']})


class User(Model):
    username = CharField()


class Performance(Api):
    description = '''The performance test'''
    plugins_exclude = (Token,)

    def get(self, params):
        for index in range(1, 100):
            id = index % 100 or 1
            username = User.get(User.id == id).username
        return self.result('success')
