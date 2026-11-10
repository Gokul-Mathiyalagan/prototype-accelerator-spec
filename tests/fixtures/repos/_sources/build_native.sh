#!/usr/bin/env bash
# Rebuild native-sdk-sample's two Linux shared libraries inside a container with gcc.
# Usage: tests/fixtures/repos/_sources/build_native.sh   (from the repo root, needs Docker)
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
MSYS_NO_PATHCONV=1 docker run --rm -v "$root:/repo" -w /repo/tests/fixtures/repos gcc:14.2.0 bash -c '
  set -euo pipefail
  make -C native-sdk-sample/vendor/tinymath CFLAGS="-O2 -fPIC -Wall -ffile-prefix-map=/repo=."
  gcc -O2 -fPIC -Wall -ffile-prefix-map=/repo=. -shared -Wl,--build-id=none \
    -Inative-sdk-sample/vendor/secretsauce/include \
    -o native-sdk-sample/vendor/secretsauce/lib/libsecretsauce.so _sources/secretsauce.c
  chown "$(stat -c %u:%g /repo)" native-sdk-sample/vendor/*/lib/*.so'
