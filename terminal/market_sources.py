"""Public display-source identities. Legacy unqualified cache keys are Bybit."""
import errno
import re
import socket
import ssl
from urllib.error import HTTPError, URLError

SOURCES=('bybit','okx')

def validate_source(source):
    if source not in SOURCES:raise ValueError('Unsupported public data source')
    return source

def cache_market(market, source='bybit'):
    validate_source(source)
    if market not in ('spot','linear'):raise ValueError('Unsupported public market')
    return market if source=='bybit' else f'{source}:{market}'

_NETWORK_ERRORS={
    errno.ECONNREFUSED:'connection refused', errno.ENETUNREACH:'network unreachable',
    errno.EHOSTUNREACH:'host unreachable', errno.ECONNRESET:'connection reset',
    errno.ECONNABORTED:'connection aborted', errno.ETIMEDOUT:'timeout',
    errno.EACCES:'permission denied', errno.EPERM:'operation not permitted',
    errno.EADDRNOTAVAIL:'local address unavailable', errno.EAFNOSUPPORT:'address family unavailable',
    errno.EPIPE:'connection closed', errno.ENOTCONN:'not connected',
    10061:'connection refused',10051:'network unreachable',10065:'host unreachable',
    10054:'connection reset',10053:'connection aborted',10060:'timeout',
    10013:'permission denied',10049:'local address unavailable',11001:'DNS lookup failed',
}

def safe_error(exc):
    """Classify local transport failures without publishing exception text.

    Async socket dialing may collapse IPv4/IPv6 failures into an OSError with
    no errno attribute. In that case extract only known numeric errno tokens;
    addresses, URLs, remote text and arbitrary reason strings never leave here.
    """
    pending=[exc];seen=set();categories=[];fallback=type(exc).__name__
    while pending and len(seen)<12:
        current=pending.pop(0)
        if not isinstance(current,BaseException) or id(current) in seen:continue
        seen.add(id(current));fallback=type(current).__name__
        if isinstance(current,HTTPError):return f'HTTP {current.code}'
        status=getattr(getattr(current,'response',None),'status_code',None)
        if type(status) is int and 100<=status<=599:return f'HTTP {status}'
        if isinstance(current,socket.gaierror):categories.append('DNS lookup failed')
        elif isinstance(current,ssl.SSLCertVerificationError):categories.append('TLS certificate verification failed')
        elif isinstance(current,ssl.SSLError):categories.append('TLS connection failed')
        elif isinstance(current,TimeoutError):categories.append('Timeout')
        elif isinstance(current,OSError):
            codes=[getattr(current,'errno',None),getattr(current,'winerror',None)]
            if all(code is None for code in codes):
                codes.extend(int(value) for value in re.findall(r'\[(?:Errno|WinError) (-?\d{1,5})\]',str(current)[:4096]))
            for code in codes:
                if type(code) is int and code in _NETWORK_ERRORS:
                    categories.append(f'{_NETWORK_ERRORS[code]} (errno {code})')
        if isinstance(current,URLError):pending.append(current.reason)
        if isinstance(current,BaseExceptionGroup):pending.extend(current.exceptions[:4])
        pending.extend([current.__cause__,current.__context__])
    return '; '.join(dict.fromkeys(categories))[:240] if categories else fallback
