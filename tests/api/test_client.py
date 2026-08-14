import unittest
from typing import Any
from unittest.mock import MagicMock, call, patch

from teamstorm.client import API_PREFIX, TsClient


def _make_client(**kwargs) -> TsClient:
    defaults = dict(
        base_url="http://test",
        token="tok",
        allow_insecure=True,
    )
    defaults.update(kwargs)
    return TsClient(**defaults)


def _page_response(items: list, next_token: str | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    body: dict = {"items": items}
    if next_token is not None:
        body["nextToken"] = next_token
    resp.json.return_value = body
    resp.content = b"x"
    return resp


def _list_response(items: list) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = items
    resp.content = b"x"
    return resp


def _json_response(payload: Any, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.content = b"x"
    return resp


def _no_content_response() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 204
    resp.content = b""
    return resp


def _bytes_response(content: bytes, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    return resp


def _error_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = "boom"
    resp.content = b"boom"
    resp.headers = {}
    return resp


class IterAllTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_iter_all_single_page(self) -> None:
        items = [{"id": "1"}, {"id": "2"}]
        with patch.object(self.client.session, "request", return_value=_page_response(items)):
            result = list(self.client.iter_all("/path"))
        self.assertEqual(items, result)

    def test_iter_all_multiple_pages(self) -> None:
        page1 = _page_response([{"id": "1"}], next_token="tok1")
        page2 = _page_response([{"id": "2"}], next_token="tok2")
        page3 = _page_response([{"id": "3"}])

        with patch.object(self.client.session, "request", side_effect=[page1, page2, page3]):
            result = list(self.client.iter_all("/path"))

        self.assertEqual([{"id": "1"}, {"id": "2"}, {"id": "3"}], result)

    def test_iter_all_repeated_token_safety(self) -> None:
        page1 = _page_response([{"id": "1"}], next_token="loop")
        page2 = _page_response([{"id": "2"}], next_token="loop")

        with patch.object(self.client.session, "request", side_effect=[page1, page2]):
            result = list(self.client.iter_all("/path"))

        self.assertEqual([{"id": "1"}, {"id": "2"}], result)

    def test_iter_all_max_pages_safety(self) -> None:
        from teamstorm.client import RetryConfig

        client = _make_client(retry=RetryConfig(max_attempts=1))

        def make_page(n):
            r = MagicMock()
            r.status_code = 200
            r.json.return_value = {"items": [{"id": str(n)}], "nextToken": f"tok{n + 1}"}
            r.content = b"x"
            return r

        pages = [make_page(i) for i in range(10_001)]
        with patch.object(client.session, "request", side_effect=pages):
            result = list(client.iter_all("/path"))

        self.assertEqual(10_000, len(result))

    def test_iter_all_list_payload(self) -> None:
        items = [{"id": "a"}, {"id": "b"}]
        with patch.object(self.client.session, "request", return_value=_list_response(items)):
            result = list(self.client.iter_all("/path"))
        self.assertEqual(items, result)

    def test_get_all_returns_list(self) -> None:
        items = [{"id": "x"}]
        with patch.object(self.client.session, "request", return_value=_page_response(items)):
            result = self.client.get_all("/path")
        self.assertIsInstance(result, list)
        self.assertEqual(items, result)

    def test_default_page_size_500(self) -> None:
        with patch.object(self.client.session, "request", return_value=_page_response([])) as mock_req:
            list(self.client.iter_all("/path"))

        _args, kwargs = mock_req.call_args
        self.assertEqual(500, kwargs["params"]["maxItemsCount"])

    def test_caller_page_size_respected(self) -> None:
        with patch.object(self.client.session, "request", return_value=_page_response([])) as mock_req:
            list(self.client.iter_all("/path", params={"maxItemsCount": 50}))

        _args, kwargs = mock_req.call_args
        self.assertEqual(50, kwargs["params"]["maxItemsCount"])

    def test_request_params_passed_directly(self) -> None:
        params = {"foo": "bar"}
        with patch.object(self.client.session, "request", return_value=_page_response([])) as mock_req:
            self.client.get("/path", params=params)

        _args, kwargs = mock_req.call_args
        self.assertIs(params, kwargs["params"])

    def test_get_all_last_page_echoing_from_token_is_not_treated_as_next_page(self) -> None:
        # Regression test: the server echoes the request's own fromToken back
        # in the response envelope on the *last* page (nextToken: null). A
        # stale fallback to payload["fromToken"] as a next-page cursor would
        # make get_all() refetch this same page and duplicate every item.
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"fromToken": "10", "nextToken": None, "items": [{"id": 1}, {"id": 2}]}
        resp.content = b"x"

        with patch.object(self.client.session, "request", return_value=resp) as mock_req:
            result = self.client.get_all("/path", params={"fromToken": "10"})

        self.assertEqual([{"id": 1}, {"id": 2}], result)
        self.assertEqual(1, mock_req.call_count)


class ExtractItemsAndTokenTestCase(unittest.TestCase):
    def test_bare_list_short_circuits(self) -> None:
        from teamstorm.client import extract_items_and_token

        items = [{"id": "1"}]
        self.assertEqual((items, None), extract_items_and_token(items))

    def test_dict_with_empty_items_returns_empty_list(self) -> None:
        from teamstorm.client import extract_items_and_token

        self.assertEqual(([], None), extract_items_and_token({"items": []}))

    def test_dict_without_items_key_raises_api_error(self) -> None:
        from teamstorm.client import ApiError, extract_items_and_token

        with self.assertRaises(ApiError):
            extract_items_and_token({"providers": [{"id": "1"}]})

    def test_from_token_is_not_used_as_next_page_token(self) -> None:
        from teamstorm.client import extract_items_and_token

        items, token = extract_items_and_token({"fromToken": "10", "nextToken": None, "items": [{"id": 1}]})
        self.assertEqual([{"id": 1}], items)
        self.assertIsNone(token)

    def test_continuation_token_fallback_still_works(self) -> None:
        from teamstorm.client import extract_items_and_token

        items, token = extract_items_and_token({"continuationToken": "next", "items": [{"id": 1}]})
        self.assertEqual([{"id": 1}], items)
        self.assertEqual("next", token)


class PostPutOptionalBodyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_post_with_no_body_sends_no_json_payload(self) -> None:
        with patch.object(self.client.session, "request", return_value=_json_response({})) as mock_req:
            self.client.post("/path")

        _args, kwargs = mock_req.call_args
        self.assertEqual("POST", kwargs["method"])
        self.assertEqual(f"http://test{API_PREFIX}/path", kwargs["url"])
        self.assertIsNone(kwargs["json"])

    def test_post_with_body_still_sends_json_payload(self) -> None:
        body = {"name": "x"}
        with patch.object(self.client.session, "request", return_value=_json_response({})) as mock_req:
            self.client.post("/path", body)

        _args, kwargs = mock_req.call_args
        self.assertEqual("POST", kwargs["method"])
        self.assertEqual(f"http://test{API_PREFIX}/path", kwargs["url"])
        self.assertEqual(body, kwargs["json"])

    def test_put_with_no_body_sends_no_json_payload(self) -> None:
        with patch.object(self.client.session, "request", return_value=_json_response({})) as mock_req:
            self.client.put("/path")

        _args, kwargs = mock_req.call_args
        self.assertEqual("PUT", kwargs["method"])
        self.assertEqual(f"http://test{API_PREFIX}/path", kwargs["url"])
        self.assertIsNone(kwargs["json"])

    def test_put_with_body_still_sends_json_payload(self) -> None:
        body = {"name": "y"}
        with patch.object(self.client.session, "request", return_value=_json_response({})) as mock_req:
            self.client.put("/path", body)

        _args, kwargs = mock_req.call_args
        self.assertEqual("PUT", kwargs["method"])
        self.assertEqual(f"http://test{API_PREFIX}/path", kwargs["url"])
        self.assertEqual(body, kwargs["json"])

    def test_post_no_body_returns_parsed_json(self) -> None:
        with patch.object(self.client.session, "request", return_value=_json_response({"ok": True})):
            result = self.client.post("/users/block/u1")

        self.assertEqual({"ok": True}, result)

    def test_post_no_body_handles_204(self) -> None:
        with patch.object(self.client.session, "request", return_value=_no_content_response()):
            result = self.client.post("/users/block/u1")

        self.assertIsNone(result)


class DeleteOptionalBodyTestCase(unittest.TestCase):
    """
    DELETE /workspaces/{workspace}/documents/{document}/workitem-links is the
    one operation in the whole spec where DELETE carries a JSON request body
    (identifying which linked workitem to remove) instead of a path id or
    query params. TsClient.delete() needs an optional `body` kwarg to send
    it; every pre-existing call site omits `body` and must keep behaving
    exactly as before (no JSON payload sent).
    """

    def setUp(self) -> None:
        self.client = _make_client()

    def test_delete_with_no_body_sends_no_json_payload(self) -> None:
        with patch.object(self.client.session, "request", return_value=_no_content_response()) as mock_req:
            result = self.client.delete("/path")

        _args, kwargs = mock_req.call_args
        self.assertEqual("DELETE", kwargs["method"])
        self.assertEqual(f"http://test{API_PREFIX}/path", kwargs["url"])
        self.assertIsNone(kwargs["json"])
        self.assertIsNone(result)

    def test_delete_with_body_sends_json_payload(self) -> None:
        body = {"workitem": "WI-1", "workitemWorkspace": "WS2"}
        with patch.object(self.client.session, "request", return_value=_no_content_response()) as mock_req:
            result = self.client.delete("/path", body=body)

        _args, kwargs = mock_req.call_args
        self.assertEqual("DELETE", kwargs["method"])
        self.assertEqual(f"http://test{API_PREFIX}/path", kwargs["url"])
        self.assertEqual(body, kwargs["json"])
        self.assertIsNone(result)

    def test_delete_still_passes_params(self) -> None:
        params = {"foo": "bar"}
        with patch.object(self.client.session, "request", return_value=_no_content_response()) as mock_req:
            self.client.delete("/path", params=params)

        _args, kwargs = mock_req.call_args
        self.assertIs(params, kwargs["params"])
        self.assertIsNone(kwargs["json"])


class PostMultipartTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_sends_multipart_with_file_field_name(self) -> None:
        with patch.object(self.client.session, "request", return_value=_no_content_response()) as mock_req:
            self.client.post_multipart(
                "/workspaces/WS/workitems/T/attachments/A/upload",
                file_name="report.pdf",
                content=b"binary-data",
            )

        _args, kwargs = mock_req.call_args
        self.assertEqual("POST", kwargs["method"])
        self.assertEqual(
            f"http://test{API_PREFIX}/workspaces/WS/workitems/T/attachments/A/upload",
            kwargs["url"],
        )
        self.assertIn("file", kwargs["files"])
        self.assertEqual(("report.pdf", b"binary-data"), kwargs["files"]["file"])

    def test_custom_field_name(self) -> None:
        with patch.object(self.client.session, "request", return_value=_no_content_response()) as mock_req:
            self.client.post_multipart(
                "/path",
                file_name="report.pdf",
                content=b"binary-data",
                field_name="attachment",
            )

        _args, kwargs = mock_req.call_args
        self.assertIn("attachment", kwargs["files"])
        self.assertNotIn("file", kwargs["files"])

    def test_content_type_included_in_file_tuple_when_given(self) -> None:
        with patch.object(self.client.session, "request", return_value=_no_content_response()) as mock_req:
            self.client.post_multipart(
                "/path",
                file_name="report.pdf",
                content=b"binary-data",
                content_type="application/pdf",
            )

        _args, kwargs = mock_req.call_args
        self.assertEqual(("report.pdf", b"binary-data", "application/pdf"), kwargs["files"]["file"])

    def test_explicit_empty_content_type_is_honored(self) -> None:
        with patch.object(self.client.session, "request", return_value=_no_content_response()) as mock_req:
            self.client.post_multipart(
                "/path",
                file_name="report.pdf",
                content=b"binary-data",
                content_type="",
            )

        _args, kwargs = mock_req.call_args
        self.assertEqual(("report.pdf", b"binary-data", ""), kwargs["files"]["file"])

    def test_does_not_force_json_content_type(self) -> None:
        # The session pins Content-Type: application/json globally (client.py __init__).
        # post_multipart must override it per-request so requests can set its own
        # multipart/form-data; boundary=... header instead.
        with patch.object(self.client.session, "request", return_value=_no_content_response()) as mock_req:
            self.client.post_multipart("/path", file_name="x.bin", content=b"data")

        _args, kwargs = mock_req.call_args
        self.assertIsNone(kwargs["headers"]["Content-Type"])

    def test_no_json_body_sent(self) -> None:
        with patch.object(self.client.session, "request", return_value=_no_content_response()) as mock_req:
            self.client.post_multipart("/path", file_name="x.bin", content=b"data")

        _args, kwargs = mock_req.call_args
        self.assertIsNone(kwargs["json"])

    def test_returns_parsed_json_when_present(self) -> None:
        with patch.object(self.client.session, "request", return_value=_json_response({"id": "abc"})):
            result = self.client.post_multipart("/path", file_name="x.bin", content=b"data")

        self.assertEqual({"id": "abc"}, result)

    def test_returns_none_on_204(self) -> None:
        with patch.object(self.client.session, "request", return_value=_no_content_response()):
            result = self.client.post_multipart("/path", file_name="x.bin", content=b"data")

        self.assertIsNone(result)

    def test_retries_once_on_500_then_succeeds(self) -> None:
        error = _error_response(500)
        ok = _no_content_response()
        with (
            patch.object(self.client.session, "request", side_effect=[error, ok]) as mock_req,
            patch("teamstorm.client.time.sleep", return_value=None),
        ):
            result = self.client.post_multipart("/path", file_name="x.bin", content=b"data")

        self.assertIsNone(result)
        self.assertEqual(2, mock_req.call_count)


class GetBytesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _make_client()

    def test_returns_raw_bytes_without_json_parsing(self) -> None:
        payload = b"\x89PNG-raw-bytes"
        resp = _bytes_response(payload)
        with patch.object(self.client.session, "request", return_value=resp) as mock_req:
            result = self.client.get_bytes("/workspaces/WS/workitems/T/attachments/A/download")

        _args, kwargs = mock_req.call_args
        self.assertEqual("GET", kwargs["method"])
        self.assertEqual(
            f"http://test{API_PREFIX}/workspaces/WS/workitems/T/attachments/A/download",
            kwargs["url"],
        )
        self.assertEqual(payload, result)
        resp.json.assert_not_called()

    def test_passes_params_through(self) -> None:
        params = {"version": "2"}
        with patch.object(self.client.session, "request", return_value=_bytes_response(b"x")) as mock_req:
            self.client.get_bytes("/path", params=params)

        _args, kwargs = mock_req.call_args
        self.assertIs(params, kwargs["params"])

    def test_returns_empty_bytes_on_204(self) -> None:
        with patch.object(self.client.session, "request", return_value=_no_content_response()):
            result = self.client.get_bytes("/path")

        self.assertEqual(b"", result)

    def test_retries_once_on_500_then_succeeds(self) -> None:
        error = _error_response(500)
        ok = _bytes_response(b"payload-bytes")
        with (
            patch.object(self.client.session, "request", side_effect=[error, ok]) as mock_req,
            patch("teamstorm.client.time.sleep", return_value=None),
        ):
            result = self.client.get_bytes("/path")

        self.assertEqual(b"payload-bytes", result)
        self.assertEqual(2, mock_req.call_count)

    def test_raises_api_error_on_4xx(self) -> None:
        from teamstorm.client import ApiError

        with patch.object(self.client.session, "request", return_value=_error_response(404)):
            with self.assertRaises(ApiError):
                self.client.get_bytes("/path")
