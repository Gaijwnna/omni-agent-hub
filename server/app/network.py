"""Public HTTP fetcher: validate all DNS answers and pin them at socket connect time."""
import asyncio, ipaddress, socket
from urllib.parse import urlsplit, urlunsplit, urljoin
import aiohttp
from aiohttp.abc import AbstractResolver
from urllib.robotparser import RobotFileParser

USER_AGENT = 'OmniAgentScanner/1.0'
MAX_BYTES = 2_000_000

class FetchError(ValueError):
    pass

def public_ip(value):
    ip = ipaddress.ip_address(value)
    return ip.is_global and not ip.is_multicast and not ip.is_reserved and not getattr(ip, 'ipv4_mapped', None)

def normalize_url(url: str) -> str:
    """Normalize a user-supplied URL: add https:// if missing, strip query/fragment."""
    url = url.strip()
    if url and '://' not in url:
        url = 'https://' + url
    p = urlsplit(url)
    # Strip query params and fragment silently — they often contain tokens
    return urlunsplit((p.scheme, p.netloc, p.path or '/', '', ''))

def validate_url(url):
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) < 33 for c in url) or '\\' in url:
        raise FetchError('Invalid URL')
    p = urlsplit(url)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username is not None or p.password is not None:
        raise FetchError('Only public HTTP(S) URLs are allowed (e.g. https://example.com)')
    if p.port not in (None, 80, 443):
        raise FetchError('Only ports 80 and 443 are allowed')
    host = p.hostname.encode('idna').decode('ascii').lower().rstrip('.')
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal', '.test', '.invalid')):
        raise FetchError('Private hosts are not allowed')
    try:
        if not public_ip(host):
            raise FetchError('Private or reserved addresses are not allowed')
    except ValueError as e:
        if isinstance(e, FetchError):
            raise
    if ':' in host:
        host = '[' + host + ']'
    return urlunsplit((p.scheme, host + (f':{p.port}' if p.port else ''), p.path or '/', p.query, ''))


class PublicResolver(AbstractResolver):
    async def resolve(self, host, port=0, family=socket.AF_INET):
        entries = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM, family=family)
        addresses = {r[4][0] for r in entries}
        if not addresses or not all(public_ip(ip) for ip in addresses):
            raise FetchError('DNS resolves to a private or reserved address')
        return [{'hostname': host, 'host': r[4][0], 'port': port, 'family': r[0],
                 'proto': r[2], 'flags': socket.AI_NUMERICHOST} for r in entries]
    async def close(self):
        pass

async def fetch(url, *, limit=MAX_BYTES, method='GET', data=None, headers=None, redirects=3):
    url = validate_url(url)
    connector = aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False, limit=8)
    async with aiohttp.ClientSession(
        connector=connector, trust_env=False,
        timeout=aiohttp.ClientTimeout(total=15),
        headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity'},
        auto_decompress=True,
    ) as session:
        for turn in range(redirects + 1):
            async with session.request(method, url, data=data, headers=headers, allow_redirects=False) as response:
                if response.status in (301, 302, 303, 307, 308):
                    if method != 'GET' or turn == redirects:
                        raise FetchError('Redirect not allowed')
                    url = validate_url(urljoin(url, response.headers.get('Location', '')))
                    continue
                chunks = []
                size = 0
                async for chunk in response.content.iter_chunked(16384):
                    size += len(chunk)
                    if size > limit:
                        raise FetchError('Response exceeds size limit')
                    chunks.append(chunk)
                return {'url': url, 'status': response.status, 'headers': dict(response.headers), 'body': b''.join(chunks)}
    raise FetchError('Redirect limit exceeded')

def text(response):
    return response['body'].decode('utf-8', errors='replace')

async def robots(url):
    p = urlsplit(validate_url(url))
    origin = f'{p.scheme}://{p.netloc}'
    try:
        r = await fetch(origin + '/robots.txt', limit=256_000)
    except FetchError:
        parser = RobotFileParser()
        parser.set_url(origin + '/robots.txt')
        parser.parse([])
        return parser, None
    parser = RobotFileParser()
    parser.set_url(origin + '/robots.txt')
    if r['status'] == 404:
        parser.parse([])
    elif r['status'] == 200:
        parser.parse(text(r).splitlines())
    elif r['status'] in (401, 403):
        parser.disallow_all = True
    else:
        parser.parse([])
    return parser, r

async def fetch_page(url):
    """Fetch HTML page. Robots policy is checked and REPORTED but never blocks the scan.
    Website owners choose their policy; we report it as a scored check, not a gate."""
    url = validate_url(url)
    for _ in range(4):
        r = await fetch_once(url)
        if r['status'] in (301, 302, 303, 307, 308):
            url = validate_url(urljoin(url, r['headers'].get('Location', r['headers'].get('location', ''))))
            continue
        return r
    raise FetchError('Too many redirects')

async def fetch_once(url):
    url = validate_url(url)
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False),
        trust_env=False,
        timeout=aiohttp.ClientTimeout(total=15),
    ) as s:
        async with s.get(url, allow_redirects=False, headers={'User-Agent': USER_AGENT}) as r:
            body = bytearray()
            async for part in r.content.iter_chunked(16384):
                body.extend(part)
                if len(body) > MAX_BYTES:
                    raise FetchError('Response exceeds size limit')
            return {'url': url, 'status': r.status, 'headers': dict(r.headers), 'body': bytes(body)}
