#!/usr/bin/env python3
"""Sanity-check the static site in ``site/``.

Verifies that every local ``href`` / ``src`` resolves to a file, that in-page
``#anchors`` exist, and that no page loads third-party resources (the site is
telemetry-free and makes no external requests when rendered). Standard library
only.
"""

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

SITE = Path(__file__).resolve().parent.parent / "site"
LOAD_ATTRS = {("link", "href"), ("script", "src"), ("img", "src"), ("source", "src"), ("iframe", "src")}


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.refs = []  # (tag, attr, value)

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value is None:
                continue
            if name == "id":
                self.ids.add(value)
            elif name in ("href", "src"):
                self.refs.append((tag, name, value))


def main() -> int:
    errors = []
    pages = sorted(SITE.rglob("*.html"))
    if not pages:
        errors.append(f"no HTML pages found in {SITE}")

    parsed = {}
    for page in pages:
        collector = Collector()
        collector.feed(page.read_text(encoding="utf-8"))
        parsed[page] = collector

    for page, collector in parsed.items():
        rel = page.relative_to(SITE)
        for tag, attr, value in collector.refs:
            url = urlparse(value)
            if url.scheme in ("http", "https"):
                if (tag, attr) in LOAD_ATTRS:
                    errors.append(f"{rel}: <{tag}> loads external resource {value}")
                continue
            if url.scheme in ("mailto", "tel"):
                continue
            if url.path.startswith("/"):
                errors.append(f"{rel}: root-relative URL {value!r} breaks path-based Pages hosting")
                continue

            target = page if not url.path else (page.parent / url.path).resolve()
            if not target.exists():
                errors.append(f"{rel}: missing file for {value!r}")
                continue
            if url.fragment and target.suffix == ".html":
                ids = parsed[target].ids if target in parsed else set()
                if url.fragment not in ids:
                    errors.append(f"{rel}: missing anchor #{url.fragment} in {target.name}")

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if not errors:
        print(f"OK: checked {len(pages)} page(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
