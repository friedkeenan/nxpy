#ifndef _CTYPES_DLFCN_H_
#define _CTYPES_DLFCN_H_

#ifdef __cplusplus
extern "C" {
#endif /* __cplusplus */

#if !defined(MS_WIN32) && !defined(__SWITCH__)

#include <dlfcn.h>

#ifndef CTYPES_DARWIN_DLFCN

#define ctypes_dlsym dlsym
#define ctypes_dlerror dlerror
#define ctypes_dlopen dlopen
#define ctypes_dlclose dlclose
#define ctypes_dladdr dladdr

#endif /* !CTYPES_DARWIN_DLFCN */

#endif /* !MS_WIN32 && !__SWITCH__*/

#ifdef __cplusplus
}
#endif /* __cplusplus */
#endif /* _CTYPES_DLFCN_H_ */
