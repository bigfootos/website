# Repository Layout & GitLab Pages Deployment

[← Back to Bigfoot Website Overview](../README.md)

---

## Layout

| Path | Purpose |
| :--- | :--- |
| [`site/`](../site) | Everything that gets published. `index.html`, `assets/`, `site.webmanifest`, `robots.txt`, `sitemap.xml`. |
| [`scripts/build-assets.sh`](../scripts/build-assets.sh) | Renders derived WebP images, favicons, and webmanifest icons from source SVGs/PNGs. |
| [`scripts/check-site.py`](../scripts/check-site.py) | Verifies local links, `srcset` assets, SEO metadata, JSON-LD, `site.webmanifest`, `sitemap.xml`, `robots.txt`, and anchors resolve and that nothing loads external resources. |
| [`Containerfile`](../Containerfile) | Multi-stage Alpine + Nginx container build that renders derived assets via `scripts/build-assets.sh` and serves `site/` on port `80`. |
| [`nginx/default.conf`](../nginx/default.conf) | Nginx virtual host configuration with gzip compression, cache headers, and security headers (`X-Content-Type-Options`, `Referrer-Policy`). |
| [`.gitlab-ci.yml`](../.gitlab-ci.yml) | `build:assets` + `check:site` + `check:w3c` on every pipeline, `pages` and `docker` deploy on `main`. |

> [!IMPORTANT]
> Keep every URL in `site/` **relative** (`assets/css/style.css`, not `/assets/css/style.css`). The site is served from a sub-path of the group Pages domain, and `check-site.py` fails the pipeline on root-relative URLs.

---

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

Pushing to `main` also triggers the `docker` job, which builds [`Containerfile`](../Containerfile) with `buildah` and pushes the self-contained Nginx container image to the GitLab Container Registry:

**`git.sektor64.net:5005/bigfoot/website:latest`**
