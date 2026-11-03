"""One persistent dispatcher, with a small number of worker processes."""
from contextlib import contextmanager
import os
import subprocess
import sys
import time
from core import DATA, ROOT, raw_jobs, save, queue_settings, job_path, media_identity, detached

@contextmanager
def queue_lock():
    DATA.mkdir(parents=True,exist_ok=True)
    handle=open(DATA/'queue.lock','a+b');handle.seek(0)
    if os.fstat(handle.fileno()).st_size==0:handle.write(b'0');handle.flush()
    handle.seek(0);locked=False
    try:
        if os.name=='nt':
            import msvcrt
            try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1);locked=True
            except OSError:pass
        else:
            import fcntl
            try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);locked=True
            except OSError:pass
        yield locked
    finally:
        if locked:
            handle.seek(0)
            if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle,fcntl.LOCK_UN)
        handle.close()

def alive(pid):
    if not pid:return False
    if os.name=='nt':
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.restype=ctypes.c_void_p
        handle=kernel.OpenProcess(0x1000,False,int(pid))
        if not handle:return False
        try:
            code=ctypes.c_ulong();kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code));return code.value==259
        finally:kernel.CloseHandle(ctypes.c_void_p(handle))
    try:os.kill(int(pid),0);return True
    except OSError:return False

def dispatch_once(children,last_start,clock=time.time):
    now=clock();settings=queue_settings();jobs=raw_jobs()
    for ident,process in list(children.items()):
        if process.poll() is not None:children.pop(ident)
    active=[]
    for job in jobs:
        if job['status'] in ('starting','downloading','processing','expanding'):
            if job['id'] in children or alive(job.get('pid')):active.append(job)
            elif now-job.get('started',job['created'])>30:
                job.update(status='queued',pid=None,message='Resuming an interrupted download');save(job)
    if settings['paused'] or len(active)>=settings['concurrency'] or now-last_start<settings['gap_seconds']:return last_start,bool(active or any(j['status']=='queued' for j in jobs))
    by_id={j['id']:j for j in jobs}
    def output_key(job):return (media_identity(job['url']),job['folder'],job.get('media_type','video'),job.get('audio_format') if job.get('media_type')=='audio' else job.get('quality'))
    active_keys={output_key(j) for j in active}
    waiting=sorted((j for j in jobs if j['status']=='queued' and j.get('job_type')!='batch' and output_key(j) not in active_keys
                    and (not j.get('batch_id') or by_id.get(j['batch_id'],{}).get('status')=='tracking')),key=lambda j:j['created'])
    if waiting:
        job=waiting[0]
        if job_path(job['id']).with_suffix('.cancel').exists():
            job.update(status='cancelled');save(job);return last_start,True
        job.update(status='starting',started=now,pid=None,message='Starting queued download');save(job)
        command=[sys.executable,'--worker',job['id']] if getattr(sys,'frozen',False) else [sys.executable,str(ROOT/'worker.py'),job['id']]
        try:
            children[job['id']]=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**detached())
        except Exception as error:job.update(status='failed',message=str(error));save(job)
        return now,True
    return last_start,bool(active)

def run():
    with queue_lock() as acquired:
        if not acquired:return
        (DATA/'queue-starting.flag').unlink(missing_ok=True)
        children={};last_start=0;idle_since=time.time()
        while True:
            last_start,busy=dispatch_once(children,last_start)
            if busy:idle_since=time.time()
            elif time.time()-idle_since>8:return
            time.sleep(.5)

if __name__=='__main__':run()
