"""
The binding between FreeLAN's memory function and the nose plugin.
"""

from pyfreelan.api import (
    native,
    ffi,
)

memory_map = {}
memory_usage = {
    'current': 0,
    'max': 0,
    'sum': 0,
    'allocs': 0,
    'reallocs': 0,
    'deallocs': 0,
}
memory_sequence = []


class PointerInfo(object):
    def __init__(self, pointer, size):
        self.pointer = pointer
        self.size = size
        self._file = ffi.NULL
        self._line = None

    def mark_pointer(self, file, line):
        self._file = file
        self._line = line

    @property
    def file(self):
        if self._file == ffi.NULL:
            return "<unknown file>"
        else:
            return ffi.string(self._file)

    @property
    def line(self):
        if self._line is None:
            return "<unknown line>"
        else:
            return self._line

    def __repr__(self):
        return (
            "{self.pointer} ({self.size} bytes) allocated at "
            "{self.file}:{self.line}".format(self=self)
        )


class Allocation(object):
    def __init__(self, ptrinfo):
        self.ptrinfo = ptrinfo
        self.action = "malloc"

    def __repr__(self):
        return "Allocation({self.ptrinfo})".format(self=self)


class Deallocation(object):
    def __init__(self, ptrinfo):
        self.ptrinfo = ptrinfo
        self.action = "free"

    def __repr__(self):
        return "Deallocation({self.ptrinfo})".format(self=self)


class Reallocation(object):
    def __init__(self, old_ptrinfo, new_ptrinfo):
        self.old_ptrinfo = old_ptrinfo
        self.new_ptrinfo = new_ptrinfo
        self.action = "realloc"

    def __repr__(self):
        return "Reallocation({self.old_ptrinfo} => {self.new_ptrinfo})".format(
            self=self,
        )


@ffi.callback("void* (size_t)")
def malloc(size):
    result = native.malloc(size)
    ptrinfo = PointerInfo(result, size)
    memory_sequence.append(Allocation(ptrinfo))
    memory_map[result] = ptrinfo
    memory_usage['sum'] += size
    memory_usage['current'] += size
    memory_usage['max'] = max(memory_usage['max'], memory_usage['current'])
    memory_usage['allocs'] += 1

    return result


@ffi.callback("void* (void*, size_t)")
def realloc(ptr, size):
    result = native.realloc(ptr, size)
    old_ptrinfo = memory_map[ptr]
    new_ptrinfo = PointerInfo(result, size)
    memory_sequence.append(Reallocation(old_ptrinfo, new_ptrinfo))

    if result != ffi.NULL:
        del memory_map[ptr]
        memory_map[result] = new_ptrinfo
        memory_usage['sum'] += size
        memory_usage['current'] += (size - old_ptrinfo.size)
        memory_usage['max'] = max(memory_usage['max'], memory_usage['current'])
        memory_usage['reallocs'] += 1

    return result


@ffi.callback("void (void*)")
def free(ptr):
    ptrinfo = memory_map[ptr]
    memory_sequence.append(Deallocation(ptrinfo))
    result = native.free(ptr)
    memory_usage['deallocs'] += 1
    memory_usage['current'] -= memory_map[ptr].size
    del memory_map[ptr]

    return result


@ffi.callback("void* (void*, const char*, unsigned int)")
def mark_pointer(ptr, file, line):
    memory_map[ptr].mark_pointer(file, line)

    return ptr


def register_memory_functions():
    """
    Instructs libfreelan to use the Python memory functions.

    Use only for debugging as it has a huge performance cost.
    """
    native.freelan_register_memory_functions(
        malloc,
        realloc,
        free,
        ffi.NULL,
    )
    native.freelan_register_memory_debug_functions(
        mark_pointer,
    )


def unregister_memory_functions():
    """
    Instructs libfreelan to use the default memory functions.
    """
    native.freelan_register_memory_debug_functions(
        ffi.NULL,
    )
    native.freelan_register_memory_functions(
        ffi.NULL,
        ffi.NULL,
        ffi.NULL,
        ffi.NULL,
    )
