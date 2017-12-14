#!/usr/bin/env python
import platform

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from mash.version import __VERSION__

python_version = platform.python_version().split('.')[0]

config = {
    'name': 'mash',
    'description': 'Public Cloud Release Tool',
    'author': 'PubCloud Development team',
    'url': 'https://gitlab.suse.de/pub-cloud/mash',
    'download_url': 'https://gitlab.suse.de/pub-cloud/mash',
    'author_email': 'public-cloud-dev@susecloud.net',
    'version': __VERSION__,
    'install_requires': [
        'setuptools>=5.4',
        'PyYAML',
        'PyJWT',
        'python-dateutil',
        'APScheduler>=3.3.1',
        'amqpstorm',
        'python3-ipa'
    ],
    'packages': ['mash'],
    'entry_points': {
        'console_scripts': [
            'mash-obs-service=mash.services.obs_service:main',
            'mash-logger-service=mash.services.logger_service:main',
            'mash-credentials-service=mash.services.credentials_service:main',
            'mash-job_creator-service=mash.services.job_creator_service:main',
            'mash-testing-service=mash.services.testing_service:main'
        ]
    },
    'include_package_data': True,
    'zip_safe': False,
    'classifiers': [
        # http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.4',
        'Topic :: System :: Operating System'
    ]
}

setup(**config)
