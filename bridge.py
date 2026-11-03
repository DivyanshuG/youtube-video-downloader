"""Explicitly enabled, temporary HTTPS MCP sharing for cloud AI clients."""
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
import urllib.request
import urllib.error
import ssl
import certifi
import http.client
import json
import dns.resolver

from core import ROOT, RESOURCES, DATA, EXE, IS_WIN, find_tool

class ResolvedHTTPSConnection(http.client.HTTPSConnection):
    """Use a fallback DNS lookup for newly created tunnel names. TLS still
    verifies the original hostname using the normal certificate checks."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._create_connection=self.connect_address

    @staticmethod
    def connect_address(address,timeout=socket._GLOBAL_DEFAULT_TIMEOUT,source_address=None,**kwargs):
        try:return socket.create_connection(address,timeout,source_address,**kwargs)
        except socket.gaierror:
            if not address[0].endswith('.trycloudflare.com'):raise
            resolver=dns.resolver.Resolver(configure=False)
            resolver.nameservers=['1.1.1.1','8.8.8.8'];resolver.timeout=2;resolver.lifetime=5
            ip=next(iter(resolver.resolve(address[0],'A'))).address
            return socket.create_connection((ip,address[1]),timeout,source_address,**kwargs)

class ResolvedHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self,request):
        return self.do_open(ResolvedHTTPSConnection,request,context=self._context)

def check_public_mcp(url):
    opener=urllib.request.build_opener(ResolvedHTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())))
    def call(method,params,request_id):
        body=json.dumps({'jsonrpc':'2.0','id':request_id,'method':method,'params':params}).encode()
        request=urllib.request.Request(url,data=body,headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'})
        with opener.open(request,timeout=8) as response:return json.load(response)
    initialized=call('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'Sonika connection check','version':'2.0'}},1)
    if 'result' not in initialized:raise RuntimeError('MCP initialization failed')
    found=call('tools/list',{},2)
    return [tool['name'] for tool in found['result']['tools']]

class ConnectionBridge:
    def __init__(self):
        self.server = self.tunnel = None
        self.local_url = self.public_url = ''
        self.state = 'off'
        self.message = 'AI connections are off. Click Create connection links to start.'
        self.abort = threading.Event()
        self.lock = threading.RLock()

    def start(self):
        with self.lock:
            if self.state in ('starting', 'ready'):
                return
            self.abort.clear()
            self.state = 'starting'
            self.message = 'Starting the local MCP server…'
        try:
            binary = RESOURCES / 'bin' / ('cloudflared' + EXE)
            if not binary.exists() and not getattr(sys, 'frozen', False):
                binary = Path(os.environ.get('SONIKA_CLOUDFLARED', ROOT / 'vendor' / ('cloudflared' + EXE)))
            if not binary.exists() and not IS_WIN:
                found = find_tool('cloudflared')
                if found:binary = Path(found)
            if not binary.exists():
                raise RuntimeError('Cloudflare connection helper is missing. Reinstall Sonika.')
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
            token = secrets.token_urlsafe(32)
            self.local_url = f'http://127.0.0.1:{port}/{token}/mcp'
            env = dict(os.environ, SONICA_BRIDGE_TOKEN=token, SONICA_BRIDGE_PORT=str(port))
            command = [sys.executable, '--mcp-http'] if getattr(sys, 'frozen', False) else [sys.executable, str(ROOT / 'remote_server.py')]
            DATA.mkdir(parents=True, exist_ok=True)
            log = open(DATA / 'connection-server.log', 'w', encoding='utf-8')
            with self.lock:
                if self.abort.is_set(): return
                self.server = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            log.close()
            for _ in range(60):
                if self.abort.wait(.25): return
                if self.server.poll() is not None: raise RuntimeError('The MCP server could not start. See connection-server.log.')
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=.3): break
                except OSError: pass
            else: raise RuntimeError('The MCP server did not start in time.')
            self.message = 'Creating a temporary HTTPS link through Cloudflare…'
            with self.lock:
                if self.abort.is_set(): return
                self.tunnel = subprocess.Popen([str(binary), 'tunnel', '--no-autoupdate', '--url', f'http://127.0.0.1:{port}',
                                                '--http-host-header', f'127.0.0.1:{port}', '--protocol', 'http2'],
                                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                              text=True, encoding='utf-8', errors='replace',
                                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            # A watchdog bounds a stalled tunnel without blocking the UI.
            watchdog = threading.Timer(120, self._timeout)
            watchdog.daemon = True; watchdog.start()
            try:
                for line in self.tunnel.stderr:
                    if self.abort.is_set(): return
                    match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
                    if match:
                        (DATA / 'connection-host.txt').write_text(match.group(),encoding='utf-8')
                        candidate = match.group() + f'/{token}/mcp'
                        # Continue draining stderr while checking reachability. Otherwise
                        # verbose tunnel startup can fill the pipe and block connection.
                        threading.Thread(target=self._drain, daemon=True).start()
                        self.message = 'Checking the HTTPS connection…'
                        last_error = 'not reachable'
                        for _ in range(60):
                            if self.abort.wait(1): return
                            try:
                                names=check_public_mcp(candidate)
                                if 'download_audio' in names and 'download_video' in names:
                                    self.public_url = candidate
                                    self.state = 'ready'
                                    self.message = 'Links ready. Keep Sonika open. Stop sharing revokes all these links.'
                                    watchdog.cancel()
                                    return
                            except (OSError,ValueError,KeyError,RuntimeError,dns.exception.DNSException) as error:
                                last_error = str(error.reason) if isinstance(error, urllib.error.URLError) else type(error).__name__
                        raise RuntimeError('HTTPS connection check failed: ' + last_error + '. Try again.')
            finally:
                watchdog.cancel()
            raise RuntimeError('Cloudflare could not create a link. Try again on your network.')
        except Exception as error:
            if not self.abort.is_set():
                self.stop()
                self.state = 'error'; self.message = str(error)

    def _timeout(self):
        if self.state == 'starting':
            self.stop(); self.state = 'error'; self.message = 'Connection timed out. Try again.'

    def _drain(self):
        process = self.tunnel
        try:
            for _ in process.stderr:
                if self.abort.is_set(): return
        except (OSError, ValueError): pass
        if self.state == 'ready' and not self.abort.is_set():
            self.stop(); self.state = 'error'; self.message = 'Connection ended. Create a new link to reconnect.'

    def stop(self):
        with self.lock:
            self.abort.set()
            for process in (self.tunnel, self.server):
                if process is not None and process.poll() is None:
                    process.terminate()
            self.public_url = self.local_url = ''
            self.state = 'off'
            self.message = 'Sharing stopped. Previous connection links no longer work.'
