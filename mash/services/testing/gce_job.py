# Copyright (c) 2018 SUSE LLC.  All rights reserved.
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
import random

from mash.services.testing.job import TestingJob

instance_types = [
    'n1-standard-1',
    'n1-highmem-2',
    'n1-highcpu-2',
    'f1-micro',
    'n1-ultramem-40'
]


class GCETestingJob(TestingJob):
    """
    Class for an GCE testing job.
    """

    def __init__(
        self, id, provider, ssh_private_key_file, test_regions, tests, utctime,
        job_file=None, credentials=None, description=None, distro='sles',
        instance_type=None, ipa_timeout=None, ssh_user='root'
    ):
        if not instance_type:
            instance_type = random.choice(instance_types)

        super(GCETestingJob, self).__init__(
            id, provider, ssh_private_key_file, test_regions, tests, utctime,
            job_file=job_file, description=description, distro=distro,
            instance_type=instance_type, ipa_timeout=ipa_timeout,
            ssh_user=ssh_user
        )

    def _add_provider_creds(self, creds, ipa_kwargs):
        """
        Update IPA kwargs with GCE credentials.
        """
        ipa_kwargs['service_account_credentials'] = json.dumps(creds)

        return ipa_kwargs