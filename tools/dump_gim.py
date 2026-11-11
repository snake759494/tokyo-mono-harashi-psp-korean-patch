import sys,os;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from tree import expand
import gim, znt
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out=ROOT+'/work/img'
import sys as _s
ONLY_ZNT='znt' in _s.argv;n=0;err=0;lst=[]
for r,ds,fs in os.walk(ROOT+'/work/pak'):
  for f in fs:
    p=os.path.join(r,f).replace(os.sep,'/');b=open(p,'rb').read()
    for q,d in expand(b,p):
      if q.endswith('.znt'):
        for nm,a,e in znt.entries(d):
          rel=q.split('/work/pak/',1)[1]+'#'+nm
          try:
            im=gim.decode(d[a:e]); im.save(out+'/'+rel.replace('/','__').replace('#','@')+'.png'); n+=1
            lst.append((rel,im.size,gim.blocks(d[a:e])['img']['fmt']))
          except Exception as ex: err+=1; print('ERR',rel,ex)
        continue
      if not q.endswith('.gim') or ONLY_ZNT: continue
      rel=q.split('/work/pak/',1)[1]
      try:
        im=gim.decode(d); dst=out+'/'+rel.replace('/','__')+'.png'
        im.save(dst); n+=1; lst.append((rel,im.size,gim.blocks(d)['img']['fmt']))
      except Exception as e: err+=1; print('ERR',rel,e)
os.makedirs(out,exist_ok=True)
open(out+('/_list_znt.txt' if ONLY_ZNT else '/_list.txt'),'w',encoding='utf8').write('\n'.join(f'{a}\t{b[0]}x{b[1]}\t{c}' for a,b,c in lst))
print(n,err)
