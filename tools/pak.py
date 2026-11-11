import struct,sys,os
def read_toc(f):
    f.seek(0); h=f.read(16); nd,nf,nameend,dstart=struct.unpack('<4I',h)
    toc=f.read(dstart-16)
    dirs=[struct.unpack_from('<HHHHHH',toc,i*12)[:1]+struct.unpack_from('<HHHHHH',toc,i*12)[2:] for i in range(nd)]
    fo=nd*12
    files=[list(struct.unpack_from('<III',toc,fo+i*12)) for i in range(nf)]
    nb=16+fo+nf*12
    names=toc[nb-16:]
    nm=lambda o:names[o:names.index(b'\0',o)].decode()
    paths=[None]*nf
    def walk(di,pre):
        n,fd,ndd,ff,nff=dirs[di]
        p=pre+nm(n)+'/' if di else ''
        for k in range(ff,ff+nff): paths[k]=p+nm(files[k][0])
        for k in range(fd,fd+ndd): walk(k,p)
    walk(0,'')
    return dict(nd=nd,nf=nf,dstart=dstart,dirs=dirs,files=files,paths=paths,hdr=h,toc=toc,names_off=nb)
if __name__=='__main__':
    f=open(sys.argv[1],'rb'); t=read_toc(f)
    for i,(p,(n,o,s)) in enumerate(zip(t['paths'],t['files'])): print(i,hex(o),s,p)
