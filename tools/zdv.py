import struct,zlib
def unzdv(b):
    usz,a,n,csz=struct.unpack_from('<4I',b)
    if csz==0xffffffff: return b[16:16+usz]
    if n==1 and b[16:17]==b'\x78': return zlib.decompress(b[16:16+csz])
    raise ValueError((usz,a,n,csz))
