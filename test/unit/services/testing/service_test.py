from pytest import raises
from unittest.mock import MagicMock, Mock, patch

from amqpstorm import AMQPError
from apscheduler.jobstores.base import JobLookupError

from mash.services.base_service import BaseService
from mash.services.testing.service import TestingService
from mash.services.testing.ec2_job import EC2TestingJob

open_name = "builtins.open"


class TestIPATestingService(object):

    @patch.object(BaseService, '__init__')
    def setup(
        self, mock_base_init
    ):
        mock_base_init.return_value = None

        self.config = Mock()
        self.config.config_data = None
        self.channel = Mock()
        self.channel.basic_ack.return_value = None

        self.tag = Mock()
        self.method = {'delivery_tag': self.tag}

        self.message = MagicMock(
            channel=self.channel,
            method=self.method,
        )

        self.testing = TestingService()
        self.testing.jobs = {}
        self.testing.log = Mock()
        self.testing.service_exchange = 'testing'
        self.testing.service_queue = 'service'
        self.testing.job_document_key = 'job_document'

        self.error_message = '{"testing_result": ' \
            '{"id": "1", "status": "error"}}'
        self.status_message = '{"testing_result": ' \
            '{"cloud_image_name": "image123", "id": "1", ' \
            '"source_regions": {"us-east-2": "test-account"}, ' \
            '"status": "success"}}'

    @patch.object(TestingService, 'set_logfile')
    @patch.object(TestingService, 'stop')
    @patch.object(TestingService, 'start')
    @patch.object(TestingService, 'restart_jobs')
    @patch('mash.services.testing.service.TestingConfig')
    @patch.object(TestingService, '_process_message')
    @patch.object(TestingService, 'consume_queue')
    def test_testing_post_init(
        self, mock_consume_queue, mock_process_message,
        mock_testing_config, mock_restart_jobs,
        mock_start, mock_stop, mock_set_logfile
    ):
        mock_testing_config.return_value = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/testing_service.log'

        self.testing.post_init()

        self.config.get_log_file.assert_called_once_with()
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/testing_service.log'
        )
        mock_consume_queue.assert_called_once_with(mock_process_message)
        mock_start.assert_called_once_with()
        mock_stop.assert_called_once_with()

    @patch.object(TestingService, 'set_logfile')
    @patch.object(TestingService, 'stop')
    @patch.object(TestingService, 'start')
    @patch.object(TestingService, 'restart_jobs')
    @patch('mash.services.testing.service.TestingConfig')
    @patch.object(TestingService, '_handle_jobs')
    @patch.object(TestingService, 'consume_queue')
    def test_testing_post_init_exceptions(
        self, mock_consume_queue, mock_handle_jobs,
        mock_testing_config, mock_restart_jobs,
        mock_start, mock_stop, mock_set_logfile
    ):
        mock_testing_config.return_value = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/testing_service.log'

        mock_start.side_effect = KeyboardInterrupt()

        self.testing.post_init()

        mock_stop.assert_called_once_with()
        mock_start.side_effect = Exception()
        mock_stop.reset_mock()
        with raises(Exception):
            self.testing.post_init()

        mock_stop.assert_called_once_with()

    @patch.object(TestingService, '_create_job')
    def test_testing_add_job(self, mock_create_job):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': '1', 'provider': 'EC2'}

        self.testing._add_job({'id': '1', 'provider': 'EC2'})

        mock_create_job.assert_called_once_with(
            EC2TestingJob, {'id': '1', 'provider': 'EC2'}
        )

    def test_testing_add_job_exists(self):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': '1'}

        self.testing.jobs['1'] = Mock()
        self.testing._add_job({'id': '1', 'provider': 'EC2'})

        self.testing.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': '1'}
        )

    def test_testing_add_job_invalid(self):
        self.testing._add_job({'id': '1', 'provider': 'fake'})
        self.testing.log.exception.assert_called_once_with(
            'Provider fake is not supported.'
        )

    @patch.object(TestingService, 'bind_listener_queue')
    @patch.object(TestingService, 'persist_job_config')
    def test_testing_create_job(
        self, mock_persist_config, mock_bind_listener_queue
    ):
        mock_persist_config.return_value = 'temp-config.json'

        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': '1'}

        job_class = Mock()
        job_class.return_value = job
        job_config = {'id': '1', 'provider': 'EC2'}
        self.testing._create_job(job_class, job_config)

        job_class.assert_called_once_with(id='1', provider='EC2')
        job.set_log_callback.assert_called_once_with(
            self.testing._log_job_message
        )
        assert job.config_file == 'temp-config.json'
        mock_bind_listener_queue.assert_called_once_with('1')
        self.testing.log.info.assert_called_once_with(
            'Job queued, awaiting uploader result.',
            extra={'job_id': '1'}
        )

    def test_testing_create_job_exception(self):
        job_class = Mock()
        job_class.side_effect = Exception('Cannot create job.')
        job_config = {'id': '1', 'provider': 'EC2'}

        self.testing._create_job(job_class, job_config)
        self.testing.log.exception.assert_called_once_with(
            'Invalid job configuration: Cannot create job.'
        )

    @patch.object(TestingService, 'unbind_queue')
    def test_testing_delete_job(self, mock_unbind_queue):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': '1'}

        scheduler = Mock()
        scheduler.remove_job.side_effect = JobLookupError('1')

        self.testing.scheduler = scheduler
        self.testing.jobs['1'] = job
        self.testing._delete_job('1')

        self.testing.log.info.assert_called_once_with(
            'Deleting job.',
            extra={'job_id': '1'}
        )
        scheduler.remove_job.assert_called_once_with('1')
        mock_unbind_queue.assert_called_once_with(
            'service', 'testing', '1'
        )

    @patch.object(TestingService, '_delete_job')
    @patch.object(TestingService, '_publish_message')
    def test_testing_cleanup_job(self, mock_publish_message, mock_delete_job):
        job = Mock()
        job.id = '1'
        job.status = "success"
        job.image_id = 'image123'
        job.utctime = 'now'
        job.get_metadata.return_value = {'job_id': '1'}

        self.testing.jobs['1'] = job
        self.testing._cleanup_job(job, 1)

        self.testing.log.warning.assert_called_once_with(
            'Failed upstream.',
            extra={'job_id': '1'}
        )
        mock_delete_job.assert_called_once_with('1')
        mock_publish_message.assert_called_once_with(job)

    def test_testing_delete_invalid_job(self):
        self.testing._delete_job('1')

        self.testing.log.warning.assert_called_once_with(
            'Job deletion failed, job is not queued.',
            extra={'job_id': '1'}
        )

    @patch.object(TestingService, '_validate_job')
    @patch.object(TestingService, '_add_job')
    def test_testing_handle_jobs_add(
        self, mock_add_job, mock_validate_job
    ):
        self.message.body = '{"testing_job": {"id": "1"}}'
        self.testing._handle_jobs(self.message)

        mock_validate_job.assert_called_once_with({'id': '1'})
        self.message.ack.assert_called_once_with()
        mock_add_job.assert_called_once_with({'id': '1'})

    @patch.object(TestingService, '_notify_invalid_config')
    def test_testing_handle_jobs_invalid(self, mock_notify):
        self.message.body = '{"testing_job_update": {"id": "1"}}'

        self.testing._handle_jobs(self.message)

        self.message.ack.assert_called_once_with()
        self.testing.log.error.assert_called_once_with(
            'Invalid testing job: Desc must contain '
            'testing_job key.'
        )
        mock_notify.assert_called_once_with(self.message.body)

    @patch.object(TestingService, '_notify_invalid_config')
    def test_testing_handle_jobs_format(self, mock_notify):
        self.message.body = 'Invalid format.'
        self.testing._handle_jobs(self.message)

        self.message.ack.assert_called_once_with()
        self.testing.log.error.assert_called_once_with(
            'Invalid job config file: Expecting value:'
            ' line 1 column 1 (char 0).'
        )
        mock_notify.assert_called_once_with(self.message.body)

    @patch.object(TestingService, '_validate_job')
    @patch.object(TestingService, '_notify_invalid_config')
    def test_testing_handle_jobs_fail_validation(
        self, mock_notify, mock_validate_job
    ):
        mock_validate_job.return_value = False
        self.message.body = '{"testing_job": {"id": "1"}}'
        self.testing._handle_jobs(self.message)

        self.message.ack.assert_called_once_with()
        mock_notify.assert_called_once_with(self.message.body)

    def test_testing_get_status_message(self):
        job = Mock()
        job.id = '1'
        job.status = "success"
        job.cloud_image_name = 'image123'
        job.source_regions = {'us-east-2': 'test-account'}

        data = self.testing._get_status_message(job)
        assert data == self.status_message

    def test_testing_log_job_message(self):
        self.testing._log_job_message('Test message', {'job_id': '1'})

        self.testing.log.info.assert_called_once_with(
            'Test message',
            extra={'job_id': '1'}
        )

    @patch.object(TestingService, '_publish')
    def test_testing_notify(self, mock_publish):
        self.testing._notify_invalid_config('invalid')
        mock_publish.assert_called_once_with(
            'jobcreator',
            'invalid_config',
            'invalid'
        )

    @patch.object(TestingService, '_publish')
    def test_testing_notify_exception(self, mock_publish):
        mock_publish.side_effect = AMQPError('Broken')
        self.testing._notify_invalid_config('invalid')

        self.testing.log.warning.assert_called_once_with(
            'Message not received: {0}'.format('invalid')
        )

    @patch.object(TestingService, '_test_image')
    def test_testing_process_message_listener_event(self, mock_test_image):
        self.method['routing_key'] = 'listener_1'
        self.testing._process_message(self.message)

        mock_test_image.assert_called_once_with(self.message)

    @patch.object(TestingService, '_handle_jobs')
    def test_testing_process_message_job_document(self, mock_handle_jobs):
        self.method['routing_key'] = 'job_document'
        self.testing._process_message(self.message)

        mock_handle_jobs.assert_called_once_with(self.message)

    @patch.object(TestingService, '_delete_job')
    @patch.object(TestingService, '_publish')
    @patch.object(TestingService, '_get_status_message')
    @patch.object(TestingService, 'bind_queue')
    def test_testing_process_test_result(
        self, mock_bind_queue, mock_get_status_message,
        mock_publish, mock_delete_job
    ):
        mock_get_status_message.return_value = self.status_message

        event = Mock()
        event.job_id = '1'
        event.exception = None

        job = Mock()
        job.id = '1'
        job.utctime = 'now'
        job.status = "success"
        job.iteration_count = 1
        job.get_metadata.return_value = {'job_id': '1'}

        self.testing.jobs['1'] = job
        self.testing._process_test_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.testing.log.info.assert_called_once_with(
            'Pass[1]: Testing successful.',
            extra={'job_id': '1'}
        )
        mock_get_status_message.assert_called_once_with(job)
        mock_bind_queue.assert_called_once_with('publisher', '1', 'service')
        mock_publish.assert_called_once_with(
            'publisher', '1', self.status_message
        )

    def test_testing_process_test_result_exception(self):
        event = Mock()
        event.job_id = '1'
        event.exception = 'Broken!'

        job = Mock()
        job.utctime = 'always'
        job.status = "exception"
        job.iteration_count = 1
        job.get_metadata.return_value = {'job_id': '1'}

        message = Mock()
        job.listener_msg = message

        self.testing.jobs['1'] = job
        self.testing._process_test_result(event)

        self.testing.log.error.assert_called_once_with(
            'Pass[1]: Exception testing image: Broken!',
            extra={'job_id': '1'}
        )
        message.ack.assert_called_once_with()

    @patch.object(TestingService, '_delete_job')
    @patch.object(TestingService, 'publish_job_result')
    @patch.object(TestingService, '_get_status_message')
    def test_testing_process_test_result_fail(
        self, mock_get_status_message,
        mock_publish, mock_delete_job
    ):
        mock_get_status_message.return_value = self.error_message

        event = Mock()
        event.job_id = '1'
        event.exception = None

        job = Mock()
        job.id = '1'
        job.cloud_image_name = 'image123'
        job.source_regions = {'us-east-2': 'test-account'}
        job.status = "error"
        job.utctime = 'now'
        job.iteration_count = 1
        job.get_metadata.return_value = {'job_id': '1'}

        self.testing.jobs['1'] = job
        self.testing._process_test_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.testing.log.error.assert_called_once_with(
            'Pass[1]: Error occurred testing image with IPA.',
            extra={'job_id': '1'}
        )
        mock_get_status_message.assert_called_once_with(job)
        mock_publish.assert_called_once_with(
            'publisher', '1', self.error_message
        )

    @patch.object(TestingService, 'bind_queue')
    @patch.object(TestingService, '_publish')
    def test_testing_publish_message(self, mock_publish, mock_bind_queue):
        job = Mock()
        job.id = '1'
        job.status = "success"
        job.cloud_image_name = 'image123'
        job.source_regions = {'us-east-2': 'test-account'}

        self.testing._publish_message(job)
        mock_bind_queue.assert_called_once_with('publisher', '1', 'service')
        mock_publish.assert_called_once_with(
            'publisher', '1', self.status_message
        )

    @patch.object(TestingService, 'bind_queue')
    @patch.object(TestingService, '_publish')
    def test_testing_publish_message_exception(
        self, mock_publish, mock_bind_queue
    ):
        job = Mock()
        job.image_id = 'image123'
        job.id = '1'
        job.status = "error"
        job.get_metadata.return_value = {'job_id': '1'}

        mock_publish.side_effect = AMQPError('Broken')
        self.testing._publish_message(job)

        mock_bind_queue.assert_called_once_with('publisher', '1', 'service')
        self.testing.log.warning.assert_called_once_with(
            'Message not received: {0}'.format(self.error_message),
            extra={'job_id': '1'}
        )

    def test_testing_run_test(self):
        job = Mock()
        job.provider = 'EC2'
        job.account = 'test_account'
        job.distro = 'SLES'
        job.image_id = 'image123'
        job.tests = 'test1,test2'
        self.testing.jobs['1'] = job
        self.testing.host = 'localhost'

        self.testing._run_test('1')
        job.test_image.assert_called_once_with(host='localhost')

    @patch.object(TestingService, '_validate_listener_msg')
    @patch.object(TestingService, '_run_test')
    def test_testing_test_image(
        self, mock_run_test, mock_validate_listener_msg
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.testing.jobs['1'] = job

        mock_validate_listener_msg.return_value = job

        scheduler = Mock()
        self.testing.scheduler = scheduler

        self.message.body = \
            '{"uploader_result": {"id": "1", ' \
            '"image_id": "image123", "status": "success"}}'

        self.testing._test_image(self.message)

        scheduler.add_job.assert_called_once_with(
            mock_run_test,
            args=('1',),
            id='1',
            max_instances=1,
            misfire_grace_time=None,
            coalesce=True
        )

    @patch.object(TestingService, '_validate_listener_msg')
    def test_testing_test_image_no_job(self, mock_validate_listener_msg):
        mock_validate_listener_msg.return_value = None

        self.message.body = '{"uploader_result": {"id": "1"}}'
        self.testing._test_image(self.message)

        self.message.ack.assert_called_once_with()

    def test_testing_validate_job(self):
        job_config = {
            'id': '1',
            'provider': 'EC2',
            'tests': 'test_stuff',
            'utctime': 'now',
            'test_regions': {'us-east-2': 'test-account'}
        }

        result = self.testing._validate_job(job_config)
        assert result

    def test_testing_validate_no_provider(self):
        job = {
            'account': 'account',
            'id': '1',
            'tests': 'test_stuff',
            'utctime': 'now'
        }

        self.testing._validate_job(job)
        self.testing.log.error.assert_called_once_with(
            'provider is required in testing job config.'
        )

    def test_testing_validate_listener_msg(self):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.testing.jobs['1'] = job

        self.message.body = \
            '{"uploader_result": {"id": "1", ' \
            '"cloud_image_name": "My image", ' \
            '"source_regions": {"us-east-2":"test-account"}, ' \
            '"status": "success"}}'
        result = self.testing._validate_listener_msg(self.message.body)

        assert result == job
        assert job.cloud_image_name == 'My image'
        assert job.source_regions == {'us-east-2': 'test-account'}

    @patch.object(TestingService, '_cleanup_job')
    def test_testing_validate_listener_msg_failed(self, mock_cleanup_job):
        job = Mock()
        job.utctime = 'always'
        self.testing.jobs['1'] = job

        self.message.body = \
            '{"uploader_result": {"id": "1", ' \
            '"image_id": "image123", "status": "error"}}'
        self.testing._validate_listener_msg(self.message.body)

        mock_cleanup_job.assert_called_once_with(job, 'error')

    def test_testing_validate_listener_msg_invalid(self):
        self.message.body = ''
        result = self.testing._validate_listener_msg(self.message.body)

        assert result is None
        self.testing.log.error.assert_called_once_with(
            'Invalid uploader result file: '
        )

    def test_testing_validate_listener_msg_job_invalid(self):
        self.message.body = '{"uploader_result": {"id": "2"}}'
        result = self.testing._validate_listener_msg(self.message.body)

        assert result is None
        self.testing.log.error.assert_called_once_with(
            'Invalid testing service job with id: 2.'
        )

    def test_testing_validate_listener_msg_no_id(self):
        self.message.body = '{"uploader_result": {"provider": "EC2"}}'
        result = self.testing._validate_listener_msg(self.message.body)

        assert result is None
        self.testing.log.error.assert_called_once_with(
            'id is required in uploader result.'
        )

    def test_testing_validate_listener_msg_no_source_regions(self):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.testing.jobs['1'] = job

        self.message.body = \
            '{"uploader_result": {"id": "1", ' \
            '"cloud_image_name": "My image", "status": "success"}}'
        result = self.testing._validate_listener_msg(self.message.body)

        assert result is None
        self.testing.log.error.assert_called_once_with(
            'source_regions is required in uploader result.'
        )

    def test_testing_start(self):
        scheduler = Mock()
        self.testing.scheduler = scheduler

        self.channel.consumer_tags = []
        self.testing.channel = self.channel

        self.testing.start()
        scheduler.start.assert_called_once_with()
        self.channel.start_consuming.assert_called_once_with()

    @patch.object(TestingService, '_open_connection')
    def test_testing_start_exception(self, mock_open_connection):
        scheduler = Mock()
        self.testing.scheduler = scheduler
        self.channel.start_consuming.side_effect = [AMQPError('Broken!'), None]
        self.channel.consumer_tags = []
        self.testing.channel = self.channel

        self.testing.start()
        self.testing.log.warning.assert_called_once_with('Broken!')
        mock_open_connection.assert_called_once_with()

    @patch.object(TestingService, 'close_connection')
    def test_testing_stop(self, mock_close_connection):
        scheduler = Mock()
        self.testing.scheduler = scheduler

        self.testing.stop()
        scheduler.shutdown.assert_called_once_with()
        mock_close_connection.assert_called_once_with()
