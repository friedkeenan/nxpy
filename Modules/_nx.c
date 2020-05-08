#define PY_SSIZE_T_CLEAN
#include <Python.h>

#ifdef __SWITCH__

#include <switch.h>

#else

static unsigned char g_tls[0x100];

#endif

static PyObject *nx_armGetTls(PyObject *self, PyObject *args) {
    #ifdef __SWITCH__
    
    return PyLong_FromUnsignedLongLong((unsigned long long) armGetTls());

    #else

    return PyLong_FromUnsignedLongLong((unsigned long long) g_tls);

    #endif
}

static PyObject *nx_svcSendSyncRequest(PyObject *self, PyObject *args) {
    #ifdef __SWITCH__

    Handle tmp_h;

    if (!PyArg_ParseTuple(args, "I", &tmp_h))
        return NULL;

    Result rc = svcSendSyncRequest(tmp_h);

    return PyLong_FromUnsignedLong(rc);

    #else

    return PyLong_FromUnsignedLong(0);

    #endif
}

static PyObject *nx_svcConnectToNamedPort(PyObject *self, PyObject *args) {
    #ifdef __SWITCH__

    const char *name;

    if (!PyArg_ParseTuple(args, "s", &name))
        return NULL;

    Handle tmp_h;
    Result rc = svcConnectToNamedPort(&tmp_h, name);

    return Py_BuildValue("II", rc, tmp_h);

    #else

    return Py_BuildValue("II", 0, 1);

    #endif
}

static PyObject *nx_svcSleepThread(PyObject *self, PyObject *args) {
    #ifdef __SWITCH__

    s64 nano;

    if (!PyArg_ParseTuple(args, "L", &nano))
        return NULL;

    svcSleepThread(nano);

    #endif

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef NxMethods[] = {
    {"armGetTls", nx_armGetTls, METH_VARARGS},
    {"svcSendSyncRequest", nx_svcSendSyncRequest, METH_VARARGS},
    {"svcConnectToNamedPort", nx_svcConnectToNamedPort, METH_VARARGS},
    {"svcSleepThread", nx_svcSleepThread, METH_VARARGS},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef nxmodule = {
    PyModuleDef_HEAD_INIT,
    "_nx",
    NULL,
    -1,
    NxMethods
};

PyMODINIT_FUNC PyInit__nx() {
    return PyModule_Create(&nxmodule);
}