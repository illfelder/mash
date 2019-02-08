from pytest import raises
from unittest.mock import Mock, patch

from mash.services.deprecation.deprecation_job import DeprecationJob


class TestDeprecationJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'deprecation',
            'cloud': 'ec2',
            'old_cloud_image_name': 'old_image_123',
            'utctime': 'now'
        }

    def test_valid_job(self):
        job = DeprecationJob(**self.job_config)

        assert job.id == '1'
        assert job.cloud == 'ec2'
        assert job.utctime == 'now'

    def test_deprecate(self):
        job = DeprecationJob(**self.job_config)
        with raises(NotImplementedError):
            job._deprecate()

    @patch.object(DeprecationJob, '_deprecate')
    def test_deprecate_image(self, mock_deprecate):
        job = DeprecationJob(**self.job_config)
        job.log_callback = Mock()
        job.process_job()

        mock_deprecate.assert_called_once_with()
