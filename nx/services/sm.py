from ctypes import *

from .. import sf, kernel
from ..types import ResultException

class ServiceManager(sf.Service):
    class ServiceName(LittleEndianStructure):
        _fields_ = [
            ("name", c_char * 8)
        ]

    def __init__(self):
        while True:
            try:
                handle = kernel.svc.connect_to_named_port("sm:")
                break
            except ResultException as e:
                if e.result != kernel.result("NotFound"):
                    raise e

                kernel.svc.sleep_thread(50 * 10**6)

        super().__init__(handle)

        self.overrides = {}

        try:
            self.get_service("")
        except ResultException as e:
            if e.result == 0x415:
                self.initialize()

    def initialize(self):
        self.dispatch(0, c_uint64(),
            in_send_pid = True,
        )

    def get_service(self, name, original=False):
        if not original and name in self.overrides:
            handle = self.overrides[name]
            own_handle = False
        else:
            out = self.dispatch(1, self.ServiceName(name.encode()),
                out_handle_attrs = (
                    sf.OutHandleAttr.HipcMove,
                )
            )

            handle = out["handles"][0]
            own_handle = True

        return handle, own_handle

    def register_service(self, name, is_light=False, max_sessions=1):
        class In(LittleEndianStructure):
            _fields_ = [
                ("name",         self.ServiceName),
                ("is_light",     c_bool),
                ("max_sessions", c_int32)
            ]

        out = self.dispatch(2, In(self.ServiceName(name.encode()), is_light, max_sessions),
            out_handle_attrs = (
                sf.OutHandleAttr.HipcMove,
            )
        )

        return out["handles"][0]

    def unregister_service(self, name):
        self.dispatch(3, self.ServiceName(name.encode()))

    def is_service_registered(self, name):
        """
        Atmopshere extension
        """

        out = self.dispatch(65100, self.ServiceName(name.encode()), c_bool)

        return out["out"].value