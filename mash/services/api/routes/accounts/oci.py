# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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
import json

from flask import jsonify, request, make_response, current_app
from flask_restplus import fields, marshal, Model, Namespace, Resource
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity
)
from sqlalchemy.exc import IntegrityError

from mash.mash_exceptions import MashException
from mash.services.api.schema import (
    default_response,
    validation_error
)
from mash.services.api.schema.accounts.oci import (
    add_account_oci,
    oci_account_update
)
from mash.services.api.utils.accounts.oci import (
    create_oci_account,
    get_oci_account,
    get_oci_accounts,
    delete_oci_account,
    update_oci_account
)

api = Namespace(
    'OCI Accounts',
    description='OCI account operations'
)
add_oci_account_request = api.schema_model('oci_account', add_account_oci)
update_oci_account_request = api.schema_model(
    'oci_account_update',
    oci_account_update
)
validation_error_response = api.schema_model(
    'validation_error', validation_error
)

oci_account_response = Model(
    'oci_account_response', {
        'id': fields.String,
        'name': fields.String,
        'bucket': fields.String,
        'region': fields.String,
        'availability_domain': fields.String,
        'compartment_id': fields.String,
        'oci_user_id': fields.String,
        'tenancy': fields.String
    }
)

api.models['oci_account_response'] = oci_account_response


@api.route('/')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class OCIAccountCreateAndList(Resource):
    """
    Handles list accounts and create accounts for OCI.
    """

    @api.doc('create_oci_account')
    @jwt_required
    @api.expect(add_oci_account_request)
    @api.response(201, 'OCI account created', oci_account_response)
    @api.response(400, 'Validation error', validation_error_response)
    @api.response(409, 'Duplicate account', default_response)
    def post(self):
        """
        Create a new OCI account.
        """
        data = json.loads(request.data.decode())

        try:
            account = create_oci_account(
                get_jwt_identity(),
                data['account_name'],
                data['bucket'],
                data['region'],
                data['availability_domain'],
                data['compartment_id'],
                data['oci_user_id'],
                data['tenancy'],
                data['signing_key']
            )
        except MashException as error:
            return make_response(
                jsonify({'msg': str(error)}),
                400
            )
        except IntegrityError:
            return make_response(
                jsonify({'msg': 'Account already exists'}),
                409
            )
        except Exception as error:
            current_app.logger.warning(error)
            return make_response(
                jsonify({'msg': 'Failed to add OCI account'}),
                400
            )

        return make_response(
            jsonify(marshal(account, oci_account_response, skip_none=True)),
            201
        )

    @api.doc('get_oci_accounts')
    @jwt_required
    @api.marshal_list_with(oci_account_response, skip_none=True)
    @api.response(200, 'Success', default_response)
    def get(self):
        """
        Get all OCI accounts.
        """
        oci_accounts = get_oci_accounts(get_jwt_identity())
        return oci_accounts


@api.route('/<string:name>')
@api.doc(security='apiKey')
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class OCIAccount(Resource):
    @api.doc('delete_oci_account')
    @jwt_required
    @api.response(200, 'OCI account deleted', default_response)
    @api.response(400, 'Delete OCI account failed', default_response)
    @api.response(404, 'Not found', default_response)
    def delete(self, name):
        """
        Delete OCI account matching name for requesting user.
        """
        try:
            rows_deleted = delete_oci_account(name, get_jwt_identity())
        except Exception as error:
            current_app.logger.warning(error)
            return make_response(
                jsonify({'msg': 'Delete OCI account failed'}),
                400
            )

        if rows_deleted:
            return make_response(
                jsonify({'msg': 'OCI account deleted'}),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'OCI account not found'}),
                404
            )

    @api.doc('get_oci_account')
    @jwt_required
    @api.response(200, 'Success', oci_account_response)
    @api.response(404, 'Not found', default_response)
    def get(self, name):
        """
        Get OCI account.
        """
        account = get_oci_account(name, get_jwt_identity())

        if account:
            return make_response(
                jsonify(marshal(account, oci_account_response, skip_none=True)),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'OCI account not found'}),
                404
            )

    @api.doc('update_oci_account')
    @jwt_required
    @api.expect(update_oci_account_request)
    @api.response(200, 'Success', oci_account_response)
    @api.response(400, 'Validation error', validation_error_response)
    @api.response(404, 'Not found', default_response)
    def post(self, name):
        """
        Update OCI account.
        """
        data = json.loads(request.data.decode())

        try:
            account = update_oci_account(
                get_jwt_identity(),
                name,
                data.get('bucket'),
                data.get('region'),
                data.get('availability_domain'),
                data.get('compartment_id'),
                data.get('oci_user_id'),
                data.get('tenancy'),
                data.get('signing_key')
            )
        except Exception as error:
            current_app.logger.warning(error)
            return make_response(
                jsonify({'msg': str(error)}),
                400
            )

        if account:
            return make_response(
                jsonify(marshal(account, oci_account_response, skip_none=True)),
                200
            )
        else:
            return make_response(
                jsonify({'msg': 'OCI account not found'}),
                404
            )