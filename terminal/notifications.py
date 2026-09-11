"""Local notification delivery with scoped Windows Credential Manager secrets.

Only fixed, safe diagnostics leave this module. In particular urllib exceptions
can contain the bot credential in a URL and must never be formatted or chained.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import re
from urllib import request


class NotificationError(ValueError):
    pass


class Credential(ctypes.Structure):
    _fields_=[('Flags',wintypes.DWORD),('Type',wintypes.DWORD),('TargetName',wintypes.LPWSTR),
              ('Comment',wintypes.LPWSTR),('LastWritten',wintypes.FILETIME),('CredentialBlobSize',wintypes.DWORD),
              ('CredentialBlob',ctypes.POINTER(ctypes.c_ubyte)),('Persist',wintypes.DWORD),
              ('AttributeCount',wintypes.DWORD),('Attributes',ctypes.c_void_p),
              ('TargetAlias',wintypes.LPWSTR),('UserName',wintypes.LPWSTR)]


class WindowsCredentials:
    def __init__(self,root):
        self.target='TradingTerminal/Telegram/'+hashlib.sha256(str(Path(root).resolve()).casefold().encode()).hexdigest()[:32]
        self.api=ctypes.WinDLL('Advapi32.dll',use_last_error=True)
        self.api.CredWriteW.argtypes=[ctypes.POINTER(Credential),wintypes.DWORD]
        self.api.CredWriteW.restype=wintypes.BOOL
        self.api.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.POINTER(Credential))]
        self.api.CredReadW.restype=wintypes.BOOL
        self.api.CredFree.argtypes=[ctypes.c_void_p]
        self.api.CredFree.restype=None
        self.api.CredDeleteW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD]
        self.api.CredDeleteW.restype=wintypes.BOOL

    def save(self,token,chat_id):
        validate_credentials(token,chat_id)
        blob=json.dumps({'token':token,'chat_id':chat_id}).encode('utf-8')
        buffer=(ctypes.c_ubyte*len(blob)).from_buffer_copy(blob)
        credential=Credential(Type=1,TargetName=self.target,CredentialBlobSize=len(blob),CredentialBlob=buffer,Persist=2,UserName='Trading Terminal')
        try:
            if not self.api.CredWriteW(ctypes.byref(credential),0):
                raise NotificationError('Windows protected credential storage failed')
        finally:
            ctypes.memset(buffer,0,len(blob))

    def load(self):
        pointer=ctypes.POINTER(Credential)()
        if not self.api.CredReadW(self.target,1,0,ctypes.byref(pointer)):
            if ctypes.get_last_error()==1168:
                return None
            raise NotificationError('Windows protected credential storage unavailable')
        try:
            value=json.loads(ctypes.string_at(pointer.contents.CredentialBlob,pointer.contents.CredentialBlobSize))
            validate_credentials(value['token'],value['chat_id'])
            return value
        except Exception:
            raise NotificationError('Stored Telegram credential cannot be read') from None
        finally:
            ctypes.memset(pointer.contents.CredentialBlob,0,pointer.contents.CredentialBlobSize)
            self.api.CredFree(pointer)

    def clear(self):
        if not self.api.CredDeleteW(self.target,1,0) and ctypes.get_last_error()!=1168:
            raise NotificationError('Stored Telegram credential could not be cleared')


def validate_credentials(token,chat_id):
    if not isinstance(token,str) or not re.fullmatch(r'[0-9]{5,16}:[A-Za-z0-9_-]{20,100}',token):
        raise NotificationError('Invalid Telegram bot credential format')
    if not isinstance(chat_id,str) or not re.fullmatch(r'-?[0-9]{1,20}',chat_id):
        raise NotificationError('Telegram chat ID must be numeric')


class NoTelegramRedirect(request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise NotificationError('Telegram redirect refused')


class Telegram:
    def __init__(self,credentials,opener=None):
        self.credentials=credentials
        self.opener=opener or request.build_opener(NoTelegramRedirect)

    def status(self):
        return {'configured':self.credentials.load() is not None,'storage':'Windows Credential Manager'}

    def send(self,text):
        if not isinstance(text,str) or not 1<=len(text)<=1000:
            raise NotificationError('Notification text exceeds the supported size')
        secret=self.credentials.load()
        if secret is None:
            raise NotificationError('Telegram is not configured')
        try:
            payload=json.dumps({'chat_id':secret['chat_id'],'text':text,'disable_web_page_preview':True}).encode()
            req=request.Request('https://api.telegram.org/bot'+secret['token']+'/sendMessage',data=payload,
                                headers={'Content-Type':'application/json'},method='POST')
            with self.opener.open(req,timeout=8) as response:
                raw=response.read(65537)
            if len(raw)>65536 or json.loads(raw).get('ok') is not True:
                raise NotificationError('Telegram delivery failed')
        except Exception:
            # Never leak exception URLs, provider response text, token or chat ID.
            raise NotificationError('Telegram delivery failed; verify configuration and connectivity') from None


def play_sound():
    import winsound
    winsound.PlaySound('SystemNotification',winsound.SND_ALIAS|winsound.SND_ASYNC)


def windows_notification(text):
    import os
    import subprocess
    import winreg
    if not isinstance(text,str) or not 1<=len(text)<=1000:
        raise NotificationError('Notification text exceeds the supported size')
    # Per-user app identity, not a security/notification policy change. No
    # service, COM activator, startup task or third-party application is altered.
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Classes\AppUserModelId\TradingTerminal.Research') as key:
        winreg.SetValueEx(key,'DisplayName',0,winreg.REG_SZ,'Trading Terminal')
    executable=Path(os.environ.get('TRADING_TERMINAL_HOST',Path(__file__).resolve().parents[1]/'src-tauri/target/debug/trading-terminal.exe'))
    try:
        result=subprocess.run([str(executable),'--notification',text],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise NotificationError('Windows notification delivery failed')
    except Exception:
        raise NotificationError('Windows notification delivery failed') from None
