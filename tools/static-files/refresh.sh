#!/usr/bin/env bash
# Refresh the static files the browser downloads, in a local copy of the site.
#
#   refresh.sh SITE_DIR
#
# Run it by hand. It downloads every filter list in sources.txt from its
# publisher, copies the experimental
# list and the fonts component from the repository, writes the component
# manifest, checks everything, and only then replaces the contents of SITE_DIR
# (a checkout of the branch the site is published from). It never commits or
# pushes: review the result, then commit and push by hand.
#
# Environment:
#   BASE       base address the browser downloads the static files from
#              default https://hawkff.github.io/cromite/
#   FONTS_URL  download address of fonts_component.zip written into the manifest
#              default ${BASE}components/fonts_component.zip
#   SOURCES    list of filter lists, default sources.txt next to this script
#   REPO       repository checkout, default the one this script is in
#   FORCE=1    accept a list that shrank to less than half of its published size
set -euo pipefail

site=${1:?usage: refresh.sh SITE_DIR}
BASE=${BASE:-https://hawkff.github.io/cromite/}
FONTS_URL=${FONTS_URL:-${BASE}components/fonts_component.zip}
here=$(dirname "$(readlink -f "$0")")
SOURCES=${SOURCES:-$here/sources.txt}
REPO=${REPO:-$(dirname "$(dirname "$here")")}

[ -d "$site" ] || { echo "no such directory: $site" >&2; exit 1; }
[ -f "$REPO/tools/filters/experimental-cromite-filters.txt" ] ||
  { echo "REPO=$REPO is not a checkout of this repository" >&2; exit 1; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/filters" "$tmp/components"

fail() { echo "refresh: $*" >&2; exit 1; }

# A filter list starts with "[Adblock ...]" or with "!" comment lines.
# An error page served with status 200 must not replace a good list.
check_list() {
  local file=$1 name=$2
  [ -s "$file" ] || fail "$name is empty"
  head -c 512 "$file" | grep -qi '<html\|<!doctype' && fail "$name looks like an HTML page"
  head -n 5 "$file" | grep -q '^\[Adblock\|^!' || fail "$name does not look like a filter list"
  local old="$site/filters/$name"
  if [ -f "$old" ] && [ "${FORCE:-0}" != 1 ]; then
    local new_size old_size
    new_size=$(stat -c %s "$file"); old_size=$(stat -c %s "$old")
    [ $((new_size * 2)) -ge "$old_size" ] ||
      fail "$name shrank from $old_size to $new_size bytes; rerun with FORCE=1 if that is expected"
  fi
}

{
  echo "# Unmodified copies of the filter lists below, retrieved $(date -u +%Y-%m-%dT%H:%MZ)."
  echo "# Each list keeps its own header with its title, homepage and license."
} > "$tmp/filters/SOURCES.txt"

while read -r name url; do
  case $name in ''|'#'*) continue ;; esac
  [ -n "$url" ] || fail "no URL for $name in $SOURCES"
  echo "downloading $name"
  curl -fsSL --proto '=https,file' --max-time 300 --retry 2 -o "$tmp/filters/$name" "$url" ||
    fail "download failed: $url"
  check_list "$tmp/filters/$name" "$name"
  printf '%s %s\n' "$name" "$url" >> "$tmp/filters/SOURCES.txt"
done < "$SOURCES"

cp "$REPO/tools/filters/experimental-cromite-filters.txt" "$tmp/filters/"
check_list "$tmp/filters/experimental-cromite-filters.txt" experimental-cromite-filters.txt

# The component manifest names the CRX by SHA-256 and size; both must match the file.
zip="$REPO/build/components/fonts_component.zip"
manifest="$REPO/build/components/query4_0.json"
sha=$(sha256sum "$zip" | cut -d' ' -f1)
size=$(stat -c %s "$zip")
grep -qi "\"sha256\": \"$sha\"" "$manifest" || fail "fonts_component.zip does not match the sha256 in query4_0.json"
grep -q "\"size\": $size\b" "$manifest" || fail "fonts_component.zip does not match the size in query4_0.json"
cp "$zip" "$tmp/components/"
# Escape the characters that are special in a sed replacement.
fonts_url_escaped=$(printf '%s' "$FONTS_URL" | sed -e 's/[&#\\]/\\&/g')
sed -E "s#\"url\": \"[^\"]*fonts_component\.zip\"#\"url\": \"$fonts_url_escaped\"#" "$manifest" > "$tmp/components/query4_0.json"
grep -qF "\"url\": \"$FONTS_URL\"" "$tmp/components/query4_0.json" || fail "could not set the fonts URL in query4_0.json"

# GitHub Pages would otherwise run the files through Jekyll.
: > "$tmp/.nojekyll"

rsync -a --checksum --delete --exclude .git --exclude CNAME "$tmp/" "$site/"

echo
echo "updated $site ($(du -sh --exclude .git "$site" | cut -f1))"
if git -C "$site" rev-parse --git-dir > /dev/null 2>&1; then
  git -C "$site" status --short
  echo "review, then: git -C $site add -A && git -C $site commit -m 'Update filter lists' && git -C $site push"
fi
