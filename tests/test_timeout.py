"""Request timeouts for API calls and the OAuth token request; no Adobe credentials."""

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
import requests
from requests.adapters import HTTPAdapter

from cjapy import connector as connector_module
from cjapy.connector import AdobeRequest


def make_connector(**config):
    request = AdobeRequest(
        config_object={"org_id": "test-org", "token": "not-a-real-token",
                       "date_limit": float("inf"), **config},
        header={"Authorization": "Bearer not-a-real-token"},
    )
    request.session.trust_env = False
    return request


@pytest.fixture
def adapter_timeouts(monkeypatch):
    """Replace the network call in HTTPAdapter and record the timeout of each request."""
    seen = []

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        seen.append(timeout)
        response = requests.Response()
        response.status_code = 200
        response._content = b"{}"
        response.request = request
        response.url = request.url
        return response

    monkeypatch.setattr(HTTPAdapter, "send", send)
    return seen


def test_session_requests_use_the_default_timeout(adapter_timeouts):
    make_connector().getData("http://127.0.0.1:1/resource")
    assert adapter_timeouts == [connector_module.DEFAULT_TIMEOUT]


def test_config_timeout_replaces_the_default(adapter_timeouts):
    make_connector(timeout=30).getData("http://127.0.0.1:1/resource")
    assert adapter_timeouts == [30]


def test_config_timeout_from_a_json_list_becomes_a_tuple(adapter_timeouts):
    make_connector(timeout=[5, 60]).getData("http://127.0.0.1:1/resource")
    assert adapter_timeouts == [(5, 60)]


def test_a_timeout_passed_to_the_session_call_is_kept(adapter_timeouts):
    make_connector().session.get("http://127.0.0.1:1/resource", timeout=7)
    assert adapter_timeouts == [7]


def test_token_request_uses_the_timeout(monkeypatch):
    seen = {}

    class FakeResponse:
        def json(self):
            return {"access_token": "abc", "expires_in": 86399}

    def post(url, data=None, proxies=None, timeout=None, **kwargs):
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(connector_module.requests, "post", post)
    make_connector().get_oauth_token_and_expiry_for_config(
        {"client_id": "c", "secret": "s", "scopes": "openid",
         "oauthTokenEndpoint": "http://127.0.0.1:1/token", "timeout": 20})
    assert seen["timeout"] == 20


def test_a_slow_server_stops_the_request_at_the_timeout(retry_clock):
    received = []

    class SlowHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            received.append(self.command)
            time.sleep(1)
            content = json.dumps({"late": True}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        do_POST = do_GET

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()
    try:
        start = time.monotonic()
        with pytest.raises(requests.exceptions.Timeout):
            make_connector(timeout=0.1).postData(f"http://127.0.0.1:{server.server_port}/resource",
                                                 data={"name": "test"})
        assert time.monotonic() - start < 1
        # A read timeout is not retried, so the POST reached the server once.
        assert received == ["POST"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_configure_stores_the_timeout(sdk):
    sdk.configure(org_id="o", client_id="c", secret="s", scopes="openid", timeout=45)
    assert sdk.config_object["timeout"] == 45


def test_configure_return_object_keeps_the_timeout(sdk):
    bundle = sdk.configure(org_id="o", client_id="c", secret="s", scopes="openid",
                           timeout=45, return_object=True)
    assert bundle.config_object["timeout"] == 45


def test_importConfigFile_reads_the_timeout(sdk, tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"org_id": "o", "client_id": "c", "secret": "s",
                                "scopes": "openid", "timeout": [5, 60]}))
    sdk.importConfigFile(str(path))
    assert sdk.config_object["timeout"] == [5, 60]
    assert sdk.importConfigFile(str(path), return_object=True).config_object["timeout"] == [5, 60]


def test_the_adapter_keeps_its_timeout_after_pickling():
    import pickle
    adapter = connector_module.TimeoutHTTPAdapter(timeout=(3, 30))
    assert pickle.loads(pickle.dumps(adapter)).timeout == (3, 30)
