from unittest.mock import patch, Mock

from mash.mash_exceptions import MashDeprecationException
from mash.services.deprecation_service import main


class TestDeprecationServiceMain(object):
    @patch('mash.services.deprecation_service.BaseJobFactory')
    @patch('mash.services.deprecation_service.BaseConfig')
    @patch('mash.services.deprecation_service.ListenerService')
    def test_main(self, mock_deprecation_service, mock_config, mock_factory):
        config = Mock()
        mock_config.return_value = config

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_deprecation_service.assert_called_once_with(
            service_exchange='deprecation',
            config=config,
            custom_args={
                'listener_msg_args': ['source_regions'],
                'job_factory': factory
            }
        )

    @patch('mash.services.deprecation_service.BaseJobFactory')
    @patch('mash.services.deprecation_service.BaseConfig')
    @patch('mash.services.deprecation_service.ListenerService')
    @patch('sys.exit')
    def test_deprecation_main_mash_error(
        self, mock_exit, mock_deprecation_service, mock_config, mock_factory
    ):
        config = Mock()
        mock_config.return_value = config

        factory = Mock()
        mock_factory.return_value = factory

        mock_deprecation_service.side_effect = MashDeprecationException(
            'error'
        )

        main()

        mock_deprecation_service.assert_called_once_with(
            service_exchange='deprecation',
            config=config,
            custom_args={
                'listener_msg_args': ['source_regions'],
                'job_factory': factory
            }
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.deprecation_service.BaseConfig')
    @patch('mash.services.deprecation_service.ListenerService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_deprecation_service, mock_config
    ):
        mock_deprecation_service.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.deprecation_service.BaseConfig')
    @patch('mash.services.deprecation_service.ListenerService')
    @patch('sys.exit')
    def test_deprecation_main_system_exit(
        self, mock_exit, mock_deprecation_service, mock_config
    ):
        mock_deprecation_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(mock_deprecation_service.side_effect)

    @patch('mash.services.deprecation_service.BaseConfig')
    @patch('mash.services.deprecation_service.ListenerService')
    @patch('sys.exit')
    def test_deprecation_main_unexpected_error(
        self, mock_exit, mock_deprecation_service, mock_config
    ):
        mock_deprecation_service.side_effect = Exception('Error!')

        main()
        mock_exit.assert_called_once_with(1)
