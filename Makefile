ifeq ($(strip $(DEVKITPRO)),)
$(error "Please set DEVKITPRO in your environment. export DEVKITPRO=<path to>/devkitpro")
endif

export PORTLIBS_PREFIX := $(DEVKITPRO)/portlibs/switch
export PATH := $(PORTLIBS_PREFIX)/bin:$(PATH)

export ARCH := -march=armv8-a+crc+crypto -mtune=cortex-a57 -mtp=soft -fPIC -ftls-model=local-exec
export CFLAGS := $(ARCH) -O2 -ffunction-sections -fdata-sections
export CXXFLAGS := $(CFLAGS)
export CPPFLAGS := -D__SWITCH__ -I$(PORTLIBS_PREFIX)/include -isystem$(DEVKITPRO)/libnx/include
export LDFLAGS := $(ARCH) -L$(PORTLIBS_PREFIX)/lib -L$(DEVKITPRO)/libnx/lib
export LIBS := -lnx

.PHONY: all clean

all: cpython/libpython3.8.a
	$(MAKE) -C application

clean:
	$(MAKE) -C cpython clean
	@rm -f cpython/Makefile

cpython/libpython3.8.a: cpython/Makefile
	@cp Modules/_nxmodule.c cpython/Modules
	@cat Modules/Setup > cpython/Modules/Setup.local

	$(MAKE) -C cpython
	
	@rm -rf application/libs/python
	@mkdir -p application/libs/python/lib
	@cp $@ application/libs/python/lib
	@cp -r cpython/Include application/libs/python/include
	@cp cpython/pyconfig.h application/libs/python/include

cpython/Makefile:
	@echo Configuring...
	@cd cpython; \
	./configure \
		LDFLAGS="-specs=$(DEVKITPRO)/libnx/switch.specs $(LDFLAGS)" \
		CONFIG_SITE="../config.site" \
		--host=aarch64-none-elf \
		--build=$(shell ./cpython/config.guess) \
		--prefix="$(PORTLIBS_PREFIX)" \
		--disable-ipv6 \
		--disable-shared

	@echo Fixing pyconfig.h
	@for func in SETGROUPS FCHDIR FDATASYNC SYMLINK CHROOT ; do \
	  sed -i "s/#define HAVE_$$func 1/\/* #undef HAVE_$func *\//" cpython/pyconfig.h ; \
	done