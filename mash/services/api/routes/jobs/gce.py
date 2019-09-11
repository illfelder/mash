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

import json

from flask import jsonify, make_response, request
from flask_restplus import marshal, Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from mash.mash_exceptions import MashException
from mash.services.api.schema import (
    default_response,
    validation_error
)
from mash.services.api.routes.jobs import job_response
from mash.services.api.schema.jobs.gce import gce_job_message
from mash.services.api.utils.jobs import create_job
from mash.services.api.utils.jobs.gce import update_gce_job_accounts

api = Namespace(
    'GCE Jobs',
    description='GCE Job operations'
)
gce_job = api.schema_model('gce_job', gce_job_message)
validation_error_response = api.schema_model(
    'validation_error', validation_error
)


@api.route('/')
@api.doc(security='apiKey')
@api.response(400, 'Validation error', validation_error_response)
@api.response(401, 'Unauthorized', default_response)
@api.response(422, 'Not processable', default_response)
class GCEJobCreate(Resource):
    @api.doc('add_gce_job')
    @jwt_required
    @api.expect(gce_job)
    @api.response(201, 'Job added', job_response)
    def post(self):
        """
        Add GCE job.
        """
        data = json.loads(request.data.decode())
        data['cloud'] = 'gce'
        data['requesting_user'] = get_jwt_identity()

        try:
            data = update_gce_job_accounts(data)
            job = create_job(data)
        except MashException as error:
            return make_response(
                jsonify({'msg': 'Job failed: {0}'.format(error)}),
                400
            )
        except Exception:
            return make_response(
                jsonify({'msg': 'Failed to start job'}),
                400
            )

        return make_response(
            jsonify(marshal(job, job_response, skip_none=True)),
            201
        )
