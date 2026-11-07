"""Error handling: today's default behavior, and the opt-in raise_on_error setting."""

import pytest

import cjapy
from cjapy import CJAAPIError

from test_connector import METHODS, call


ERROR = (404, {"errorCode": "not_found", "message": "No such data view"}, {})


def page(item_id, last):
    return (200, {"content": [{"id": item_id}], "lastPage": last}, {})


@pytest.fixture
def cja_factory(http_server):
    """Build a CJA client whose requests all go to the local test server."""
    clients = []

    def create(*responses, **kwargs):
        url, received = http_server(*responses)
        cja = cjapy.CJA(
            config_object={"org_id": "test-org", "token": "t", "date_limit": float("inf")},
            **kwargs,
        )
        cja.connector.session.trust_env = False
        cja.endpoint = url.rsplit("/", 1)[0]
        clients.append(cja)
        return cja, received

    yield create
    for cja in clients:
        cja.connector.session.close()


# Default behavior (raise_on_error=False). These pin down what happens today.


@pytest.mark.parametrize("method", ["getData", "postData", "patchData", "putData"])
def test_default_returns_error_body(connector_factory, http_server, retry_clock, method):
    url, _ = http_server(ERROR)

    assert call(connector_factory(), method, url) == ERROR[1]


def test_default_delete_returns_status_code(connector_factory, http_server, retry_clock):
    url, _ = http_server(ERROR)

    assert connector_factory().deleteData(url) == 404


def test_default_error_on_second_page_returns_partial_list(cja_factory, retry_clock):
    cja, received = cja_factory(page("m1", last=False), ERROR)

    metrics = cja.getMetrics("dv_1")

    assert metrics["id"].tolist() == ["m1"]
    assert len(received) == 2


def test_default_get_data_views_error_raises_key_error(cja_factory, retry_clock):
    cja, _ = cja_factory(ERROR)

    with pytest.raises(KeyError, match="content"):
        cja.getDataViews()


# Opt-in behavior (raise_on_error=True).


@pytest.mark.parametrize("method", METHODS)
def test_raise_on_error_raises_with_details(connector_factory, http_server, retry_clock, method):
    url, _ = http_server(ERROR)

    with pytest.raises(CJAAPIError) as raised:
        call(connector_factory(raise_on_error=True), method, url)

    error = raised.value
    assert error.status_code == 404
    assert error.method == method.removesuffix("Data").upper()
    assert error.url.startswith(url)
    assert error.payload == ERROR[1]


@pytest.mark.parametrize("method", METHODS)
def test_raise_on_error_leaves_success_unchanged(connector_factory, http_server, retry_clock, method):
    payload = {"ok": True}
    url, _ = http_server((200, payload, {}))

    result = call(connector_factory(raise_on_error=True), method, url)

    assert result == (200 if method == "deleteData" else payload)


def test_raise_on_error_raises_after_retries_are_used_up(connector_factory, http_server, retry_clock):
    url, received = http_server((503, {"message": "unavailable"}, {}))

    with pytest.raises(CJAAPIError) as raised:
        connector_factory(retry=0, raise_on_error=True).getData(url)

    assert raised.value.status_code == 503
    assert len(received) == 4  # the first try plus three retries


def test_cja_raise_on_error_stops_pagination(cja_factory, retry_clock):
    cja, received = cja_factory(page("m1", last=False), ERROR, raise_on_error=True)

    with pytest.raises(CJAAPIError) as raised:
        cja.getMetrics("dv_1")

    assert raised.value.status_code == 404
    assert len(received) == 2


def test_cja_raise_on_error_for_get_data_views(cja_factory, retry_clock):
    cja, _ = cja_factory(ERROR, raise_on_error=True)

    with pytest.raises(CJAAPIError):
        cja.getDataViews()
