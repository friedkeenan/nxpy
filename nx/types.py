from ctypes import *

Handle = c_uint32

class Result(Union):
    class Split(LittleEndianStructure):
        _fields_ = [
            ("module",      c_uint32, 9),
            ("description", c_uint32, 13)
        ]

    _anonymous_ = ("split",)
    _fields_ = [
        ("value", c_uint32),
        ("split", Split)
    ]

    @property
    def failed(self):
        return self.value != 0

    @property
    def succeeded(self):
        return self.value == 0

    def __eq__(self, other):
        if not isinstance(other, int):
            other = other.value

        return self.value == other

    def __str__(self):
        return f"2{self.module:03}-{self.description:04} ({self.value:#x})"

    def __repr__(self):
        return f"Result({self})"

class ResultException(Exception):
    def __init__(self, result):
        super().__init__(str(result))

        self.result = result

class HosVersion:
    class Range:
        def __init__(self, a, b=None):
            if b is None:
                b = a
                a = HosVersion(0,0,0)

            if not isinstance(a, HosVersion):
                a = HosVersion(*a)
            if not isinstance(b, HosVersion):
                b = HosVersion(*b)

            self.a = a.packed
            self.b = b.packed

        def __contains__(self, key):
            if not isinstance(key, HosVersion):
                key = HosVersion(*key)

            return self.a <= key.packed <= self.b

    def __init__(self, major, minor, micro):
        self.major = major
        self.minor = minor
        self.micro = micro

    def in_range(self, a, b=None):
        return self in self.Range(a, b)

    @property
    def packed(self):
        return (self.major << 16) | (self.minor << 8) | self.micro

    def __eq__(self, other):
        if not isinstance(other, HosVersion):
            other = type(self)(*other)

        return self.packed == other.packed

    def __gt__(self, other):
        if not isinstance(other, HosVersion):
            other = type(self)(*other)

        return self.packed > other.packed

    def __lt__(self, other):
        if not isinstance(other, HosVersion):
            other = type(self)(*other)

        return self.packed < other.packed

    def __ge__(self, other):
        if not isinstance(other, HosVersion):
            other = type(self)(*other)

        return self.packed >= other.packed

    def __le__(self, other):
        if not isinstance(other, HosVersion):
            other = type(self)(*other)

        return self.packed <= other.packed

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.micro}"

    def __repr__(self):
        return f"HosVersion({str(self)})"