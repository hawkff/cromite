# Cromite AdBlock engine

## Modified version of Adblock plus integrated in cromite

Cromite uses a modified version of adblock plus.

Some adblock plus rules cannot be used:
- removed support for header and csp filter option
- removed support for json-override, simulate-event-poc, simulate-mouse-event snippets
- allowed the use of override-property-read by eliminating the possibility of specifying a number as an argument (except 0 and 1)
- removed support for sitekey

Some improvements have been included:
- Added dns CNAME support
- Block of WebSockets and WebTransport urls
- Block of service workers fetchs

All default filters are downloaded from https://hawkff.github.io/cromite/filters/. The lists there are unmodified copies of the publishers' lists, and [SOURCES.txt](https://hawkff.github.io/cromite/filters/SOURCES.txt) names the origin of each one. The Cromite experimental filters are [tools/filters/experimental-cromite-filters.txt](../tools/filters/experimental-cromite-filters.txt) from this repository. You can enter your lists via the settings: http url redirection is prohibited.

### Update mechanism

The Cromite AdBlock Update Service downloads the filters after the first start and checks for updates about every 12 hours. It downloads a list again when the list's own expiry time has passed, which each list sets between one hour and 14 days. The requests carry no cookies. Turning off "Enable Adblock Plus" in the settings stops them.

GitHub Pages serves the default filters, so GitHub receives the requesting IP address and the request headers, including the user agent. The project gets no access logs. See the [GitHub Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement).

## Legacy bromite adblock engine

Since v77 Bromite uses [Chromium subresource filter](https://github.com/chromium/chromium/tree/master/components/subresource_filter).

This engine does not currently support CSS rules; as a result some sites will show ads.

In cromite it is disabled by default.

### Update mechanism

The Bromite AdBlock Update Service checks at startup (after 5 seconds) and periodically (every week) if new filters are published.

### Original Bromite AdBlock engine
The ad-blocking engine of Bromite till v76 was an improved version of the original engine of [NoChromo](https://forum.xda-developers.com/android/apps-games/app-nochromo-w)

