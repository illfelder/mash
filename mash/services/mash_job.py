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

from mash.mash_exceptions import MashJobException
from mash.services.status_levels import UNKOWN


class MashJob(object):
    """
    Class for an individual mash job.
    """
    def __init__(self, job_config, config):
        self.job_config = job_config

        # Properties
        self._cloud_image_name = None
        self._credentials = None
        self._log_callback = None
        self._source_regions = None
        self._job_file = job_config.get('job_file')

        self.config = config
        self.iteration_count = 0
        self.status = UNKOWN

        try:
            self.id = job_config['id']
            self.last_service = job_config['last_service']
            self.cloud = job_config['cloud']
            self.utctime = job_config['utctime']
        except KeyError as error:
            raise MashJobException(
                'Jobs require a(n) {0} key in the job doc.'.format(
                    error
                )
            )

        self.notification_email = job_config.get('notification_email')
        self.notification_type = job_config.get('notification_type', 'single')

        self.post_init()

    def get_job_id(self):
        """
        Return dictionary with job id.
        """
        return {'job_id': self.id}

    def send_log(self, message, success=True):
        """
        Send a log message to the log callback function.
        """
        if self.log_callback:
            self.log_callback(
                'Pass[{0}]: {1}'.format(
                    self.iteration_count,
                    message
                ),
                self.get_job_id(),
                success
            )

    def run_job(self):
        """
        Start and run job workflow.
        """
        raise NotImplementedError(
            'This {0} class does not implement the '
            '_run_job method.'.format(
                self.__class__.__name__
            )
        )

    def process_job(self):
        """
        Update iteration count and run job.
        """
        self.iteration_count += 1
        self.run_job()

    @property
    def cloud_image_name(self):
        """Cloud image name property."""
        return self._cloud_image_name

    @cloud_image_name.setter
    def cloud_image_name(self, name):
        """
        Setter for cloud image name.
        """
        self._cloud_image_name = name

    @property
    def credentials(self):
        """Credentials property."""
        return self._credentials

    @credentials.setter
    def credentials(self, creds):
        """Setter for credentials."""
        self._credentials = creds

    @property
    def job_file(self):
        """Job file property."""
        return self._job_file

    @job_file.setter
    def job_file(self, file):
        """Setter for job file."""
        self._job_file = file

    @property
    def log_callback(self):
        """Log callback property."""
        return self._log_callback

    @log_callback.setter
    def log_callback(self, callback):
        """
        Set log_callback function to callback.
        """
        self._log_callback = callback

    @property
    def source_regions(self):
        """Source regions property."""
        return self._source_regions

    @source_regions.setter
    def source_regions(self, regions):
        """
        Setter for source_regions dictionary.
        """
        self._source_regions = regions

    def post_init(self):
        """
        Post initialization method.

        Implementation in child class.
        """
        pass
