import sys,os,time,json;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from ppsspp_rpc import Debugger
def shot(path):
    d=Debugger();r=d.frame(path);d.call('cpu.resume');d.close();return r
def press(btn,n=1,hold=0.1,gap=0.4):
    d=Debugger()
    for _ in range(n):
        d.call('input.buttons.press',button=btn,duration=max(1,int(hold*60))); time.sleep(gap)
    d.close()
if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='shot': print(shot(sys.argv[2]))
    elif cmd=='press':
        for b in sys.argv[2:]:
            if b.startswith('sleep'): time.sleep(float(b[5:])); continue
            n=1
            if '*' in b: b,n=b.split('*'); n=int(n)
            press(b,n)
