# Dependencies and bundled tool provenance

## Python dependency inventory

Exact release pins, including build and test dependencies, are in requirements-lock.txt. Python 3.14.6 provides the standard library and Tkinter; Tcl/Tk patch versions are recorded below. No external AI API is required.

| Distribution | Version | Declared license |
| --- | --- | --- |
| altgraph | 0.17.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| attrs | 26.1.0 | MIT |
| brotli | 1.2.1 | MIT |
| certifi | 2026.10.23 | MPL-2.0 |
| cffi | 2.1.1 | MIT-0 |
| charset-normalizer | 3.5.2 | MIT |
| click | 8.5.0 | BSD-3-Clause |
| colorama | 0.4.6 | See installed distribution notices |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| dnspython | 2.9.0 | ISC |
| h11 | 0.16.0 | MIT |
| httpcore | 1.0.9 | BSD-3-Clause |
| httpx | 0.28.1 | BSD-3-Clause |
| httpx-sse | 0.4.3 | MIT |
| idna | 3.20 | BSD-3-Clause |
| iniconfig | 2.3.1 | MIT |
| jsonschema | 4.26.0 | MIT |
| jsonschema-specifications | 2025.9.1 | MIT |
| mcp | 1.30.0 | MIT |
| mutagen | 1.48.1 | GPL-2.0-or-later |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pefile | 2024.8.26 | MIT |
| pillow | 13.0.0 | MIT-CMU |
| pluggy | 1.7.0 | MIT |
| pycparser | 3.12 | BSD-3-Clause |
| pycryptodomex | 3.24.1 | BSD, Public Domain |
| pydantic | 2.14.1 | MIT |
| pydantic-settings | 2.16.1 | MIT |
| pydantic_core | 2.50.1 | MIT |
| Pygments | 2.21.0 | BSD-2-Clause |
| pyinstaller | 6.22.3 | GPLv2-or-later with a special exception which allows to use PyInstaller to build and distribute non-free progr |
| pyinstaller-hooks-contrib | 2026.9 | See installed distribution notices |
| PyJWT | 2.15.1 | MIT |
| pytest | 9.1.1 | MIT |
| python-dotenv | 1.2.4 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| pywin32 | 312 | PSF |
| pywin32-ctypes | 0.2.3 | BSD-3-Clause |
| referencing | 0.37.0 | MIT |
| requests | 2.34.2 | Apache-2.0 |
| rpds-py | 2026.9.1 | MIT |
| setuptools | 84.2.1 | MIT |
| sse-starlette | 3.6.0 | BSD-3-Clause |
| starlette | 1.10.0 | BSD-3-Clause |
| typing-inspection | 0.4.4 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| urllib3 | 2.8.0 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause |
| websockets | 17.3 | BSD-3-Clause |
| yt-dlp | 2026.10.26 | Unlicense |
| yt-dlp-ejs | 0.8.0 | Unlicense AND MIT AND ISC |

Tcl patch level: 8.6.15. Tk patch level: 8.6.15 (confirmed from the distributed tk.tcl). Tk is distributed with the same CPython Windows runtime. The installer includes the runtime provided by that CPython installation.

Installer toolchain: Inno Setup 7.1.0; PyInstaller version and related hooks are listed above. pip 26.1.2 was present in the external build environment; pip is not shipped as an application dependency.

## Obtaining bundled executables

- Python: official Windows x64 CPython 3.14.6 installer from https://www.python.org/downloads/ . Include Tkinter.
- FFmpeg and FFprobe: Gyan 9.0.2 full build, currently installed through WinGet package Gyan.FFmpeg. Build-provider URL: https://www.gyan.dev/ffmpeg/builds/ . Exact executable hashes are pinned in vendor/tools-manifest.json; provider landing pages may later change. Arrange matching corresponding source for this GPL build before public distribution.
- Node.js: official Node.js 24.19.0 Windows x64 distribution at https://nodejs.org/dist/v24.19.0/ . Verify SHASUMS256.txt from that release before installation; the exact bundled node.exe hash is also in the manifest.
- cloudflared: official 2026.10.5 Windows amd64 release. packaging/fetch_cloudflared.py downloads the pinned URL and verifies the upstream release SHA-256 stored in vendor/cloudflared-release.json before writing it. Store it outside the source tree and set SONIKA_CLOUDFLARED.
- Inno Setup: official compiler from https://jrsoftware.org/isdl.php . The release uses 7.1.0. This is an external build prerequisite; the compiler is not committed.

The build validates exact executable hashes and Python package pins. All runtimes and helpers are staged into the installer; none of their binaries are tracked in this repository. Build directories and QA profiles remain outside the source tree. Bundled licenses and upstream URLs are collected during staging; network access is needed for official Node/cloudflared notices.

## Redistribution review

The Gyan FFmpeg binary enables GPL v3 and statically links many libraries. An upstream FFmpeg-only source link is not enough to document the complete matching build. Resolve corresponding-source delivery before publishing a binary release. See THIRD_PARTY_NOTICES.md.
