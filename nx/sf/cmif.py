import enum
from ctypes import *

from .. import arm
from ..types import Handle, Result, ResultException
from ..kernel import svc

from . import hipc, util
from . import BufferAttr, Buffer

class CommandType(enum.Enum):
    Invalid            = 0
    LegacyRequst       = 1
    Close              = 2
    LegacyControl      = 3
    Request            = 4
    Control            = 5
    RequestWithContext = 6
    ControlWithContext = 7

class DomainRequestType(enum.Enum):
    Invalid     = 0
    SendMessage = 1
    Close       = 2

class InHeader(LittleEndianStructure):
    _fields_ = [
        ("magic",      c_char * 4),
        ("version",    c_uint32),
        ("command_id", c_uint32),
        ("token",      c_uint32)
    ]

    def __init__(self, magic=b"SFCI", *args, **kwargs):
        super().__init__(magic, *args, **kwargs)

    @property
    def valid(self):
        return self.magic == b"SFCI"

class OutHeader(LittleEndianStructure):
    _fields_ = [
        ("magic",   c_char * 4),
        ("version", c_uint32),
        ("result",  Result),
        ("token",   c_uint32)
    ]

    def __init__(self, magic=b"SFCO", *args, **kwargs):
        super().__init__(magic, *args, **kwargs)

    @property
    def valid(self):
        return self.magic == b"SFCO"

class DomainInHeader(LittleEndianStructure):
    _fields_ = [
        ("type",           c_uint8),
        ("num_in_objects", c_uint8),
        ("data_size",      c_uint16),
        ("object_id",      c_uint32),
        ("padding",        c_uint32),
        ("token",          c_uint32)
    ]

class DomainOutHeader(LittleEndianStructure):
    _fields_ = [
        ("num_out_objects", c_uint32),
        ("padding",         c_uint32 * 3)
    ]

class RequestFormat:
    def __init__(self, **kwargs):
        self.object_id = 0
        self.request_id = 0
        self.context = 0
        self.data_size = 0
        self.server_pointer_size = 0
        self.num_in_auto_buffers = 0
        self.num_out_auto_buffers = 0
        self.num_in_buffers = 0
        self.num_out_buffers = 0
        self.num_inout_buffers = 0
        self.num_in_pointers = 0
        self.num_out_pointers = 0
        self.num_out_fixed_pointers = 0
        self.num_objects = 0
        self.num_handles = 0
        self.send_pid = False

        for key, value in kwargs.items():
            setattr(self, key, value)

    def process_buffer(self, attr):
        if attr == 0:
            return

        is_in = attr & BufferAttr.In.value != 0
        is_out = attr & BufferAttr.Out.value != 0

        if attr & BufferAttr.HipcAutoSelect.value:
            if is_in:
                self.num_in_auto_buffers += 1
            if is_out:
                self.num_out_auto_buffers += 1
        elif attr & BufferAttr.HipcPointer.value:
            if is_in:
                self.num_in_pointers += 1
            if is_out:
                if attr & BufferAttr.FixedSize.value:
                    self.num_out_fixed_pointers += 1
                else:
                    self.num_out_pointers += 1
        elif attr & BufferAttr.HipcMapAlias.value:
            if is_in and is_out:
                self.num_inout_buffers += 1
            elif is_in:
                self.num_in_buffers += 1
            elif is_out:
                self.num_out_buffers += 1

class Request:
    def __init__(self, base, fmt):
        self.base = base

        actual_size = 16

        if fmt.object_id != 0:
            actual_size += sizeof(DomainInHeader) + fmt.num_objects * sizeof(c_uint32)

        actual_size += sizeof(InHeader) + fmt.data_size
        actual_size = util.align(actual_size, 2)

        out_pointer_size_table_offset = actual_size
        out_pointer_size_table_size = fmt.num_out_auto_buffers + fmt.num_out_pointers

        actual_size += sizeof(c_uint16) * out_pointer_size_table_size

        num_data_words = (actual_size + 3) // 4

        self.hipc = hipc.Request(base,
            type = CommandType.RequestWithContext if fmt.context else CommandType.Request,
            num_send_statics = fmt.num_in_auto_buffers + fmt.num_in_pointers,
            num_send_buffers = fmt.num_in_auto_buffers + fmt.num_in_buffers,
            num_recv_buffers = fmt.num_out_auto_buffers + fmt.num_out_buffers,
            num_exch_buffers = fmt.num_inout_buffers,
            num_data_words = num_data_words,
            num_recv_statics = out_pointer_size_table_size + fmt.num_out_fixed_pointers,
            send_pid = fmt.send_pid,
            num_copy_handles = fmt.num_handles,
            num_move_handles = 0,
        )

        self.data = util.align(self.hipc.data_words, 16)

        if fmt.object_id != 0:
            payload_size = sizeof(InHeader) + fmt.data_size

            domain_hdr = DomainInHeader(
                type = DomainRequestType.SendMessage.value,
                num_in_objects = fmt.num_objects,
                data_size = payload_size,
                object_id = fmt.object_id,
                padding = 0,
                token = fmt.context,
            )

            self.insert(self.data, domain_hdr)
            self.data += sizeof(domain_hdr)
            self.objects = self.data + payload_size

        hdr = InHeader(
            version = 1 if fmt.context else 0,
            command_id = fmt.request_id,
            token = 0 if fmt.object_id else fmt.context,
        )

        self.insert(self.data, hdr)
        self.data += sizeof(hdr)

        self.out_pointer_sizes = self.hipc.data_words + out_pointer_size_table_offset
        self.server_pointer_size = fmt.server_pointer_size

        self.cur_in_ptr_id = 0

    def extend_to_offset(self, offset):
        util.extend_buf_to_offset(self.base, offset)

    def insert(self, offset, obj):
        util.buf_insert(self.base, offset, obj)

    def add_object(self, obj):
        obj_id = c_uint32(obj.object_id)
        self.insert(self.objects, obj_id)

        self.objects += sizeof(obj_id)

    def add_handle(self, h):
        h = Handle(h)
        self.insert(self.hipc.copy_handles, h)

        self.hipc.copy_handles += sizeof(h)

    def add_in_buffer(self, buf, mode):
        send = hipc.BufferDescriptor(buf, mode)
        self.insert(self.hipc.send_buffers, send)

        self.hipc.send_buffers += sizeof(send)

    def add_out_buffer(self, buf, mode):
        recv = hipc.BufferDescriptor(buf, mode)
        self.insert(self.hipc.recv_buffers, recv)

        self.hipc.recv_buffers += sizeof(recv)

    def add_inout_buffer(self, buf, mode):
        exch = hipc.BufferDescriptor(buf, mode)
        self.insert(self.hipc.exch_buffers, exch)

        self.hipc.exch_buffers += sizeof(exch)

    def add_in_pointer(self, buf):
        send = hipc.StaticDescriptor(buf, self.cur_in_ptr_id)
        self.cur_in_ptr_id += 1

        self.insert(self.hipc.send_statics, send)
        self.hipc.send_statics += sizeof(send)

        self.server_pointer_size -= buf.size

    def add_out_fixed_pointer(self, buf):
        recv = hipc.RecvListEntry(buf)
        
        self.insert(self.hipc.recv_list, recv)
        self.hipc.recv_list += sizeof(recv)

        self.server_pointer_size -= buf.size

    def add_out_pointer(self, buf):
        self.add_out_fixed_pointer(buf)

        size = c_uint16(buf.size)
        self.insert(self.out_pointer_sizes, size)

        self.out_pointer_sizes += sizeof(size)

    def add_in_auto_buffer(self, buf):
        if self.server_pointer_size > 0 and buf.size <= self.server_pointer_size:
            self.add_in_pointer(buf)
            self.add_in_buffer(Buffer(), hipc.BufferMode.Normal)
        else:
            self.add_in_pointer(Buffer())
            self.add_in_buffer(buf, hipc.BufferMode.Normal)

    def add_out_auto_buffer(self, buf):
        if self.server_pointer_size > 0 and buf.size <= self.server_pointer_size:
            self.add_out_pointer(buf)
            self.add_out_buffer(Buffer(), hipc.BufferMode.Normal)
        else:
            self.add_out_pointer(Buffer())
            self.add_out_buffer(buf, hipc.BufferMode.Normal)

    def process_buffer(self, buf, attr):
        if attr == 0:
            return

        is_in = attr & BufferAttr.In.value != 0
        is_out = attr & BufferAttr.Out.value != 0

        if attr & BufferAttr.HipcAutoSelect.value:
            if is_in:
                self.add_in_auto_buffer(buf)
            if is_out:
                self.add_out_auto_buffer(buf)
        elif attr & BufferAttr.HipcPointer.value:
            if is_in:
                self.add_in_pointer(buf)
            if is_out:
                if attr & BufferAttr.FixedSize.value:
                    self.add_out_fixed_pointer(buf)
                else:
                    self.add_out_pointer(buf)
        elif attr & BufferAttr.HipcMapAlias.value:
            mode = hipc.BufferMode.Normal
            if attr & BufferAttr.HipcMapTransferAllowsNonSecure.value:
                mode = hipc.BufferMode.NonSecure
            if attr & BufferAttr.HipcMapTransferAllowsNonDevice.value:
                mode = hipc.BufferMode.NonDevice

            if is_in and is_out:
                self.add_inout_buffer(buf, mode)
            elif is_in:
                self.add_in_buffer(buf, mode)
            elif is_out:
                self.add_out_buffer(buf, mode)

class Response:
    def __init__(self, base, is_domain, size):
        h = hipc.Response(base)
        self.copy_handles = h.copy_handles
        self.move_handles = h.move_handles

        self.data = util.align(h.data_words, 16)

        self.objects = -1
        if is_domain:
            domain_hdr = DomainOutHeader.from_buffer(base, self.data)
            self.data += sizeof(domain_hdr)

            self.objects = self.data + sizeof(OutHeader) + size

        hdr = OutHeader.from_buffer(base, self.data)
        self.data += sizeof(hdr)

        if not hdr.valid:
            raise ValueError(f"Invalid magic for out header: {hdr.magic}")

        if hdr.result.failed:
            raise ResultException(hdr.result)

        self.base = base

    def get_object(self):
        obj = c_uint32.from_buffer(self.base, self.objects)
        self.objects += sizeof(obj)

        return obj.value

    def get_copy_handle(self):
        h = Handle.from_buffer(self.base, self.copy_handles)
        self.copy_handles += sizeof(h)

        return h.value

    def get_move_handle(self):
        h = Handle.from_buffer(self.base, self.move_handles)
        self.move_handles += sizeof(h)

        return h.value

def make_control_request(base, request_id, size):
        actual_size = 16 + sizeof(InHeader) + size

        h = hipc.Request(base,
            type = CommandType.Control.value,
            num_data_words = (actual_size + 3) // 4,
        )

        data_offset = util.align(h.data_words, 16)

        hdr = InHeader(
            version = 0,
            command_id = request_id,
            token = 0,
        )
        util.buf_insert(base, data_offset, hdr)

        return data_offset + sizeof(hdr)

def make_close_request(base, object_id):
    if object_id != 0:
        h = hipc.Request(base,
            type = CommandType.Request.value,
            num_data_words = (16 + sizeof(DomainInHeader)) // 4,
        )

        data_offset = util.align(h.data_words, 16)

        domain_hdr = DomainInHeader(
            type=DomainRequestType.Close.value,
            object_id = object_id,
        )
        util.buf_insert(base, data_offset, domain_hdr)
    else:
        hipc.Request(base,
            type = CommandType.Close
        )

def query_pointer_buffer_size(handle):
    base = bytearray()
    make_control_request(base, 3, 0)

    tls = arm.tls()
    for i, v in enumerate(base):
        tls[i] = v

    svc.send_sync_request(handle)

    base = bytearray(tls[:0x100])
    resp = Response(base, false, sizeof(c_uint16))

    return c_uint16.from_buffer(base, resp.data).value