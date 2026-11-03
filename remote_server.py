"""Restricted MCP endpoint. Knowledge of its random URL grants session access."""
import os
from pathlib import Path
import re
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from core import start_download, start_batch, start_playlist, get_job, read_job, cancel_download, retry_download, DOWNLOADS

def create_server(token, port):
    if not re.fullmatch(r'[A-Za-z0-9_-]{40,100}', token):
        raise ValueError('A strong connection token is required')
    mcp = FastMCP('YouTube Video Downloader', host='127.0.0.1', port=port,
                  streamable_http_path=f'/{token}/mcp', stateless_http=True, json_response=True,
                  transport_security=TransportSecuritySettings(allowed_hosts=[f'127.0.0.1:{port}'], allowed_origins=[]))
    session_jobs = set()
    def owned(job_id):
        if job_id in session_jobs:return True
        try:
            if read_job(job_id).get('batch_id') in session_jobs:
                session_jobs.add(job_id);return True
        except (OSError,ValueError):pass
        return False
    def result(job):
        return {k: job[k] for k in ('id', 'title', 'status', 'progress', 'media_type', 'audio_format', 'message','job_ids','items_done','items_failed','items_total') if k in job} | {
            'files': [Path(f).name for f in job.get('files', [])]}
    def launch(url, media_type, quality='Best available', audio_format='MP3'):
        job = start_download(url, quality=quality, folder=str(DOWNLOADS), media_type=media_type, audio_format=audio_format)
        session_jobs.add(job['id'])
        return result(job)
    @mcp.tool()
    def download_video(url: str, quality: str = 'Best available') -> dict:
        """Queue a YouTube, Instagram or Pinterest video to the user's PC. Returns a job ID.
        Quality: Best available, 2160p, 1080p or 720p. Poll download_status for completion.
        """
        return launch(url, 'video', quality)
    @mcp.tool()
    def download_audio(url: str, audio_format: str = 'MP3') -> dict:
        """Save only the audio of a video to the PC. Format: MP3, M4A or Original audio."""
        return launch(url, 'audio', audio_format=audio_format)
    @mcp.tool()
    def download_batch(urls: list[str], media_type: str = 'video', quality: str = 'Best available', audio_format: str = 'MP3') -> dict:
        """Queue many YouTube, Instagram or Pinterest links. No total-video cap;
        simultaneous transfers are controlled by the user's persistent queue.
        """
        batch=start_batch(urls,quality,str(DOWNLOADS),None,media_type,audio_format)
        session_jobs.update(batch['job_ids']);session_jobs.add(batch['batch_id'])
        return batch
    @mcp.tool()
    def download_playlist(url: str, media_type: str = 'video', quality: str = 'Best available', audio_format: str = 'MP3', playlist_items: str | None = None) -> dict:
        """Queue a complete YouTube playlist, or select positions such as 1-20. Poll its ID for overall progress."""
        job=start_playlist(url,quality,str(DOWNLOADS),None,media_type,audio_format,playlist_items)
        session_jobs.add(job['id']);return result(job)
    @mcp.tool()
    def retry_queued_download(job_id: str) -> dict:
        """Retry unfinished items of a download/batch created through this connection."""
        if not owned(job_id):raise ValueError('Job is not part of this connection')
        return result(retry_download(job_id))
    @mcp.tool()
    def download_status(job_id: str) -> dict:
        """Check a download started through this connection. Files remain on the user's PC."""
        if not owned(job_id): raise ValueError('Job is not part of this connection')
        return result(get_job(job_id))
    @mcp.tool()
    def download_history() -> list[dict]:
        """List downloads started through this temporary connection."""
        return [result(get_job(j)) for j in session_jobs]
    @mcp.tool()
    def cancel_video_download(job_id: str) -> dict:
        """Cancel a download started through this connection."""
        if not owned(job_id): raise ValueError('Job is not part of this connection')
        return cancel_download(job_id)
    return mcp

def run():
    token = os.environ['SONICA_BRIDGE_TOKEN']
    port = int(os.environ['SONICA_BRIDGE_PORT'])
    server = create_server(token, port)
    uvicorn.run(server.streamable_http_app(), host='127.0.0.1', port=port, access_log=False, log_level='warning')

if __name__ == '__main__': run()
