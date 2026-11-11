import struct
from PIL import Image
class IPK:
    def __init__(s,b):
        s.b=bytearray(b)
        s.n,_,s.pw,s.ph,s.cw,s.ch=struct.unpack_from('<6H',b,16)
        s.ent=[list(struct.unpack_from('<HBBH',b,0x1c+6*k)) for k in range(s.n)]
        s.img=b.index(b'IMG ')
        s.cols=s.pw//s.cw; s.rows=s.ph//s.ch; s.per=s.cols*s.rows
        s.psize=s.pw*s.ph//2
    def page(s,i):
        o=s.img+16+i*s.psize; d=s.b[o:o+s.psize]
        im=Image.new('L',(s.pw,s.ph)); px=im.load()
        for y in range(s.ph):
            for x in range(s.pw):
                v=d[(y*s.pw+x)//2]; v=(v>>4) if x&1 else v&15
                px[x,y]=v*17
        return im
