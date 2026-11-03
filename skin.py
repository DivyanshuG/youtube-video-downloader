"""Native Windows widgets styled to match the supplied glossy red reference."""
import math
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageDraw, ImageFilter, ImageTk

import sys
UI_FONT='Segoe UI' if sys.platform.startswith('win') else 'Helvetica Neue'
MONO_FONT='Consolas' if sys.platform.startswith('win') else 'Menlo'

def wheel_units(event):
    """Mouse-wheel delta -> scroll units. Windows reports 120 per notch; macOS reports small values."""
    return -event.delta if sys.platform=='darwin' else -int(event.delta/120)

BG='#090a0c'
PANEL='#101113'
TEXT='#f4f4f6'
RED='#ff193a'

def mix(a,b,t):return tuple(round(x+(y-x)*t) for x,y in zip(a,b))

def surface(w,h,accent=False,selected=False):
    w,h=max(12,w),max(12,h)
    image=Image.new('RGBA',(w,h),(0,0,0,0))
    mask=Image.new('L',(w,h));d=ImageDraw.Draw(mask)
    d.rounded_rectangle((4,4,w-5,h-5),radius=7,fill=255)
    top,bottom=((255,42,68),(194,0,29)) if accent else ((40,42,47),(20,22,25))
    fill=Image.new('RGBA',(w,h));dr=ImageDraw.Draw(fill)
    for y in range(h):dr.line((0,y,w,y),fill=mix(top,bottom,y/max(1,h-1))+(255,))
    if accent:
        glow=Image.new('RGBA',(w,h));g=ImageDraw.Draw(glow)
        g.rounded_rectangle((4,4,w-5,h-5),radius=7,outline=(255,0,45,220),width=3)
        image=Image.alpha_composite(image,glow.filter(ImageFilter.GaussianBlur(4)))
    image=Image.alpha_composite(image,Image.composite(fill,Image.new('RGBA',(w,h)),mask))
    dr=ImageDraw.Draw(image)
    dr.rounded_rectangle((4,4,w-5,h-5),radius=7,outline=(255,114,136,255) if accent else (65,67,73,255),width=1)
    dr.line((13,5,w-14,5),fill=(255,194,204,190) if accent else (102,105,112,100))
    return image

class GlossButton(tk.Canvas):
    def __init__(self,parent,text='',command=None,style='',state='normal',accent=False,**kw):
        self.text=text;self.command=command;self.enabled=state!='disabled';self.accent=accent or style=='Accent.TButton';self.hover=False
        self.font=tkfont.Font(family=UI_FONT,size=10,weight='bold' if self.accent else 'normal')
        width=max(72,self.font.measure(text)+32)
        super().__init__(parent,width=width,height=39,bg=parent.cget('bg'),highlightthickness=0,bd=0,cursor='hand2',takefocus=True)
        self.bind('<Configure>',lambda e:self.draw())
        self.bind('<Enter>',lambda e:self.set_hover(True));self.bind('<Leave>',lambda e:self.set_hover(False))
        self.bind('<Button-1>',lambda e:self.invoke());self.bind('<Return>',lambda e:self.invoke());self.bind('<space>',lambda e:self.invoke())
        self.draw()
    def invoke(self):
        if self.enabled and self.command:self.command()
    def set_hover(self,value):self.hover=value;self.draw()
    def configure(self,cnf=None,**kw):
        if isinstance(cnf,dict):kw={**cnf,**kw}
        if 'text' in kw:self.text=kw.pop('text');super().configure(width=max(72,self.font.measure(self.text)+32))
        if 'state' in kw:self.enabled=kw.pop('state')!='disabled'
        if 'accent' in kw:
            self.accent=kw.pop('accent');self.font.configure(weight='bold' if self.accent else 'normal')
        if kw:super().configure(**kw)
        if hasattr(self,'font'):self.draw()
    config=configure
    def draw(self):
        w=self.winfo_width();h=self.winfo_height()
        if w<10:w=int(self.cget('width'))
        if h<10:h=int(self.cget('height'))
        img=surface(w,h,self.accent)
        if not self.enabled:img=Image.blend(img,Image.new('RGBA',img.size,(15,15,17,200)),.55)
        if self.hover and self.enabled:
            img=Image.blend(img,Image.new('RGBA',img.size,(255,100,120,35)),.07)
        self.photo=ImageTk.PhotoImage(img);self.delete('all');self.create_image(0,0,image=self.photo,anchor='nw')
        self.create_text(w/2,h/2,text=self.text,fill=TEXT if self.enabled else '#777980',font=self.font)

class WaveBanner(tk.Canvas):
    def __init__(self,parent):
        super().__init__(parent,height=83,bg=BG,highlightthickness=0)
        self.bind('<Configure>',lambda e:self.draw())
    def draw(self):
        w=max(300,self.winfo_width());h=max(83,self.winfo_height())
        base=Image.new('RGBA',(w,h),BG);lines=Image.new('RGBA',(w,h));d=ImageDraw.Draw(lines)
        for j in range(8):
            points=[]
            for x in range(int(w*.34),w+1,3):
                t=(x-w*.34)/(w*.66)
                y=h*(.85-.51*math.sin(t*7.4-1.1)+.13*math.sin(t*15+j*.15))-j*3
                points.append((x,y))
            d.line(points,fill=(245,0,35,100+j*14),width=1 if j%2 else 2)
        base=Image.alpha_composite(base,lines.filter(ImageFilter.GaussianBlur(6)))
        base=Image.alpha_composite(base,lines)
        self.photo=ImageTk.PhotoImage(base);self.delete('all');self.create_image(0,0,image=self.photo,anchor='nw')
        title_font=tkfont.Font(family=UI_FONT,size=27,weight='bold')
        self.create_text(4,1,anchor='nw',text='Video',font=title_font,fill='white')
        self.create_text(4+title_font.measure('Video '),1,anchor='nw',text='Downloader',font=title_font,fill=RED)
        self.create_text(5,52,anchor='nw',text='Save the video. Keep just the music. Make it yours.',font=(UI_FONT,10),fill='#d1d2d8')

class RibbonBackground(tk.Label):
    def __init__(self,parent):
        super().__init__(parent,bg=BG,bd=0)
        self.place(x=0,y=0,relwidth=1,relheight=1);self.lower()
        self.bind('<Configure>',self.draw)
    def draw(self,event):
        w,h=max(1,event.width),max(1,event.height)
        image=Image.new('RGBA',(w,h),'#0b090c');glow=Image.new('RGBA',(w,h));d=ImageDraw.Draw(glow)
        points=[(w,h*.38),(w*.78,h*.61),(-20,h*.91),(w*.35,h*.73),(w,h*.48)]
        d.polygon(points,fill=(210,0,30,85));d.line(points[:3],fill=(255,10,48,210),width=2)
        image=Image.alpha_composite(image,glow.filter(ImageFilter.GaussianBlur(9)));image=Image.alpha_composite(image,glow)
        ImageDraw.Draw(image).line((w-1,0,w-1,h),fill=(190,0,25,240),width=1)
        self.photo=ImageTk.PhotoImage(image);self.configure(image=self.photo)

class GlassPanel(tk.Frame):
    def __init__(self,parent,**kw):
        kw.pop('highlightbackground',None);kw.pop('highlightthickness',None)
        super().__init__(parent,**kw)
        self.backdrop=tk.Label(self,bg=BG,bd=0);self.backdrop.place(x=0,y=0,relwidth=1,relheight=1);self.backdrop.lower()
        self.bind('<Configure>',self.draw)
    def draw(self,event):
        w,h=event.width,event.height
        if min(w,h)<5:return
        image=Image.new('RGB',(w,h),BG);d=ImageDraw.Draw(image)
        d.rounded_rectangle((0,0,w-1,h-1),radius=13,fill=PANEL,outline='#46474d',width=1)
        d.line((18,1,w-18,1),fill='#77787e')
        self.photo=ImageTk.PhotoImage(image);self.backdrop.configure(image=self.photo)

class DownloadList(tk.Frame):
    """A scrollable native download table with real, per-row progress bars."""
    def __init__(self,parent,**kw):
        super().__init__(parent,bg=PANEL,highlightbackground='#b82138',highlightthickness=1)
        self.rows={};self.order=[];self.selected_ids=();self.redraw_pending=False
        self.font=tkfont.Font(family=UI_FONT,size=10);self.small=tkfont.Font(family=UI_FONT,size=9)
        self.header=tk.Canvas(self,height=32,bg='#17181c',highlightthickness=0);self.header.pack(fill='x')
        self.body=tk.Canvas(self,bg='#0b0c0e',highlightthickness=0);self.body.pack(fill='both',expand=True)
        self.external_scroll=None;self.last_view=None
        self.body.configure(yscrollcommand=self.scrolled)
        self.body.bind('<Configure>',lambda e:self.schedule());self.body.bind('<Button-1>',self.choose)
        self.body.bind('<MouseWheel>',lambda e:self.body.yview_scroll(wheel_units(e),'units'))
        self.header.bind('<Configure>',lambda e:self.schedule())
    def positions(self):
        w=max(500,self.body.winfo_width());return w,max(170,w-340),w-260,w-175
    def heading(self,*a,**kw):pass
    def column(self,*a,**kw):pass
    def tag_configure(self,*a,**kw):pass
    def exists(self,i):return i in self.rows
    def insert(self,parent,index,iid,values,tags=()):
        self.rows[iid]=tuple(values);self.order.append(iid);self.schedule();return iid
    def item(self,i,**kw):
        if 'values' in kw:
            values=tuple(kw['values'])
            if self.rows.get(i)!=values:self.rows[i]=values;self.schedule()
        return {'values':self.rows.get(i,())}
    def move(self,i,parent,index):
        if self.order.index(i)!=index:self.order.remove(i);self.order.insert(index,i);self.schedule()
    def selection(self):return self.selected_ids
    def selection_set(self,i):
        self.selected_ids=(i,);self.schedule();self.event_generate('<<TreeviewSelect>>')
    def see(self,i):
        if i in self.order and self.order:self.body.yview_moveto(self.order.index(i)/len(self.order))
    def yview(self,*args):return self.body.yview(*args)
    def configure(self,cnf=None,**kw):
        if isinstance(cnf,dict):kw={**cnf,**kw}
        if 'yscrollcommand' in kw:self.external_scroll=kw.pop('yscrollcommand')
        if kw:super().configure(**kw)
    config=configure
    def scrolled(self,*args):
        if self.external_scroll:self.external_scroll(*args)
        if args!=self.last_view:self.last_view=args;self.schedule()
    def bind(self,sequence=None,func=None,add=None):
        if sequence=='<Double-1>' and hasattr(self,'body'):return self.body.bind(sequence,func,add)
        return super().bind(sequence,func,add)
    def choose(self,event):
        index=int(self.body.canvasy(event.y)//32)
        if 0<=index<len(self.order):self.selection_set(self.order[index])
    def schedule(self):
        if not self.redraw_pending:self.redraw_pending=True;self.after_idle(self.draw)
    def fit(self,text,width):
        if self.font.measure(text)<=width:return text
        low,high=0,len(text)
        while low<high:
            middle=(low+high+1)//2
            if self.font.measure(text[:middle]+'…')<=width:low=middle
            else:high=middle-1
        return text[:low]+'…'
    def draw(self):
        self.redraw_pending=False
        w,fmt,status,progress=self.positions();self.header.delete('all');self.body.delete('all')
        for text,x in [('TITLE',14),('FORMAT',fmt),('STATUS',status),('PROGRESS',progress)]:
            self.header.create_text(x,16,text=text,anchor='w',font=self.small,fill='#b9bbc4')
        first=max(0,int(self.body.canvasy(0)//32)-1)
        last=min(len(self.order),first+max(1,self.body.winfo_height()//32)+3)
        for n in range(first,last):
            i=self.order[n]
            values=self.rows[i];title,kind,state,percent=values;y=n*32
            selected=i in self.selected_ids
            self.body.create_rectangle(0,y,w,y+32,fill='#351219' if selected else '#0b0c0e',outline='')
            if selected:self.body.create_line(1,y+1,1,y+31,fill=RED,width=2)
            self.body.create_line(0,y+31,w,y+31,fill='#202125')
            color='#45f0b0' if state.lower()=='complete' else '#ff5368' if state.lower() in ('failed','cancelled','blocked') else '#ffcd72' if state.lower() in ('paused','partial') else '#f3f3f6'
            self.body.create_text(14,y+16,text=self.fit(title,fmt-28),anchor='w',font=self.font,fill=TEXT)
            self.body.create_text(fmt,y+16,text=kind,anchor='w',font=self.small,fill='#dde0e8')
            self.body.create_text(status,y+16,text=state,anchor='w',font=self.small,fill=color)
            self.body.create_text(progress,y+16,text=percent,anchor='w',font=self.small,fill=color)
            start=progress+43;end=w-30;value=max(0,min(100,float(percent.rstrip('%'))))
            self.body.create_line(start,y+16,end,y+16,fill='#292c32',width=6,capstyle='round')
            if value:self.body.create_line(start,y+16,start+(end-start)*value/100,y+16,fill='#24edaa' if state.lower()=='complete' else RED,width=6,capstyle='round')
        self.body.configure(scrollregion=(0,0,w,max(1,len(self.order))*32))
