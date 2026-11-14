#!/usr/bin/env python3
"""Sanity-check the static site in ``site/``.

Verifies that every local ``href`` / ``src`` / ``srcset`` resolves to a file,
that in-page ``#anchors`` exist, that JSON-LD structured data is valid JSON,
that canonical-origin metadata URLs resolve locally, and that no page loads
third-party resources (the site is telemetry-free and makes no external
requests when rendered). Standard library only.
"""

import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

SITE = Path(__file__).resolve().parent.parent / "site"
CANONICAL_ORIGIN = "https://bigfoot.sektor64.net"
LOAD_ATTRS = {
    ("link", "href"),
    ("script", "src"),
    ("img", "src"),
    ("img", "srcset"),
    ("source", "src"),
    ("source", "srcset"),
    ("iframe", "src"),
}
# <link rel="..."> tokens that declare page metadata and are never fetched by browsers.
PASSIVE_LINK_RELS = {"canonical"}
META_URL_KEYS = {"og:url", "og:image", "twitter:image"}


def iter_srcset_urls(value: str):
    for candidate in value.split(","):
        parts = candidate.strip().split()
        if parts:
            yield parts[0]


def iter_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from iter_strings(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_strings(item)


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.refs = []  # (tag, attr, value, rels)
        self.meta_urls = []  # (key, value)
        self.json_ld = []  # raw script contents
        self._in_json_ld = False
        self._json_ld_chunks = []

    def handle_starttag(self, tag, attrs):
        attr_map = {name: value for name, value in attrs if value is not None}
        rels = frozenset(attr_map.get("rel", "").lower().split())

        if tag == "script" and attr_map.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_chunks = []

        if tag == "meta":
            key = (attr_map.get("property") or attr_map.get("name") or "").lower()
            content = attr_map.get("content")
            if key in META_URL_KEYS and content:
                self.meta_urls.append((key, content))

        for name, value in attrs:
            if value is None:
                continue
            if name == "id":
                self.ids.add(value)
            elif name in ("href", "src"):
                self.refs.append((tag, name, value, rels))
            elif name == "srcset":
                for candidate_url in iter_srcset_urls(value):
                    self.refs.append((tag, name, candidate_url, rels))

    def handle_data(self, data):
        if self._in_json_ld:
            self._json_ld_chunks.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._json_ld_chunks))
            self._in_json_ld = False
            self._json_ld_chunks = []


def check_canonical_origin_url(rel_page: Path, label: str, value: str, parsed: dict, errors: list):
    if not value.startswith(CANONICAL_ORIGIN):
        return
    url = urlparse(value)
    rel_path = url.path.lstrip("/")
    target = (SITE / "index.html") if not rel_path else (SITE / rel_path).resolve()
    if not target.exists():
        errors.append(f"{rel_page}: {label} points to missing site file {value!r}")
        return
    if url.fragment and target.suffix == ".html":
        ids = parsed[target].ids if target in parsed else set()
        if url.fragment not in ids:
            errors.append(f"{rel_page}: {label} points to missing anchor #{url.fragment} in {target.name}")


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
        for tag, attr, value, rels in collector.refs:
            url = urlparse(value)
            if url.scheme in ("http", "https"):
                is_passive_link = tag == "link" and bool(rels) and rels <= PASSIVE_LINK_RELS
                if (tag, attr) in LOAD_ATTRS and not is_passive_link:
                    errors.append(f"{rel}: <{tag}> loads external resource {value}")
                elif is_passive_link:
                    check_canonical_origin_url(rel, f"<{tag} rel={' '.join(sorted(rels))}>", value, parsed, errors)
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

        for key, content in collector.meta_urls:
            if not content.startswith(("http://", "https://")):
                errors.append(f"{rel}: <meta {key}> must be an absolute HTTPS URL, got {content!r}")
            else:
                check_canonical_origin_url(rel, f"<meta {key}>", content, parsed, errors)

        for idx, raw_json in enumerate(collector.json_ld, start=1):
            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError as exc:
                errors.append(f"{rel}: invalid JSON-LD block #{idx}: {exc}")
                continue
            for s in iter_strings(data):
                check_canonical_origin_url(rel, f"JSON-LD #{idx}", s, parsed, errors)

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if not errors:
        print(f"OK: checked {len(pages)} page(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
