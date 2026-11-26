# Static files

The browser downloads its fonts pack and two filter lists from https://hawkff.github.io/cromite/. GitHub Pages publishes that site from the `pages` branch of this repository.

The two lists that may run snippets, `abp-filters-anti-cv.txt` ("ABP filters") and `experimental-cromite-filters.txt` ("Cromite experimental filters"), are always downloaded from this site, so a change to them reaches users only after it was published here. Every other list is downloaded from its publisher; the copies on this site are only a fallback for a first download that cannot reach the publisher.

## Contents

- `filters/`: unmodified copies of the filter lists named in `sources.txt` (live for the anti-circumvention list, fallbacks for the others), plus `experimental-cromite-filters.txt` from `tools/filters/`. `filters/SOURCES.txt` gives the origin URL of each list and the retrieval time.
- `components/query4_0.json`: the component manifest. Its `url` field points at the fonts pack below.
- `components/fonts_component.zip`: the fonts pack, a copy of `build/components/fonts_component.zip`.
- `.nojekyll`: an empty file that stops GitHub Pages from running Jekyll.

## Refresh by hand

Refresh every two weeks, before each release build, and on the same day when sites report ad-block walls or pages broken in a way the anti-circumvention list covers. Run it on Linux: `refresh.sh` uses GNU `stat` and `sha256sum`.

The experimental list is copied from `tools/filters/` in this checkout, never from upstream. When upstream's `tools/filters/experimental-cromite-filters.txt` has changed, check it as in step 2 and update the copy in `tools/filters/` through a pull request first.

1. Fetch into a `pages` worktree:
   ```
   git worktree add ../cromite-pages pages
   tools/static-files/refresh.sh ../cromite-pages
   ```
2. Check both lists that may run snippets against the published copies:
   ```
   git -C ../cromite-pages show HEAD:filters/abp-filters-anti-cv.txt > /tmp/anti-cv.old
   python3 tools/static-files/snippet_review.py /tmp/anti-cv.old ../cromite-pages/filters/abp-filters-anti-cv.txt
   git -C ../cromite-pages show HEAD:filters/experimental-cromite-filters.txt > /tmp/exp.old
   python3 tools/static-files/snippet_review.py /tmp/exp.old ../cromite-pages/filters/experimental-cromite-filters.txt
   ```
   `snippet_review.py` parses each rule the way the browser does. It prints the counts of added and removed snippet rules, every added rule the browser rejects or drops (with the reason), how many added rules run, every added `$header=` rule, and the domains that get running snippets for the first time. Then it prints in full, under their own headings, every removed snippet rule (with what it did in the published copy) and every added rule that runs (with its domains and snippet names). If it exits with status 1 (a self-check failed, or the new copy adds a header filter), stop and do not publish.
3. Read every added snippet rule, including those reported as dropped: `git -C ../cromite-pages diff -- filters/abp-filters-anti-cv.txt filters/experimental-cromite-filters.txt`. Accept only rules limited to named domains whose purpose is clear from the domain and the arguments, such as ad-block walls, video ads and consent overlays. Look harder at `cookie-remover`, `abort-*` and `override-property-read` on login, bank, mail or payment domains, because those can break sites or remove session state.
4. Look over the other lists and publish:
   ```
   git -C ../cromite-pages diff --stat
   git -C ../cromite-pages add -A
   git -C ../cromite-pages commit -m 'Update filter lists'
   git -C ../cromite-pages push origin pages
   git worktree remove ../cromite-pages
   ```

The lists are not refreshed on a schedule: a scheduled job would publish snippet rules that nobody has read.

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
