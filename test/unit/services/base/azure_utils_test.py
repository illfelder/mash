import json

from datetime import date
from pytest import raises
from unittest.mock import MagicMock, patch
from collections import namedtuple

from azure.mgmt.storage import StorageManagementClient
from mash.mash_exceptions import MashAzureUtilsException
from mash.utils.azure import (
    acquire_access_token,
    delete_image,
    delete_blob,
    deprecate_image_in_offer_doc,
    get_blob_url,
    go_live_with_cloud_partner_offer,
    get_blob_service_with_account_keys,
    log_operation_response_status,
    publish_cloud_partner_offer,
    put_cloud_partner_offer_doc,
    request_cloud_partner_offer_doc,
    update_cloud_partner_offer_doc,
    wait_on_cloud_partner_operation,
    upload_azure_file,
    get_blob_service_with_sas_token,
    blob_exists,
    image_exists,
    get_client_from_json
)

creds = {
    "clientId": "09876543-1234-1234-1234-123456789012",
    "clientSecret": "09876543-1234-1234-1234-123456789012",
    "subscriptionId": "09876543-1234-1234-1234-123456789012",
    "tenantId": "09876543-1234-1234-1234-123456789012"
}


@patch('mash.utils.azure.adal')
def test_acquire_access_token(mock_adal):
    context = MagicMock()
    context.acquire_token_with_client_credentials.return_value = {
        'accessToken': '1234567890'
    }
    mock_adal.AuthenticationContext.return_value = context

    with open('test/data/azure_creds.json') as f:
        credentials = json.load(f)

    acquire_access_token(credentials)

    mock_adal.AuthenticationContext.assert_called_once_with(
        'https://login.microsoftonline.com/'
        '09876543-1234-1234-1234-123456789012'
    )
    context.acquire_token_with_client_credentials.assert_called_once_with(
        'https://management.core.windows.net/',
        '09876543-1234-1234-1234-123456789012',
        '09876543-1234-1234-1234-123456789012'
    )


@patch('mash.utils.azure.adal')
def test_acquire_access_token_cloud_partner(mock_adal):
    context = MagicMock()
    context.acquire_token_with_client_credentials.return_value = {
        'accessToken': '1234567890'
    }
    mock_adal.AuthenticationContext.return_value = context

    with open('test/data/azure_creds.json') as f:
        credentials = json.load(f)

    acquire_access_token(credentials, cloud_partner=True)

    mock_adal.AuthenticationContext.assert_called_once_with(
        'https://login.microsoftonline.com/'
        '09876543-1234-1234-1234-123456789012'
    )
    context.acquire_token_with_client_credentials.assert_called_once_with(
        'https://cloudpartner.azure.com',
        '09876543-1234-1234-1234-123456789012',
        '09876543-1234-1234-1234-123456789012'
    )


@patch('mash.utils.azure.generate_container_sas')
def test_get_blob_url(mock_generate_container_sas):
    blob_service = MagicMock()
    blob_service.credential.account_key = 'key123'
    mock_generate_container_sas.return_value = 'token123'

    url = get_blob_url(
        blob_service, 'blob1', 'sa1', 'container1'
    )

    sas_url = 'https://sa1.blob.core.windows.net/container1/blob1?token123'
    assert url == sas_url


@patch('mash.utils.azure.get_client_from_json')
@patch('mash.utils.azure.BlobServiceClient')
def test_get_blob_service_with_account_keys(
    mock_blob_service,
    mock_get_client_from_json
):
    storage_client = MagicMock()
    mock_get_client_from_json.return_value = storage_client

    key1 = MagicMock()
    key1.value = '12345678'
    key2 = MagicMock()
    key2.value = '87654321'
    key_list = MagicMock()
    key_list.keys = [key1, key2]
    storage_client.storage_accounts.list_keys.return_value = key_list

    blob_service = MagicMock()
    mock_blob_service.return_value = blob_service

    service = get_blob_service_with_account_keys(
        creds, 'rg1', 'sa1'
    )

    assert service == blob_service
    storage_client.storage_accounts.list_keys.assert_called_once_with(
        'rg1', 'sa1'
    )
    mock_blob_service.assert_called_once_with(
        account_url='https://sa1.blob.core.windows.net',
        credential='12345678'
    )


@patch('mash.utils.azure.get_blob_service_with_account_keys')
def test_delete_blob(mock_get_blob_service):
    blob_service = MagicMock()
    container_client = MagicMock()
    blob_client = MagicMock()

    container_client.get_blob_client.return_value = blob_client
    blob_service.get_container_client.return_value = container_client
    mock_get_blob_service.return_value = blob_service

    delete_blob(
        creds, 'blob1', 'container1', 'rg1', 'sa1'
    )

    blob_client.delete_blob.assert_called_once_with()


@patch('mash.utils.azure.get_blob_service_with_account_keys')
def test_blob_exists(mock_get_blob_service):
    blob_service = MagicMock()
    container_client = MagicMock()
    blob_client = MagicMock()

    blob_client.exists.return_value = True
    container_client.get_blob_client.return_value = blob_client
    blob_service.get_container_client.return_value = container_client
    mock_get_blob_service.return_value = blob_service

    result = blob_exists(
        creds, 'blob1', 'container1', 'rg1', 'sa1'
    )

    assert result


@patch('mash.utils.azure.get_client_from_json')
def test_delete_image(mock_get_client):
    compute_client = MagicMock()
    async_wait = MagicMock()
    compute_client.images.begin_delete.return_value = async_wait
    mock_get_client.return_value = compute_client

    delete_image(
        creds, 'rg1', 'image123'
    )
    compute_client.images.begin_delete.assert_called_once_with(
        'rg1', 'image123'
    )
    async_wait.result.assert_called_once_with()


@patch('mash.utils.azure.get_client_from_json')
def test_image_exists(mock_get_client):
    compute_client = MagicMock()
    image = MagicMock()
    image.name = 'image123'
    compute_client.images.list.return_value = [image]
    mock_get_client.return_value = compute_client

    result = image_exists(
        creds, 'image123'
    )

    assert result
    compute_client.images.list.assert_called_once_with()


@patch('mash.utils.azure.requests')
@patch('mash.utils.azure.acquire_access_token')
def test_go_live_with_cloud_partner_offer(
    mock_acquire_access_token, mock_requests
):
    mock_acquire_access_token.return_value = '1234567890'

    response = MagicMock()
    response.status_code = 200
    response.headers = {'Location': '/api/endpoint/url'}
    mock_requests.post.return_value = response

    with open('test/data/azure_creds.json') as f:
        credentials = json.load(f)

    response = go_live_with_cloud_partner_offer(
        credentials, 'sles', 'suse'
    )

    assert response == '/api/endpoint/url'


@patch('mash.utils.azure.requests')
@patch('mash.utils.azure.acquire_access_token')
def test_publish_cloud_partner_offer(
    mock_acquire_access_token, mock_requests
):
    mock_acquire_access_token.return_value = '1234567890'

    response = MagicMock()
    response.status_code = 200
    response.headers = {'Location': '/api/endpoint/url'}
    mock_requests.post.return_value = response

    with open('test/data/azure_creds.json') as f:
        credentials = json.load(f)

    response = publish_cloud_partner_offer(
        credentials, 'sles', 'suse'
    )

    assert response == '/api/endpoint/url'


def test_log_operation_response_status():
    callback = MagicMock()
    response = {
        'steps': [{
            'status': 'inProgress',
            'stepName': 'Publishing the image',
            'progressPercentage': 30
        }]
    }

    log_operation_response_status(response, callback)
    callback.info.assert_called_once_with(
        'Publishing the image 30% complete.'
    )


@patch('mash.utils.azure.requests')
@patch('mash.utils.azure.acquire_access_token')
def test_put_cloud_partner_offer_doc(
    mock_acquire_access_token, mock_requests
):
    mock_acquire_access_token.return_value = '1234567890'

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {'response': 'doc'}
    mock_requests.put.return_value = response

    with open('test/data/azure_creds.json') as f:
        credentials = json.load(f)

    request_doc = {'test': 'doc'}

    response = put_cloud_partner_offer_doc(
        credentials, request_doc, 'sles', 'suse'
    )

    assert response['response'] == 'doc'


@patch('mash.utils.azure.acquire_access_token')
@patch('mash.utils.azure.requests')
def test_request_cloud_partner_offer_doc(
    mock_requests, mock_acquire_access_token
):
    mock_acquire_access_token.return_value = '1234567890'
    response = MagicMock()
    response.json.return_value = {'offer': 'doc'}
    mock_requests.get.return_value = response

    with open('test/data/azure_creds.json') as f:
        credentials = json.load(f)

    request_cloud_partner_offer_doc(
        credentials, 'sles', 'suse',
    )
    mock_requests.get.assert_called_once_with(
        'https://cloudpartner.azure.com/api/publishers/suse/'
        'offers/sles?api-version=2017-10-31',
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer 1234567890'
        }
    )


def test_update_cloud_partner_offer_doc():
    today = date.today()
    release = today.strftime("%Y.%m.%d")
    vm_images_key = 'microsoft-azure-corevm.vmImagesPublicAzure'

    doc = {
        'definition': {
            'plans': [
                {
                    'planId': 'gen1',
                    'diskGenerations': [{'planId': 'image-gen2'}]
                }
            ]
        }
    }

    doc = update_cloud_partner_offer_doc(
        doc,
        'blob/url/.vhd',
        'New image for v123',
        'new-image',
        'New Image 123',
        'gen1',
        generation_id='image-gen2',
        cloud_image_name_generation_suffix='gen2'
    )

    plan = doc['definition']['plans'][0]
    assert plan[vm_images_key][release]['label'] == 'New Image 123'
    assert plan['diskGenerations'][0][vm_images_key][release]['mediaName'] == \
        'new-image-gen2'

    with raises(MashAzureUtilsException):
        update_cloud_partner_offer_doc(
            doc,
            'blob/url/.vhd',
            'New image for v123',
            'new-image',
            'New Image 123',
            'gen2',
            generation_id='image-gen2',
            cloud_image_name_generation_suffix='gen2'
        )

    with raises(MashAzureUtilsException):
        update_cloud_partner_offer_doc(
            doc,
            'blob/url/.vhd',
            'New image for v123',
            'new-image',
            'New Image 123',
            'gen1',
            generation_id='image-gen3',
            cloud_image_name_generation_suffix='gen2'
        )


def test_update_cloud_partner_offer_doc_existing_date():
    vm_images_key = 'microsoft-azure-corevm.vmImagesPublicAzure'

    doc = {
        'definition': {
            'plans': [
                {'planId': '123'}
            ]
        }
    }

    doc = update_cloud_partner_offer_doc(
        doc,
        'blob/url/.vhd',
        'New image for v123',
        'New Image 20180909',
        'New Image 123',
        '123'
    )

    label = doc['definition']['plans'][0][vm_images_key]['2018.09.09']['label']
    assert label == 'New Image 123'


@patch('mash.utils.azure.log_operation_response_status')
@patch('mash.utils.azure.time')
@patch('mash.utils.azure.acquire_access_token')
@patch('mash.utils.azure.requests')
def test_wait_on_cloud_partner_operation(
    mock_requests, mock_acquire_access_token, mock_time,
    mock_log_operation
):
    mock_acquire_access_token.return_value = '1234567890'
    callback = MagicMock()
    response = MagicMock()
    response.json.side_effect = [
        {'status': 'running'},
        {'status': 'complete'}
    ]
    mock_requests.get.return_value = response

    with open('test/data/azure_creds.json') as f:
        credentials = json.load(f)

    wait_on_cloud_partner_operation(
        credentials, '/api/test/operation', callback
    )


@patch('mash.utils.azure.time')
@patch('mash.utils.azure.acquire_access_token')
@patch('mash.utils.azure.requests')
def test_wait_on_cloud_partner_operation_failed(
    mock_requests, mock_acquire_access_token, mock_time
):
    mock_acquire_access_token.return_value = '1234567890'
    callback = MagicMock()
    response = MagicMock()
    response.json.return_value = {'status': 'failed'}
    mock_requests.get.return_value = response

    with open('test/data/azure_creds.json') as f:
        credentials = json.load(f)

    with raises(MashAzureUtilsException) as error:
        wait_on_cloud_partner_operation(
            credentials, '/api/test/operation', callback
        )

    assert str(error.value) == \
        'Cloud partner operation did not finish successfully.'


def test_deprecate_image_in_offer():
    vm_images_key = 'microsoft-azure-corevm.vmImagesPublicAzure'
    callback = MagicMock()

    doc = {
        'definition': {
            'plans': [
                {
                    'planId': '123',
                    vm_images_key: {
                        '2018.09.09': {
                            'label': 'New Image 20180909',
                            'mediaName': 'new_image_20180909'
                        }
                    }
                }
            ]
        }
    }

    doc = deprecate_image_in_offer_doc(
        doc,
        'new_image_20180909',
        '123',
        callback
    )

    release = doc['definition']['plans'][0][vm_images_key]['2018.09.09']
    assert release['showInGui'] is False


def test_deprecate_image_in_offer_invalid():
    vm_images_key = 'microsoft-azure-corevm.vmImagesPublicAzure'
    callback = MagicMock()

    doc = {
        'definition': {
            'plans': [
                {
                    'planId': '123'
                }
            ]
        }
    }

    deprecate_image_in_offer_doc(
        doc,
        'new_image',
        '123',
        callback
    )

    doc = {
        'definition': {
            'plans': [
                {
                    'planId': '123',
                    vm_images_key: {
                        '2018.09.09': {
                            'label': 'New Image 20180909',
                            'mediaName': 'new_image'
                        }
                    }
                }
            ]
        }
    }

    deprecate_image_in_offer_doc(
        doc,
        'new_image_20180909',
        '123',
        callback
    )

    callback.assert_called_once_with(
        'Deprecation image name, new_image_20180909 does match the '
        'mediaName attribute, new_image.'
    )


@patch('builtins.open')
@patch('mash.utils.azure.get_client_from_json')
@patch('mash.utils.azure.BlobServiceClient')
@patch('mash.utils.azure.FileType')
@patch('mash.utils.azure.lzma')
def test_upload_azure_file(
    mock_lzma,
    mock_FileType,
    mock_blob_service,
    mock_get_client_from_json,
    mock_open
):
    lzma_handle = MagicMock()
    lzma_handle.__enter__.return_value = lzma_handle
    mock_lzma.LZMAFile.return_value = lzma_handle

    open_handle = MagicMock()
    open_handle.__enter__.return_value = open_handle
    mock_open.return_value = open_handle

    client = MagicMock()
    mock_get_client_from_json.return_value = client

    blob_service = MagicMock()
    mock_blob_service.return_value = blob_service

    container_client = MagicMock()
    blob_client = MagicMock()
    container_client.get_blob_client.return_value = blob_client
    blob_service.get_container_client.return_value = container_client

    key_type = namedtuple('key_type', ['value', 'key_name'])
    async_create_image = MagicMock()
    storage_key_list = MagicMock()
    storage_key_list.keys = [
        key_type(value='key', key_name='key_name')
    ]

    client.storage_accounts.list_keys.return_value = storage_key_list
    client.images.create_or_update.return_value = async_create_image

    system_image_file_type = MagicMock()
    system_image_file_type.get_size.return_value = 1024
    system_image_file_type.is_xz.return_value = True
    mock_FileType.return_value = system_image_file_type

    credentials = {
        'clientId': 'a',
        'clientSecret': 'b',
        'subscriptionId': 'c',
        'tenantId': 'd',
        'activeDirectoryEndpointUrl': 'https://login.microsoftonline.com',
        'resourceManagerEndpointUrl': 'https://management.azure.com/',
        'activeDirectoryGraphResourceId': 'https://graph.windows.net/',
        'sqlManagementEndpointUrl':
            'https://management.core.windows.net:8443/',
        'galleryEndpointUrl': 'https://gallery.azure.com/',
        'managementEndpointUrl': 'https://management.core.windows.net/'
    }

    upload_azure_file(
        'name.vhd',
        'container',
        'file.vhdfixed.xz',
        'storage',
        max_retry_attempts=5,
        max_workers=8,
        credentials=credentials,
        resource_group='group_name',
        is_page_blob=True
    )

    mock_get_client_from_json.assert_called_once_with(
        StorageManagementClient,
        credentials
    )
    client.storage_accounts.list_keys.assert_called_once_with(
        'group_name', 'storage'
    )
    mock_blob_service.assert_called_once_with(
        account_url='https://storage.blob.core.windows.net',
        credential='key'
    )
    mock_FileType.assert_called_once_with('file.vhdfixed.xz')
    system_image_file_type.is_xz.assert_called_once_with()
    blob_client.upload_blob.assert_called_once_with(
        lzma_handle,
        blob_type='PageBlob',
        length=1024,
        max_concurrency=8
    )

    # Test sas token upload
    mock_blob_service.reset_mock()
    upload_azure_file(
        'name.vhd',
        'container',
        'file.vhdfixed.xz',
        'storage',
        max_retry_attempts=5,
        max_workers=8,
        sas_token='sas_token',
        is_page_blob=True
    )
    mock_blob_service.assert_called_once_with(
        account_url='https://storage.blob.core.windows.net',
        credential='sas_token'
    )

    # Test image blob create exception
    system_image_file_type.is_xz.return_value = False
    blob_client.upload_blob.side_effect = Exception

    # Assert raises exception if create blob fails
    with raises(MashAzureUtilsException):
        upload_azure_file(
            'name.vhd',
            'container',
            'file.vhdfixed.xz',
            'storage',
            max_retry_attempts=5,
            max_workers=8,
            credentials=credentials,
            resource_group='group_name'
        )

    # Assert raises exception if missing required args
    with raises(MashAzureUtilsException):
        upload_azure_file(
            'name.vhd',
            'container',
            'file.vhdfixed.xz',
            'storage',
            max_retry_attempts=5,
            max_workers=8,
            is_page_blob=True
        )


@patch('mash.utils.azure.BlobServiceClient')
def test_get_blob_service_with_sas_token(mock_blob_service):
    blob_service = MagicMock()
    mock_blob_service.return_value = blob_service
    service = get_blob_service_with_sas_token('storage', 'sas_token')
    assert service == blob_service


@patch('mash.utils.azure.ClientSecretCredential')
def test_get_client_from_json(mock_cred_client):
    cred = MagicMock()
    client = MagicMock()
    mock_cred_client.return_value = cred

    get_client_from_json(client, creds)

    mock_cred_client.assert_called_once_with(
        tenant_id=creds['tenantId'],
        client_id=creds['clientId'],
        client_secret=creds['clientSecret']
    )
