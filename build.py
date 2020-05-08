import os
import sys
from distutils.core import setup, Extension

dkp = os.getenv("DEVKITPRO")
if dkp is None:
    print("Please set DEVKITPRO in your environment. export DEVKITPRO=<path to>/devkitpro")
    sys.exit(1)

libnx = f"{dkp}/libnx"

nx_ext = Extension("_nx",
    include_dirs = [f"{libnx}/include"],
    #define_macros = [("__SWITCH__",)],
    #libraries = ["nx"],
    #library_dirs = [f"{libnx}/lib"],
    sources = ["Modules/_nx.c"],
)

setup(
    name = "_nx",
    ext_modules = [nx_ext],
)