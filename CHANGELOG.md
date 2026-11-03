# Changelog

## Unreleased

- macOS support: platform-aware data/download folders, fonts, mouse-wheel scrolling, Open folder, bundled-tool lookup and cloudflared helper.
- `Sonika-mac.spec` and a GitHub Actions workflow that builds `Sonika.app` as a DMG for Apple Silicon and Intel.

## v1.0.0 - 2026-10-31

First public source release, based on the internal 3.1 desktop build.

- Windows desktop interface with the Sonika red and black theme and application icon.
- YouTube, Instagram and Pinterest URL validation and download jobs.
- Highest available source quality and optional resolution limits.
- Audio extraction to MP3, M4A or the original audio format.
- Batch link entry, text-file import and YouTube playlist expansion with position ranges.
- Durable queue with 1-4 concurrent jobs, delays, pause, cancel and retry controls.
- Local stdio MCP tools and explicitly enabled temporary HTTPS MCP connections.
- Source-only packaging, portable build scripts, pinned dependencies and third-party notices.

### Known limitations

- LinkedIn downloads are not supported.
- Website login requirements and rate limits can prevent otherwise public downloads.
- Installer is unsigned. There is no built-in hosted browser application.
- Public binary publication is pending corresponding-source arrangements for the GPL FFmpeg build and review of the release test results.
