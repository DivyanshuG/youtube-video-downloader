"""Shared, local-only download service used by the desktop and MCP."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import re
import shutil
from urllib.parse import urlsplit, parse_qs

IS_WIN = os.name == 'nt'
IS_MAC = sys.platform == 'darwin'
EXE = '.exe' if IS_WIN else ''

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
RESOURCES = Path(getattr(sys, '_MEIPASS', ROOT))
def _default_data():
    if IS_WIN:base=Path(os.environ.get('LOCALAPPDATA', Path.home()))
    elif IS_MAC:base=Path.home() / 'Library' / 'Application Support'
    else:base=Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    return base / 'VideoDesk'

DATA = Path(os.environ.get('VIDEODESK_DATA', str(_default_data())))
JOBS = DATA / 'jobs'
DOWNLOADS = Path.home() / ('Movies' if IS_MAC else 'Videos') / 'Sonica'
AUDIO_FORMATS = {'MP3': 'mp3', 'M4A': 'm4a', 'Original audio': 'best'}
TERMINAL = {'complete','failed','cancelled','blocked','partial'}
PIN_TLDS = ('com','fr','de','ch','jp','cl','ca','it','co.uk','nz','ru','com.au','at','pt','co.kr','es','com.mx','dk','ph','th','com.uy','co','nl','info','kr','ie','vn','com.vn','ec','mx','in','pe','co.at','hu','co.in','co.nz','id','com.ec','com.py','tw','be','uk','com.bo','com.pe')
QUALITIES = {'Best available': 'bv*+ba/b', '2160p': 'bv*[height<=2160]+ba/b[height<=2160]',
             '1080p': 'bv*[height<=1080]+ba/b[height<=1080]', '720p': 'bv*[height<=720]+ba/b[height<=720]'}

def find_tool(name):
    """Bundled copy first, then PATH. macOS apps do not inherit the shell PATH, so Homebrew folders are added."""
    bundled = RESOURCES / 'bin' / (name + EXE)
    if bundled.exists():return str(bundled)
    path = os.environ.get('PATH', '')
    if IS_MAC:path += os.pathsep + os.pathsep.join(['/opt/homebrew/bin', '/usr/local/bin'])
    return shutil.which(name, path=path)

def detached():
    """Popen options that keep background workers alive after the window closes."""
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if IS_WIN else {'start_new_session': True}

def media_identity(url):
    p=urlsplit(url);host=p.hostname or '';query=parse_qs(p.query)
    if host=='youtu.be':return 'youtube:'+p.path.strip('/')
    if host=='youtube.com' or host.endswith('.youtube.com'):
        ident=(query.get('v') or [''])[0]
        if not ident and p.path.startswith(('/shorts/','/embed/','/live/')):ident=p.path.split('/')[2]
        if ident:return 'youtube:'+ident
    if 'pinterest.' in host:
        match=re.search(r'(?:/pin/|--)(\d+)/?$',p.path)
        if match:return 'pinterest:'+match[1]
    if host=='instagram.com' or host.endswith('.instagram.com'):return 'instagram:'+p.path.rstrip('/')
    return url.split('#')[0]

def validate_url(url):
    url = url.strip()
    p = urlsplit(url)
    allowed = ('youtube.com', 'youtu.be', 'instagram.com','pin.it') + tuple('pinterest.'+t for t in PIN_TLDS)
    host = (p.hostname or '').lower()
    if p.scheme != 'https' or p.username or p.password or p.port not in (None, 443) or not any(host == d or host.endswith('.' + d) for d in allowed):
        raise ValueError('Paste an HTTPS YouTube, Instagram or Pinterest video link.')
    return url

def job_path(job_id):
    if not isinstance(job_id, str) or len(job_id) != 32 or any(c not in '0123456789abcdef' for c in job_id):
        raise ValueError('Invalid job ID')
    return JOBS / (job_id + '.json')

def save(job):
    JOBS.mkdir(parents=True, exist_ok=True)
    target = job_path(job['id'])
    tmp = target.with_suffix('.'+uuid.uuid4().hex+'.tmp')
    tmp.write_text(json.dumps(job, ensure_ascii=False), encoding='utf-8')
    for attempt in range(10):
        try:
            tmp.replace(target)
            return
        except PermissionError:
            time.sleep(.05)
    tmp.replace(target)

def read_job(job_id):
    return json.loads(job_path(job_id).read_text(encoding='utf-8'))

def raw_jobs():
    JOBS.mkdir(parents=True, exist_ok=True)
    jobs = []
    for p in JOBS.glob('*.json'):
        try:
            jobs.append(json.loads(p.read_text(encoding='utf-8')))
        except (OSError, ValueError):
            pass
    return sorted(jobs, key=lambda j: j['created'], reverse=True)

def summarize(job,by_id):
    ids=job.get('job_ids')
    if job.get('job_type') not in ('batch','playlist') or not ids:return job
    if job['status'] not in ('tracking','cancelled'):return job
    children=[by_id[i] for i in ids if i in by_id]
    if not children:return job
    result=dict(job)
    done=sum(j['status']=='complete' for j in children)
    failed=sum(j['status'] in ('failed','blocked','cancelled') for j in children)
    waiting=sum(j['status'] in ('paused','blocked') for j in children)
    result.update(items_done=done,items_failed=failed,items_total=len(children),
                  progress=round(sum(j.get('progress',0) if j['status'] not in TERMINAL else 100 for j in children)/len(children),1),
                  files=[f for j in children for f in j.get('files',[])])
    if job['status']!='cancelled':
        if all(j['status'] in TERMINAL for j in children):result['status']='complete' if done==len(children) else 'partial' if done else 'blocked' if waiting else 'failed'
        elif waiting and all(j['status'] in TERMINAL or j['status']=='paused' for j in children):result['status']='paused'
        else:result['status']='downloading' if any(j['status'] in ('starting','downloading','processing') for j in children) else 'queued'
    result['message']=f'{done}/{len(children)} complete • {failed} failed/cancelled • {waiting} need attention'
    return result

def list_jobs():
    jobs=raw_jobs();by_id={j['id']:j for j in jobs}
    return [summarize(j,by_id) for j in jobs]

def get_job(job_id):
    job=read_job(job_id)
    return summarize(job,{j['id']:j for j in raw_jobs()}) if job.get('job_ids') else job

def options(quality, folder, cookie_file=None, media_type='video', audio_format='MP3'):
    if quality not in QUALITIES:
        raise ValueError('Unknown quality')
    if media_type not in ('video', 'audio'):
        raise ValueError('Choose video or audio')
    if audio_format not in AUDIO_FORMATS:
        raise ValueError('Unknown audio format')
    opts = {'format': QUALITIES[quality], 'outtmpl': str(Path(folder) / '%(title).160B [%(id)s].%(ext)s'),
            'noplaylist': True, 'windowsfilenames': True, 'merge_output_format': 'mkv',
            'quiet': True, 'no_warnings': True, 'socket_timeout': 30, 'retries': 3,
            'overwrites': False, 'js_runtimes': {'node': {}},
            'restrictfilenames': False}
    if media_type == 'audio':
        opts.update(format='bestaudio/best',
                    outtmpl=str(Path(folder) / ('%(title).160B [%(id)s].audio-' + AUDIO_FORMATS[audio_format] + '.%(ext)s')),
                    postprocessors=[{'key': 'FFmpegExtractAudio',
                                     'preferredcodec': AUDIO_FORMATS[audio_format], 'preferredquality': '0'}])
    elif quality!='Best available':
        opts['outtmpl']=str(Path(folder)/('%(title).160B [%(id)s].'+quality+'.%(ext)s'))
    ffmpeg = find_tool('ffmpeg')
    if ffmpeg:
        opts['ffmpeg_location'] = str(Path(ffmpeg).parent)
    node = find_tool('node')
    if node:
        opts['js_runtimes'] = {'node': {'path': node}}
    if cookie_file:
        cookie = Path(cookie_file).expanduser().resolve()
        if not cookie.is_file():
            raise ValueError('Cookie file does not exist')
        opts['cookiefile'] = str(cookie)
    return opts

def new_job(url, quality='Best available', folder=None, cookie_file=None, media_type='video', audio_format='MP3',batch_id=None):
    url = validate_url(url)
    destination = Path(folder or DOWNLOADS).expanduser().resolve()
    options(quality, destination, cookie_file, media_type, audio_format)
    destination.mkdir(parents=True, exist_ok=True)
    job = {'id': uuid.uuid4().hex, 'url': url, 'quality': quality, 'folder': str(destination),
           'cookie_file': cookie_file, 'created': time.time(), 'status': 'queued', 'progress': 0,
           'title': url, 'message': 'Waiting for worker', 'files': [],
           'media_type': media_type, 'audio_format': audio_format,'batch_id':batch_id,'job_type':'single'}
    return job

def ensure_dispatcher():
    from queue_runner import queue_lock
    with queue_lock() as available:
        if not available:return
    reservation=DATA/'queue-starting.flag'
    try:
        if reservation.exists() and time.time()-reservation.stat().st_mtime>15:reservation.unlink()
        fd=os.open(reservation,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    except FileExistsError:return
    command=[sys.executable,'--queue'] if getattr(sys,'frozen',False) else [sys.executable,str(ROOT/'queue_runner.py')]
    try:
        subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**detached())
    except Exception:
        reservation.unlink(missing_ok=True);raise

def start_download(url, quality='Best available', folder=None, cookie_file=None, media_type='video', audio_format='MP3'):
    job=new_job(url,quality,folder,cookie_file,media_type,audio_format)
    save(job)
    try:
        ensure_dispatcher()
    except Exception as e:
        job.update(status='failed', message=str(e)); save(job)
        raise
    return job

def parse_batch(text):
    if not isinstance(text,str):raise ValueError('Paste one link per line')
    links=re.findall(r'https?://[^\s<>"\']+',text)
    if not links:raise ValueError('Add at least one video link')
    return [validate_url(link.rstrip(',;')) for link in links]

def start_batch(urls,quality='Best available',folder=None,cookie_file=None,media_type='video',audio_format='MP3',title=None):
    if isinstance(urls,str):urls=parse_batch(urls)
    if not urls:raise ValueError('Add at least one video link')
    by_identity={}
    for url in urls:
        url=validate_url(url);by_identity.setdefault(media_identity(url),url)
    unique=list(by_identity.values())
    parent=new_job(unique[0],quality,folder,cookie_file,media_type,audio_format)
    children=[new_job(url,quality,parent['folder'],cookie_file,media_type,audio_format,parent['id']) for url in unique]
    parent.update(job_type='batch',status='tracking',title=title or f'Batch • {len(children)} {media_type} downloads',job_ids=[j['id'] for j in children],message='Batch queued')
    for child in children:save(child)
    save(parent);ensure_dispatcher()
    return {'batch_id':parent['id'],'job_ids':parent['job_ids'],'count':len(children),'duplicates_removed':len(urls)-len(unique)}

def validate_playlist_items(items):
    if not items:return None
    items=items.replace(' ','')
    if not re.fullmatch(r'\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*',items):raise ValueError('Use playlist numbers such as 1-20 or 1-10,15,20-30')
    for chunk in items.split(','):
        values=[int(v) for v in chunk.split('-')]
        if min(values)<1 or (len(values)==2 and values[0]>values[1]):raise ValueError('Playlist positions start at 1; ranges must go forward')
    return items

def start_playlist(url,quality='Best available',folder=None,cookie_file=None,media_type='video',audio_format='MP3',playlist_items=None):
    url=validate_url(url);p=urlsplit(url)
    if not (p.hostname or '').endswith('youtube.com') or not parse_qs(p.query).get('list'):raise ValueError('Paste a YouTube playlist link containing list=...')
    job=new_job(url,quality,folder,cookie_file,media_type,audio_format)
    job.update(job_type='playlist',title='YouTube playlist • waiting to load',playlist_items=validate_playlist_items(playlist_items),job_ids=[])
    save(job);ensure_dispatcher();return job

def queue_settings():
    try:data=json.loads((DATA/'queue-settings.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):data={}
    return {'concurrency':max(1,min(4,int(data.get('concurrency',2)))),'gap_seconds':max(0,min(300,float(data.get('gap_seconds',5)))),'paused':bool(data.get('paused',False))}

def configure_queue(concurrency=None,gap_seconds=None,paused=None):
    settings=queue_settings()
    if concurrency is not None:
        if not 1<=int(concurrency)<=4:raise ValueError('Parallel downloads must be between 1 and 4')
        settings['concurrency']=int(concurrency)
    if gap_seconds is not None:
        if not 0<=float(gap_seconds)<=300:raise ValueError('Delay must be between 0 and 300 seconds')
        settings['gap_seconds']=float(gap_seconds)
    if paused is not None:settings['paused']=bool(paused)
    DATA.mkdir(parents=True,exist_ok=True)
    target=DATA/'queue-settings.json';temp=target.with_suffix('.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(settings),encoding='utf-8');temp.replace(target)
    if not settings['paused']:ensure_dispatcher()
    return settings

def retry_download(job_id,cookie_file=None):
    job=read_job(job_id)
    if job.get('job_type')=='playlist' and not job.get('expansion_complete') and job.get('job_ids'):
        for child_id in job['job_ids']:cancel_download(child_id)
        job['job_ids']=[]
    if job.get('job_ids'):
        for child_id in job['job_ids']:
            child=read_job(child_id)
            if child['status'] in ('failed','blocked','paused','cancelled'):retry_download(child_id,cookie_file)
        job.update(status='tracking');save(job)
    elif job['status'] in ('failed','blocked','paused','cancelled'):
        marker=job_path(job_id).with_suffix('.cancel')
        if marker.exists():marker.unlink()
        job.update(status='queued',progress=0,message='Retry queued',pid=None)
        if cookie_file:
            options(job['quality'],job['folder'],cookie_file);job['cookie_file']=cookie_file
        save(job)
    ensure_dispatcher();return get_job(job_id)

def cancel_download(job_id):
    job = get_job(job_id)
    if job['status'] in TERMINAL:return {'id':job_id,'message':'This download is already finished or stopped.'}
    if job.get('job_ids'):
        for child_id in job['job_ids']:cancel_download(child_id)
        job.update(status='cancelled',message='Batch cancelled');save(job)
    elif job['status'] in ('queued','paused'):
        job_path(job_id).with_suffix('.cancel').touch();job.update(status='cancelled',message='Cancelled before download');save(job)
    elif job['status'] not in TERMINAL:
        job_path(job_id).with_suffix('.cancel').touch()
    return {'id': job_id, 'message': 'Cancellation requested; a current network operation may take up to 30 seconds.'}

def inspect_video(url, cookie_file=None):
    import yt_dlp
    with yt_dlp.YoutubeDL(options('Best available', DOWNLOADS, cookie_file)) as ydl:
        info = ydl.extract_info(validate_url(url), download=False)
    if info.get('entries'):
        return {'title': info.get('title'), 'message': 'This link contains multiple items; use a direct video link.'}
    return {'title': info.get('title'), 'duration': info.get('duration'), 'uploader': info.get('uploader'),
            'resolutions': sorted({f['height'] for f in info.get('formats', []) if f.get('height')}),
            'url': url}
