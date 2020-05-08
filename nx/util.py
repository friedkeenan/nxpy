from ctypes import sizeof

def align(value, a, up=True):
    if up:
        return (value + a - 1) & ~(a - 1)
    else:
        return (value - (a - 1)) & ~(a - 1)

def bit(*args):
    ret = 0

    for arg in args:
        ret |= 1 << arg

    return ret

def bits(value, low, high):
    return (value & ((1 << high) - 1)) >> low

def extend_buf_to_offset(buf, offset):
    buf_len = len(buf)
    if buf_len < offset:
        buf.extend(b"\x00" * (offset - buf_len))

def buf_insert(buf, offset, obj):
    if obj is None:
        return

    extend_buf_to_offset(buf, offset)

    if isinstance(obj, (bytes, bytearray)):
        size = len(obj)
    else:
        size = sizeof(obj)

    buf[offset : offset + size] = bytes(obj)