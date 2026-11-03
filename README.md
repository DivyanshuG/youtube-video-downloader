# YouTube Video Downloader

A Windows and macOS desktop app for YouTube, Instagram and Pinterest video, audio, batch and playlist downloads, with optional MCP tools.

**Only download videos you own or have permission to use**

## Screenshots

<!-- Screenshot placeholder: main downloader window, with an empty history and no personal paths. -->
<!-- Screenshot placeholder: batch and playlist dialog, with no private links. -->

Screenshots will be added before publication. Do not upload screenshots containing personal download history, cookies or connection links.

## Install from GitHub Releases

1. Open this repository's **Releases** page (right sidebar), then select **v1.0.0** once published.
2. Download `Sonika-Downloader-Setup-1.0.0-x64.exe` and `SHA256.txt`. Do not download the source ZIP if you only want to use the app.
3. In PowerShell, run `Get-FileHash .\Sonika-Downloader-Setup-1.0.0-x64.exe -Algorithm SHA256` and compare the result with `SHA256.txt`.
4. Run the installer. This app is not code-signed, so Windows SmartScreen may show a warning. After verifying the trusted release and checksum, use **More info > Run anyway** if that option is available. Managed PCs may prohibit this; contact your administrator.
5. Choose the install folder, optionally create a desktop shortcut, and launch Sonika from Start.

Requires Windows 10 build 19041 or later / Windows 11 on an Intel or AMD x64 PC. The installer includes its runtimes. No Python or editor installation is needed for end users. This repository preparation does not itself publish a GitHub Release.

## Install on a Mac

1. Open this repository's **Releases** page and download the `.dmg` that matches your Mac: `arm64` for Apple Silicon (M1 or newer) or `x86_64` for Intel. Check under Apple menu > About This Mac > Chip.
2. Open the DMG and drag **YouTube Video Downloader** into **Applications**.
3. The app is not signed by Apple, so the first launch is blocked. Open the app once, then go to System Settings > Privacy & Security, scroll down and click **Open Anyway**. (Terminal alternative: `xattr -dr com.apple.quarantine /Applications/YouTube\ Video\ Downloader.app`.)

Requires macOS 11 or later. FFmpeg, FFprobe, Node and the connection helper are bundled when the release is built; if a tool is missing, the app tells you and falls back to a Homebrew copy (`brew install ffmpeg node`). Downloads default to `Movies/Sonica`; history is kept in `~/Library/Application Support/VideoDesk`.

Release builds come from `.github/workflows/build-mac.yml`: push a tag such as `v1.0.1`, or run the workflow by hand from the Actions tab. To run from source on a Mac instead: `brew install python-tk ffmpeg node`, create a virtual environment, `pip install -r requirements.txt`, then `python app.py`. The macOS build bundles a GPL FFmpeg build, so the same corresponding-source review as for Windows applies before public distribution.

## Use

Paste a supported HTTPS link, choose Video or Audio only, select quality or MP3/M4A/original audio, and choose a save folder. Best available uses the source's highest available quality without upscaling. Separate video/audio streams may be merged into MKV.

Use **Batch / Playlist** for multiple links, a text file of links, or a YouTube playlist. Set 1-4 simultaneous jobs and a delay; additional jobs remain queued. Pause queue stops new starts while active jobs finish. Retry selected preserves completed items.

## Build from source

Use Windows x64, Python 3.14.6 (with Tkinter), FFmpeg/FFprobe 9.0.2, Node.js 24.19.0 and Inno Setup 7.1.0. Exact Python dependency pins are in `requirements-lock.txt`; provenance and hashes for the release tools are in `vendor/tools-manifest.json`.

```powershell
# Run in the cloned source directory. Keep all generated files outside it.
py -3.14 -m venv ..\release\build-env
..\release\build-env\Scripts\python.exe -m pip install -r requirements-lock.txt
..\release\build-env\Scripts\python.exe packaging\fetch_cloudflared.py --output ..\release\tools\cloudflared.exe
$env:SONIKA_CLOUDFLARED = (Resolve-Path ..\release\tools\cloudflared.exe).Path
$env:PYTHONPYCACHEPREFIX = [IO.Path]::GetFullPath('..\release\pycache')
..\release\build-env\Scripts\python.exe -m pytest -q -p no:cacheprovider
..\release\build-env\Scripts\python.exe app.py
```

Put the documented FFmpeg, FFprobe and Node executables on PATH. Install Inno Setup from its official vendor, then build:

```powershell
..\release\build-env\Scripts\python.exe packaging\build_release.py --output ..\release --iscc 'PATH_TO_INNO_SETUP\ISCC.exe'
```

The builder validates tool hashes against the manifest, uses a new external work directory, stages third-party notices, creates the installer and writes `../release/SHA256.txt`. It refuses an output directory inside the repository and never publishes anything. To use different tool versions, update the manifest and dependency documentation after validating provenance.

## MCP

For a local stdio MCP client, set the command to your virtual environment's Python executable and its argument to the absolute path of `mcp_server.py`. Put machine-specific client settings in your client's configuration or an ignored `*.local.json` file.

**Connect AI / MCP** optionally starts a local server and a temporary Cloudflare Tunnel. Set `SONIKA_CLOUDFLARED` when running from source. Keep the full connection link private: it grants download control for that sharing session. Stop sharing or close the app to revoke it. Keep the PC on; downloads are saved on the PC, not in a hosted web app. No AI API key is required. Client/account connector support varies.

## FAQ

**Why does YouTube ask me to sign in, or stop many downloads?** Sites can require login, rate-limit downloads or block automation. Use a delay, retry later, or explicitly select your own cookie file when permitted. Sonika does not bypass access controls and does not read browser logins automatically. Never commit cookie exports.

**Does it support LinkedIn?** No. The current URL allowlist supports YouTube, Instagram and Pinterest. LinkedIn links are rejected; adding support would be a separate change.

**Can I deploy this directly to Cloudflare Pages?** No. This is a Tkinter desktop app. A hosted product needs a browser interface, backend, authentication and durable cloud storage.

**Why does a resolution limit say the format is unavailable?** The source may not offer a rendition below that ceiling. Choose Best available; the app selects source formats and does not transcode video to create a missing lower resolution.

**Where is history stored?** In your local application data folder under `VideoDesk`; that internal legacy name preserves existing user data. Downloads default to your Videos folder under `Sonica`. Neither is part of this repository. Uninstalling leaves your history and media in place.

**Why version 1.0.0 after internal 3.1 builds?** Version 1.0.0 is the first public source release; internal development builds used 3.x numbering. Do not assume a 1.0.0 installer is an automatic upgrade over an internal build.

## License and included tools

Application source is MIT, copyright 2026 Mehul Soni. Third-party tools retain their own licenses; the MIT grant does not relicense FFmpeg or other dependencies. See `THIRD_PARTY_NOTICES.md` and `DEPENDENCIES.md`. Review the FFmpeg corresponding-source requirement before distributing the installer publicly.
