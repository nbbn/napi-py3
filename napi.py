#!/usr/bin/env python3
# original file by gim,krzynio,dosiu,hash 2oo8.
# modified by github.com/nbbn

import hashlib, sys, urllib.request, os


def f(z):
    idx = [0xe, 0x3, 0x6, 0x8, 0x2]
    mul = [2, 2, 5, 4, 3]
    add = [0, 0xd, 0x10, 0xb, 0x5]

    b = []
    for i in range(len(idx)):
        a = add[i]
        m = mul[i]
        i = idx[i]

        t = a + int(z[i], 16)
        v = int(z[t:t + 2], 16)
        b.append(("%x" % (v * m))[-1])

    return ''.join(b)

if (len(sys.argv) == 1):
    print("wy*dalaj na stadion po film")
    sys.exit(2)

d = hashlib.md5();
d.update(open(sys.argv[1], mode='br').read(10485760))

str = "http://napiprojekt.pl/unit_napisy/dl.php?l=PL&f=" + d.hexdigest() + "&t=" + f(
    d.hexdigest()) + "&v=other&kolejka=false&nick=&pass=&napios=" + os.name

open("napisy.7z", "bw").write(urllib.request.urlopen(str).read())
nazwa = sys.argv[1][:-3] + 'txt'

if (os.system("/usr/bin/7z x -y -so -piBlm8NTigvru0Jr0 napisy.7z 2>/dev/null >\"" + nazwa + "\"")):
    print("nie ma napisa do filmu")
    os.remove(nazwa)
else:
    print("napisy pobrano, milordzie!")
os.remove("napisy.7z")

lines = [line for line in open(nazwa, 'r', encoding='cp1250')]
os.remove(nazwa)
open(nazwa, 'w').writelines(lines)
