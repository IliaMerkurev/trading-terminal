import io
import json
import unittest
from unittest.mock import Mock
from urllib.error import URLError

from terminal.notifications import NotificationError, Telegram, validate_credentials, NoTelegramRedirect


class NotificationTests(unittest.TestCase):
    def secret(self):
        return {'token':str(1234567)+':'+'x'*35,'chat_id':str(-123456789)}

    def test_send_uses_post_and_does_not_return_secrets(self):
        credentials=Mock();credentials.load.return_value=self.secret()
        opener=Mock();opener.open.return_value=io.BytesIO(b'{"ok":true}')
        telegram=Telegram(credentials,opener)
        self.assertIsNone(telegram.send('Trading Terminal: synthetic notification test'))
        req=opener.open.call_args.args[0]
        self.assertEqual(req.method,'POST')
        self.assertEqual(json.loads(req.data)['chat_id'],self.secret()['chat_id'])
        self.assertEqual(telegram.status(),{'configured':True,'storage':'Windows Credential Manager'})

    def test_provider_and_network_errors_never_expose_secret_values(self):
        credentials=Mock();credentials.load.return_value=self.secret()
        for error in (URLError('https://api.telegram.org/bot'+self.secret()['token']),RuntimeError(self.secret()['chat_id'])):
            opener=Mock();opener.open.side_effect=error
            with self.assertRaises(NotificationError) as raised:Telegram(credentials,opener).send('Synthetic test')
            self.assertNotIn(self.secret()['token'],str(raised.exception))
            self.assertNotIn(self.secret()['chat_id'],str(raised.exception))
            self.assertTrue(raised.exception.__suppress_context__)

    def test_rejected_response_redirect_and_unconfigured(self):
        credentials=Mock();credentials.load.return_value=None
        with self.assertRaises(NotificationError):Telegram(credentials).send('Test')
        credentials.load.return_value=self.secret()
        opener=Mock();opener.open.return_value=io.BytesIO(b'{"ok":false,"description":"provider detail"}')
        with self.assertRaisesRegex(NotificationError,'delivery failed'):Telegram(credentials,opener).send('Test')
        with self.assertRaises(NotificationError):NoTelegramRedirect().redirect_request(None)

    def test_validation_does_not_echo_untrusted_values(self):
        with self.assertRaises(NotificationError) as raised:validate_credentials('sensitive invalid value','private chat value')
        self.assertNotIn('sensitive',str(raised.exception))
        with self.assertRaises(NotificationError):validate_credentials(self.secret()['token'],'https://example.com')
