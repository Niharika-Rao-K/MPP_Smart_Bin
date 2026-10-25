
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


_CACHE = {}
_CACHE_TTL_SECONDS = 6 * 60 * 60
_MAX_RESPONSE_BYTES = 1_000_000
_MAX_TEXT_CHARS = 1200
_TIMEOUT_SECONDS = 4


class _TextExtractor(HTMLParser):
    """Extract readable text while ignoring scripts and styles."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip_depth = max(0, self.skip_depth - 1)

    def handle_data(self, data):
        if not self.skip_depth:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def fetch_reference_page(url):
    """
    Fetch a configured public reference page for supporting context.

    This does not verify prices or change reward eligibility.
    Website failures are returned as metadata.
    """
    retrieved_at = datetime.now(timezone.utc).isoformat()

    if not url:
        return {
            "status": "not_configured",
            "retrieved_at": retrieved_at,
            "text_excerpt": "",
        }

    try:
        parsed = urlparse(str(url))

        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return {
                "status": "invalid_url",
                "retrieved_at": retrieved_at,
                "text_excerpt": "",
            }

        cache_key = str(url)
        cached = _CACHE.get(cache_key)
        now = time.monotonic()

        if cached and now - cached["cached_at"] < _CACHE_TTL_SECONDS:
            return {
                "status": "cached",
                "source_url": cache_key,
                "retrieved_at": cached["retrieved_at"],
                "text_excerpt": cached["text_excerpt"],
            }

        request = Request(
            cache_key,
            headers={
                "User-Agent": "SmartBin-ReferenceRetriever/1.0"
            },
        )

        with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            final_url = urlparse(response.geturl())

            if final_url.scheme not in {"http", "https"}:
                raise ValueError("Unexpected redirect scheme")

            content_type = response.headers.get_content_type().lower()

            if content_type not in {
                "text/html",
                "text/plain",
                "application/xhtml+xml",
            }:
                return {
                    "status": "unsupported_content_type",
                    "source_url": cache_key,
                    "retrieved_at": retrieved_at,
                    "text_excerpt": "",
                }

            raw = response.read(_MAX_RESPONSE_BYTES + 1)

            if len(raw) > _MAX_RESPONSE_BYTES:
                return {
                    "status": "response_too_large",
                    "source_url": cache_key,
                    "retrieved_at": retrieved_at,
                    "text_excerpt": "",
                }

            charset = response.headers.get_content_charset() or "utf-8"
            page = raw.decode(charset, errors="replace")

        if content_type == "text/plain":
            extracted = " ".join(page.split())
        else:
            parser = _TextExtractor()
            parser.feed(page)
            extracted = " ".join(parser.parts)

        excerpt = extracted[:_MAX_TEXT_CHARS]

        _CACHE[cache_key] = {
            "cached_at": time.monotonic(),
            "retrieved_at": retrieved_at,
            "text_excerpt": excerpt,
        }

        return {
            "status": "fetched",
            "source_url": cache_key,
            "retrieved_at": retrieved_at,
            "text_excerpt": excerpt,
        }

    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        ValueError,
    ) as exc:
        return {
            "status": "unavailable",
            "source_url": str(url),
            "retrieved_at": retrieved_at,
            "error_type": type(exc).__name__,
            "text_excerpt": "",
        }
