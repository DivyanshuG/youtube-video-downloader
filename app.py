import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
from core import IS_WIN, IS_MAC, find_tool, DATA, DOWNLOADS, RESOURCES, QUALITIES, AUDIO_FORMATS, TERMINAL, start_download, start_batch, start_playlist, list_jobs, cancel_download, inspect_video, retry_download, queue_settings, configure_queue, ensure_dispatcher
from bridge import ConnectionBridge
from branding import APP_NAME, VERSION
from PIL import Image, ImageTk
from skin import GlossButton as Button, WaveBanner, RibbonBackground, GlassPanel, DownloadList, BG, PANEL, RED, UI_FONT, MONO_FONT, wheel_units

# Keep canvas artwork, hit targets and native controls in the same coordinate
# system on Windows displays that use scaling above 100 percent.
if os.name=='nt':
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError,OSError):pass

FIELD, LINE, TEXT, MUTED = '#1b1d22', '#3a3c44', '#f5f5f7', '#b3b5be'

def label(parent, text='', size=10, color=TEXT, bold=False, **kw):
    return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color, font=(UI_FONT, size, 'bold' if bold else 'normal'), **kw)

def open_path(path):
    if IS_WIN:os.startfile(path)
    else:subprocess.run(['open' if IS_MAC else 'xdg-open',str(path)],check=True)

def flat_button(parent,text,command,fg,bg=PANEL,**kw):
    """tk.Button on Windows; a clickable label on macOS, where tk.Button ignores custom colours."""
    font=kw.pop('font',None)
    if IS_WIN:
        return tk.Button(parent,text=text,command=command,bg=bg,fg=fg,activebackground=kw.pop('activebackground',bg),activeforeground=TEXT,relief='flat',bd=0,cursor='hand2',font=font,**kw)
    kw.pop('activebackground',None)
    widget=tk.Label(parent,text=text,bg=bg,fg=fg,cursor='pointinghand' if IS_MAC else 'hand2',font=font,**kw)
    widget.bind('<Button-1>',lambda e:command())
    return widget

def dark_titlebar(window):
    if os.name!='nt':return
    try:
        import ctypes
        hwnd=int(window.wm_frame(),0)
        value=ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd,20,ctypes.byref(value),ctypes.sizeof(value))
        caption=ctypes.c_int(0x00151312);text=ctypes.c_int(0x00f5f5f5)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd,35,ctypes.byref(caption),ctypes.sizeof(caption))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd,36,ctypes.byref(text),ctypes.sizeof(text))
    except (AttributeError,OSError,ValueError):pass

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        width=min(1400,self.winfo_screenwidth()-80);height=min(880,self.winfo_screenheight()-80)
        self.geometry(f'{width}x{height}');self.minsize(min(1100,width),min(710,height));self.configure(bg=BG)
        self.app_icon=ImageTk.PhotoImage(Image.open(RESOURCES/'assets'/'app-icon.png').resize((64,64),Image.Resampling.LANCZOS))
        self.sidebar_icon=ImageTk.PhotoImage(Image.open(RESOURCES/'assets'/'app-icon.png').resize((76,76),Image.Resampling.LANCZOS))
        self.iconphoto(True,self.app_icon)
        self.after(50,lambda:dark_titlebar(self))
        if IS_WIN:
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Sonika.YTIG.Downloader.3')
            except (AttributeError,OSError):pass
        self.events=queue.Queue(); self.bridge=ConnectionBridge(); self.setup_window=None; self.jobs=[]
        self.settings_path=DATA/'settings.json'
        try:self.settings=json.loads(self.settings_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):self.settings={}
        self.configure_styles()
        self.columnconfigure(1,weight=1);self.rowconfigure(0,weight=1)
        sidebar=tk.Frame(self,bg=PANEL,width=202);sidebar.grid(row=0,column=0,sticky='nsew');sidebar.grid_propagate(False)
        RibbonBackground(sidebar)
        tk.Label(sidebar,image=self.sidebar_icon,bg=PANEL,bd=0).pack(anchor='w',padx=22,pady=(17,4))
        label(sidebar,'YOUTUBE',16,bold=True).pack(anchor='w',padx=22)
        label(sidebar,'video downloader',9,MUTED).pack(anchor='w',padx=22,pady=(4,25))
        Button(sidebar,text='↓  Downloader',accent=True).pack(fill='x',padx=8)
        flat_button(sidebar,'↗   Connect AI',self.open_setup,TEXT,activebackground=FIELD,anchor='w',padx=14,pady=15).pack(fill='x',padx=10,pady=5)
        Button(sidebar,text='☷  Batch / Playlist',command=self.open_batch).pack(fill='x',padx=8,pady=(8,0))
        label(sidebar,'LOCAL DOWNLOADS\nYouTube · Instagram\nPinterest\n\nv1.0.0',9,MUTED,justify='left').pack(side='bottom',anchor='w',padx=22,pady=24)
        main=tk.Frame(self,bg=BG,padx=24,pady=20);main.grid(row=0,column=1,sticky='nsew');main.columnconfigure(0,weight=1);main.rowconfigure(3,weight=1)
        header=WaveBanner(main);header.grid(row=0,column=0,sticky='ew',pady=(0,7))
        card=GlassPanel(main,bg=PANEL,padx=18,pady=15)
        card.grid(row=1,column=0,sticky='ew');card.columnconfigure(0,weight=1)
        top=tk.Frame(card,bg=PANEL);top.grid(row=0,column=0,sticky='ew')
        label(top,'YOUTUBE · INSTAGRAM · PINTEREST',9,MUTED,True).pack(side='left')
        self.mode=tk.StringVar(value=self.settings.get('mode','video'))
        self.video_button=Button(top,text='Video',command=lambda:self.set_mode('video'))
        self.audio_button=Button(top,text='♫  Audio only',command=lambda:self.set_mode('audio'))
        self.audio_button.pack(side='right');self.video_button.pack(side='right',padx=(0,4))
        self.url=tk.StringVar();self.url_entry=ttk.Entry(card,textvariable=self.url,font=(UI_FONT,11))
        self.url_entry.grid(row=1,column=0,sticky='ew',pady=12);self.url_entry.bind('<Return>',lambda e:self.download())
        controls=tk.Frame(card,bg=PANEL);controls.grid(row=2,column=0,sticky='ew')
        self.quality=tk.StringVar(value=self.settings.get('quality','Best available'))
        self.audio_format=tk.StringVar(value=self.settings.get('audio_format','MP3'))
        self.format_label=label(controls,'Quality',color=MUTED);self.format_label.pack(side='left',padx=(0,10))
        self.format_box=ttk.Combobox(controls,textvariable=self.quality,values=list(QUALITIES),state='readonly',width=19);self.format_box.pack(side='left')
        self.inspect_button=Button(controls,text='Check link',command=self.inspect);self.inspect_button.pack(side='left',padx=8)
        Button(controls,text='Batch / Playlist',command=self.open_batch).pack(side='left')
        self.download_button=Button(controls,text='↓  Download video',style='Accent.TButton',command=self.download);self.download_button.pack(side='right')
        self.hint=tk.StringVar();label(card,textvariable=self.hint,size=9,color=MUTED,anchor='w').grid(row=3,column=0,sticky='ew',pady=(10,0))
        self.folder=tk.StringVar(value=self.settings.get('folder',str(DOWNLOADS)))
        pathrow=tk.Frame(card,bg=PANEL);pathrow.grid(row=4,column=0,sticky='ew',pady=(12,0));pathrow.columnconfigure(1,weight=1)
        label(pathrow,'Save to',color=MUTED).grid(row=0,column=0,padx=(0,10))
        ttk.Entry(pathrow,textvariable=self.folder).grid(row=0,column=1,sticky='ew');Button(pathrow,text='Browse',command=self.browse_folder).grid(row=0,column=2,padx=(8,0))
        self.cookies=tk.StringVar();self.cookie_label=tk.StringVar(value='Login cookies: none')
        login=tk.Frame(card,bg=PANEL);login.grid(row=5,column=0,sticky='ew',pady=(8,0))
        label(login,textvariable=self.cookie_label,size=9,color=MUTED).pack(side='left')
        flat_button(login,'Choose cookies file',self.choose_cookies,'#eb848b',font=(UI_FONT,9)).pack(side='right')
        section=tk.Frame(main,bg=BG);section.grid(row=2,column=0,sticky='ew',pady=(18,10))
        label(section,'▎',16,RED,True).pack(side='left');label(section,'Your downloads',13,bold=True).pack(side='left');self.summary=tk.StringVar()
        label(section,textvariable=self.summary,size=9,color=MUTED).pack(side='right')
        table=tk.Frame(main,bg=PANEL);table.grid(row=3,column=0,sticky='nsew');table.rowconfigure(0,weight=1);table.columnconfigure(0,weight=1)
        self.tree=DownloadList(table)
        for col,title,width,stretch in [('title','TITLE',350,True),('type','FORMAT',80,False),('state','STATUS',100,False),('progress','PROGRESS',84,False)]:
            self.tree.heading(col,text=title);self.tree.column(col,width=width,minwidth=width if not stretch else 160,stretch=stretch)
        self.tree.grid(row=0,column=0,sticky='nsew')
        scroll=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview);scroll.grid(row=0,column=1,sticky='ns');self.tree.configure(yscrollcommand=scroll.set)
        self.tree.tag_configure('complete',foreground='#a3d6b3');self.tree.tag_configure('failed',foreground='#ff8e96')
        self.tree.bind('<<TreeviewSelect>>',lambda e:self.show_details());self.tree.bind('<Double-1>',lambda e:self.open_folder())
        footer=tk.Frame(main,bg=BG);footer.grid(row=4,column=0,sticky='ew',pady=(10,0))
        Button(footer,text='Open folder',command=self.open_folder).pack(side='left');Button(footer,text='Cancel selected',command=self.cancel).pack(side='left',padx=8)
        Button(footer,text='Retry selected',command=self.retry).pack(side='left')
        self.pause_button=Button(footer,text='Pause queue',command=self.toggle_queue);self.pause_button.pack(side='left',padx=8)
        Button(footer,text='Connect AI / MCP',command=self.open_setup).pack(side='right')
        self.status=tk.StringVar(value='Ready. Paste a link to get started.')
        label(main,textvariable=self.status,size=9,color=MUTED,anchor='w',justify='left',wraplength=780).grid(row=5,column=0,sticky='ew',pady=(10,0))
        self.set_mode(self.mode.get() if self.mode.get() in ('video','audio') else 'video')
        self.protocol('WM_DELETE_WINDOW',self.close);ensure_dispatcher();self.refresh()
        if not IS_WIN:self.after(800,self.check_tools)

    def check_tools(self):
        missing=[name for name in ('ffmpeg','node') if not find_tool(name)]
        if missing:messagebox.showwarning('Missing helper tools','The app could not find: '+', '.join(missing)+'.\n\nFFmpeg is needed to merge video and audio and to make MP3 files; Node is needed for some YouTube links.\n\nInstall them with Homebrew:\n    brew install ffmpeg node',parent=self)

    def configure_styles(self):
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('.',font=(UI_FONT,10),background=PANEL,foreground=TEXT)
        style.configure('TButton',background=FIELD,foreground=TEXT,borderwidth=0,padding=(12,9),focuscolor=RED)
        style.map('TButton',background=[('active','#35353a')],foreground=[('disabled','#777780')])
        style.configure('Accent.TButton',background=RED,foreground='white',font=(UI_FONT,10,'bold'));style.map('Accent.TButton',background=[('active','#fb4a56')])
        style.configure('TEntry',fieldbackground=FIELD,foreground=TEXT,insertcolor=TEXT,bordercolor=LINE,lightcolor=LINE,darkcolor=LINE,padding=9)
        style.map('TEntry',bordercolor=[('focus',RED)])
        style.configure('TCombobox',fieldbackground=FIELD,foreground=TEXT,arrowcolor=TEXT,bordercolor=LINE,padding=7)
        style.configure('TSpinbox',fieldbackground=FIELD,foreground=TEXT,background=FIELD,arrowcolor=TEXT,bordercolor=LINE,insertcolor=TEXT,padding=5)
        style.map('TCombobox',fieldbackground=[('readonly',FIELD)],foreground=[('readonly',TEXT)],selectbackground=[('readonly',FIELD)],selectforeground=[('readonly',TEXT)])
        self.option_add('*TCombobox*Listbox.background',FIELD);self.option_add('*TCombobox*Listbox.foreground',TEXT);self.option_add('*TCombobox*Listbox.selectBackground',RED)
        style.configure('Treeview',background=PANEL,fieldbackground=PANEL,foreground=TEXT,rowheight=36,borderwidth=0)
        style.map('Treeview',background=[('selected','#482329')],foreground=[('selected','white')])
        style.configure('Treeview.Heading',background=FIELD,foreground=MUTED,font=(UI_FONT,9,'bold'),padding=(10,9),relief='flat')
        style.map('Treeview.Heading',background=[('active',FIELD)])
        style.configure('Vertical.TScrollbar',background=LINE,troughcolor=PANEL,borderwidth=0,arrowcolor=MUTED)
        style.configure('TNotebook',background=BG,borderwidth=0)
        style.configure('TNotebook.Tab',background=FIELD,foreground=TEXT,padding=(16,9))
        style.map('TNotebook.Tab',background=[('selected','#571b29')],foreground=[('selected','white')])

    def set_mode(self,mode):
        self.mode.set(mode)
        for button,selected in ((self.video_button,mode=='video'),(self.audio_button,mode=='audio')):
            button.configure(accent=selected)
        self.format_label.configure(text='Audio format' if mode=='audio' else 'Quality')
        self.format_box.configure(textvariable=self.audio_format if mode=='audio' else self.quality,values=list(AUDIO_FORMATS) if mode=='audio' else list(QUALITIES))
        self.download_button.configure(text='♫  Download audio' if mode=='audio' else '↓  Download video')
        self.hint.set('MP3 is widely compatible. Choose Original audio to avoid re-encoding.' if mode=='audio' else 'Highest available source quality. Separate video and audio streams are merged into MKV.')

    def browse_folder(self):
        path=filedialog.askdirectory(initialdir=self.folder.get() if Path(self.folder.get()).is_dir() else None)
        if path:self.folder.set(path)

    def choose_cookies(self):
        path=filedialog.askopenfilename(title='Select your Netscape cookies.txt',filetypes=[('Cookies text files','*.txt'),('All files','*.*')])
        if path:self.cookies.set(path);self.cookie_label.set('Login cookies: '+Path(path).name)

    def save_settings(self):
        DATA.mkdir(parents=True,exist_ok=True)
        self.settings_path.write_text(json.dumps({'mode':self.mode.get(),'quality':self.quality.get(),'audio_format':self.audio_format.get(),'folder':self.folder.get()}),encoding='utf-8')

    def download(self):
        try:
            job=start_download(self.url.get(),self.quality.get(),self.folder.get(),self.cookies.get() or None,self.mode.get(),self.audio_format.get())
            self.save_settings();self.status.set('Download started. Closing this window leaves downloads running.');self.follow_job=job['id']
        except Exception as e:messagebox.showerror('Cannot start download',str(e),parent=self)

    def inspect(self):
        url,cookies=self.url.get(),self.cookies.get() or None
        self.inspect_button.configure(state='disabled');self.status.set('Checking the link…')
        def work():
            try:self.events.put(('info',inspect_video(url,cookies)))
            except Exception as e:self.events.put(('error',str(e)))
        threading.Thread(target=work,daemon=True).start()

    def selected(self):
        ids=self.tree.selection()
        return next((j for j in self.jobs if ids and j['id']==ids[0]),None)

    def show_details(self):
        job=self.selected()
        if job:self.status.set(job['message'])

    def open_folder(self):
        job=self.selected();path=job['folder'] if job else self.folder.get()
        try:os.makedirs(path,exist_ok=True);open_path(path)
        except (OSError,subprocess.SubprocessError) as e:messagebox.showerror('Folder unavailable',str(e),parent=self)

    def cancel(self):
        job=self.selected()
        if job:self.status.set(cancel_download(job['id'])['message'])

    def retry(self):
        job=self.selected()
        if not job:return
        try:
            retry_download(job['id'],self.cookies.get() or None);self.status.set('Unfinished downloads queued again.');self.follow_job=job['id']
        except Exception as error:messagebox.showerror('Cannot retry',str(error),parent=self)

    def toggle_queue(self):
        settings=configure_queue(paused=not queue_settings()['paused'])
        self.status.set('Queue paused; active transfers finish normally.' if settings['paused'] else 'Queue resumed.')

    def open_batch(self):
        window=tk.Toplevel(self);window.title('YouTube Video Downloader • Batch / Playlist');window.configure(bg=BG)
        height=min(800,self.winfo_screenheight()-100);window.geometry(f'850x{height}');window.minsize(780,min(650,height))
        window.after(50,lambda:dark_titlebar(window))
        footer=tk.Frame(window,bg=BG,padx=24,pady=12);footer.pack(side='bottom',fill='x')
        content=tk.Frame(window,bg=BG);content.pack(fill='both',expand=True)
        canvas=tk.Canvas(content,bg=BG,highlightthickness=0)
        scroll=ttk.Scrollbar(content,orient='vertical',command=canvas.yview);scroll.pack(side='right',fill='y')
        canvas.pack(side='left',fill='both',expand=True);canvas.configure(yscrollcommand=scroll.set)
        outer=tk.Frame(canvas,bg=BG,padx=24,pady=18);item=canvas.create_window((0,0),window=outer,anchor='nw')
        outer.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
        label(outer,'Batch & Playlist downloads',22,bold=True).pack(anchor='w')
        label(outer,'Queue many links. Downloads continue in the background.',color=MUTED).pack(anchor='w',pady=(3,12))
        notebook=ttk.Notebook(outer);notebook.pack(fill='x')
        batch=tk.Frame(notebook,bg=PANEL,padx=14,pady=14);playlist=tk.Frame(notebook,bg=PANEL,padx=14,pady=14)
        notebook.add(batch,text='Batch links');notebook.add(playlist,text='YouTube playlist')
        label(batch,'Paste one YouTube, Instagram or Pinterest video link per line.',9,MUTED).pack(anchor='w',pady=(0,8))
        text_frame=tk.Frame(batch,bg=PANEL);text_frame.pack(fill='x')
        text=tk.Text(text_frame,height=6,bg=FIELD,fg=TEXT,insertbackground=TEXT,selectbackground='#702336',wrap='word',font=(UI_FONT,10),relief='flat',padx=10,pady=8,highlightthickness=1,highlightbackground=LINE)
        text.pack(side='left',fill='x',expand=True)
        text_scroll=ttk.Scrollbar(text_frame,orient='vertical',command=text.yview);text_scroll.pack(side='right',fill='y');text.configure(yscrollcommand=text_scroll.set)
        window.bind('<MouseWheel>',lambda e:canvas.yview_scroll(wheel_units(e),'units') if e.widget!=text else None)
        def load_text():
            path=filedialog.askopenfilename(parent=window,title='Load video links',filetypes=[('Text files','*.txt'),('All files','*.*')])
            if path:
                try:
                    data=Path(path).read_text(encoding='utf-8-sig');text.insert('end','\n'+data)
                except (OSError,UnicodeError) as error:messagebox.showerror('Cannot load links',str(error),parent=window)
        Button(batch,text='Load links from .txt',command=load_text).pack(anchor='w',pady=(6,0))
        label(playlist,'Paste a full YouTube playlist URL (containing list=…).',9,MUTED).pack(anchor='w',pady=(0,10))
        playlist_url=tk.StringVar();ttk.Entry(playlist,textvariable=playlist_url).pack(fill='x')
        label(playlist,'Items (optional): leave blank for the complete playlist.',9,MUTED).pack(anchor='w',pady=(16,8))
        items=tk.StringVar();ttk.Entry(playlist,textvariable=items).pack(fill='x')
        label(playlist,'Examples: 1-20  or  1-10,15,20-30. Each video gets its own status.',9,MUTED).pack(anchor='w',pady=(9,8))
        media=tk.StringVar(value='Audio only' if self.mode.get()=='audio' else 'Video')
        chosen=tk.StringVar(value=self.audio_format.get() if self.mode.get()=='audio' else self.quality.get())
        row=tk.Frame(outer,bg=BG);row.pack(fill='x',pady=(16,10))
        label(row,'Save as',color=MUTED).pack(side='left',padx=(0,10))
        ttk.Combobox(row,textvariable=media,values=['Video','Audio only'],state='readonly',width=13).pack(side='left')
        format_box=ttk.Combobox(row,textvariable=chosen,values=list(AUDIO_FORMATS) if media.get()=='Audio only' else list(QUALITIES),state='readonly',width=20);format_box.pack(side='left',padx=8)
        def change_format(*args):
            audio=media.get()=='Audio only';format_box.configure(values=list(AUDIO_FORMATS) if audio else list(QUALITIES));chosen.set(self.audio_format.get() if audio else self.quality.get())
        media.trace_add('write',change_format)
        settings=queue_settings();parallel=tk.StringVar(value=str(settings['concurrency']));delay=tk.StringVar(value=str(settings['gap_seconds']))
        row=tk.Frame(outer,bg=BG);row.pack(fill='x',pady=5)
        label(row,'Parallel downloads',color=MUTED).pack(side='left',padx=(0,9));ttk.Spinbox(row,from_=1,to=4,textvariable=parallel,width=5).pack(side='left')
        label(row,'Delay between starts (seconds)',color=MUTED).pack(side='left',padx=(20,9));ttk.Spinbox(row,from_=0,to=300,textvariable=delay,width=6).pack(side='left')
        label(outer,'No total-video cap. Parallel transfers are limited to 1–4; extra links wait in the queue.\nA delay can reduce rate-limit errors. Platform verification can still require your own cookies.',9,MUTED,justify='left').pack(anchor='w',pady=(8,10))
        label(outer,'Save to: '+self.folder.get(),9,MUTED,wraplength=760,justify='left').pack(anchor='w')
        label(outer,'Login cookies: '+(Path(self.cookies.get()).name if self.cookies.get() else 'none — choose them in the main window if required'),9,MUTED,wraplength=760).pack(anchor='w',pady=(4,10))
        hint=tk.StringVar(value='Duplicate links in the same batch are skipped.')
        label(outer,textvariable=hint,color='#ff9da3',wraplength=760,justify='left').pack(anchor='w',pady=(0,8))
        def submit():
            try:configure_queue(concurrency=int(parallel.get()),gap_seconds=float(delay.get()))
            except (ValueError,OSError) as error:messagebox.showerror('Queue settings',str(error),parent=window);return
            kind='audio' if media.get()=='Audio only' else 'video'
            quality=self.quality.get() if kind=='audio' else chosen.get();audio_format=chosen.get() if kind=='audio' else self.audio_format.get()
            links=text.get('1.0','end');url=playlist_url.get();selection=items.get();is_playlist=notebook.index('current')==1
            folder,cookies=self.folder.get(),self.cookies.get() or None
            button.configure(state='disabled');hint.set('Adding downloads to your queue…')
            def work():
                try:
                    result=start_playlist(url,quality,folder,cookies,kind,audio_format,selection) if is_playlist else start_batch(links,quality,folder,cookies,kind,audio_format)
                    ident=result['id'] if is_playlist else result['batch_id']
                    self.events.put(('queued',(window,ident)))
                except Exception as error:self.events.put(('batch_error',(window,button,str(error))))
            threading.Thread(target=work,daemon=True).start()
        button=Button(footer,text='↓  Add to download queue',style='Accent.TButton',command=submit);button.pack(side='right')

    def copy_text(self,text):
        if text:self.clipboard_clear();self.clipboard_append(text);self.update();self.connection_status.set('Copied. Paste into your AI app’s MCP / connector URL field.')

    def start_links(self):
        if self.bridge.state=='starting':return
        self.bridge.stop();self.bridge=ConnectionBridge();threading.Thread(target=self.bridge.start,daemon=True).start()

    def open_setup(self):
        if self.setup_window and self.setup_window.winfo_exists():self.setup_window.lift();return
        window=tk.Toplevel(self);self.setup_window=window;window.title('YouTube Video Downloader • Connect your AI');window.configure(bg=BG);window.geometry('830x660');window.minsize(790,540)
        window.after(50,lambda:dark_titlebar(window))
        canvas=tk.Canvas(window,bg=BG,highlightthickness=0)
        scrollbar=ttk.Scrollbar(window,orient='vertical',command=canvas.yview);scrollbar.pack(side='right',fill='y')
        canvas.pack(side='left',fill='both',expand=True);canvas.configure(yscrollcommand=scrollbar.set)
        outer=tk.Frame(canvas,bg=BG,padx=24,pady=20);item=canvas.create_window((0,0),window=outer,anchor='nw')
        outer.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
        window.bind('<MouseWheel>',lambda e:canvas.yview_scroll(wheel_units(e),'units'))
        label(outer,'Connect your AI',23,bold=True).pack(anchor='w');label(outer,'One connection link. Your downloads stay on this PC.',color=MUTED).pack(anchor='w',pady=(4,14))
        label(outer,'1  Create links.    2  Copy a link.    3  Add it in your AI app’s connector settings.').pack(anchor='w')
        actions=tk.Frame(outer,bg=BG);actions.pack(fill='x',pady=(14,7))
        self.start_link_button=Button(actions,text='Create connection links',style='Accent.TButton',command=self.start_links);self.start_link_button.pack(side='left')
        Button(actions,text='Stop sharing',command=self.bridge_stop).pack(side='left',padx=8)
        self.connection_status=tk.StringVar(value=self.bridge.message)
        label(outer,textvariable=self.connection_status,color='#ff9da3',wraplength=760,justify='left',anchor='w',height=2).pack(fill='x',pady=(0,7))
        self.link_vars=[];self.copy_buttons=[]
        cards=[('Grok Bot','Use this URL with an MCP-capable Grok client or an MCP client on the Bot’s computer.\nCustom server setup varies by version; see Setup help. Native Grok Bot setup is unverified.','https://docs.x.ai/grok-bot/computer-and-apps'),
               ('ChatGPT','Open Plugins / Apps → Add custom MCP server. Paste the link as the server URL.\nChoose no additional authentication. Your account must support custom MCP servers.','https://developers.openai.com/plugins/deploy/connect-chatgpt'),
               ('Claude','Open Settings → Connectors → Add custom connector.\nName it YouTube Video Downloader, paste the link, and connect.','https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp')]
        for name,instructions,docs in cards:
            card=tk.Frame(outer,bg=PANEL,highlightbackground=LINE,highlightthickness=1,padx=14,pady=11);card.pack(fill='x',pady=5)
            title=tk.Frame(card,bg=PANEL);title.pack(fill='x');label(title,name,12,bold=True).pack(side='left')
            flat_button(title,'Setup help ↗',lambda u=docs:webbrowser.open(u),MUTED).pack(side='right')
            label(card,instructions,9,MUTED,justify='left',anchor='w').pack(fill='x',pady=(4,7))
            row=tk.Frame(card,bg=PANEL);row.pack(fill='x');var=tk.StringVar(value=self.bridge.public_url or 'Create a connection link first');self.link_vars.append(var)
            ttk.Entry(row,textvariable=var,state='readonly',font=(MONO_FONT,9)).pack(side='left',fill='x',expand=True)
            button=Button(row,text='Copy link',command=lambda v=var:self.copy_text(v.get()),state='normal' if self.bridge.state=='ready' else 'disabled');button.pack(side='right',padx=(8,0));self.copy_buttons.append(button)
        label(outer,'Links are temporary and private: anyone with the full link can start downloads. Cloudflare relays\nconnection requests. Keep the app open; Stop sharing revokes access. A new session creates new links.\nAdd the URL in connector settings — pasting it into a normal chat does not install a connector.',9,MUTED,justify='left').pack(anchor='w',pady=(10,0))
        self.last_bridge_state=None

    def bridge_stop(self):self.bridge.stop();self.last_bridge_state=None

    def close(self):self.save_settings();self.bridge.stop();self.destroy()

    def refresh(self):
        self.jobs=list_jobs()
        for job in self.jobs:
            kind=job.get('audio_format','MP3') if job.get('media_type')=='audio' else 'Video'
            if kind=='Original audio':kind='Audio'
            if job.get('job_type') in ('batch','playlist'):kind=job['job_type'].capitalize()
            values=(job['title'],kind,job['status'].capitalize(),f"{job['progress']:.0f}%")
            if self.tree.exists(job['id']):self.tree.item(job['id'],values=values,tags=(job['status'],))
            else:self.tree.insert('','end',iid=job['id'],values=values,tags=(job['status'],))
        for index,job in enumerate(self.jobs):self.tree.move(job['id'],'',index)
        if getattr(self,'follow_job',None) and self.tree.exists(self.follow_job):self.tree.selection_set(self.follow_job);self.tree.see(self.follow_job);self.follow_job=None
        individuals=[j for j in self.jobs if j.get('job_type') not in ('batch','playlist')]
        active=sum(j['status'] in ('starting','downloading','processing') for j in individuals)
        queued=sum(j['status']=='queued' for j in individuals)
        self.summary.set(f'{active} active / {queued} queued / {sum(j["status"]=="complete" for j in individuals)} complete')
        paused=queue_settings()['paused'];self.pause_button.configure(text='Resume queue' if paused else 'Pause queue')
        if self.selected():self.show_details()
        while not self.events.empty():
            kind,data=self.events.get();self.inspect_button.configure(state='normal')
            if kind=='queued':
                window,ident=data
                if window.winfo_exists():window.destroy()
                self.follow_job=ident;self.status.set('Batch / playlist queued. Select its row for overall progress.');continue
            if kind=='batch_error':
                window,button,message=data
                if window.winfo_exists():button.configure(state='normal');messagebox.showerror('Cannot queue downloads',message,parent=window)
                continue
            if kind=='error':messagebox.showerror('Could not check link',data,parent=self);self.status.set('Link check failed')
            else:
                resolutions=', '.join(str(h)+'p' for h in data.get('resolutions',[])) or 'Not reported'
                messagebox.showinfo('Video information',f"{data.get('title','Video')}\n\nCreator: {data.get('uploader','Unknown')}\nDuration: {data.get('duration','?')} seconds\nResolutions: {resolutions}",parent=self)
                self.status.set('Link checked. Choose video or audio and download.')
        if self.setup_window and self.setup_window.winfo_exists():
            marker=(self.bridge.state,self.bridge.message)
            if marker!=getattr(self,'last_bridge_state',None):
                self.connection_status.set(self.bridge.message)
                for var in self.link_vars:var.set(self.bridge.public_url or 'Create a connection link first')
                for button in self.copy_buttons:button.configure(state='normal' if self.bridge.state=='ready' else 'disabled')
                self.start_link_button.configure(state='disabled' if self.bridge.state=='starting' else 'normal');self.last_bridge_state=marker
        self.after(750,self.refresh)

if __name__=='__main__':
    if '--worker' in sys.argv or '--mcp-http' in sys.argv or '--queue' in sys.argv:
        sys.stdout=sys.stdout or open(os.devnull,'w');sys.stderr=sys.stderr or open(os.devnull,'w')
        if '--worker' in sys.argv:
            from worker import run
            run(sys.argv[sys.argv.index('--worker')+1])
        elif '--queue' in sys.argv:
            from queue_runner import run
            run()
        else:
            from remote_server import run
            run()
    else:App().mainloop()
