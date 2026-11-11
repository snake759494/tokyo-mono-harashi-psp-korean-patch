import pycdlib,sys,os
iso=pycdlib.PyCdlib();iso.open(sys.argv[1])
for p in sys.argv[3:]:
    out=os.path.join(sys.argv[2],p.split('/')[-1]); iso.get_file_from_iso(out,iso_path=p)
