# Bigfoot Website (`bigfoot/website`)

The official website of **Bigfoot OS**. A dependency-free static site (plain HTML, CSS and a few lines of progressive-enhancement JavaScript) deployed with **GitLab Pages**.

It follows the [Bigfoot design system](https://git.sektor64.net/bigfoot/design-guidelines) (OLED obsidian `#06070a` palette, soft-white pill actions, hairline surfaces), uses system fonts and makes no third-party requests, so visiting it is as private as running the OS.

## Layout

| Path | Purpose |
| :--- | :--- |
| [`site/`](site) | Everything that gets published. `index.html`, `assets/`, `robots.txt`, `sitemap.xml`. |
| [`scripts/build-assets.sh`](scripts/build-assets.sh) | Renders derived WebP images and favicons from source SVGs/PNGs. |
| [`scripts/check-site.py`](scripts/check-site.py) | Verifies local links, `srcset` assets, JSON-LD and anchors resolve and that nothing loads external resources. |
| [`.gitlab-ci.yml`](.gitlab-ci.yml) | `build:assets` + `check:site` + `check:w3c` on every pipeline, `pages` and `docker` deploy on `main`. |

## Local preview

```bash
./scripts/build-assets.sh
python3 scripts/check-site.py
python3 -m http.server --directory site 8000   # http://localhost:8000
```

> [!IMPORTANT]
> Keep every URL in `site/` **relative** (`assets/css/style.css`, not `/assets/css/style.css`). The site is served from a sub-path of the group Pages domain, and `check-site.py` fails the pipeline on root-relative URLs.

## Deployment

Pushing to `main` runs the `pages` job, which publishes `site/` to:

**https://bigfoot.pages.sector64.net/website/**

The project uses a **non-unique** Pages domain (like [`bigfoot/flatpaks`](https://git.sektor64.net/bigfoot/flatpaks)), so the URL is stable and human-readable instead of a generated `*-<hash>.pages…` hostname. This is configured per project under **Deploy → Pages → Use unique domain** (off), or via the API:

```bash
curl -X PATCH -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  --data "pages_unique_domain_enabled=false" \
  "$GITLAB_HOST/api/v4/projects/bigfoot%2Fwebsite/pages"
```

Pages access control must also be set to **Everyone** so the public can view the site (**Settings → General → Visibility → Pages**).

## License

Apache-2.0. See [LICENSE](LICENSE).
