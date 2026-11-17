# Static files

The browser downloads its filter lists and its fonts pack from https://hawkff.github.io/cromite/. GitHub Pages publishes that site from the `pages` branch of this repository.

## Contents

- `filters/`: unmodified copies of the filter lists named in `sources.txt`, plus `experimental-cromite-filters.txt` from `tools/filters/`. `filters/SOURCES.txt` gives the origin URL of each list and the retrieval time.
- `components/query4_0.json`: the component manifest. Its `url` field points at the fonts pack below.
- `components/fonts_component.zip`: the fonts pack, a copy of `build/components/fonts_component.zip`.
- `.nojekyll`: an empty file that stops GitHub Pages from running Jekyll.

## Refresh by hand

```
git worktree add ../cromite-pages pages
tools/static-files/refresh.sh ../cromite-pages
git -C ../cromite-pages diff --stat
git -C ../cromite-pages add -A
git -C ../cromite-pages commit -m 'Update filter lists'
git -C ../cromite-pages push origin pages
```

`refresh.sh` downloads every list in `sources.txt` from its publisher and copies the experimental list and the fonts pack from this checkout. It writes the component manifest with the fonts download address set to `<BASE>components/fonts_component.zip`. Only after every check passes does it replace the contents of the site directory. It never commits or pushes.

Environment variables:
- `BASE`: the site address, default `https://hawkff.github.io/cromite/`.
- `FONTS_URL`: the fonts download address written into the manifest.
- `SOURCES`: the list file, default `sources.txt` in this directory.
- `REPO`: the repository checkout, default the one this directory belongs to.
- `FORCE=1`: accept a list that shrank to less than half of its published size.

`test-refresh.sh` runs `refresh.sh` offline against `file://` copies.

## What the checks refuse

The script stops and leaves the site directory unchanged when:
- a download fails or returns an empty file;
- a list starts like an HTML page, or none of its first five lines starts with `[Adblock` or `!`;
- a list is less than half the size of the published copy, unless `FORCE=1` is set;
- the SHA-256 or the size of `fonts_component.zip` differs from the values in `build/components/query4_0.json`;
- it cannot set the fonts download address in the manifest.

The browser accepts any file served with status 200 as a filter list, so an error page published by mistake would replace a list until the next good download.
