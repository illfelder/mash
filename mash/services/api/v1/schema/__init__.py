# Copyright (c) 2019 SUSE LLC.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#

from flask_restx import fields, Model


def string_with_example(example, description='', min_length=1):
    return {
        'type': 'string',
        'description': description,
        'minLength': min_length,
        'example': example
    }


def integer_with_example(example, description=''):
    return {
        'type': 'integer',
        'description': description,
        'example': example
    }


email = {
    'type': 'string',
    'format': 'regex',
    'pattern': r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
    'example': 'test@fake.com'
}

non_empty_string = {
    'type': 'string',
    'minLength': 1
}

default_response = Model(
    'default_response', {
        'msg': fields.String,
    }
)

errors = {
    'type': 'object',
    'properties': {
        'key': string_with_example('value')
    }
}

validation_error = {
    'type': 'object',
    'properties': {
        'errors': errors,
        'message': non_empty_string
    },
    'additionalProperties': False
}

add_account = {
    'type': 'object',
    'properties': {
        'email': email,
        'password': string_with_example('secretpassword123')
    },
    'additionalProperties': False,
    'required': [
        'email',
        'password'
    ]
}

login_request_model = {
    'type': 'object',
    'properties': {
        'email': email,
        'password': string_with_example('secretpassword123')
    },
    'additionalProperties': False,
    'required': [
        'email',
        'password'
    ]
}

password_reset = {
    'type': 'object',
    'properties': {'email': email},
    'additionalProperties': False,
    'required': [
        'email'
    ]
}

password_change = {
    'type': 'object',
    'properties': {
        'email': email,
        'current_password': string_with_example('secretpassword123'),
        'new_password': string_with_example('secretpassword123')
    },
    'additionalProperties': False,
    'required': [
        'email',
        'current_password',
        'new_password'
    ]
}

oauth2_request_model = {
    'type': 'object',
    'additionalProperties': False
}

oauth2_login_model = {
    'type': 'object',
    'properties': {
        'auth_code': string_with_example('codefromauthprovider'),
        'state': string_with_example('statefromoauth2req'),
        'redirect_port': integer_with_example(9000)
    },
    'additionalProperties': False,
    'required': [
        'auth_code',
        'state',
        'redirect_port'
    ]
}

job_list = {
    'type': 'object',
    'properties': {
        'page': integer_with_example(1),
        'per_page': integer_with_example(10)
    },
    'additionalProperties': False
}
