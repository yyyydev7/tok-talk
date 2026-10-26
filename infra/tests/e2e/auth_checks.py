"""Shared HTTP and cookie checks for the development and demo stacks."""

from email.message import Message
from http.cookiejar import CookieJar
import json
import secrets
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    Request,
    build_opener,
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        # Signup and logout return 302; their target page is not an API response.
        return None


class HttpClient:
    def __init__(
        self, base: str, origin: str | None = None, *, cookies: CookieJar | None = None
    ) -> None:
        self.base = base.rstrip("/")
        self.origin = origin
        self.cookies = cookies if cookies is not None else CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies), NoRedirect())

    def request(
        self, path: str, method: str = "GET", form: dict[str, str] | None = None,
        *, timeout: float = 10,
    ) -> tuple[int, str, Message]:
        headers = {}
        if self.origin is not None:
            headers["Origin"] = self.origin
        data = None
        if form is not None:
            data = urlencode(form).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = Request(self.base + path, data=data, headers=headers, method=method)
        try:
            response = self.opener.open(request, timeout=timeout)
        except HTTPError as error:
            response = error
        with response:
            return response.code, response.read().decode("utf-8"), response.headers


def origin_of(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def expect_status(actual: int, expected: int, step: str) -> None:
    if actual != expected:
        raise AssertionError(f"{step}: expected HTTP {expected}, got {actual}")


def check_anonymous_rag(client: HttpClient) -> None:
    for path, method in (("/chemicals", "GET"), ("/rag-query", "POST"),
                         ("/rag-query/auto", "POST")):
        # No question body is sent, so this check cannot generate an LLM answer.
        status, body, _ = client.request(path, method)
        expect_status(status, 401, f"Anonymous RAG request: {path}")
        assert json.loads(body).get("detail") == "UNAUTHORIZED", "RAG auth error missing"


def check_chemicals(client: HttpClient, index_ready: bool) -> None:
    # The first authenticated call also loads the embedding model into memory.
    status, body, _ = client.request("/chemicals", timeout=180)
    expect_status(status, 200 if index_ready else 503, "Authenticated chemical list")
    payload = json.loads(body)
    if not index_ready:
        assert payload.get("detail") == "RAG 인덱스를 사용할 수 없습니다.", "Index error missing"
        print("PASS rag: authenticated chemical list reports unavailable index")
        return
    expected = {
        "acetone": "67-64-1",
        "ethanol": "64-17-5",
        "methanol": "67-56-1",
        "toluene": "108-88-3",
        "acetic_acid": "64-19-7",
    }
    items = payload.get("items")
    assert isinstance(items, list) and len(items) == len(expected), "Expected five loaded chemicals"
    assert all(isinstance(item, dict) for item in items), "Invalid chemical list entries"
    actual = {item.get("material_id"): item.get("cas_number") for item in items}
    assert actual == expected, "Loaded chemical IDs or CAS numbers differ"
    print("PASS rag: authenticated chemical list contains all five expected materials")


def check_authentication(base: str, origin: str, *, rag_base: str, index_ready: bool,
                         require_secure_cookie: bool = False) -> None:
    client = HttpClient(base, origin)
    rag_client = HttpClient(rag_base, origin, cookies=client.cookies)
    username = "smoke_" + secrets.token_hex(12)
    password = secrets.token_urlsafe(24)
    form = {"username": username, "password": password}

    status, body, _ = client.request("/api/auth/check")
    expect_status(status, 401, "Anonymous authentication")
    assert json.loads(body).get("error") == "unauthorized", "Anonymous error missing"
    check_anonymous_rag(rag_client)
    status, body, _ = rag_client.request("/inventory")
    expect_status(status, 404, "Unimplemented inventory")
    assert json.loads(body).get("detail") == "Not Found", "Inventory route changed"

    status, body, headers = client.request("/api/signup", "POST", form)
    expect_status(status, 302, "Signup")
    assert json.loads(body).get("ok") is True, "Signup did not succeed"
    assert headers.get("Location") == "/login", "Signup redirect target changed"

    status, body, _ = client.request("/api/signup", "POST", form)
    expect_status(status, 409, "Duplicate signup")
    assert json.loads(body).get("error") == "username_exists", "Duplicate account error missing"

    invalid_form = {"username": username, "password": password + "-wrong"}
    status, body, _ = client.request("/api/login", "POST", invalid_form)
    expect_status(status, 401, "Incorrect password")
    assert json.loads(body).get("error") == "invalid_credentials", "Invalid login error missing"
    assert not any(cookie.name == "ACCESS_TOKEN" for cookie in client.cookies), "Invalid login issued a token"

    status, body, headers = client.request("/api/login", "POST", form)
    expect_status(status, 200, "Login")
    assert json.loads(body).get("ok") is True, "Login did not succeed"
    assert headers.get("Access-Control-Allow-Origin") == origin, "Login CORS origin missing"
    assert headers.get("Access-Control-Allow-Credentials") == "true", "Login cookie CORS missing"
    token_cookies = [cookie for cookie in client.cookies if cookie.name == "ACCESS_TOKEN"]
    assert len(token_cookies) == 1 and token_cookies[0].value, "Login cookie missing"
    assert token_cookies[0].has_nonstandard_attr("HttpOnly"), "Login cookie must be HttpOnly"
    if require_secure_cookie:
        assert token_cookies[0].secure, "Public HTTPS login cookie must be Secure"
        assert token_cookies[0].get_nonstandard_attr("SameSite") == "Strict", "SameSite must be Strict"

    status, body, _ = client.request("/api/auth/check")
    expect_status(status, 200, "Authenticated request")
    payload = json.loads(body)
    assert payload.get("ok") is True and payload.get("via") == "jwt", "JWT authentication failed"
    assert payload.get("username") == username and payload.get("sub") == username, "JWT user mismatch"
    check_chemicals(rag_client, index_ready)

    status, body, headers = client.request("/api/logout", "POST")
    expect_status(status, 302, "Logout")
    assert json.loads(body).get("ok") is True, "Logout did not succeed"
    assert headers.get("Location") == "/login", "Logout redirect target changed"
    if require_secure_cookie:
        assert "; Secure" in headers.get("Set-Cookie", ""), "Logout cookie must also be Secure"
    assert not any(cookie.name == "ACCESS_TOKEN" for cookie in client.cookies), "Logout cookie was not cleared"

    status, body, _ = client.request("/api/auth/check")
    expect_status(status, 401, "Authentication after logout")
    assert json.loads(body).get("error") == "unauthorized", "Logout did not end cookie authentication"
    check_anonymous_rag(rag_client)
    print("PASS auth: signup, duplicate rejection, invalid password, JWT cookie, logout")
    print("PASS rag: anonymous protected routes rejected; inventory remains unimplemented")
