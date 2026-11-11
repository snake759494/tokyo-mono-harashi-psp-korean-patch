"""python tools/play.py <btn> <n> [gap] [tag]  -> presses btn n times, screenshot each, contact sheet work/play/<tag>.png"""
import sys,os,time;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from ppsspp_rpc import Debugger
from PIL import Image,ImageDraw
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
btn,n=sys.argv[1],int(sys.argv[2]);gap=float(sys.argv[3]) if len(sys.argv)>3 else 1.5;tag=sys.argv[4] if len(sys.argv)>4 else 'sheet'
D=ROOT+'/work/play';os.makedirs(D,exist_ok=True);shots=[]
for i in range(n):
    d=Debugger()
    if btn!='none': d.call('input.buttons.press',button=btn,duration=6)
    d.close();time.sleep(gap)
    d=Debugger();p=f'{D}/{tag}_{i:02d}.png';d.frame(p);d.call('cpu.resume');d.close();shots.append(p)
from PIL import ImageChops, ImageStat
keep=[];last=None
for p in shots:
    im=Image.open(p).convert('L').resize((120,68))
    if ImageStat.Stat(im).mean[0]<6: os.remove(p); continue
    if last is not None and ImageStat.Stat(ImageChops.difference(im,last)).mean[0]<4: os.remove(p); continue
    keep.append(p); last=im
shots=keep[-18:]
for p in keep[:-18]: os.remove(p)
W,H=480,272;C=3;R=max(1,(len(shots)+C-1)//C)
sh=Image.new('RGB',(W*C,H*R),(255,0,255));dr=ImageDraw.Draw(sh)
for i,p in enumerate(shots):
    im=Image.open(p).convert('RGB').resize((W-2,H-2));sh.paste(im,((i%C)*W,(i//C)*H));dr.text(((i%C)*W+3,(i//C)*H+3),str(i),fill=(255,255,0))
    os.remove(p)
sh.save(f'{D}/{tag}.png');print(f'{D}/{tag}.png')
