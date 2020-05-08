import enum
from ctypes import *

from .. import arm, util
from ..types import HosVersion
from ..kernel import svc

from . import cmif, Buffer, BufferAttr, OutHandleAttr

class Service:
    name = None
    domain = False

    version = HosVersion(0,0,0)

    sm = None

    def __init__(self, handle=0):
        if handle == 0:
            handle, own_handle = self.sm.get_service(self.name)
            super().__init__(handle)
            self.own_handle = own_handle

            if self.domain:
                self.convert_to_domain()
        else:
            self.session = handle
            self.own_handle = True
            self.object_id = 0

            try:
                self.pointer_buffer_size = cmif.query_pointer_buffer_size(handle)
            except:
                self.pointer_buffer_size = 0

    def dispatch(self, request_id, in_data=None, out_type=None, *,
                    target_session=0, context=0, buffers=(),
                    in_send_pid=False, in_objects=(), in_handles=(),
                    out_num_objects=0, out_handle_attrs=()):
        if in_data is None:
            in_size = 0
        elif isinstance(in_data, (bytes, bytearray)):
            in_size = len(in_data)
        else:
            in_size = sizeof(in_data)

        if out_type is None:
            out_size = 0
        elif isinstance(out_type, int):
            out_size = out_type
        elif isinstance(out_type, type):
            out_size = sizeof(out_type)
        else:
            raise ValueError("Invalid argument for out_type")

        real_buffers = self.parse_buffers(buffers)

        base = bytearray()
        in_off = self.make_request(base, request_id, context, in_size,
                    in_send_pid, real_buffers, in_objects, in_handles)

        util.buf_insert(base, in_off, in_data)

        print(base)

        tls = arm.tls()
        for i, v in enumerate(base):
            tls[i] = v

        svc.send_sync_request(self.session if target_session == 0 else target_session)

        base = bytearray(tls[:0x100])
        base = base.replace(b"SFCI", b"SFCO")

        out = self.parse_response(base, out_size, out_num_objects, out_handle_attrs)
        
        if isinstance(out_type, type):
            out["out"] = out_type.from_buffer_copy(out["out"])

        out["buffers"] = []
        for buf, real_buf in zip(buffers, real_buffers):
            if not isinstance(buf[0], Buffer) and real_buf[1] & BufferAttr.Out.value:
                out["buffers"].append(real_buf[0].contents)

        return out

    def make_request(self, base, request_id, context, data_size,
                        send_pid, buffers, objects, handles):
        fmt = cmif.RequestFormat(
                object_id = self.object_id,
                request_id = request_id,
                context = context,
                data_size = data_size,
                server_pointer_size = self.pointer_buffer_size,
                num_objects = len(objects),
                num_handles = len(handles),
                send_pid = send_pid,
            )

        for _, attr in buffers:
            fmt.process_buffer(attr)

        req = cmif.Request(base, fmt)

        if self.object_id != 0:
            for obj in objects:
                req.add_object(obj)

        for h in handles:
            req.add_handle(h)

        for buf, attr in buffers:
            req.process_buffer(buf, attr)

        return req.data

    def parse_response(self, base, out_size, num_out_objects, out_handle_attrs):
        out = {
            "objects": [],
            "handles": [],
        }

        is_domain = self.object_id != 0

        res = cmif.Response(base, is_domain, out_size)

        out["out"] = bytes(base[res.data : res.data + out_size])

        for i in range(num_out_objects):
            if is_domain:
                out["objects"].append(DomainSubService(self, res.get_object()))
            else:
                out["objects"].append(NonDomainSubService(self, res.get_move_handle()))

        for attr in out_handle_attrs:
            if attr == OutHandleAttr.HipcCopy:
                out["handles"].append(res.get_copy_handle())
            elif attr == OutHandleAttr.HipcMove:
                out["handles"].append(res.get_move_handle())

        return out

    @staticmethod
    def parse_buffers(buffers):
        real_buffers = []
        for first, attr in buffers:
            if isinstance(attr, enum.Enum):
                attr = attr.value

            if isinstance(first, Buffer):
                buf = first
            else:
                if isinstance(first, int):
                    size = first
                    first = (c_char * size)()
                    attr |= BufferAttr.Out.value
                elif isinstance(first, type):
                    size = sizeof(first)

                    if Buffer.ArrayType in first.__bases__:
                        first = first()
                    else:
                        first = pointer(first())

                    attr |= BufferAttr.Out.value
                elif isinstance(first, (bytes, bytearray)):
                    size = len(first)
                    first = (c_char * size)(*first)
                    attr |= BufferAttr.In.value
                else:
                    size = sizeof(first)
                    first = pointer(first)
                    attr |= BufferAttr.In.value

                buf = Buffer(first, size)

            real_buffers.append((buf, attr))

        return real_buffers

    @property
    def active(self):
        return self.session != 0

    @property
    def closed(self):
        return self.session == 0

    @property
    def is_domain(self):
        return self.active and self.own_handle and self.object_id != 0

    @property
    def is_domain_subservice(self):
        return self.active and not self.own_handle and self.object_id != 0

    def close(self):
        if not self.closed:
            if self.own_handle or self.object_id != 0:
                base = bytearray()
                cmif.make_close_request(base, 0 if self.own_handle else self.object_id)

                tls = arm.tls()
                for i, v in enumerate(base):
                    tls[i] = v

                try:
                    svc.send_sync_request(self.session)
                except:
                    pass

                try:
                    if self.own_handle:
                        svc.close_handle(self.session)
                except:
                    pass

            self.session = 0
            self.own_handle = False
            self.object_id = 0
            self.pointer_buffer_size = 0

    def convert_to_domain(self):
        if not self.own_handle:
            pass

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self):
        self.close()

class NonDomainSubService(Service):
    def __init__(self, parent, handle):
        self.session = handle
        self.own_handle = True
        self.object_id = 0
        self.pointer_buffer_size = parent.pointer_buffer_size

class DomainSubService(Service):
    def __init__(self, parent, object_id):
        self.session = parent.session
        self.own_handle = False
        self.object_id = object_id
        self.pointer_buffer_size = parent.pointer_buffer_size

class SubService:
    def __init__(self, srv):
        self.srv = srv

    def dispatch(self, *args, **kwargs):
        return self.srv.dispatch(*args, **kwargs)

    @property
    def version(self):
        return self.srv.version

    @property
    def closed(self):
        return self.srv.closed

    def close(self):
        if not self.closed:
            self.srv.close()

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()