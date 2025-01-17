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

import re

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.mash_utils import format_string_with_date
from mash.services.status_levels import SUCCESS
from mash.utils.azure import upload_azure_file


# https://[storage-account].[maangement-url]/[container]?[SAS token]
sas_url_match = r'^https://([A-Za-z]+).+/([A-Za-z|-]+)\?(.+)$'


class AzureSASUploadJob(MashJob):
    """
    Implements VM image upload to Azure via SAS token.
    """
    def post_init(self):
        try:
            self.raw_image_upload_location = self.job_config['raw_image_upload_location']
        except KeyError as error:
            raise MashUploadException(
                'Azure SAS upload jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.cloud_image_name = self.job_config.get('cloud_image_name')

    def run_job(self):
        self.status = SUCCESS
        self.log_callback.info('Uploading image.')

        if self.cloud_image_name:
            self.cloud_image_name = format_string_with_date(
                self.cloud_image_name
            )
            self.blob_name = ''.join([self.cloud_image_name, '.vhd'])
        else:
            self.cloud_image_name = self.status_msg['cloud_image_name']
            self.blob_name = self.status_msg['blob_name']

        build = re.search(sas_url_match, self.raw_image_upload_location)

        upload_azure_file(
            self.blob_name,
            build.group(2),
            self.status_msg['image_file'],
            build.group(1),
            max_retry_attempts=self.config.get_azure_max_retry_attempts(),
            max_workers=self.config.get_azure_max_workers(),
            sas_token=build.group(3),
            is_page_blob=True
        )
        self.log_callback.info(
            'Uploaded blob: {blob} using sas token.'.format(
                blob=self.blob_name
            )
        )
