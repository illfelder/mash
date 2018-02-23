# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
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

import logging
import threading

from ipa.ipa_controller import test_image

from mash.services.status_levels import EXCEPTION, FAILED, SUCCESS


def ipa_test(
    results, provider=None, access_key_id=None, description=None, distro=None,
    image_id=None, instance_type=None, region=None, secret_access_key=None,
    ssh_key_name=None, ssh_private_key=None, ssh_user=None, tests=None
):
    name = threading.current_thread().getName()
    # TODO determine if we want to handle key-pair issues manually or
    # automagically with temp key files.
    try:
        status, result = test_image(
            provider.upper(),  # TODO remove uppercase when IPA update released
            access_key_id=access_key_id,
            desc=description,
            distro=distro,
            image_id=image_id,
            instance_type=instance_type,
            log_level=logging.WARNING,
            region=region,
            secret_access_key=secret_access_key,
            ssh_key_name=ssh_key_name,
            ssh_private_key=ssh_private_key,
            ssh_user=ssh_user,
            tests=tests
        )
    except Exception as error:
        results[name] = {'status': EXCEPTION, 'msg': str(error)}
    else:
        status = SUCCESS if status == 0 else FAILED
        results[name] = {'status': status}