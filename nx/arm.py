from ctypes import *

import _nx

def tls():
    return cast(_nx.armGetTls(), POINTER(c_char))