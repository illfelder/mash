# Copyright (c) 2017 SUSE Linux GmbH.  All rights reserved.
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
# project
from mash.utils.json_format import JsonFormat
from mash.services.uploader.cloud import Upload


class UploadImage(object):
    """
    Process an upload into the public cloud

    Before an upload can start information from the obs service
    about the image and information about the credentials from the
    credentials service to access the cloud needs to be retrieved.
    This class implements the pipeline connection to obs and credentials
    services and provides an interface to upload into the cloud

    * :attr:`pika_connection`
        instance of pika.BlockingConnection

    * :attr:`job_id`
        job number

    * :attr:`csp_name`
        cloud service provider name

    * :attr:`cloud_image_name`
        name of the image in the public cloud
        has to follow naming conventions

    * :attr:`cloud_image_description`
        description of the image in the public cloud

    * :attr:`custom_uploader_args`
        dictionary of parameters for the used upload tool
        specific to the selected cloud and uploader class

    * :attr:`custom_credentials_args`
        dictionary of parameters for the instance handling
        credentials. specific to the selected cloud and
        credentials class
    """
    def __init__(
        self, pika_connection, job_id, csp_name,
        cloud_image_name, cloud_image_description,
        custom_uploader_args=None, custom_credentials_args=None
    ):
        self.job_id = job_id
        self.csp_name = csp_name
        self.cloud_image_name = cloud_image_name
        self.cloud_image_description = cloud_image_description
        self.obs_listen_queue = 'obs.listener_{0}'.format(
            self.job_id
        )
        self.credentials_listen_queue = 'credentials.{0}'.format(csp_name)
        self.connection = pika_connection
        self.channel = self.connection.channel()
        self.custom_uploader_args = custom_uploader_args
        self.custom_credentials_args = custom_credentials_args
        self.system_image_file = None
        self.credentials_token = None

        self._setup_request_for_credentials_token()
        self._setup_request_for_obs_image()

    def upload(self, service_lookup_timeout_sec=None):
        """
        Upload image to the specified cloud

        Creates an instance of the Upload factory and returns
        an image identifier once the upload has been processed
        successfully. The image identifier is cloud specific
        as well as the information handed over in the custom
        uploader and credentials arguments
        """
        if service_lookup_timeout_sec:
            self.connection.add_timeout(
                service_lookup_timeout_sec, self._consuming_timeout
            )
        self.channel.start_consuming()

        if self.system_image_file and self.credentials_token:
            uploader = Upload(
                self.csp_name, self.system_image_file,
                self.cloud_image_name, self.cloud_image_description,
                self.credentials_token,
                self.custom_uploader_args,
                self.custom_credentials_args
            )
            return uploader.upload()

    def _setup_request_for_credentials_token(self):
        """
        Lookup credentials from the credentials service for the specified csp
        """
        self.channel.queue_declare(
            queue=self.credentials_listen_queue, durable=True
        )
        self.channel.basic_consume(
            self._credentials_job_data, queue=self.credentials_listen_queue
        )

    def _setup_request_for_obs_image(self):
        """
        Lookup image from the obs service for the specified job
        """
        self.channel.queue_declare(
            queue=self.obs_listen_queue, durable=True
        )
        self.channel.basic_consume(
            self._obs_job_data, queue=self.obs_listen_queue
        )

    def _obs_job_data(self, channel, method, properties, body):
        channel.basic_ack(method.delivery_tag)
        self.channel.queue_delete(queue=self.obs_listen_queue)
        obs_result = JsonFormat.json_loads_byteified(body)
        self.system_image_file = obs_result['image_source'][0]

    def _credentials_job_data(self, channel, method, properties, body):
        credentials_result = JsonFormat.json_loads_byteified(body)
        self.credentials_token = credentials_result['credentials']

    def _consuming_timeout(self):
        return
