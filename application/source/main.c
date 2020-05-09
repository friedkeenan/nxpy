#include <switch.h>

#include <Python.h>

int main(int argc, char **argv) {
    consoleInit(NULL);

    printf("Fuck\n");
    consoleUpdate(NULL);

    Py_NoSiteFlag = 1;
    Py_IgnoreEnvironmentFlag = 1;
    Py_NoUserSiteDirectory = 1;
    //Py_VerboseFlag += 1;

    /* Calculate absolute home dir */
    char cwd[PATH_MAX];
    getcwd(cwd, sizeof(cwd));
    /* Strip the leading sdmc: to workaround a bug somewhere... */
    char *stripped_cwd = strchr(cwd, '/');
    if (stripped_cwd == NULL) stripped_cwd = cwd;

    printf("%s\n", stripped_cwd);
    consoleUpdate(NULL);
    svcSleepThread(3e+9L);

    Py_SetPythonHome(Py_DecodeLocale(stripped_cwd, NULL));

    Py_Initialize();
    fatalThrow(0xb00b5);

    /* Print some info */
    printf("Python %s on %s\n", Py_GetVersion(), Py_GetPlatform());
    consoleUpdate(NULL);

    /* set up import path */
    PyObject *sysPath = PySys_GetObject("path");
    PyObject *path = PyUnicode_FromString("");
    PyList_Insert(sysPath, 0, path);

    consoleUpdate(NULL);

    /* ... */

    consoleUpdate(NULL);

    Py_DECREF(path); /* are these decrefs needed? Are they in the right place? */
    Py_DECREF(sysPath);

    Py_FinalizeEx();

    while (appletMainLoop()) {
        hidScanInput();
        
        u64 kDown = hidKeysDown(CONTROLLER_P1_AUTO);
        if (kDown & KEY_PLUS)
            break;
    }

    consoleExit(NULL);

    return 0;
}