# Builds lib/libtinymath.so on Linux, lib/libtinymath.dylib on macOS.
CC ?= cc
CFLAGS ?= -O2 -fPIC -Wall
UNAME := $(shell uname -s)
ifeq ($(UNAME),Darwin)
LIB := lib/libtinymath.dylib
LDFLAGS := -dynamiclib
else
LIB := lib/libtinymath.so
LDFLAGS := -shared -Wl,--build-id=none
endif

$(LIB): src/tinymath.c include/tinymath.h
	mkdir -p lib
	$(CC) $(CFLAGS) -Iinclude $(LDFLAGS) -o $@ src/tinymath.c
