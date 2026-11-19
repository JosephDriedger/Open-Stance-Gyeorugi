"""Write a copy of a C3D with marker labels corrected; the original file is never changed.

    py Tools/Validation/relabel_c3d.py <in.c3d> <out.c3d> NAME=LABEL [NAME=LABEL ...]

Each NAME=LABEL says the marker that should be called NAME is the one currently labelled LABEL. Example, the
10 Nov 2026 spin kick, whose head labels are rotated one place around the head:

    py Tools/Validation/relabel_c3d.py "Subject 1_testspinkick1.c3d" spin_fixed.c3d LFHD=LBHD RFHD=LFHD RBHD=RFHD LBHD=RBHD

Only the POINT:LABELS parameter is rewritten (same fixed width), so all data blocks stay byte-identical.
"""
import struct
import sys


def main(src, dst, pairs):
    b = bytearray(open(src, 'rb').read())
    p = (b[0] - 1) * 512 + 4
    groups, found = {}, None
    while True:
        nlen, gid = struct.unpack('bb', b[p:p + 2])
        if nlen == 0:
            break
        name = b[p + 2:p + 2 + abs(nlen)].decode('latin1')
        q = p + 2 + abs(nlen)
        off = struct.unpack('<h', b[q:q + 2])[0]
        if gid < 0:
            groups[-gid] = name
        elif name == 'LABELS' and groups.get(gid) == 'POINT':
            r = q + 2
            nd = b[r + 1]
            dims = list(b[r + 2:r + 2 + nd])
            found = (r + 2 + nd, dims[0], dims[1])
        if off == 0:
            break
        p = q + off
    assert found, 'POINT:LABELS not found'
    start, width, count = found
    labels = [b[start + i * width:start + (i + 1) * width].decode('latin1').strip() for i in range(count)]
    index = {l.upper(): i for i, l in enumerate(labels)}
    new = list(labels)
    for pair in pairs:
        name, current = pair.split('=')
        assert current.upper() in index, f'no marker labelled {current}'
        new[index[current.upper()]] = name
    assert len({l.upper() for l in new}) == len(new), f'duplicate labels after relabel: {new}'
    for i, l in enumerate(new):
        b[start + i * width:start + (i + 1) * width] = l.ljust(width).encode('latin1')[:width]
    open(dst, 'wb').write(b)
    changed = [(labels[i], new[i]) for i in range(count) if labels[i] != new[i]]
    print('relabelled (was -> now):', changed)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
