import io
import json
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
import ssl

from terminal.notifications import NotificationError, Telegram, TelegramDeliveryError, validate_credentials, NoTelegramRedirect


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

    def test_http_failures_have_fixed_actionable_diagnostics(self):
        credentials=Mock();credentials.load.return_value=self.secret()
        for status,description,expected in [(401,'untrusted detail','token'),(403,'untrusted detail','forbidden'),
                (400,'Bad Request: chat not found','chat'),(400,'untrusted detail','unknown'),
                (429,'untrusted detail','rate'),(503,'untrusted detail','server'),(404,'untrusted detail','unknown')]:
            with self.subTest(status=status,description=description):
                body=io.BytesIO(json.dumps({'ok':False,'error_code':status,'description':description,'private':self.secret()}).encode())
                opener=Mock();opener.open.side_effect=HTTPError('https://api.telegram.org/bot'+self.secret()['token'],status,self.secret()['chat_id'],{},body)
                with self.assertRaises(TelegramDeliveryError) as raised:Telegram(credentials,opener).send('Test')
                self.assertEqual(raised.exception.code,expected)
                self.assertNotIn('untrusted detail',str(raised.exception))
                for value in self.secret().values():self.assertNotIn(value,str(raised.exception))
                self.assertTrue(body.closed)
                self.assertTrue(raised.exception.__suppress_context__)

    def test_forbidden_distinguishes_telegram_rejections_from_intermediaries(self):
        credentials=Mock();credentials.load.return_value=self.secret()
        for description,expected in [('Forbidden: bot was blocked by the user','blocked'),
                ("Forbidden: bot can't initiate conversation with a user",'not_started'),
                ("Forbidden: bot can't send messages to bots",'bot_recipient'),('unknown response','forbidden')]:
            body=json.dumps({'ok':False,'error_code':403,'description':description}).encode()
            opener=Mock();opener.open.side_effect=HTTPError('private URL',403,'private reason',{},io.BytesIO(body))
            with self.assertRaises(TelegramDeliveryError) as raised:Telegram(credentials,opener).send('Test')
            self.assertEqual(raised.exception.code,expected)
        opener=Mock();opener.open.side_effect=HTTPError('private URL',403,'private reason',{},io.BytesIO(b'<html>Forbidden</html>'))
        with self.assertRaises(TelegramDeliveryError) as raised:Telegram(credentials,opener).send('Test')
        self.assertEqual(raised.exception.code,'http_forbidden')

    def test_tls_timeout_and_oversized_errors_are_bounded(self):
        credentials=Mock();credentials.load.return_value=self.secret()
        for error,expected in [(URLError(ssl.SSLCertVerificationError('private detail')),'tls'),(TimeoutError('private detail'),'network'),
                (HTTPError('private URL',400,'private reason',{},io.BytesIO(b'x'*65537)),'unknown')]:
            opener=Mock();opener.open.side_effect=error
            with self.assertRaises(TelegramDeliveryError) as raised:Telegram(credentials,opener).send('Test')
            self.assertEqual(raised.exception.code,expected)
            self.assertNotIn('private',str(raised.exception))
