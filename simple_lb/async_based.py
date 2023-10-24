import json
import logging
import re
import sys
from dataclasses import dataclass
from typing import List

import httpx
from starlette.datastructures import URL, MutableHeaders
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

HDR_CONNECTION = "connection"

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stdout)

logger = logging.getLogger("app")


class HttpClient:
    def __init__(self):
        self.limits = httpx.Limits(max_keepalive_connections=5, max_connections=100)
        self.timeout = httpx.Timeout(None)
        self._pool = None
        self._async_pool_initialized = False

    async def init_async_pool(self):
        if not self._async_pool_initialized:
            await self.pool.__aenter__()
            self._async_pool_initialized = True

    @property
    def pool(self):
        if self._pool is None:
            params = dict(follow_redirects=True, timeout=self.timeout, limits=self.limits)
            self._pool = httpx.AsyncClient(**params)
            self._async_pool_initialized = False
        return self._pool

    def build_request(self, *args, **kwargs):
        return self.pool.build_request(*args, **kwargs)

    async def request(self, *args, **kwargs):
        await self.init_async_pool()
        try:
            return await self.pool.request(*args, **kwargs)
        finally:
            await self.pool.__aexit__()

    async def send(self, *args, **kwargs):
        await self.init_async_pool()
        try:
            return await self._pool.send(*args, **kwargs)
        finally:
            await self.pool.__aexit__()


def validate_ipv4(ip):
    pattern = r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$"
    match = re.match(pattern, ip)
    if match:
        groups = match.groups()
        if all(0 <= int(g) <= 255 for g in groups):
            return True
    return False


@dataclass
class LoadBalancerTarget:
    ip_address: str
    port: int

    def __init__(self, ip_address, port):
        if validate_ipv4(ip_address):
            self.ip_address = ip_address
        else:
            raise ValueError("Invalid IP address")
        self.port = int(port)
        super().__init__()

    def __hash__(self):
        return hash((self.ip_address, self.port))


class LoadBalancerTargets:
    def __init__(self, *targets: List[LoadBalancerTarget]):
        self.targets = targets
        self.current_index = -1

    def add(self, target: LoadBalancerTarget):
        if target in self.targets:
            raise ValueError("Target already exists")
        self.targets.append(target)

    def reset_round_robin(self):
        self.current_index = -1

    def __len__(self):
        return len(self.targets)

    def get_next_target(self):
        if len(self.targets) == 0:
            raise ValueError("No targets registered")
        if self.current_index >= len(self.targets):
            self.reset_round_robin()
        self.current_index += 1
        return self.targets[self.current_index]


targets = LoadBalancerTargets(
    LoadBalancerTarget(ip_address="99.83.207.202", port=80),
    LoadBalancerTarget(ip_address="216.58.209.14", port=80),
    LoadBalancerTarget(ip_address="80.252.0.135", port=80),
)


def get_sanitized_headers(headers) -> MutableHeaders:
    new_headers = MutableHeaders(headers=headers)
    del new_headers[HDR_CONNECTION]
    return new_headers


async def handle_target_registration(req: Request) -> Response:
    try:
        json_body = await req.json()
    except json.JSONDecodeError:
        return Response(status_code=400, content="Invalid JSON")
    ip_addr = json_body.get("ip_address")
    port = json_body.get("port")
    try:
        target = LoadBalancerTarget(ip_addr, port)
    except ValueError:
        return Response(status_code=400, content="Invalid IP address or address")
    try:
        targets.add(target)
        logger.info("Registered target: %s:%s", ip_addr, port)
    except ValueError:
        return Response(status_code=400, content="Target already exists")
    return Response(status_code=200)


async def get_proxied_response(client, incoming_req):
    next_target = targets.get_next_target()
    target_url = URL(hostname=next_target.ip_address, port=next_target.port)
    scheme = target_url.scheme or "http"
    target_url = incoming_req.url.replace(hostname=target_url.hostname, scheme=scheme, port=target_url.port)
    logger.debug("Forwarding to: " + str(target_url))
    # Create a new request to the target server
    endpoint = target_url.hostname
    headers = get_sanitized_headers(incoming_req.headers)
    headers["host"] = endpoint
    has_content = int(headers.get("content-length", 0)) > 0
    data = incoming_req.stream() if has_content else None
    proxy_request = client.build_request(incoming_req.method, str(target_url), headers=headers, data=data)
    response = await client.send(proxy_request)
    # Create a streaming response to send back to the client
    if response.status_code != 204:
        return StreamingResponse(response.aiter_bytes(), status_code=response.status_code, headers=response.headers)
    else:
        return Response(status_code=response.status_code, headers=response.headers)


def create_app():
    http_client = HttpClient()

    async def app(scope, receive, send):
        method = scope.get("method")
        path = scope.get("path")
        logger.debug("Received request: %s %s", method, path)
        if method == "POST" and path == "/register":
            request = Request(scope, receive)
            response = await handle_target_registration(request)
            await response(scope, receive, send)
            return
        if len(targets) == 0:
            response = Response(status_code=503, content="No targets registered")
            await response(scope, receive, send)
            return
        response = await get_proxied_response(http_client, Request(scope, receive))
        await response(scope, receive, send)

    return app
