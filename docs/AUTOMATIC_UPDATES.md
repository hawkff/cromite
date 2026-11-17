Cromite update notifications are disabled by default.

## How to enable or disable
You can enable or disable update notifications with "Allow checking for updates" in Settings -> About Cromite. The first-run screen offers the same setting.

When this setting is enabled, Cromite checks the [releases of this repository](https://github.com/hawkff/cromite/releases) at most once a day. It sends one HEAD request for the latest release file and reads the version from the redirect. The request follows the browser's proxy settings. When a newer version exists, the menu offers the update, and Cromite downloads it only when you tap it. No release has been published yet.

No cookies are used when interacting with the releases page, please refer to the [GitHub Privacy Statement](https://docs.github.com/en/github/site-policy/github-privacy-statement)
