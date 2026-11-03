# Third party notices

The application source is licensed under MIT by Mehul Soni. Bundled components and dependencies retain their own copyright and licenses. They are not covered by the application's MIT grant.

| Component | Release version | License and source |
| --- | --- | --- |
| CPython and Tkinter runtime | 3.14.6 | PSF license plus bundled Tcl/Tk and other notices; https://www.python.org/downloads/ and https://github.com/python/cpython |
| yt-dlp | 2026.10.26 | Unlicense for the upstream project; included dependencies have separate terms; https://github.com/yt-dlp/yt-dlp |
| yt-dlp-ejs | 0.8.0 | License text collected from installed distribution; https://github.com/yt-dlp/ejs |
| MCP Python SDK | 1.30.0 | MIT; https://github.com/modelcontextprotocol/python-sdk |
| Pillow | 13.0.0 | HPND and included third-party notices; https://python-pillow.org/ |
| dnspython | 2.9.0 | ISC; https://www.dnspython.org/ |
| FFmpeg and FFprobe Gyan full build | 9.0.2 | GPL v3-enabled build with additional library notices; https://www.gyan.dev/ffmpeg/builds/ and https://ffmpeg.org/legal.html |
| Node.js | 24.19.0 | MIT with bundled third-party notices; https://nodejs.org/en/about/previous-releases |
| cloudflared | 2026.10.5 | Apache-2.0 with upstream notices; https://github.com/cloudflare/cloudflared |
| PyInstaller build tool and bootloader | 6.22.3 | GPL with a bootloader exception; https://pyinstaller.org/en/stable/license.html |
| Inno Setup compiler and installer runtime | 7.1.0 | Inno Setup license; https://jrsoftware.org/isinfo.php |

All Python package names, versions and declared licenses are enumerated in `DEPENDENCIES.md`. The installer includes a `licenses` directory containing collected distribution license/notice files, the Python license, Node license, cloudflared license and the FFmpeg build license and configuration. Consult those component texts; package metadata alone is not a legal grant.

## FFmpeg distribution status

This release candidate invokes FFmpeg and FFprobe as separate executables. The selected Gyan binary was configured with `--enable-gpl --enable-version3` and numerous third-party libraries. It must not be described as MIT or LGPL-only.

Upstream FFmpeg revision reported by the build provider: `946fcce07b`. Reference source: https://github.com/FFmpeg/FFmpeg/tree/946fcce07b . This link by itself is not a complete corresponding-source distribution for the entire statically linked Gyan build and all its libraries. Before public binary distribution, arrange a compliant matching source/build-material distribution or replace the binaries with an appropriately documented build and re-test. No written source offer is made on behalf of the author by this notice.

Keep the provided notices in any redistributed installer. The application does not claim ownership of FFmpeg, Node.js, yt-dlp, Cloudflare, YouTube, Instagram, Pinterest or any media downloaded by users.
