# Sources for fixture binaries

`secretsauce.c` builds the prebuilt `vendor/secretsauce/lib/libsecretsauce.so` in `native-sdk-sample`. It lives outside the fixture repo so the fixture looks like a real vendored, source-less binary. Rebuild both libraries with `build_native.sh` (runs in Docker, writes into the fixture).
