import io
import json
import sys

from mock import MagicMock, Mock, patch
from pytest import raises

from mash.mash_exceptions import MashLoggerException
from mash.services.base_service import BaseService
from mash.services.logger.config import LoggerConfig
from mash.services.logger.service import LoggerService

open_name = "__builtin__.open" if sys.version_info.major < 3 \
    else "builtins.open"


class TestLoggerService(object):

    @patch.object(BaseService, '__init__')
    def setup(
        self, mock_base_init
    ):
        mock_base_init.return_value = None

        self.config = Mock()
        self.config.get_log_file.return_value = '/tmp/file.log'

        self.message = {
            "levelname": "INFO",
            "msg": u"INFO 2017-11-01 11:36:36.782072 "
                   "LoggerService \n Job[4711]: Test log message! \n"
        }

        self.channel = Mock()
        self.channel.basic_ack.return_value = None

        self.logger = LoggerService()
        self.logger.channel = self.channel
        self.logger.close_connection = Mock()

    @patch.object(LoggerConfig, '__init__')
    @patch.object(LoggerService, '_bind_logger_queue')
    @patch.object(LoggerService, '_process_log')
    @patch.object(LoggerService, 'consume_queue')
    def test_logger_post_init(
        self, mock_consume_queue, mock_process_log,
        mock_bind_logger_queue, mock_logger_config
    ):
        mock_logger_config.return_value = None
        self.logger.post_init()
        mock_consume_queue.assert_called_once_with(
            mock_process_log, mock_bind_logger_queue.return_value
        )
        mock_bind_logger_queue.assert_called_once_with(
            queue_name='mash.logger', route='mash.logger'
        )
        self.logger.channel.start_consuming.side_effect = KeyboardInterrupt
        self.logger.post_init()
        self.logger.channel.stop_consuming.assert_called_once_with()
        self.logger.close_connection.assert_called_once_with()

    @patch.object(LoggerService, '_declare_direct_exchange')
    @patch.object(LoggerService, '_declare_queue')
    def test_logger_bind_logger_queue(
        self, mock_declare_queue, mock_declare_direct_exchange
    ):
        self.logger.channel = Mock()
        self.logger.service_exchange = 'logger'

        assert self.logger._bind_logger_queue(
            queue_name='mash.logger', route='mash.logger'
        ) == 'mash.logger'

        mock_declare_direct_exchange.assert_called_once_with('logger')
        mock_declare_queue.assert_called_once_with('mash.logger')
        self.logger.channel.queue_bind.assert_called_once_with(
            exchange='logger',
            queue='mash.logger',
            routing_key='mash.logger'
        )

    def test_logger_process_invalid_log(self):
        with raises(MashLoggerException):
            self.logger._process_log(self.channel, Mock(), Mock(), '')

    @patch('os.path.exists')
    def test_logger_process_append(
        self, mock_path_exists
    ):
        mock_path_exists.return_value = True
        self.logger.config = self.config
        self.message['job_id'] = '4711'

        with patch(open_name, create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.logger._process_log(
                self.channel, Mock(), Mock(), json.dumps(self.message)
            )
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.assert_called_with(
                u'INFO 2017-11-01 11:36:36.782072 '
                'LoggerService \n Test log message! \n'
            )

    @patch('os.path.exists')
    def test_logger_process_write_exception(
        self, mock_path_exists
    ):
        mock_path_exists.return_value = True
        self.logger.config = self.config
        self.message['job_id'] = '4711'

        with patch(open_name, create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.side_effect = Exception('Error writing file!')

            with raises(MashLoggerException):
                self.logger._process_log(
                    self.channel, Mock(), Mock(), json.dumps(self.message)
                )
