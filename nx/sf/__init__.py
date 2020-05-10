import enum
from ctypes import *
import _ctypes

from .. import util

class BufferAttr(enum.Enum):
    In                             = util.bit(0)
    Out                            = util.bit(1)
    HipcMapAlias                   = util.bit(2)
    HipcPointer                    = util.bit(3)
    FixedSize                      = util.bit(4)
    HipcAutoSelect                 = util.bit(5)
    HipcMapTransferAllowsNonSecure = util.bit(6)
    HipcMapTransferAllowsNonDevice = util.bit(7)

    def __or__(self, other):
        if not isinstance(other, int):
            other = other.value

        return self.value | other

class OutHandleAttr(enum.Enum):
    HipcCopy = 1
    HipcMove = 2

class Buffer:
    def __init__(self, ptr=None, size=0):
        self.ptr_orig = ptr

        ptr = cast(ptr, c_void_p).value

        if ptr is None:
            ptr = 0

        self.ptr = ptr
        self.size = size

    @property
    def contents(self):
        if isinstance(self.ptr_orig, _ctypes._Pointer):
            return self.ptr_orig.contents
        elif isinstance(self.ptr_orig, _ctypes.Array):
            if len(self.ptr_orig) > 0 and isinstance(self.ptr_orig[0], bytes):
                return b"".join(self.ptr_orig)

            return self.ptr_orig
        else:
            p = cast(self.ptr, POINTER(c_char))
            return p[:self.size]

from .service import Service, SubService