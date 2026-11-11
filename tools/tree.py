# recursively expand CROW.PAK: yields (path, bytes) of leaf data (zdv decompressed)
import sys,io,struct,os;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import pak
from zdv import unzdv
def is_pak(b):
    if len(b)<16: return False
    nd,nf,ne,ds=struct.unpack_from('<4I',b)
    return 0<nd<1000 and 0<nf<100000 and ds<=len(b) and ne<=ds and b[16:18]==b'\0\0'
def expand(b,pre):
    if pre.endswith('.zdv'):
        b=unzdv(b); pre=pre[:-4]
    if pre.endswith('.pak') and is_pak(b):
        t=pak.read_toc(io.BytesIO(b))
        for p,(n,o,s) in zip(t['paths'],t['files']):
            yield from expand(b[t['dstart']+o:t['dstart']+o+s],pre+'/'+p)
    else: yield pre,b
