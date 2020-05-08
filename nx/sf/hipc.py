import enum
from ctypes import *

from .. import util
from ..types import Handle

from . import cmif

auto_recv_static = 0xff

class BufferMode(enum.Enum):
    Normal    = 0
    NonSecure = 1
    Invalid   = 2
    NonDevice = 3

class Header(LittleEndianStructure):
    _fields_ = [
        ("type",               c_uint32, 16),
        ("num_send_statics",   c_uint32, 4),
        ("num_send_buffers",   c_uint32, 4),
        ("num_recv_buffers",   c_uint32, 4),
        ("num_exch_buffers",   c_uint32, 4),
        ("num_data_words",     c_uint32, 10),
        ("recv_static_mode",   c_uint32, 4),
        ("padding",            c_uint32, 6),
        ("recv_list_offset",   c_uint32, 11),
        ("has_special_header", c_bool, 1)
    ]

class SpecialHeader(LittleEndianStructure):
    _fields_ = [
        ("send_pid",         c_uint32, 1),
        ("num_copy_handles", c_uint32, 4),
        ("num_move_handles", c_uint32, 4),
        ("padding",          c_uint32, 23)
    ]

class StaticDescriptor(LittleEndianStructure):
    _fields_ = [
        ("index",        c_uint32, 6),
        ("address_high", c_uint32, 6),
        ("address_mid",  c_uint32, 4),
        ("size",         c_uint32, 16),
        ("address_low",  c_uint32)
    ]

    def __init__(self, buf, index):
        super().__init__(index=index, size=buf.size)

        self.address = buf.ptr

    @property
    def address(self):
        return self.address_low | (self.address_mid << 32) | (self.address_high << 36)

    @address.setter
    def address(self, addr):
        self.address_high = util.bits(addr, 36, 42)
        self.address_mid = util.bits(addr, 32, 36)
        self.address_low = util.bits(addr, 0, 32)

class BufferDescriptor(LittleEndianStructure):
    _fields_ = [
        ("size_low",     c_uint32),
        ("address_low",  c_uint32),
        ("mode",         c_uint32, 2),
        ("address_high", c_uint32, 22),
        ("size_high",    c_uint32, 4),
        ("address_mid",  c_uint32, 4)
    ]

    def __init__(self, buf, mode):
        if isinstance(mode, enum.Enum):
            mode = mode.value

        super().__init__(mode=mode)

        self.address = buf.ptr
        self.size = buf.size

    @property
    def address(self):
        return self.address_low | (self.address_mid << 32) | (self.address_high << 36)

    @address.setter
    def address(self, addr):
        self.address_high = util.bits(addr, 36, 58)
        self.address_mid = util.bits(addr, 32, 36)
        self.address_low = util.bits(addr, 0, 32)

    @property
    def size(self):
        return self.size_low | (self.size_high << 32)

    @size.setter
    def size(self, size):
        self.size_high = util.bits(size, 32, 36)
        self.size_low = util.bits(size, 0, 32)

class RecvListEntry(LittleEndianStructure):
    _fields_ = [
        ("address_low",  c_uint32),
        ("address_high", c_uint32, 16),
        ("size",         c_uint32, 16)
    ]

    def __init__(self, buf):
        super().__init__(size=buf.size)

        self.address = buf.ptr

    @property
    def address(self):
        return self.address_low | (self.address_high << 32)

    @address.setter
    def address(self, addr):
        self.address_high = util.bits(addr, 32, 48)
        self.address_low = util.bits(addr, 0, 32)

class Metadata:
    def __init__(self, **kwargs):
        self.type = cmif.CommandType.Invalid
        self.num_send_statics = 0
        self.num_send_buffers = 0
        self.num_recv_buffers = 0
        self.num_exch_buffers = 0
        self.num_data_words = 0
        self.num_recv_statics = 0
        self.send_pid = False
        self.num_copy_handles = 0
        self.num_move_handles = 0

        for key, value in kwargs.items():
            setattr(self, key, value)

class Request:
    def __init__(self, base, meta=None, **kwargs):
        if meta is None:
            meta = Metadata(**kwargs)

        has_special_header = meta.send_pid or meta.num_copy_handles > 0 or meta.num_move_handles > 0

        if meta.num_recv_statics > 0:
            recv_static_mode = 2
            if meta.num_recv_statics != auto_recv_static:
                recv_static_mode += meta.num_recv_statics
        else:
            recv_static_mode = 0

        hdr = Header(
            type = meta.type.value,
            num_send_statics = meta.num_send_statics,
            num_send_buffers = meta.num_send_buffers,
            num_recv_buffers = meta.num_recv_buffers,
            num_exch_buffers = meta.num_exch_buffers,
            num_data_words = meta.num_data_words,
            recv_static_mode = recv_static_mode,
            padding = 0,
            recv_list_offset = 0,
            has_special_header = has_special_header,
        )

        base.extend(bytes(hdr))

        if has_special_header:
            sp_hdr = SpecialHeader(
                send_pid = meta.send_pid,
                num_copy_handles = meta.num_copy_handles,
                num_move_handles = meta.num_move_handles,
            )

            base.extend(bytes(sp_hdr))

            if meta.send_pid:
                base.extend(bytes(c_uint64()))

        offset = len(base)

        if meta.num_copy_handles > 0:
            self.copy_handles = offset
            offset += sizeof(Handle) * meta.num_copy_handles
        else:
            self.num_copy_handles = -1

        if meta.num_move_handles > 0:
            self.move_handles = offset
            offset += sizeof(Handle) * meta.num_move_handles
        else:
            self.num_move_handles = -1

        if meta.num_send_statics > 0:
            self.send_statics = offset
            offset += sizeof(StaticDescriptor) * meta.num_send_statics
        else:
            self.send_statics = -1

        if meta.num_send_buffers > 0:
            self.send_buffers = offset
            offset += sizeof(BufferDescriptor) * meta.num_send_buffers
        else:
            self.send_buffers = -1

        if meta.num_recv_buffers > 0:
            self.recv_buffers = offset
            offset += sizeof(BufferDescriptor) * meta.num_recv_buffers
        else:
            self.recv_buffers = -1

        if meta.num_exch_buffers > 0:
            self.exch_buffers = offset
            offset += sizeof(BufferDescriptor) * meta.num_exch_buffers
        else:
            self.exch_buffers = -1

        if meta.num_data_words > 0:
            self.data_words = offset
            offset += sizeof(c_uint32) * meta.num_data_words
        else:
            self.data_words = -1

        if meta.num_recv_statics > 0:
            self.recv_list = offset
            offset += sizeof(RecvListEntry) * meta.num_recv_statics
        else:
            self.recv_list = -1

class Response:
    def __init__(self, base):
        hdr = Header.from_buffer(base)
        offset = sizeof(hdr)

        self.num_statics = hdr.num_send_statics
        self.num_data_words = hdr.num_data_words
        self.num_copy_handles = 0
        self.num_move_handles = 0
        self.pid = 0xFFFFFFFF

        if hdr.has_special_header:
            sp_hdr = SpecialHeader.from_buffer(base, offset)
            offset += sizeof(sp_hdr)

            self.num_copy_handles = sp_hdr.num_copy_handles
            self.num_move_handles = sp_hdr.num_move_handles

            if sp_hdr.send_pid:
                self.pid = c_uint64.from_buffer(base, offset).value
                offset += sizeof(c_uint64)

        self.copy_handles = offset
        offset += sizeof(Handle) * self.num_copy_handles

        self.move_handles = offset
        offset += sizeof(Handle) * self.num_move_handles

        self.data_words = offset