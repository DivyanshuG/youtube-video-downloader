import sys
import time
import os
import re
import yt_dlp
from urllib.parse import urlsplit
from core import read_job, job_path, options, save, new_job, raw_jobs, cancel_download, media_identity

class PlatformBlocked(RuntimeError):pass

def platform(url):
    host=urlsplit(url).hostname or ''
    return 'youtube' if 'youtu' in host else 'instagram' if 'instagram' in host else 'pinterest'

def is_blocked(message):
    return bool(re.search(r'not a bot|too many requests|HTTP Error 429|rate.?limit|login required|log in to|sign in to confirm',str(message),re.I))

class Logger:
    def debug(self,message):pass
    def warning(self,message):pass
    def error(self,message):
        if is_blocked(message):raise PlatformBlocked(message)

def expand_playlist(job,check):
    job.update(status='expanding',message='Loading playlist videos…',job_ids=[],expansion_complete=False);save(job)
    opts=options(job['quality'],job['folder'],job.get('cookie_file'))
    opts.update(extract_flat='in_playlist',skip_download=True,noplaylist=False,ignoreerrors=True,lazy_playlist=True,
                logger=Logger(),sleep_interval_requests=1)
    if job.get('playlist_items'):opts['playlist_items']=job['playlist_items']
    with yt_dlp.YoutubeDL(opts) as ydl:
        info=ydl.extract_info(job['url'],download=False)
        if not info or 'entries' not in info:raise ValueError('This URL did not return a playlist')
        seen=set()
        for entry in info['entries']:
            check()
            if not entry:continue
            url=entry.get('webpage_url') or entry.get('url') or ''
            if not url.startswith('https://'):
                ident=entry.get('id',url)
                if not re.fullmatch(r'[A-Za-z0-9_-]{11}',ident):continue
                url='https://www.youtube.com/watch?v='+ident
            identity=media_identity(url)
            if identity in seen:continue
            seen.add(identity)
            child=new_job(url,job['quality'],job['folder'],job.get('cookie_file'),job.get('media_type','video'),job.get('audio_format','MP3'),job['id'])
            child['title']=entry.get('title') or url
            child['playlist_index']=entry.get('playlist_index')
            save(child);job['job_ids'].append(child['id'])
        check()
        if not job['job_ids']:raise ValueError('No accessible videos were found in this playlist')
        job.update(status='tracking',expansion_complete=True,title=info.get('title') or 'YouTube playlist',message=f'{len(job["job_ids"])} playlist videos queued')
        save(job)

def run(job_id):
    job = read_job(job_id)
    cancelled = job_path(job_id).with_suffix('.cancel')
    last = 0
    completed_files = []
    def check():
        if cancelled.exists():
            raise RuntimeError('Cancelled by user')
    def progress(d):
        nonlocal last
        check()
        if time.monotonic() - last < .5 and d['status'] != 'finished':
            return
        last = time.monotonic()
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
        job.update(status='downloading' if d['status'] != 'finished' else 'processing',
                   progress=round(100 * d.get('downloaded_bytes', 0) / total, 1) if total else 0,
                   title=d.get('info_dict', {}).get('title', job['title']),
                   message='Merging / finishing' if d['status'] == 'finished' else
                   f"{(d.get('speed') or 0)/1048576:.1f} MB/s • ETA {d.get('eta') or '?'}s")
        save(job)
    def post(d):
        check()
        job.update(status='processing', message='Extracting audio' if job.get('media_type') == 'audio' else 'Merging audio and video'); save(job)
    try:
        check()
        job.update(status='starting',pid=os.getpid(),started=time.time(),message='Reading available streams'); save(job)
        if job.get('job_type')=='playlist':
            expand_playlist(job,check)
            return
        opts = options(job['quality'], job['folder'], job.get('cookie_file'), job.get('media_type', 'video'), job.get('audio_format', 'MP3'))
        opts.update(progress_hooks=[progress], postprocessor_hooks=[post], post_hooks=[completed_files.append],logger=Logger())
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(job['url'], download=True)
        check()
        entries = list(info.get('entries') or [info])
        files = list(completed_files)
        for entry in entries:
            if files:
                continue
            if entry and entry.get('filepath'):
                files.append(entry['filepath'])
            elif entry:
                files.extend(d['filepath'] for d in entry.get('requested_downloads', []) if d.get('filepath'))
        job.update(status='complete', progress=100, title=info.get('title', job['title']),
                   message='Download complete', files=files)
    except Exception as e:
        blocked=isinstance(e,PlatformBlocked) or is_blocked(e)
        job.update(status='cancelled' if cancelled.exists() else 'blocked' if blocked else 'failed',
                   message='Service needs sign-in/verification or has temporarily rate-limited downloads. Select your own cookies file and Retry when available.' if blocked else str(e),
                   error_detail=str(e))
        save(job)
        if blocked and job.get('batch_id'):
            for pending in raw_jobs():
                if pending.get('batch_id')==job['batch_id'] and pending['status']=='queued' and platform(pending['url'])==platform(job['url']):
                    pending.update(status='paused',message='Batch paused after a service verification/rate-limit response. Select cookies and Retry this batch.');save(pending)
        if cancelled.exists() and job.get('job_type')=='playlist':
            for pending in raw_jobs():
                if pending.get('batch_id')==job_id:cancel_download(pending['id'])
        elif job.get('job_type')=='playlist':
            for pending in raw_jobs():
                if pending.get('batch_id')==job_id and pending['status']=='queued':
                    pending.update(status='paused',message='Playlist loading was interrupted. Retry the playlist row.');save(pending)
    save(job)

if __name__ == '__main__':
    run(sys.argv[1])
