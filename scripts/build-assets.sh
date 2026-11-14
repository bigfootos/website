#!/bin/sh
# Render derived WebP images and favicon assets from source SVGs/PNGs in site/.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SITE="$ROOT/site"
IMG_DIR="$SITE/assets/img"

render_svg() {
    src=$1
    dst=$2
    w=${3:-}
    h=${4:-}
    if command -v rsvg-convert >/dev/null 2>&1; then
        if [ -n "$w" ] && [ -n "$h" ]; then
            rsvg-convert -w "$w" -h "$h" "$src" -o "$dst"
        else
            rsvg-convert "$src" -o "$dst"
        fi
    elif command -v qlmanage >/dev/null 2>&1 && command -v sips >/dev/null 2>&1; then
        tmpdir=$(mktemp -d)
        size=${w:-1920}
        qlmanage -t -s "$size" -o "$tmpdir" "$src" >/dev/null 2>&1
        tmp_png="$tmpdir/$(basename "$src").png"
        if [ -n "$w" ] && [ -n "$h" ]; then
            sips -z "$h" "$w" "$tmp_png" --out "$dst" >/dev/null
        else
            cp "$tmp_png" "$dst"
        fi
        rm -rf "$tmpdir"
    else
        echo "ERROR: need rsvg-convert (or macOS qlmanage+sips) to rasterize $src" >&2
        exit 1
    fi
}

# 1. Brand favicons and touch icon derived from site/assets/img/logo.svg
if [ -f "$IMG_DIR/logo.svg" ]; then
    cp "$IMG_DIR/logo.svg" "$SITE/favicon.svg"
    render_svg "$IMG_DIR/logo.svg" "$SITE/favicon-48x48.png" 48 48
    render_svg "$IMG_DIR/logo.svg" "$SITE/apple-touch-icon.png" 180 180
fi

# 2. Rasterize any other SVG in site/assets/img/*.svg to a PNG fallback
for svg in "$IMG_DIR"/*.svg; do
    [ -f "$svg" ] || continue
    stem=$(basename "$svg" .svg)
    [ "$stem" = "logo" ] && continue
    render_svg "$svg" "$IMG_DIR/$stem.png"
done

# 3. Encode every PNG in site/assets/img/*.png to WebP
for png in "$IMG_DIR"/*.png; do
    [ -f "$png" ] || continue
    stem=$(basename "$png" .png)
    cwebp -quiet -q 86 -m 6 -sharp_yuv "$png" -o "$IMG_DIR/$stem.webp"
done
