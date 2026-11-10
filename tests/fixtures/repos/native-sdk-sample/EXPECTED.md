# Expected findings: native-sdk-sample

What a correct extraction of this fixture should find, per playbook, for golden tests (T-107, T-109, T-114). Paths are relative to this folder. Each evidence entry is `path:line` and a snippet that appears on that line; `tests/extract/test_fixture_repos.py` checks every one.

Format: `- **<finding id>** · <confidence> · <claim> Evidence: \`path:line\` "snippet"; ...`

## repo-overview

- **repo-overview.layout** · high · A Python client in `python/` calls two vendored native libraries in `vendor/` through ctypes. Evidence: `python/sdk_client.py:12` "ctypes.CDLL"; `README.md:5` "vendor/tinymath/"

## native-artifacts

- **native-artifacts.inventory** · high · Two ELF shared libraries are vendored: `vendor/tinymath/lib/libtinymath.so` (with source) and `vendor/secretsauce/lib/libsecretsauce.so` (no source). Evidence: `python/sdk_client.py:12` "lib{name}{SUFFIX}"
- **native-artifacts.tinymath-license** · high · tinymath is MIT-licensed, so C8 allows Ghidra analysis. Evidence: `vendor/tinymath/LICENSE:5` "Permission is hereby granted"
- **native-artifacts.tinymath-exports** · high · tinymath exports `tm_add`, `tm_mul`, `tm_clamp` and `tm_version`; the code calls `tm_clamp` and `tm_version`. Evidence: `vendor/tinymath/include/tinymath.h:4` "int tm_add"; `python/sdk_client.py:28` "tinymath.tm_clamp(raw"
- **native-artifacts.secretsauce-calls** · high · The code calls `ss_score` (declared in the vendor header) to score segments. Evidence: `vendor/secretsauce/include/secretsauce.h:5` "int ss_score"; `python/sdk_client.py:27` "secretsauce.ss_score("
- **native-artifacts.secretsauce-license** · high · secretsauce's license forbids reverse engineering, so C8 skips it: no Ghidra analysis, and it goes to `unknowns.md`. Evidence: `vendor/secretsauce/LICENSE:7` "You may not reverse engineer"
- **native-artifacts.build** · medium · tinymath builds from source with `make`, to `.so` on Linux and `.dylib` on macOS. Evidence: `vendor/tinymath/Makefile:10` "-shared"

## Not included

`ui-architecture`, `design-system`, `api-surface`, `auth-sso`, `data-access`, `ai-llm`, `backend-architecture`, `observability` and `delivery` have nothing to examine here, so `extract prepare` should leave them out.

## Planted sensitive data

None.

## Unknowns

These should go to `unknowns.md`: what `libsecretsauce.so` does internally (license forbids analysis), and how the vendor versions are updated.
