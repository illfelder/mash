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

import copy

from flask import current_app

from mash.mash_exceptions import MashJobException
from mash.services.api.utils.users import get_user_by_username
from mash.services.api.utils.accounts.ec2 import get_ec2_group, get_ec2_account_by_id


def get_ec2_regions_by_partition(partition):
    """
    Get EC2 regions from config file based on partition.
    """
    regions = copy.deepcopy(
        current_app.config['CLOUD_DATA']['ec2']['regions'][partition]
    )
    return regions


def get_ec2_helper_images():
    """
    Get helper image data for EC2 from config file.
    """
    helper_images = copy.deepcopy(
        current_app.config['CLOUD_DATA']['ec2']['helper_images']
    )
    return helper_images


def add_target_ec2_account(
    account,
    accounts,
    cloud_accounts,
    helper_images,
    use_root_swap=None
):
    """
    Update job with account information.

    - Append any additional regions
    - Update ami for root swap if use_root_swap set
    """
    regions = get_ec2_regions_by_partition(account.partition)

    if account.additional_regions:
        for region in account.additional_regions:
            helper_images[region.name] = region.helper_image
            regions.append(region.name)

    job_doc_data = cloud_accounts.get(account.name, {})
    region = job_doc_data.get('region') or account.region
    subnet = job_doc_data.get('subnet') or account.subnet

    if use_root_swap:
        try:
            helper_image = job_doc_data['root_swap_ami']
        except KeyError:
            raise MashJobException(
                'root_swap_ami is required for account {0},'
                ' when using root swap.'.format(account.name)
            )
    else:
        helper_image = helper_images[region]

    accounts[region] = {
        'account': account.name,
        'target_regions': regions,
        'helper_image': helper_image,
        'subnet': subnet
    }


def convert_account_dict(accounts):
    """
    Create a dictionary of accounts by account name.
    """
    cloud_accounts = {}

    for account in accounts:
        cloud_accounts[account['name']] = account

    return cloud_accounts


def update_ec2_job_accounts(job_doc):
    """
    Update target_account_info for given job doc.

    Once accounts dictionary is built remove cloud_groups
    and cloud_accounts keys from job_doc.
    """
    user = get_user_by_username(job_doc['requesting_user'])
    helper_images = get_ec2_helper_images()
    cloud_accounts = convert_account_dict(job_doc['cloud_accounts'])

    accounts = {}
    target_accounts = []
    for group_name in job_doc.get('cloud_groups', []):
        group = get_ec2_group(group_name, user.id)
        target_accounts += group.accounts

    for account_name in cloud_accounts:
        cloud_account = get_ec2_account_by_id(account_name, user.id)
        target_accounts.append(cloud_account)

    for account in target_accounts:
        if account.name not in accounts:
            add_target_ec2_account(
                account,
                accounts,
                cloud_accounts,
                helper_images,
                job_doc.get('use_root_swap')
            )

    if 'cloud_groups' in job_doc:
        del job_doc['cloud_groups']

    if 'cloud_accounts' in job_doc:
        del job_doc['cloud_accounts']

    job_doc['target_account_info'] = accounts

    return job_doc
