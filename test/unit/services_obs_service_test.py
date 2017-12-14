from unittest.mock import patch
from unittest.mock import call
from unittest.mock import Mock

from .test_helper import (
    patch_open,
    context_manager
)

from mash.services.obs.service import OBSImageBuildResultService
from mash.services.base_service import BaseService


class TestOBSImageBuildResultService(object):
    @patch('mash.services.obs.service.OBSConfig')
    @patch('mash.services.base_service.BaseService.set_logfile')
    @patch('mash.services.obs.service.mkpath')
    @patch('mash.services.obs.service.pickle.load')
    @patch.object(OBSImageBuildResultService, '_start_job')
    @patch.object(OBSImageBuildResultService, '_control_in')
    @patch.object(OBSImageBuildResultService, '_send_job_response')
    @patch.object(OBSImageBuildResultService, '_send_listen_response')
    @patch.object(BaseService, '__init__')
    @patch('os.listdir')
    @patch('logging.getLogger')
    @patch('atexit.register')
    @patch_open
    def setup(
        self, mock_open, mock_register, mock_log, mock_listdir,
        mock_BaseService, mock_send_listen_response, mock_send_job_response,
        mock_control_in, mock_start_job,
        mock_pickle_load, mock_mkpath, mock_set_logfile,
        mock_OBSConfig
    ):
        job_worker = Mock()
        mock_pickle_load.return_value = job_worker
        config = Mock()
        config.get_log_file.return_value = 'logfile'
        mock_OBSConfig.return_value = config
        self.log = Mock()
        context = context_manager()
        mock_open.return_value = context.context_manager_mock
        mock_listdir.return_value = ['job']
        mock_BaseService.return_value = None

        self.obs_result = OBSImageBuildResultService()
        self.obs_result.log = self.log
        self.obs_result.consume_queue = Mock()
        self.obs_result.bind_service_queue = Mock()
        self.obs_result.channel = Mock()
        self.obs_result.channel.is_open = True
        self.obs_result.close_connection = Mock()

        self.obs_result.post_init()

        mock_set_logfile.assert_called_once_with('logfile')

        mock_mkpath.assert_called_once_with('/var/tmp/mash/obs_jobs/')
        mock_open.assert_called_once_with(
            '/var/tmp/mash/obs_jobs_done/job', 'rb'
        )
        mock_start_job.assert_called_once_with(
            '/var/tmp/mash/obs_jobs//job'
        )
        mock_pickle_load.assert_called_once_with(context.file_mock)
        job_worker.set_log_handler.assert_called_once_with(
            mock_send_job_response
        )
        job_worker.set_result_handler.assert_called_once_with(
            mock_send_listen_response
        )
        self.obs_result.consume_queue.assert_called_once_with(
            mock_control_in,
            self.obs_result.bind_service_queue.return_value
        )
        self.obs_result.channel.start_consuming.assert_called_once_with()

        self.obs_result.channel.start_consuming.side_effect = Exception
        self.obs_result.post_init()
        self.obs_result.channel.stop_consuming.assert_called_once_with()
        self.obs_result.close_connection.assert_called_once_with()
        self.obs_result.channel.reset_mock()

        mock_pickle_load.side_effect = Exception('error')
        self.obs_result.post_init()
        self.log.error.assert_called_once_with(
            'Could not reload job: error'
        )
        self.log.reset_mock()

    def test_send_job_response(self):
        self.obs_result._send_job_response('815', {})
        self.obs_result.log.info.assert_called_once_with(
            {}, extra={'job_id': '815'}
        )

    @patch.object(BaseService, 'bind_listener_queue')
    @patch.object(BaseService, 'publish_listener_message')
    @patch.object(OBSImageBuildResultService, '_send_control_response')
    def test_send_listen_response(
        self, mock_send_control_response,
        mock_publish_listener_message, mock_bind_listener_queue
    ):
        self.obs_result.clients['815'] = Mock()
        self.obs_result._send_listen_response('815', {})
        mock_bind_listener_queue.assert_called_once_with('815')
        mock_publish_listener_message.assert_called_once_with('815', '{}')
        assert '815' not in self.obs_result.clients
        self.obs_result.clients['815'] = Mock()
        mock_bind_listener_queue.side_effect = Exception
        self.obs_result._send_listen_response('815', {})
        assert '815' in self.obs_result.clients

    def test_send_control_response_local(self):
        result = {
            'message': 'message',
            'ok': False
        }
        self.obs_result._send_control_response(result, '4711')
        self.obs_result.log.error.assert_called_once_with(
            'message',
            extra={'job_id': '4711'}
        )

    def test_send_control_response_public(self):
        result = {
            'message': 'message',
            'ok': True
        }
        self.obs_result._send_control_response(result)
        self.obs_result.log.info.assert_called_once_with(
            'message',
            extra={}
        )

    @patch.object(OBSImageBuildResultService, '_delete_job')
    @patch.object(OBSImageBuildResultService, '_add_job')
    @patch.object(OBSImageBuildResultService, '_add_to_listener')
    @patch.object(OBSImageBuildResultService, '_send_control_response')
    def test_control_in(
        self, mock_send_control_response, mock_add_to_listener,
        mock_add_job, mock_delete_job
    ):
        message = Mock()
        message.body = '{"obsjob":{"id": "4711","project": ' + \
            '"Virtualization:Appliances:Images:Testing_x86","image": ' + \
            '"test-image-docker","utctime": "always"}}'
        self.obs_result._control_in(message)
        message.ack.assert_called_once_with()
        mock_add_job.assert_called_once_with(
            {
                'obsjob': {
                    'project': 'Virtualization:Appliances:Images:Testing_x86',
                    'image': 'test-image-docker',
                    'id': '4711',
                    'utctime': 'always'
                }
            }
        )
        message.body = '{"obsjob_listen": "4711"}'
        self.obs_result._control_in(message)
        mock_add_to_listener.assert_called_once_with(
            '4711'
        )
        message.body = '{"obsjob_delete": "4711"}'
        self.obs_result._control_in(message)
        mock_delete_job.assert_called_once_with(
            '4711'
        )
        message.body = '{"job_delete": "4711"}'
        self.obs_result._control_in(message)
        message.body = 'foo'
        self.obs_result._control_in(message)
        assert mock_send_control_response.call_args_list == [
            call(mock_add_job.return_value, '4711'),
            call(mock_add_to_listener.return_value, '4711'),
            call(mock_delete_job.return_value, '4711'),
            call(
                {
                    'message':
                        "No idea what to do with: {'job_delete': '4711'}",
                    'ok': False
                },
                None
            ),
            call(
                {
                    'message':
                        'JSON:deserialize error: foo : ' +
                        'Expecting value: line 1 column 1 (char 0)',
                    'ok': False
                }
            )
        ]

    def test_add_to_listener(self):
        assert self.obs_result._add_to_listener('815') == {
            'message': 'Job does not exist, can not add to listen pipeline',
            'ok': False
        }
        job = Mock()
        self.obs_result.jobs = {'815': job}
        assert self.obs_result._add_to_listener('815') == {
            'message': 'Job now in listen pipeline', 'ok': True
        }
        job.call_result_handler.assert_called_once_with()

    @patch.object(OBSImageBuildResultService, '_validate_job_description')
    @patch.object(OBSImageBuildResultService, '_start_job')
    @patch('mash.services.obs.service.NamedTemporaryFile')
    @patch_open
    def test_add_job(
        self, mock_open, mock_NamedTemporaryFile,
        mock_start_job, mock_validate_job_description
    ):
        job_data = {
            "obsjob": {
                "id": "123",
                "project": "Virtualization:Appliances:Images:Testing_x86",
                "image": "test-image-oem",
                "utctime": "now",
                "conditions": [
                    {"package": ["kernel-default", ">=4.13.1", ">=1.1"]},
                    {"image": "1.42.1"}
                ]
            }
        }
        tempfile = Mock()
        tempfile.name = 'tempfile'
        mock_NamedTemporaryFile.return_value = tempfile
        context = context_manager()
        mock_open.return_value = context.context_manager_mock
        job_info = {
            'ok': False
        }
        mock_validate_job_description.return_value = job_info
        assert self.obs_result._add_job(job_data) == job_info
        job_info = {
            'ok': True
        }
        mock_validate_job_description.return_value = job_info
        self.obs_result._add_job(job_data)
        assert context.file_mock.write.called
        mock_start_job.assert_called_once_with('tempfile')
        assert mock_validate_job_description.call_args_list == [
            call(job_data), call(job_data)
        ]

    @patch('os.remove')
    def test_delete_job(self, mock_os_remove):
        assert self.obs_result._delete_job('815') == {
            'message': 'Job does not exist, can not delete it', 'ok': False
        }
        job_worker = Mock()
        job_worker.job_file = 'job_file'
        self.obs_result.clients = {'815': None}
        self.obs_result.jobs = {'815': job_worker}
        assert self.obs_result._delete_job('815') == {
            'message': 'Job Deleted', 'ok': True
        }
        mock_os_remove.assert_called_once_with('job_file')
        job_worker.stop_watchdog.assert_called_once_with()
        assert '815' not in self.obs_result.clients
        assert '815' not in self.obs_result.jobs
        self.obs_result.jobs = {'815': job_worker}
        mock_os_remove.side_effect = Exception('remove_error')
        assert self.obs_result._delete_job('815') == {
            'message': 'Job deletion failed: remove_error', 'ok': False
        }

    @patch('mash.services.obs.service.dateutil.parser.parse')
    def test_validate_job_description(self, mock_dateutil_parse):
        mock_dateutil_parse.side_effect = Exception('mytime')
        job_data = {}
        assert self.obs_result._validate_job_description(job_data) == {
            'message': 'Invalid job: no obsjob', 'ok': False
        }
        job_data = {"obsjob": {}}
        assert self.obs_result._validate_job_description(job_data) == {
            'message': 'Invalid job: no job id', 'ok': False
        }
        job_data = {"obsjob": {"id": "123"}}
        assert self.obs_result._validate_job_description(job_data) == {
            'message': 'Invalid job: no image name', 'ok': False
        }
        job_data = {"obsjob": {"id": "123", "image": "foo"}}
        assert self.obs_result._validate_job_description(job_data) == {
            'message': 'Invalid job: no project name', 'ok': False
        }
        job_data = {"obsjob": {"id": "123", "image": "foo", "project": "foo"}}
        assert self.obs_result._validate_job_description(job_data) == {
            'message': 'Invalid job: no time given', 'ok': False
        }
        job_data = {
            "obsjob": {
                "id": "123", "image": "foo",
                "project": "foo", "utctime": "mytime"
            }
        }
        assert self.obs_result._validate_job_description(job_data) == {
            'message': 'Invalid job time: mytime', 'ok': False
        }
        mock_dateutil_parse.side_effect = None
        assert self.obs_result._validate_job_description(job_data) == {
            'message': 'OK', 'ok': True
        }
        self.obs_result.jobs = {'123': None}
        assert self.obs_result._validate_job_description(job_data) == {
            'message': 'Job already exists', 'ok': False
        }

    @patch('mash.services.obs.service.OBSImageBuildResult')
    def test_start_job_with_conditions(self, mock_OBSImageBuildResult):
        job_worker = Mock()
        mock_OBSImageBuildResult.return_value = job_worker
        self.obs_result._send_job_response = Mock()
        self.obs_result._send_listen_response = Mock()
        self.obs_result._start_job('../data/job1.json')
        job_worker.set_log_handler.assert_called_once_with(
            self.obs_result._send_job_response
        )
        job_worker.set_result_handler.assert_called_once_with(
            self.obs_result._send_listen_response
        )
        job_worker.start_watchdog.assert_called_once_with(
            isotime=None, nonstop=False
        )

    @patch('mash.services.obs.service.OBSImageBuildResult')
    def test_start_job_without_conditions(self, mock_OBSImageBuildResult):
        job_worker = Mock()
        mock_OBSImageBuildResult.return_value = job_worker
        self.obs_result._start_job('../data/job2.json')
        job_worker.start_watchdog.assert_called_once_with(
            isotime=None, nonstop=True
        )

    @patch('mash.services.obs.service.OBSImageBuildResult')
    def test_start_job_at_utctime(self, mock_OBSImageBuildResult):
        job_worker = Mock()
        mock_OBSImageBuildResult.return_value = job_worker
        self.obs_result._start_job('../data/job3.json')
        job_worker.start_watchdog.assert_called_once_with(
            isotime='2017-10-11T17:50:26+00:00', nonstop=False
        )
