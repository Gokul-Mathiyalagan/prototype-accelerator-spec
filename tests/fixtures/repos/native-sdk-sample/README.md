# Scoring SDK sample (fixture)

A small, synthetic repo with vendored native libraries, used to test Prototype Accelerator's native-artifact extraction. It isn't real company code.

- `vendor/tinymath/`: MIT-licensed C library, with source; `make -C vendor/tinymath` builds `lib/libtinymath.so` (Linux) or `lib/libtinymath.dylib` (macOS).
- `vendor/secretsauce/`: a prebuilt, proprietary scoring library. Its license forbids reverse engineering.
- `python/sdk_client.py`: calls both libraries through `ctypes`.

Run `python3 python/sdk_client.py` on Linux, or `python3 -m pytest python/tests`.
