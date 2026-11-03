from mcp.server.fastmcp import FastMCP
from core import start_download, start_batch, start_playlist, inspect_video, get_job, list_jobs, cancel_download, retry_download as retry_job, queue_settings, configure_queue

mcp = FastMCP('YouTube Video Downloader')

@mcp.tool()
def video_info(url: str, cookie_file: str | None = None) -> dict:
    """Inspect a YouTube, Instagram or Pinterest video and its source resolutions."""
    return inspect_video(url, cookie_file)

@mcp.tool()
def download_video(url: str, quality: str = 'Best available', folder: str | None = None,
                   cookie_file: str | None = None) -> dict:
    """Start a local video download. Quality: Best available, 2160p, 1080p, or 720p.
    Returns a job ID immediately; use download_status to check progress.
    Only download content the user is entitled to save. Cookies are optional local Netscape files.
    """
    return start_download(url, quality, folder, cookie_file)

@mcp.tool()
def download_status(job_id: str) -> dict:
    """Read progress, errors and output paths for a local download."""
    return get_job(job_id)

@mcp.tool()
def download_audio(url: str, audio_format: str = 'MP3', folder: str | None = None,
                   cookie_file: str | None = None) -> dict:
    """Download only audio. Format: MP3, M4A or Original audio. Returns a job ID."""
    return start_download(url, folder=folder, cookie_file=cookie_file, media_type='audio', audio_format=audio_format)

@mcp.tool()
def download_history() -> list[dict]:
    """List local downloads, newest first."""
    return list_jobs()

@mcp.tool()
def download_batch(urls: list[str], media_type: str = 'video', quality: str = 'Best available', audio_format: str = 'MP3', folder: str | None = None, cookie_file: str | None = None) -> dict:
    """Queue many YouTube, Instagram and Pinterest video links in one request.
    No total-video cap. A persistent queue limits simultaneous transfers; excess
    jobs wait instead of being rejected. media_type is video or audio.
    """
    return start_batch(urls,quality,folder,cookie_file,media_type,audio_format)

@mcp.tool()
def download_playlist(url: str, media_type: str = 'video', quality: str = 'Best available', audio_format: str = 'MP3', playlist_items: str | None = None, folder: str | None = None, cookie_file: str | None = None) -> dict:
    """Queue a full YouTube playlist. Optional playlist_items selects 1-20 or 1-10,15.
    Each video gets its own status; unavailable videos do not discard completed ones.
    """
    return start_playlist(url,quality,folder,cookie_file,media_type,audio_format,playlist_items)

@mcp.tool()
def retry_download(job_id: str, cookie_file: str | None = None) -> dict:
    """Retry a failed/blocked download or the unfinished items of a batch/playlist."""
    return retry_job(job_id,cookie_file)

@mcp.tool()
def download_queue(paused: bool | None = None) -> dict:
    """Read queue settings, or pause/resume starting new downloads. Active transfers finish."""
    return configure_queue(paused=paused) if paused is not None else queue_settings()

@mcp.tool()
def cancel_video_download(job_id: str) -> dict:
    """Request cancellation of a download."""
    return cancel_download(job_id)

if __name__ == '__main__':
    mcp.run(transport='stdio')
