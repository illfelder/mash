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

import logging
import sys

from mash.mash_exceptions import MashException
from mash.services.jobcreator.service import JobCreatorService


def main():
    """
    mash - job creator service application entry point
    """
    try:
        logging.basicConfig()
        log = logging.getLogger('MashService')
        log.setLevel(logging.DEBUG)
        # run service, enter main loop
        JobCreatorService(
            host='localhost', service_exchange='jobcreator'
        )
    except MashException as e:
        # known exception
        log.error('{0}: {1}'.format(type(e).__name__, format(e)))
        sys.exit(1)
    except SystemExit:
        # user exception, program aborted by user
        sys.exit(0)
    except Exception:
        # exception we did no expect, show python backtrace
        log.error('Unexpected error:')
        raise
