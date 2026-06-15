"""Tests for graphify/security.py - URL validation, safe fetch, path guards, label sanitisation."""
from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import socket

from graphify.security import (
    check_graph_file_size_cap,
    sanitize_label,
    sanitize_metadata,
    safe_fetch,
    safe_fetch_text,
    validate_graph_path,
    validate_url,
    _MAX_FETCH_BYTES,
    _MAX_GRAPH_FILE_BYTES,
    _MAX_TEXT_BYTES,
    _METADATA_MAX_LIST_ITEMS,
    _METADATA_MAX_VALUE_LEN,
    _NoFileRedirectHandler,
    _sanitize_metadata_string,
    _sanitize_metadata_value,
    _ssrf_guarded_socket,
)


def _patch_resolve(monkeypatch, ip_str: str, family: int = socket.AF_INET):
    """Force graphify.security's socket.getaddrinfo to resolve to *ip_str*."""
    def _fake(host, port, *args, **kwargs):
        return [(family, socket.SOCK_STREAM, 6, "", (ip_str, 0))]
    monkeypatch.setattr("graphify.security.socket.getaddrinfo", _fake)


# ---------------------------------------------------------------------------
# validate_url
# ---------------------------------------------------------------------------

def test_validate_url_accepts_http():
    assert validate_url("http://example.com/page") == "http://example.com/page"

def test_validate_url_accepts_https():
    assert validate_url("https://arxiv.org/abs/1706.03762") == "https://arxiv.org/abs/1706.03762"

def test_validate_url_rejects_file():
    with pytest.raises(ValueError, match="file"):
        validate_url("file:///etc/passwd")

def test_validate_url_rejects_ftp():
    with pytest.raises(ValueError, match="ftp"):
        validate_url("ftp://files.example.com/data.zip")

def test_validate_url_rejects_data():
    with pytest.raises(ValueError, match="data"):
        validate_url("data:text/html,<script>alert(1)</script>")

def test_validate_url_rejects_empty_scheme():
    with pytest.raises(ValueError):
        validate_url("//no-scheme.example.com")


# ---------------------------------------------------------------------------
# safe_fetch - scheme and redirect guards (mocked network)
# ---------------------------------------------------------------------------

def _make_mock_response(content: bytes, status: int = 200):
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.status = status
    mock.code = status
    chunks = [content[i:i+65536] for i in range(0, len(content), 65536)] + [b""]
    mock.read.side_effect = chunks
    return mock


def test_safe_fetch_rejects_file_url():
    with pytest.raises(ValueError, match="file"):
        safe_fetch("file:///etc/passwd")

def test_safe_fetch_rejects_ftp_url():
    with pytest.raises(ValueError, match="ftp"):
        safe_fetch("ftp://example.com/file.zip")

def test_safe_fetch_returns_bytes(tmp_path):
    mock_resp = _make_mock_response(b"hello world")
    with patch("graphify.security._build_opener") as mock_opener_fn:
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_resp
        mock_opener_fn.return_value = mock_opener
        result = safe_fetch("https://example.com/")
    assert result == b"hello world"

def test_safe_fetch_raises_on_non_2xx():
    mock_resp = _make_mock_response(b"Not Found", status=404)
    with patch("graphify.security._build_opener") as mock_opener_fn:
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_resp
        mock_opener_fn.return_value = mock_opener
        with pytest.raises(urllib.error.HTTPError):
            safe_fetch("https://example.com/missing")

def test_safe_fetch_raises_on_size_exceeded():
    # Build a response larger than max_bytes
    big_chunk = b"x" * 65_537
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200
    mock_resp.code = 200
    # Return the chunk twice so total > max_bytes=65536
    mock_resp.read.side_effect = [big_chunk, big_chunk, b""]

    with patch("graphify.security._build_opener") as mock_opener_fn:
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_resp
        mock_opener_fn.return_value = mock_opener
        with pytest.raises(OSError, match="size limit"):
            safe_fetch("https://example.com/huge", max_bytes=65_536)


# ---------------------------------------------------------------------------
# safe_fetch_text
# ---------------------------------------------------------------------------

def test_safe_fetch_text_decodes_utf8():
    content = "héllo wörld".encode("utf-8")
    mock_resp = _make_mock_response(content)
    with patch("graphify.security._build_opener") as mock_opener_fn:
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_resp
        mock_opener_fn.return_value = mock_opener
        result = safe_fetch_text("https://example.com/")
    assert result == "héllo wörld"

def test_safe_fetch_text_replaces_bad_bytes():
    bad = b"hello \xff world"
    mock_resp = _make_mock_response(bad)
    with patch("graphify.security._build_opener") as mock_opener_fn:
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_resp
        mock_opener_fn.return_value = mock_opener
        result = safe_fetch_text("https://example.com/")
    assert "hello" in result
    assert "world" in result
    assert "\xff" not in result


# ---------------------------------------------------------------------------
# validate_graph_path
# ---------------------------------------------------------------------------

def test_validate_graph_path_allows_inside_base(tmp_path):
    base = tmp_path / "graphify-out"
    base.mkdir()
    graph = base / "graph.json"
    graph.write_text("{}")
    result = validate_graph_path(str(graph), base=base)
    assert result == graph.resolve()

def test_validate_graph_path_blocks_traversal(tmp_path):
    base = tmp_path / "graphify-out"
    base.mkdir()
    evil = tmp_path / "graphify-out" / ".." / "etc_passwd"
    with pytest.raises(ValueError, match="escapes"):
        validate_graph_path(str(evil), base=base)

def test_validate_graph_path_requires_base_exists(tmp_path):
    base = tmp_path / "graphify-out"  # not created
    with pytest.raises(ValueError, match="does not exist"):
        validate_graph_path(str(base / "graph.json"), base=base)

def test_validate_graph_path_raises_if_file_missing(tmp_path):
    base = tmp_path / "graphify-out"
    base.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_graph_path(str(base / "missing.json"), base=base)


# ---------------------------------------------------------------------------
# sanitize_label
# ---------------------------------------------------------------------------

def test_sanitize_label_passthrough_html_chars():
    # sanitize_label does NOT HTML-escape — callers that inject into HTML must
    # wrap with html.escape() themselves (e.g. the title in to_html())
    assert sanitize_label("<script>") == "<script>"
    assert sanitize_label("foo & bar") == "foo & bar"

def test_sanitize_label_strips_control_chars():
    result = sanitize_label("hello\x00\x1fworld")
    assert "\x00" not in result
    assert "\x1f" not in result
    assert "helloworld" in result

def test_sanitize_label_caps_at_256():
    long_label = "a" * 300
    assert len(sanitize_label(long_label)) <= 256

def test_sanitize_label_safe_passthrough():
    assert sanitize_label("MyClass") == "MyClass"
    assert sanitize_label("extract_python") == "extract_python"


# ---------------------------------------------------------------------------
# check_graph_file_size_cap (#F4 — graph-load memory bomb protection)
# ---------------------------------------------------------------------------

def test_graph_size_cap_default_is_512_mib():
    assert _MAX_GRAPH_FILE_BYTES == 512 * 1024 * 1024


def test_graph_size_cap_under_limit_returns_none(tmp_path):
    p = tmp_path / "graph.json"
    p.write_text('{"nodes": [], "links": []}', encoding="utf-8")
    assert check_graph_file_size_cap(p) is None


def test_graph_size_cap_over_limit_raises(monkeypatch, tmp_path):
    monkeypatch.setattr("graphify.security._MAX_GRAPH_FILE_BYTES", 16)
    p = tmp_path / "graph.json"
    p.write_text('{"nodes": [], "links": [], "padding": "x" * 50}', encoding="utf-8")
    with pytest.raises(ValueError, match="exceeds"):
        check_graph_file_size_cap(p)


def test_graph_size_cap_error_message_includes_size_and_cap(monkeypatch, tmp_path):
    monkeypatch.setattr("graphify.security._MAX_GRAPH_FILE_BYTES", 8)
    p = tmp_path / "graph.json"
    p.write_text("AAAAAAAAAAAAAAAA", encoding="utf-8")  # 16 bytes
    with pytest.raises(ValueError) as excinfo:
        check_graph_file_size_cap(p)
    msg = str(excinfo.value)
    assert "16" in msg  # observed size
    assert "8" in msg   # cap
    assert "byte" in msg.lower()


def test_graph_size_cap_at_boundary_passes(monkeypatch, tmp_path):
    # Boundary: equal to cap is allowed; strictly greater is rejected.
    p = tmp_path / "graph.json"
    payload = "A" * 32
    p.write_text(payload, encoding="utf-8")
    monkeypatch.setattr("graphify.security._MAX_GRAPH_FILE_BYTES", 32)
    assert check_graph_file_size_cap(p) is None
    monkeypatch.setattr("graphify.security._MAX_GRAPH_FILE_BYTES", 31)
    with pytest.raises(ValueError):
        check_graph_file_size_cap(p)


def test_graph_size_cap_missing_file_silently_returns(tmp_path):
    # When stat() fails (FileNotFoundError → OSError), the helper returns None
    # so the caller's own existence check can surface a clearer error.
    missing = tmp_path / "does_not_exist.json"
    assert check_graph_file_size_cap(missing) is None


def test_graph_size_cap_unreadable_directory_silently_returns(monkeypatch, tmp_path):
    # Force stat() to raise PermissionError → still OSError → silent return.
    p = tmp_path / "graph.json"
    p.write_text("{}", encoding="utf-8")

    def _boom(self):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "stat", _boom)
    assert check_graph_file_size_cap(p) is None


# ---------------------------------------------------------------------------
# sanitize_metadata (recursive, bounded, HTML-safe)
# ---------------------------------------------------------------------------

def test_sanitize_metadata_string_strips_control_chars():
    result = _sanitize_metadata_string("hello\x00\x1fworld")
    assert "\x00" not in result
    assert "\x1f" not in result
    assert "helloworld" in result


def test_sanitize_metadata_string_escapes_html():
    result = _sanitize_metadata_string("<script>alert('x')</script>")
    assert "&lt;" in result
    assert "&gt;" in result
    assert "<script>" not in result


def test_sanitize_metadata_string_escapes_quotes():
    result = _sanitize_metadata_string('a"b\'c')
    # quote=True escapes both " and '
    assert "&quot;" in result
    assert "&#x27;" in result or "&apos;" in result


def test_sanitize_metadata_string_caps_length():
    long = "a" * (_METADATA_MAX_VALUE_LEN + 100)
    result = _sanitize_metadata_string(long)
    assert len(result) <= _METADATA_MAX_VALUE_LEN


def test_sanitize_metadata_string_coerces_non_string():
    # Non-str/dict/list/scalar inputs route through string sanitisation.
    class _Custom:
        def __str__(self) -> str:
            return "custom-repr"
    assert _sanitize_metadata_string(_Custom()) == "custom-repr"


def test_sanitize_metadata_value_preserves_simple_types():
    assert _sanitize_metadata_value(42) == 42
    assert _sanitize_metadata_value(3.14) == 3.14
    assert _sanitize_metadata_value(True) is True
    assert _sanitize_metadata_value(False) is False
    assert _sanitize_metadata_value(None) is None


def test_sanitize_metadata_value_recurses_into_dict():
    out = _sanitize_metadata_value({"k": "<script>x</script>"})
    assert isinstance(out, dict)
    assert "&lt;" in out["k"]


def test_sanitize_metadata_value_recurses_into_list():
    out = _sanitize_metadata_value(["<a>", "<b>", "<c>"])
    assert isinstance(out, list)
    assert all("&lt;" in s for s in out)


def test_sanitize_metadata_value_caps_list_length():
    huge = list(range(_METADATA_MAX_LIST_ITEMS * 3))
    out = _sanitize_metadata_value(huge)
    assert isinstance(out, list)
    assert len(out) == _METADATA_MAX_LIST_ITEMS


def test_sanitize_metadata_value_converts_tuple_to_list():
    out = _sanitize_metadata_value(("a", "b"))
    assert isinstance(out, list)
    assert out == ["a", "b"]


def test_sanitize_metadata_none_returns_empty_dict():
    assert sanitize_metadata(None) == {}


def test_sanitize_metadata_drops_empty_key():
    # Empty key (after control-char strip) is dropped.
    out = sanitize_metadata({"\x00": "v", "k": "v2"})
    assert "\x00" not in out
    assert out.get("k") == "v2"
    assert len(out) == 1


def test_sanitize_metadata_sanitizes_keys():
    out = sanitize_metadata({"<bad>": "v"})
    assert "<bad>" not in out
    assert any("&lt;" in k for k in out.keys())


def test_sanitize_metadata_recursive_nested():
    raw: dict[str, Any] = {
        "outer": {
            "inner": "<script>x</script>",
            "list": ["a", "<b>", 99, None, True],
        },
        "scalar": 42,
    }
    out = sanitize_metadata(raw)
    assert isinstance(out["outer"], dict)
    inner = out["outer"]
    assert isinstance(inner, dict)
    assert "&lt;" in inner["inner"]
    items = inner["list"]
    assert isinstance(items, list)
    assert items[0] == "a"
    assert "&lt;" in items[1]
    assert items[2] == 99
    assert items[3] is None
    assert items[4] is True
    assert out["scalar"] == 42


def test_sanitize_metadata_bool_not_coerced_to_int():
    # bool is an int subclass — order of isinstance checks must preserve bool.
    out = sanitize_metadata({"flag_t": True, "flag_f": False, "num": 1})
    assert out["flag_t"] is True
    assert out["flag_f"] is False
    assert out["num"] == 1


# ---------------------------------------------------------------------------
# validate_url — SSRF / private-IP blocking
# ---------------------------------------------------------------------------

def test_validate_url_blocks_loopback(monkeypatch):
    _patch_resolve(monkeypatch, "127.0.0.1")
    with pytest.raises(ValueError, match="private/internal IP"):
        validate_url("http://localhost.example.com/")

def test_validate_url_blocks_private_10(monkeypatch):
    _patch_resolve(monkeypatch, "10.0.0.5")
    with pytest.raises(ValueError, match="private/internal IP"):
        validate_url("http://internal.example.com/")

def test_validate_url_blocks_link_local_metadata(monkeypatch):
    # 169.254.169.254 — the AWS/GCP metadata endpoint.
    _patch_resolve(monkeypatch, "169.254.169.254")
    with pytest.raises(ValueError, match="private/internal IP"):
        validate_url("http://metadata.example.com/latest/meta-data/")

def test_validate_url_blocks_cgn_shared_address_space(monkeypatch):
    # RFC 6598 100.64.0.0/10 — is_private misses this on older Pythons.
    _patch_resolve(monkeypatch, "100.64.1.1")
    with pytest.raises(ValueError, match="private/internal IP"):
        validate_url("http://cgn.example.com/")

def test_validate_url_blocks_gcp_metadata_hostname():
    # Blocked by the hostname allowlist before DNS resolution.
    with pytest.raises(ValueError, match="metadata"):
        validate_url("http://metadata.google.internal/")

def test_validate_url_blocks_nat64_wrapping_private_ip(monkeypatch):
    # 64:ff9b::7f00:1 embeds 127.0.0.1 — must inspect the embedded IPv4.
    _patch_resolve(monkeypatch, "64:ff9b::7f00:1", family=socket.AF_INET6)
    with pytest.raises(ValueError, match="private/internal IP"):
        validate_url("http://nat64.example.com/")

def test_validate_url_allows_nat64_wrapping_public_ip(monkeypatch):
    # 64:ff9b::808:808 embeds 8.8.8.8 (public) — legitimate, must pass.
    _patch_resolve(monkeypatch, "64:ff9b::808:808", family=socket.AF_INET6)
    assert validate_url("http://nat64.example.com/") == "http://nat64.example.com/"

def test_validate_url_allows_public_ip(monkeypatch):
    _patch_resolve(monkeypatch, "8.8.8.8")
    assert validate_url("http://public.example.com/") == "http://public.example.com/"

def test_validate_url_dns_failure_raises(monkeypatch):
    def _boom(host, port, *args, **kwargs):
        raise socket.gaierror("name resolution failed")
    monkeypatch.setattr("graphify.security.socket.getaddrinfo", _boom)
    with pytest.raises(ValueError, match="DNS resolution failed"):
        validate_url("http://nonexistent.invalid/")


# ---------------------------------------------------------------------------
# _ssrf_guarded_socket — DNS-rebinding (TOCTOU) guard
# ---------------------------------------------------------------------------

def test_ssrf_guarded_socket_blocks_private_rebind(monkeypatch):
    # Original resolver returns a private IP at connect time → OSError.
    def _fake(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.9", 80))]
    monkeypatch.setattr(socket, "getaddrinfo", _fake)
    with _ssrf_guarded_socket():
        with pytest.raises(OSError, match="SSRF blocked"):
            socket.getaddrinfo("evil.example.com", 80)

def test_ssrf_guarded_socket_allows_public(monkeypatch):
    def _fake(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))]
    monkeypatch.setattr(socket, "getaddrinfo", _fake)
    with _ssrf_guarded_socket():
        result = socket.getaddrinfo("example.com", 80)
    assert result[0][4][0] == "93.184.216.34"

def test_ssrf_guarded_socket_skips_non_ip_addr(monkeypatch):
    # A non-IP address string (e.g. AF_UNIX path) must be skipped, not crash.
    def _fake(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("not-an-ip", 0))]
    monkeypatch.setattr(socket, "getaddrinfo", _fake)
    with _ssrf_guarded_socket():
        result = socket.getaddrinfo("h", 0)
    assert result[0][4][0] == "not-an-ip"

def test_ssrf_guarded_socket_restores_original(monkeypatch):
    sentinel = socket.getaddrinfo
    with _ssrf_guarded_socket():
        assert socket.getaddrinfo is not sentinel
    assert socket.getaddrinfo is sentinel


# ---------------------------------------------------------------------------
# _NoFileRedirectHandler — open-redirect SSRF guard
# ---------------------------------------------------------------------------

def test_redirect_handler_rejects_file_scheme():
    handler = _NoFileRedirectHandler()
    with pytest.raises(ValueError, match="scheme"):
        handler.redirect_request(
            MagicMock(), MagicMock(), 302, "Found", {}, "file:///etc/passwd"
        )

def test_redirect_handler_rejects_private_redirect(monkeypatch):
    _patch_resolve(monkeypatch, "127.0.0.1")
    handler = _NoFileRedirectHandler()
    with pytest.raises(ValueError, match="private/internal IP"):
        handler.redirect_request(
            MagicMock(), MagicMock(), 302, "Found", {}, "http://internal.example.com/"
        )

def test_redirect_handler_allows_public_redirect(monkeypatch):
    import urllib.request
    _patch_resolve(monkeypatch, "8.8.8.8")
    handler = _NoFileRedirectHandler()
    req = urllib.request.Request("http://example.com/")
    new_req = handler.redirect_request(
        req, None, 302, "Found", {}, "http://elsewhere.example.com/"
    )
    assert new_req.full_url == "http://elsewhere.example.com/"
