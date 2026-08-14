from __future__ import annotations
import logging
import random
import time
import requests
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any, BinaryIO

API_PREFIX = "/cwm/public/api/v1"
_MAX_ERROR_DETAIL_LEN = 2048


class ApiError(RuntimeError):
    """
    Raised for any CWM API/transport failure: a non-2xx response that
    survived all retries, a request that failed at the transport level after
    exhausting :class:`RetryConfig`, or a response body that could not be
    decoded. This is the one exception type callers of this package need to
    catch.

    Attributes:
        status: HTTP status code, when the failure came from a response
            (``None`` for a pure transport failure, e.g. a connection error
            that persisted across every retry attempt).
        details: raw response body text (truncated), when available -- often
            the server's own error message/validation details.
        method: HTTP method of the request that failed, e.g. ``"GET"``.
        path: API path of the request that failed (without ``base_url``/
            ``api_prefix``).
        url: full request URL, when available.
    """

    def __init__(
        self,
        message: str,
        status: int | None = None,
        details: str | None = None,
        *,
        method: str | None = None,
        path: str | None = None,
        url: str | None = None,
    ) -> None:
        """
        :param message: human-readable error message (passed to
            ``RuntimeError.__init__``, so ``str(err)`` returns it).
        :param status: HTTP status code, or ``None`` for a transport-level
            failure with no response.
        :param details: raw response body text, or ``None``.
        :param method: HTTP method of the failed request.
        :param path: API path of the failed request.
        :param url: full URL of the failed request.
        """
        super().__init__(message)
        self.status = status
        self.details = details
        self.method = method
        self.path = path
        self.url = url


def _join_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    p = path if path.startswith("/") else f"/{path}"
    return f"{base}{p}"


def extract_items_and_token(payload: Any) -> tuple[list[dict[str, Any]], str | None]:
    """
    Pagination helper:
      - list -> (list, None)
      - {items: [...], nextToken/continuationToken: "..."} -> (items, token)
      - dict with no "items" key -> raises ApiError (unrecognized envelope)

    NOTE: ``fromToken`` is deliberately NOT used as a next-page-token fallback.
    The server echoes the request's own ``fromToken`` back in the response
    envelope; it is not a "next page" cursor. Falling back to it here would
    make the last page look like it has more pages, causing callers to
    refetch and yield the same items twice. See
    docs/api-analysis/upstream-semantics.md §2a.
    """
    if isinstance(payload, list):
        return payload, None
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            token = payload.get("nextToken") or payload.get("continuationToken")
            return items, token
        raise ApiError(f"Unrecognized list envelope: dict payload has no 'items' key (keys={list(payload.keys())})")
    return [], None


@dataclass(frozen=True)
class RetryConfig:
    """
    Retry/backoff policy for :meth:`TsClient._request`, applied to transport
    failures (connection errors, timeouts) and to ``429``/``5xx`` responses.

    All delay fields are in seconds. Backoff is exponential
    (``base_delay_s * 2 ** attempt``, capped at ``max_delay_s``) plus a
    uniform random jitter of up to ``jitter_s``, except when the server sends
    a ``Retry-After`` header on a ``429``, in which case that value is used
    instead (still capped at ``max_delay_s``).

    Attributes:
        max_attempts: total number of attempts, including the first one (so
            ``max_attempts=5`` means up to 4 retries after the initial try).
        base_delay_s: base delay for exponential backoff, in seconds.
        max_delay_s: upper bound on any single sleep, in seconds.
        jitter_s: maximum uniform random jitter added to each computed delay,
            in seconds.
    """

    max_attempts: int = 5
    base_delay_s: float = 0.5
    max_delay_s: float = 8.0
    jitter_s: float = 0.25


@dataclass(frozen=True)
class TimeoutConfig:
    """
    Per-request timeout, in seconds, passed straight through to
    ``requests``'s ``timeout=`` kwarg as a ``(connect, read)`` tuple via
    :attr:`as_requests_timeout`.

    Attributes:
        connect_s: max time to establish the TCP/TLS connection, in seconds.
        read_s: max time to wait for the server to send a response once
            connected, in seconds.
    """

    connect_s: float = 10.0
    read_s: float = 60.0

    @property
    def as_requests_timeout(self) -> tuple[float, float]:
        """
        :return: ``(connect_s, read_s)``, the ``(connect, read)`` tuple form
            ``requests``'s ``timeout=`` kwarg expects.
        """
        return (self.connect_s, self.read_s)


class TsClient:
    """
    Transport client for the TeamStorm (CWM) Public API.

    Owns everything HTTP: the base URL and auth header, retry/backoff,
    timeouts, and pagination. It has no knowledge of any specific resource or
    schema -- every method here takes/returns plain ``dict``/``list`` JSON
    (see :meth:`get`/:meth:`post`/etc.), never a pydantic model. Turning that
    JSON into typed models is the job of the ``*API`` classes in
    ``teamstorm/api/`` (reached via :class:`~teamstorm.api.TeamStormAPI`),
    not this class.

    **Authentication.** Every request carries an
    ``Authorization: PrivateToken <token>`` header, set once on the shared
    ``requests.Session`` at construction time.

    **HTTPS enforcement.** ``base_url`` must start with ``https://`` or
    construction raises ``ValueError`` -- the token is a bearer credential
    and must not be sent over plaintext HTTP. Pass ``allow_insecure=True`` to
    lift this (intended for tests against a local/mock server only, never for
    a real token).

    **Retry/backoff.** Every request is retried (see :class:`RetryConfig`)
    on a transport-level failure (e.g. connection error) and on a ``429`` or
    ``5xx`` response, honoring the server's ``Retry-After`` header when
    present on a ``429``. A non-2xx response that isn't retryable (or that
    exhausts all retry attempts) raises :class:`ApiError`.

    **Typical construction** (see ``teamstorm.api.TeamStormAPI`` for the
    layer built on top of this)::

        from teamstorm.client import TsClient
        from teamstorm.api import TeamStormAPI

        client = TsClient(base_url="https://your-cwm-host", token="...")
        ts = TeamStormAPI(client)
        workspace = ts.workspaces.get("WS")
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        logger: Any | None = None,
        *,
        allow_insecure: bool = False,
        session: requests.Session | None = None,
        timeout: TimeoutConfig | None = None,
        retry: RetryConfig | None = None,
        api_prefix: str = API_PREFIX,
    ) -> None:
        """
        :param base_url: the CWM instance's base URL, e.g.
            ``"https://your-cwm-host"``. Must start with ``https://`` unless
            ``allow_insecure=True``.
        :param token: the API token sent as ``Authorization: PrivateToken
            <token>`` on every request.
        :param logger: optional ``logging.Logger``-like object for debug/
            warning messages (pagination safety stops, retry attempts, etc.);
            defaults to ``logging.getLogger(__name__)``.
        :param allow_insecure: when True, permits a non-``https://``
            ``base_url``. Tests only -- never set this with a real token.
        :param session: optional pre-built ``requests.Session`` to reuse
            (e.g. for connection pooling across multiple clients); a fresh
            one is created when omitted.
        :param timeout: per-request connect/read timeouts; defaults to
            ``TimeoutConfig()`` when omitted.
        :param retry: retry/backoff policy; defaults to ``RetryConfig()``
            when omitted.
        :param api_prefix: path prefix prepended to every request path,
            defaults to ``API_PREFIX`` (``"/cwm/public/api/v1"``).
        :raises ValueError: if ``base_url`` does not start with ``https://``
            and ``allow_insecure`` is not True.
        """
        if not allow_insecure and not base_url.startswith("https://"):
            raise ValueError(
                f"base_url must use HTTPS to protect the API token; got {base_url!r}. "
                "Pass allow_insecure=True to override (tests only)."
            )
        self.base_url = base_url
        self.log = logger or logging.getLogger(__name__)
        self.api_prefix = api_prefix

        self._timeout = timeout or TimeoutConfig()
        self._retry = retry or RetryConfig()

        self.session = session or requests.Session()
        # Authorization confirmed: PrivateToken <token>
        self.session.headers.update(
            {
                "Authorization": f"PrivateToken {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _make_url(self, path: str) -> str:
        return _join_url(self.base_url, f"{self.api_prefix}{path}")

    def _sleep_backoff(self, attempt: int, *, retry_after_s: float | None = None) -> None:
        if retry_after_s is not None and retry_after_s > 0:
            delay = min(float(retry_after_s), self._retry.max_delay_s)
        else:
            delay = min(
                self._retry.base_delay_s * (2 ** max(attempt - 1, 0)),
                self._retry.max_delay_s,
            )
            delay += random.uniform(0.0, self._retry.jitter_s)
        time.sleep(delay)

    @staticmethod
    def _parse_retry_after(resp: requests.Response) -> float | None:
        ra = resp.headers.get("Retry-After")
        if not ra:
            return None
        try:
            return float(ra)
        except ValueError:
            return None

    def _decode_json(self, resp: requests.Response, method: str, path: str, url: str) -> Any:
        """
        Decode a successful response as JSON.

        :param resp: the ``requests.Response`` for a non-retryable, non-error status.
        :param method: HTTP method of the originating request (for error messages).
        :param path: API path of the originating request (for error messages).
        :param url: full URL of the originating request (for error messages).
        :return: the parsed JSON body, or ``None`` for a ``204`` status or an empty body.
        :raises ApiError: if the body is non-empty but is not valid JSON.
        """
        if resp.status_code == 204:
            return None
        if not resp.content:
            return None

        try:
            return resp.json()
        except Exception as e:
            raise ApiError(
                f"Не удалось распарсить JSON ответа для {method} {path}: {e}",
                status=resp.status_code,
                details=(getattr(resp, "text", "") or "")[:1000],
                method=method,
                path=path,
                url=url,
            ) from e

    @staticmethod
    def _decode_bytes(resp: requests.Response, method: str, path: str, url: str) -> bytes:
        """
        Decode a successful response as raw bytes, without any JSON parsing.

        :param resp: the ``requests.Response`` for a non-retryable, non-error status.
        :param method: HTTP method of the originating request (unused, kept for a
            uniform decoder signature shared with :meth:`_decode_json`).
        :param path: API path of the originating request (unused, see above).
        :param url: full URL of the originating request (unused, see above).
        :return: the raw response body as ``bytes``; ``b""`` for a ``204`` status
            or a response with no body.
        """
        if resp.status_code == 204 or not resp.content:
            return b""
        return resp.content

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        files: Any = None,
        headers: Mapping[str, Any] | None = None,
        decode: Callable[[requests.Response, str, str, str], Any] | None = None,
    ) -> Any:
        """
        Execute an HTTP request with retry/backoff, then delegate response decoding.

        This is the single place that owns the retry loop, timeout handling, and
        error mapping (``ApiError``) for every transport method on this client.
        New request shapes (e.g. multipart uploads, raw-bytes downloads) should
        extend this method's parameters rather than duplicating the loop.

        :param method: HTTP method, e.g. ``"GET"``/``"POST"``/``"PATCH"``/``"PUT"``/``"DELETE"``.
        :param path: API path, appended to ``base_url`` + ``api_prefix``.
        :param params: optional query parameters.
        :param json: optional JSON-serializable request body.
        :param files: optional multipart file mapping, as accepted by ``requests``'s
            ``files=`` keyword argument.
        :param headers: optional per-request header overrides merged over the
            session's default headers; a header mapped to ``None`` is removed for
            this request only (used by :meth:`post_multipart` to drop the
            session-wide ``Content-Type: application/json`` so ``requests`` can
            set its own multipart boundary).
        :param decode: optional response decoder called as
            ``decode(resp, method, path, url)`` on a successful, non-retried
            response. Defaults to :meth:`_decode_json`. Pass :meth:`_decode_bytes`
            to get the raw response body instead of parsed JSON.
        :return: whatever *decode* returns for a successful response.
        :raises ApiError: on a transport failure that persists across all retry
            attempts, on a non-2xx response, or when decoding fails.
        """
        url = self._make_url(path)
        timeout = self._timeout.as_requests_timeout
        decoder = decode or self._decode_json

        for attempt in range(1, self._retry.max_attempts + 1):
            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    params=params or None,
                    json=json,
                    files=files,
                    headers=headers,
                    timeout=timeout,
                )
            except requests.RequestException as e:
                if attempt >= self._retry.max_attempts:
                    raise ApiError(
                        f"HTTP ошибка {method} {path}: {e}",
                        method=method,
                        path=path,
                        url=url,
                    ) from e
                self.log.debug(
                    "Transport error on %s %s (attempt %d/%d): %s",
                    method,
                    path,
                    attempt,
                    self._retry.max_attempts,
                    e,
                )
                self._sleep_backoff(attempt)
                continue

            # retry on 429 / 5xx
            if resp.status_code == 429 or 500 <= resp.status_code <= 599:
                if attempt < self._retry.max_attempts:
                    self.log.debug(
                        "Retryable HTTP %s on %s %s (attempt %d/%d)",
                        resp.status_code,
                        method,
                        path,
                        attempt,
                        self._retry.max_attempts,
                    )
                    self._sleep_backoff(attempt, retry_after_s=self._parse_retry_after(resp))
                    continue

            if resp.status_code >= 400:
                try:
                    body = resp.text
                    details = body[:_MAX_ERROR_DETAIL_LEN] + ("…" if len(body) > _MAX_ERROR_DETAIL_LEN else "")
                except Exception:
                    details = "<no body>"
                raise ApiError(
                    f"API вернул {resp.status_code} для {method} {path}",
                    status=resp.status_code,
                    details=details,
                    method=method,
                    path=path,
                    url=url,
                )

            return decoder(resp, method, path, url)

        raise ApiError(
            f"Не удалось выполнить запрос {method} {path} после {self._retry.max_attempts} попыток",
            method=method,
            path=path,
            url=url,
        )

    def iter_all(self, path: str, *, params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        """
        Lazy generator over all paginated items at *path*.

        Yields one item at a time, fetching the next page only when needed.
        Use this instead of get_all() when working with large result sets to
        avoid loading all pages into memory at once.

        Safety guards (max 10 000 pages, repeated-token detection) are identical
        to get_all().
        """
        p: dict[str, Any] = dict(params or {})
        p.setdefault("maxItemsCount", 500)
        seen_tokens: set[str] = set()
        if p.get("fromToken") is not None:
            # Seed with the caller-supplied fromToken too: the server echoes
            # the request's fromToken back in the response envelope (it is
            # not a next-page cursor), so without this the repeated-token
            # guard below wouldn't trip until a *second* refetch of the same
            # page. See docs/api-analysis/upstream-semantics.md §2a.
            seen_tokens.add(p["fromToken"])
        max_pages = 10_000
        page_no = 0

        while True:
            page_no += 1
            if page_no > max_pages:
                self.log.warning(
                    "Pagination safety stop: path=%s pages=%d reason=max_pages",
                    path,
                    page_no - 1,
                )
                break

            request_token = p.get("fromToken")
            payload = self._request("GET", path, params=p)
            items, token = extract_items_and_token(payload)

            response_next = payload.get("nextToken") if isinstance(payload, dict) else None
            response_from = payload.get("fromToken") if isinstance(payload, dict) else None
            self.log.debug(
                "Pagination page fetched: path=%s page=%d request_fromToken=%r "
                "response_nextToken=%r response_fromToken=%r items=%d",
                path,
                page_no,
                request_token,
                response_next,
                response_from,
                len(items),
            )

            yield from items

            if not token:
                break
            if token in seen_tokens:
                self.log.warning(
                    "Pagination safety stop: path=%s token=%r pages=%d reason=repeated_token",
                    path,
                    token,
                    page_no,
                )
                break
            seen_tokens.add(token)
            p["fromToken"] = token

    def get_all(self, path: str, *, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Collect all paginated items at *path* into a list.

        For large result sets consider iter_all() to avoid buffering everything
        in memory at once.
        """
        return list(self.iter_all(path, params=params))

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        """
        Send a GET request to *path* for a single resource or an
        already-complete (non-paginated) response.

        :param path: API path.
        :param params: optional query parameters.
        :return: the parsed JSON response, or ``None`` for a ``204``/empty
            response.
        """
        return self._request("GET", path, params=params)

    def post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        """
        Send a POST request to *path*, with an optional JSON body.

        :param path: API path.
        :param body: JSON-serializable request body. Optional — omit or pass
            ``None`` for body-less POST endpoints (e.g. ``/users/block/{userId}``,
            ``/workspaces/{ws}/documents/{document}/block``). When ``None``, no
            JSON payload is sent.
        :return: the parsed JSON response, or ``None`` for a ``204``/empty response.
        """
        return self._request("POST", path, json=body)

    def patch(self, path: str, body: dict[str, Any]) -> Any:
        """
        Send a PATCH request to *path* with a JSON body.

        Unlike :meth:`post`/:meth:`put`, *body* is required here -- a PATCH
        with no fields to change is meaningless. Callers decide how the body
        was serialized (``exclude_none=True`` vs. the ``exclude_unset=True,
        exclude_none=False`` null-clearing form); this method just forwards
        whatever dict it is given.

        :param path: API path.
        :param body: JSON-serializable request body.
        :return: the parsed JSON response, or ``None`` for a ``204``/empty
            response.
        """
        return self._request("PATCH", path, json=body)

    def put(self, path: str, body: dict[str, Any] | None = None) -> Any:
        """
        Send a PUT request to *path*, with an optional JSON body.

        :param path: API path.
        :param body: JSON-serializable request body. Optional — omit or pass
            ``None`` for body-less PUT endpoints. When ``None``, no JSON payload
            is sent.
        :return: the parsed JSON response, or ``None`` for a ``204``/empty response.
        """
        return self._request("PUT", path, json=body)

    def post_multipart(
        self,
        path: str,
        *,
        file_name: str,
        content: bytes | BinaryIO,
        content_type: str | None = None,
        field_name: str = "file",
    ) -> Any:
        """
        Upload a file to *path* as a ``multipart/form-data`` POST request.

        :param path: API path (e.g. an attachment-upload endpoint).
        :param file_name: file name reported for the uploaded multipart part.
        :param content: file content, either ``bytes`` or a binary file-like
            object (opened for reading in binary mode).
        :param content_type: optional MIME type for the uploaded part. When
            ``None``, the part is sent without an explicit per-file content type
            and ``requests``/the server infer it.
        :param field_name: multipart form field name. Defaults to ``"file"``,
            which is the field name the CWM attachment-upload endpoints expect.
        :return: the parsed JSON response, or ``None`` for a ``204``/empty
            response (attachment uploads respond ``204 No Content`` on success).

        The session-wide ``Content-Type: application/json`` header is dropped
        for this request only, so ``requests`` can set its own
        ``multipart/form-data; boundary=...`` content type instead.
        """
        file_tuple: tuple[Any, ...] = (
            (file_name, content, content_type) if content_type is not None else (file_name, content)
        )
        files = {field_name: file_tuple}
        return self._request("POST", path, files=files, headers={"Content-Type": None})

    def get_bytes(self, path: str, *, params: dict[str, Any] | None = None) -> bytes:
        """
        Send a GET request to *path* and return the raw response body.

        Unlike :meth:`get`, the response is never parsed as JSON — use this for
        binary payloads such as attachment downloads.

        :param path: API path (e.g. an attachment-download endpoint).
        :param params: optional query parameters.
        :return: the raw response body as ``bytes``; ``b""`` for a ``204``
            status or an empty response.
        """
        return self._request("GET", path, params=params, decode=self._decode_bytes)

    def delete(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        """
        Send a DELETE request to *path*, with optional query params and/or a JSON body.

        :param path: API path.
        :param params: optional query parameters.
        :param body: JSON-serializable request body. Optional — every DELETE
            endpoint except ``/workspaces/{ws}/documents/{document}/workitem-links``
            takes no body; omit or pass ``None`` for those. When ``None``, no
            JSON payload is sent.
        :return: the parsed JSON response, or ``None`` for a ``204``/empty response.
        """
        return self._request("DELETE", path, params=params, json=body)
