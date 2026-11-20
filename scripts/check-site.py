#!/usr/bin/env python3
"""Sanity-check and SEO-audit the static site in ``site/``.

Verifies that:
- Every local ``href`` / ``src`` / ``srcset`` resolves to a file.
- Every in-page ``#anchor`` exists.
- Every page has a ``<title>``, ``<meta name="description">``, ``<link rel="canonical">``,
  Open Graph metadata, a single ``<h1>``, and ``alt``/``width``/``height`` on ``<img>``.
- JSON-LD structured data is valid JSON and canonical URLs resolve locally.
- ``site.webmanifest``, ``sitemap.xml`` (including image entries), and ``robots.txt``
  are valid and reference existing files.
- No page loads third-party resources (the site is telemetry-free and makes no
  external requests when rendered). Standard library only.
"""

import json
import sys
import xml.etree.ElementTree as ET
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
REQUIRED_META_KEYS = {"description", "og:title", "og:description", "og:url", "og:image"}


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
        self.meta = {}  # key -> content
        self.meta_urls = []  # (key, value)
        self.canonical_urls = []
        self.h1_count = 0
        self.imgs = []  # attr_map
        self.title = ""
        self._in_title = False
        self.json_ld = []  # raw script contents
        self._in_json_ld = False
        self._json_ld_chunks = []

    def handle_starttag(self, tag, attrs):
        attr_map = {name: value for name, value in attrs if value is not None}
        rels = frozenset(attr_map.get("rel", "").lower().split())

        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "img":
            self.imgs.append(attr_map)
        elif tag == "link" and "canonical" in rels and attr_map.get("href"):
            self.canonical_urls.append(attr_map["href"])
        elif tag == "script" and attr_map.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_chunks = []
        elif tag == "meta":
            key = (attr_map.get("property") or attr_map.get("name") or "").lower()
            content = attr_map.get("content", "").strip()
            if key and content:
                self.meta[key] = content
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
        if self._in_title:
            self.title += data
        if self._in_json_ld:
            self._json_ld_chunks.append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._json_ld_chunks))
            self._in_json_ld = False
            self._json_ld_chunks = []


def check_canonical_origin_url(rel_page, label: str, value: str, parsed: dict, errors: list):
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
        if url.fragment not in ids and url.fragment not in ("organization", "website", "software"):
            errors.append(f"{rel_page}: {label} points to missing anchor #{url.fragment} in {target.name}")


def check_auxiliary_files(parsed: dict, errors: list):
    manifest_path = SITE / "site.webmanifest"
    if not manifest_path.exists():
        errors.append("site.webmanifest: missing file")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for icon in manifest.get("icons", []):
                src = icon.get("src", "")
                if not src or src.startswith(("/", "http://", "https://")):
                    errors.append(f"site.webmanifest: icon src {src!r} must be a relative path")
                elif not (SITE / src).exists():
                    errors.append(f"site.webmanifest: missing icon file {src!r}")
        except json.JSONDecodeError as exc:
            errors.append(f"site.webmanifest: invalid JSON: {exc}")

    sitemap_path = SITE / "sitemap.xml"
    if not sitemap_path.exists():
        errors.append("sitemap.xml: missing file")
    else:
        try:
            root = ET.fromstring(sitemap_path.read_text(encoding="utf-8"))
            ns = {
                "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
                "image": "http://www.google.com/schemas/sitemap-image/1.1",
            }
            locs = [el.text.strip() for el in root.findall(".//sm:loc", ns) if el.text]
            img_locs = [el.text.strip() for el in root.findall(".//image:loc", ns) if el.text]
            if not locs:
                errors.append("sitemap.xml: no <loc> entries found")
            for loc in locs + img_locs:
                check_canonical_origin_url("sitemap.xml", "<loc>", loc, parsed, errors)
        except ET.ParseError as exc:
            errors.append(f"sitemap.xml: invalid XML: {exc}")

    robots_path = SITE / "robots.txt"
    if not robots_path.exists():
        errors.append("robots.txt: missing file")
    else:
        robots_text = robots_path.read_text(encoding="utf-8")
        if f"Sitemap: {CANONICAL_ORIGIN}/sitemap.xml" not in robots_text:
            errors.append("robots.txt: missing canonical Sitemap directive")


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
        if not collector.title.strip():
            errors.append(f"{rel}: missing <title>")
        if collector.h1_count != 1:
            errors.append(f"{rel}: expected exactly 1 <h1>, found {collector.h1_count}")
        if len(collector.canonical_urls) != 1:
            errors.append(f"{rel}: expected 1 <link rel='canonical'>, found {len(collector.canonical_urls)}")
        for req_meta in sorted(REQUIRED_META_KEYS):
            if req_meta not in collector.meta:
                errors.append(f"{rel}: missing required <meta {req_meta}>")

        for img in collector.imgs:
            src = img.get("src", "<unknown>")
            if "alt" not in img:
                errors.append(f"{rel}: <img src={src!r}> missing alt attribute")
            if not img.get("width") or not img.get("height"):
                errors.append(f"{rel}: <img src={src!r}> missing width or height attribute")

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

    check_auxiliary_files(parsed, errors)

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if not errors:
        print(f"OK: checked {len(pages)} page(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
