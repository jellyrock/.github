# Security policy

This policy covers every repository in the JellyRock organization: the JellyRock Roku app, the JellyRock Companion server plugin and the websites (jellyrock.app, docs.jellyrock.app and dev.jellyrock.app).

## Supported versions

JellyRock projects are rolling releases. Only the newest release gets fixes, so update before you report an issue.

| Project | Supported |
| --- | --- |
| JellyRock app | The latest release in the Roku Channel Store, or the newest `main` build |
| JellyRock Companion plugin | The latest [release](https://github.com/jellyrock/jellyfin-plugin-jellyrock/releases) |
| Websites | What is live now |
| Anything older | ❌ Update first |

The plugin's [README](https://github.com/jellyrock/jellyfin-plugin-jellyrock#readme) lists the Jellyfin server versions it runs on. If your server is too old for the latest plugin release, the older release you have doesn't get fixes.

## Reporting a vulnerability

**Don't report a security vulnerability in a public GitHub issue, a discussion or the Matrix chat.**

Report it privately through GitHub:

1. Go to the **Security** tab of the repository the issue is in. If you're not sure which one, use [JellyRock's](https://github.com/jellyrock/jellyrock/security/advisories/new).
2. Select **Report a vulnerability** (GitHub's private vulnerability reporting).
3. Describe the issue, the affected version and the steps to reproduce it.

The maintainer replies as soon as they can. Allow a reasonable time to investigate and ship a fix before you disclose it publicly.

## Scope

JellyRock connects to a Jellyfin server you control. The most useful reports cover how the app and the plugin handle server credentials and tokens, any data they send off your device or server, and anything that could expose another user's session on a shared Roku or server. Report issues in the Jellyfin server itself to the Jellyfin project, not here.
