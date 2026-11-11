"""Re-sign a decrypted EBOOT with the disc's tag (d91613f0 = -t5)."""
import os, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEBOOT = r'D:\psp\디크립트 툴\PSP-ISO-Tools\EBOOT\_seboot.exe'
def sign(elf):
    tmp = ROOT + '/work/_eboot_tmp.elf'; out = ROOT + '/work/_eboot_tmp.bin'
    open(tmp, 'wb').write(elf)
    subprocess.run([SEBOOT, '-t5', tmp, out], check=True, capture_output=True)
    b = open(out, 'rb').read()
    os.remove(tmp); os.remove(out)
    return b
