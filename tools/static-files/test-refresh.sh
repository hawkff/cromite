#!/usr/bin/env bash
# Offline test of refresh.sh with file:// sources and a fake repository.
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT

mkdir -p "$t/repo/tools/filters" "$t/repo/build/components" "$t/pub" "$t/site"
printf '! Title: exp\nexample.com##.ad\n' > "$t/repo/tools/filters/experimental-cromite-filters.txt"
head -c 4096 /dev/urandom > "$t/repo/build/components/fonts_component.zip"
sha=$(sha256sum "$t/repo/build/components/fonts_component.zip" | cut -d' ' -f1)
cat > "$t/repo/build/components/query4_0.json" <<EOF
)]}' {"urls": [ { "url": "https://hawkff.github.io/cromite/components/fonts_component.zip" } ],
"out": { "sha256": "${sha^^}" }, "size": 4096 }
EOF
printf '[Adblock Plus 2.0]\n! Title: A\n%s\n' "$(seq 1 200 | sed 's/^/||ads&.example^/')" > "$t/pub/a.txt"
printf '! Title: B\n||b.example^\n' > "$t/pub/b.txt"
printf 'a.txt file://%s/pub/a.txt\n# comment\n\nb.txt file://%s/pub/b.txt\n' "$t" "$t" > "$t/sources.txt"

run() { REPO="$t/repo" SOURCES="$t/sources.txt" BASE=https://example.org/x/ "$here/refresh.sh" "$t/site" > "$t/log" 2>&1; }

run || { cat "$t/log"; echo "FAIL: first run"; exit 1; }
for f in filters/a.txt filters/b.txt filters/experimental-cromite-filters.txt filters/SOURCES.txt \
         components/fonts_component.zip components/query4_0.json .nojekyll; do
  [ -f "$t/site/$f" ] || { echo "FAIL: missing $f"; exit 1; }
done
grep -q '"url": "https://example.org/x/components/fonts_component.zip"' "$t/site/components/query4_0.json" ||
  { echo "FAIL: manifest URL"; exit 1; }

# An HTML error page must abort and leave the site untouched.
printf '<!DOCTYPE html><html>rate limited</html>\n' > "$t/pub/b.txt"
if run; then echo "FAIL: HTML accepted"; exit 1; fi
grep -q '^||b.example^' "$t/site/filters/b.txt" || { echo "FAIL: site changed after error"; exit 1; }

# A list that shrank to less than half must abort unless FORCE=1.
printf '! Title: B\n||b.example^\n' > "$t/pub/b.txt"
printf '[Adblock Plus 2.0]\n||one.example^\n' > "$t/pub/a.txt"
if run; then echo "FAIL: shrink accepted"; exit 1; fi
FORCE=1 run || { cat "$t/log"; echo "FAIL: FORCE=1"; exit 1; }

echo "PASS"
