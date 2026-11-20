#!/bin/sh
# Render derived WebP images and favicon assets from source SVGs/PNGs in site/.
set -eu

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
SITE="$ROOT/site"
IMG_DIR="$SITE/assets/img"

render_svg() {
    src=$1
    dst=$2
    w=$3
    h=$4
    if command -v rsvg-convert >/dev/null 2>&1; then
        rsvg-convert -w "$w" -h "$h" "$src" -o "$dst"
    elif command -v qlmanage >/dev/null 2>&1 && command -v sips >/dev/null 2>&1; then
        tmpdir=$(mktemp -d)
        qlmanage -t -s "$w" -o "$tmpdir" "$src" >/dev/null 2>&1
        tmp_png="$tmpdir/$(basename "$src").png"
        sips -z "$h" "$w" "$tmp_png" --out "$dst" >/dev/null
        rm -rf "$tmpdir"
    else
        echo "ERROR: need rsvg-convert (or macOS qlmanage+sips) to rasterize $src" >&2
        exit 1
    fi
}

# 1. Brand favicons, touch icon and webmanifest icons derived from site/assets/img/logo.svg
if [ -f "$IMG_DIR/logo.svg" ]; then
    cp "$IMG_DIR/logo.svg" "$SITE/favicon.svg"
    render_svg "$IMG_DIR/logo.svg" "$SITE/favicon-48x48.png" 48 48
    render_svg "$IMG_DIR/logo.svg" "$SITE/apple-touch-icon.png" 180 180
    render_svg "$IMG_DIR/logo.svg" "$SITE/icon-192.png" 192 192
    render_svg "$IMG_DIR/logo.svg" "$SITE/icon-512.png" 512 512
fi

# 2. Encode every PNG in site/assets/img/*.png (except social-preview.png) to WebP
rm -f "$IMG_DIR/social-preview.webp"
for png in "$IMG_DIR"/*.png; do
    [ -f "$png" ] || continue
    stem=$(basename "$png" .png)
    [ "$stem" = "social-preview" ] && continue
    cwebp -quiet -q 86 -m 6 -sharp_yuv "$png" -o "$IMG_DIR/$stem.webp"
done
