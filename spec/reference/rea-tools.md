# REA tools reference

REA (Reverse Engineer Anything) at the commit pinned in `setup/versions.lock` (`b2f3dc8`, package `rea-agents` 6.8.0): what its MCP server and CLI offer, and what T-008 observed when it used them on the fixture repos. Extraction code (T-105, T-106, T-107, T-112) should start here.

## How REA is reached

- **MCP (Copilot, Claude Code, Python):** `setup/rea-mcp.sh` loads `~/.accel/rea.env` and runs `node scripts/rea.mjs mcp`, a stdio server. The server identifies as `rea` 6.8.0 and offers 253 tools.
- **Python (batch mode):** the official MCP Python SDK (`mcp` 1.29) works as a stdio client. `tests/extract/test_rea_spike.py` starts the server with `docker run -i … bash setup/rea-mcp.sh`, so it runs on any host with Docker.
- **CLI:** `package.json` maps both `rea` and `rea-agents` to `scripts/rea.mjs`, so `node scripts/rea.mjs <command>` and `rea <command>` are the same program with the same subcommands (`node scripts/rea.mjs --help` prints `Usage: rea <command>`). The CLI's subcommand names are the MCP tool names in kebab case, plus a few CLI-only ones such as `doctor`.

## Reply shape

Every analysis tool returns one **Evidence** record as JSON text:

- `evidence_id`, plus `subject` (name, SHA-256, `local_path`, `format`, `architecture`);
- `provider` (`id`, `name`, `version`) and `operation`;
- `normalized_result`, which holds the facts, plus `coverage` (`status`, `examined`, `total`, `next_offset`, `exhausted`), `limitations` (always present; read them) and `unknowns`.

`detail: "summary"` (the default for most tools) returns a compact *analysis view* that points at the retained full record (`parent_evidence_id`); `detail: "complete"` returns everything inline. Errors come back as `isError: true` with `{"error": {"code", "category", "message", …}}`, for example `provider_timeout`.

## Observed on the fixtures

All calls below ran over MCP from Python against REA in a Linux container (Debian, Temurin 21.0.13, Ghidra 12.1.4). Inputs were the fixture's built web bundle, a HAR recorded from the running fixture app (`tests/fixtures/har/fastapi-react-sso.har`), and `native-sdk-sample`'s permissive `libtinymath.so`.

| Tool | Input | Result | Time |
|---|---|---|---|
| `inspect_web_network_capture` | `capture_path` (absolute), `format: "har"` | 5 of 5 records decoded. Each record keeps the reported request and response (method, URL, status, headers, body text) and its JSON pointer (`/log/entries/N`). | 0.6 s |
| `inspect_native_exports` | `path` (absolute) to an ELF or PE | ELF amd64, 4 of 4 exports (`tm_add`, `tm_mul`, `tm_clamp`, `tm_version`) with address, size, type and binding. No analysis engine needed. | 0.02 s |
| `open_binary` | `path`, `provider_id: "ghidra"` | Binds the target: `{"kind": "executable", "format": "elf", "architecture": "x86_64"}` | 0.3 s |
| `analyze_function` | `procedure: "tm_clamp"`, `detail: "complete"` | Ghidra pseudocode matching the C source, assembly (6 instructions), CFG, value flow, callers and callees, and references. | 18 s (cold) |
| `inspect_analysis_settings` | (none) | REA's effective deadlines and heaps, including `REA_GHIDRA_STARTUP_TIMEOUT_MS=900000` from `rea.env`. Read-only, needs no target. `/accel-setup` uses it as its proof of life. | < 1 s |
| `analyze_javascript_application` | `input_path` to the built `dist/` folder | Evidence returned, but the one JS file (165 KB minified, React included) was `unavailable`: the default 1024 MiB worker heap ran out after 112 s. With `max_heap_mb: 4096`, it hit the 300 s per-source deadline instead. See below. | 112 s and up |

### Limits and gotchas

- **Paths are absolute and local to the machine running REA.** In Docker, mount the inputs and pass container paths.
- **Ghidra is slow on the first query.** The first `analyze_function` imports and analyzes the binary (18 s for a 15 KB library). Later queries in the same session are fast. Ghidra metadata edits are discarded when the session closes unless `REA_GHIDRA_CHECKPOINT_DIR` is set.
- **Static JavaScript analysis of minified bundles is expensive.** On a small React bundle, the default heap ran out, and a 4 GB heap hit the 5-minute per-source deadline. The reply still succeeds (`isError: false`) with the source marked `unavailable` and 0 routes, so **check `route_inventory.sources[].status`, not just `isError`**. For the extraction stages, prefer source-map-enabled builds, raise `max_heap_mb` and `analysis_timeout_ms` deliberately, or rely on static analysis of the source plus HAR runtime evidence. This is the spec's known REA limit ("context exhaustion on large bundles").
- **HAR inspection never fetches URLs**, and it drops known authentication headers and cookies (`limitations` says so). Pass `sensitive_values` to exclude other literals.
- **Linux needs a UTF-8 locale for Ghidra paths.** `setup/rea-mcp.sh` and `install.sh verify` set `LC_ALL=C.UTF-8` when none is set (T-005).
- **Browser tools** (`analyze_web_bundle`, `inspect_web_page`, `capture_browser_scenario` and others) need a Chrome DevTools endpoint or a browser executable. They weren't exercised here; T-105 and T-106 own the runtime capture.

## Regenerating the tables

The tables below are generated from a live server. After moving the REA pin, capture `tools/list` (any MCP client) and `node scripts/rea.mjs --help`, then run:

```bash
python scripts/generate_rea_reference.py tools-list.json cli-help.txt
```

`tests/extract/test_rea_spike.py` (live) fails if the server's tool names differ from the table.

<!-- generated:start -->

### MCP tools (253)

| Tool | Required inputs | Read-only | Summary |
|---|---|---|---|
| `act_on_build_computer` | computer_id, action |  | Act on a running build computer with screenshot, click, drag, scroll, type, type_secret, key, wait, reset; actions can change app state. |
| `address_name` | (none) |  | Resolve the primary analyzed name at a code or data address. |
| `address_to_file_offset` | address |  | Map one provider-normalized virtual address to its original nonnegative file offset. |
| `analyze_function` | procedure |  | Inspect one native function by symbol or provider-returned address. |
| `analyze_javascript_application` | input_path |  | Build a static application graph from a local ASAR or extracted JavaScript app without executing it. |
| `analyze_swift_types` | (none) |  | Classify analyzed Swift procedure names into classes, structs, enums, protocols and extensions using manglings or same-address symbol alias… |
| `analyze_web_bundle` | cdp_endpoint, target_id |  | Recover a static chunk graph, route/endpoint candidates, vendor fingerprints and page-declared WebMCP metadata from JavaScript on one selec… |
| `annotate_native_function` | procedure |  | Atomically rename one function and/or change entry comments, verify readback, and return its refreshed complete dossier. |
| `batch_decompile` | (none) |  | Decompile an explicit list of procedure symbols/addresses in input order, with one provider read active per batch. |
| `binary_overview` | (none) |  | Summarize the bound document, complete provider-inventory procedure/string row counts, and segments when supported. |
| `binary_session` | (none) |  | Inspect current target, provider capabilities, analysis and server identity without starting analysis. |
| `build_call_path` | functions, start, goal |  | Build every shortest direct-callee path from complete analyze_function Evidence supplied inline or by exact retained-evidence references. |
| `build_reconstruction_obligation_ledger` | evidence_bundle, reviewed_obligations, manifest |  | Build a deterministic reconstruction-obligation ledger from an authenticated Evidence bundle, reviewed obligations and an explicit reconstr… |
| `capture_adb_screen` | serial, output_directory |  | Capture one frame of the device screen as a PNG (`screencap -p` through exec-out, no device-side file) into a caller-selected output direct… |
| `capture_browser_scenario` | browser, start_url, actions |  | Drive a browser scenario when passive observation cannot exercise the app. |
| `capture_electron_scenario` | executable_path, application_path |  | Launch and exercise an owned Electron app when passive CDP/Inspector observation cannot answer the question. |
| `capture_native_ui_scenario` | pid, window_id, steps |  | Interact with one exact native app window through selected-element press, scroll, AXValue text entry and bounded waits. |
| `capture_process_scenario` | executable |  | Run a caller-selected command under a PTY and return process capture Evidence and unknowns. |
| `capture_web_screenshot` | cdp_endpoint, target_id |  | Capture the current visible viewport of one configured page as an inline, content-addressed PNG artifact. |
| `check_build_task` | computer_id, task |  | Evaluate saved-state task checks or run a screen_judge through its configured model endpoint on a running exported app. |
| `close_binary` | (none) |  | Release the active engine and owned resources while retaining investigation Evidence and complete Unknown history in memory. |
| `close_build_computer` | computer_id |  | Tear down a build computer and discard its state, cancelling its active call and refusing queued calls. |
| `close_frida_session` | session_id |  | Unload session scripts and attempt to detach REA's Frida session. |
| `close_gdb_session` | session_id |  | Close the owned GDB process after verifying the inferior state. |
| `close_rizin_debug_session` | session_id |  | Close the REA-owned Rizin debugger only after verifying no inferior remains or detaching one with a verified caller-selected TTY output sin… |
| `collect_adb_bugreport` | serial, output_directory |  | Collect one device-generated bugreport archive (`adb bugreport`) into a caller-selected output directory, digesting the zip. |
| `comment` | (none) |  | Read the regular analysis comment at an explicit address, or the current cursor where supported. |
| `compare_application_versions` | left, right |  | Compare two authenticated JavaScript Application Graph versions, supplied inline or by exact retained reference. |
| `compare_artifacts` | left, right |  | Compare complete artifact inventories by occurrence path, content identity, metadata and graph relations; root . |
| `compare_bundles` | left_bundle_path, right_bundle_path |  | Compare two canonical Evidence bundles by exact record membership, explicit one-to-one observation pairs, and complete residual-unknown rev… |
| `compare_functions` | left, right |  | Compare two explicit analyze_function Evidence records or exact retained session references across identity, exact provider text, calls, re… |
| `compare_javascript_export_shapes` | left_module_path, left_export_name, right_module_path, right_export_name, left, right |  | Compare static return-property shapes for one exact module/export on each authenticated JavaScript Application Graph, inline or retained. |
| `compare_managed_members` | left, right |  | Compare two authenticated inspect_managed_members Evidence records, inline or retained, using unique exact type/name/signature/CIL or decod… |
| `compare_process_captures` | left, right |  | Compare compatible process captures, inline or by {kind:"retained-evidence",evidence_id}, across terminal, interaction, lifecycle, process,… |
| `compare_source_to_bundle` | reference, application |  | Map committed historical source to an authenticated JavaScript Application Graph. |
| `compare_static_and_observed_endpoints` | application, capture |  | Compare static JavaScript endpoints with requests recorded in HAR Evidence, supplied inline or retained; acquires no files, targets or URLs. |
| `compare_wasm_interfaces` | left, right, scope |  | Compare typed core WASM import/export names, kinds and exact signatures from two authenticated inspect_wasm_artifact Evidence records. |
| `compare_web_captures` | (none) |  | Compare two passive page inspections or two recorded browser scenarios. |
| `compare_web_screenshots` | before, after |  | Compare two self-verifying PNG screenshot artifacts with local pixel metrics. |
| `correlate_static_and_runtime` | static_comparisons, runtime_comparisons, mappings |  | Evaluate every explicit caller-declared hypothesis between static and runtime comparison Evidence supplied inline or by exact retained-evid… |
| `current_address` | (none) |  | Return Hopper's current cursor address for the selected document. |
| `current_document` | (none) |  | Return the document currently selected by REA's Hopper bridge. |
| `current_procedure` | (none) |  | Return the analyzed procedure containing Hopper's current cursor. |
| `cutter_command` | session_id, expected_generation, command |  | Run one arbitrary Rizin command in a selected Cutter session; it may persist edits or execute plugin effects. |
| `decode_android_resources` | path |  | Decode APK resources with apktool d --no-src: readable manifest, version/SDK facts, string resources/locales and decoded file count. |
| `decode_interface_builder` | (none) |  | Decode compiled storyboard and nib archives inside the active Apple app bundle, including keyed property lists and NIBArchive object tables… |
| `decode_signal_recording` | path, decoders |  | Decode a saved logic/signal recording with an explicitly selected sigrok decoder stack, channels and options. |
| `decompile_all` | output_directory |  | Export pseudocode for all or selected analyzed functions to a directory; returns a manifest/index, with bodies kept in files. |
| `decompile_jeb_item` | item_address, item_kind |  | Decompile one type or method to engine pseudo-code using its decompiler (Dalvik, Java, or native). |
| `demangle_swift` | symbols |  | Demangle an ordered list of single-line Swift symbols without Hopper. |
| `discover_webmcp_tools` | cdp_endpoint, target_id |  | Passively inventory every page-registered WebMCP tool and its complete structural input-schema summary using the experimental CDP WebMCP do… |
| `evaluate_reconstruction_coverage` | coverage, boundary_id | yes | Check evidence-backed reconstruction coverage for one named boundary. |
| `execute_rizin_command` | path, command |  | Run one caller-selected Rizin command on a local artifact. |
| `export_build_environment` | computer_id, tasks, directory |  | Export the stopped capture and given tasks as an agentenv app bundle, seeded at seed. |
| `export_environment_bundle` | source, output_directory |  | Write an agent environment bundle from capture_browser_scenario Evidence or HAR inspect_web_network_capture Evidence to an absent absolute… |
| `export_evidence_bundle` | path |  | Atomically write the session's deterministic Evidence bundle to the requested local path. |
| `export_web_scripts` | capture_path, output_directory |  | Export JavaScript bytes already retained in one local inspect_web_page or capture_browser_scenario JSON capture (normalized result or compl… |
| `extract_artifact` | (none) |  | Write all or selected regular files from the active supported archive to an absent absolute output_root, or a fresh temporary directory if… |
| `extract_firmware` | path, output_directory |  | Extract selected local firmware bytes with Unblob 26.6.x (verified with 26.6.4) into an absent output directory. |
| `find_changed_behavior` | comparisons |  | Aggregate validated process, artifact, and function comparison Evidence, supplied inline or by exact retained-evidence references from this… |
| `find_xrefs_to_name` | name |  | Find references to an exact analyzed symbol name: resolves the name, then returns its address and referencing addresses. |
| `frida_session_status` | session_id |  | Read observed Frida session state on each call. |
| `gdb_console` | session_id, command |  | Run one unrestricted command in a persistent GDB session; commands can run shell, change target state, access files and network. |
| `gdb_session_status` | session_id | yes | Return the observed lifecycle state and bounded recent MI records and process diagnostics for one persistent REA GDB session; truncation an… |
| `get_call_graph` | address |  | Traverse the provider-observed caller or callee graph from one symbol/address, returning canonical-address nodes with per-node outcomes. |
| `get_evidence_bundle` | (none) | yes | Read retained Evidence and tracked questions without rerunning providers. |
| `get_navigation_context` | (none) |  | Return the selected document, current address, and containing/current procedure in one provider-neutral result. |
| `get_objc_classes` | (none) |  | Find Objective-C class labels, optionally by literal substring. |
| `get_objc_protocols` | (none) |  | Discover and deduplicate Objective-C and Swift protocol labels. |
| `goto_address` | address |  | Move Hopper's GUI cursor to a mapped address and return the observed cursor address. |
| `guided_workflows` | action | yes | List or render REA's existing guided workflows. |
| `identify_flutter_build` | path |  | Identify a Flutter app's build facts by pure parsing: observed Dart snapshot hashes from lib/<abi>/libapp.so, per-ABI library digests, the… |
| `import_evidence_bundle` | path |  | Read the JSON bundle at the supplied local path, validate every Evidence ID and canonical manifest, then atomically merge it. |
| `import_managed_reconstruction` | decompiler, methods, static_members |  | Import decompiler-produced managed reconstruction against authenticated inspect_managed_members Evidence supplied inline or by exact retain… |
| `inline_comment` | (none) |  | Read the inline instruction comment at an explicit address, or the current cursor where supported. |
| `inspect_adb_client` | (none) |  | Inspect the caller-selected adb client: resolved binary, version, and install path. |
| `inspect_adb_device` | serial |  | Inspect one device's build identity through a fixed `getprop` whitelist: Android and SDK versions, security patch, fingerprint, product ide… |
| `inspect_adb_display` | serial |  | Read physical and override size/density from `wm size` and `wm density`. |
| `inspect_adb_package` | serial, package |  | Inspect installed-package versions, install times, installer, user id, flags, and requested-permission count through read-only `dumpsys pac… |
| `inspect_adb_window` | serial |  | Report the window manager's focus declarations with display context, original lines and explicit summary status. |
| `inspect_address_context` | address |  | Inspect one explicit reproducible address for its analyzed name, containing procedure, regular and inline comments, and matching bookmarks. |
| `inspect_analysis_settings` | (none) | yes | Inspect REA's editable runtime admission sizes, deadlines and worker heaps, their bounds, launch values and application points. |
| `inspect_analysis_view` | source, view |  | Read summaries, selected facts, or pages from completed Evidence without rerunning analysis. |
| `inspect_android_class` | path, class_name |  | Inspect one exact Android class's methods, fields, inner classes, DEX prototypes and encoded static final values without generating source. |
| `inspect_android_jni_bindings` | path |  | Link an APK's DEX native declarations to Java_* exports and static JNINativeMethod candidates by ABI and exact library occurrence, without… |
| `inspect_android_method` | path, class_name, method_name |  | Decompile one Android method, with explicit overload_index when names collide and smali fallback when needed. |
| `inspect_android_package` | path |  | Inspect APK package/SDK/permission declarations, decoded manifest, static components and class/resource counts without executing it or veri… |
| `inspect_api_contract` | path |  | Inspect declared APIs in local OpenAPI JSON or GraphQL SDL without a session, network requests or target execution. |
| `inspect_apk_signature` | path |  | Inspect declared APK v1/v2/v3/v3.1 signers, certificate fingerprints, digests, SDK ranges, rotation lineage and source stamp without execut… |
| `inspect_apktool_client` | (none) |  | Inspect the caller-selected apktool launcher: resolved command, selection source, and version. |
| `inspect_apple_ips` | path |  | Inspect a local Apple .ips crash report for process, exception/termination, thread, image and lossless register facts with deterministic cl… |
| `inspect_artifact` | (none) |  | Inventory the active archive, app package, firmware container or supported packaged executable without running it. |
| `inspect_asset_catalog` | (none) |  | Inspect compiled Assets.car metadata in an active Apple app bundle. |
| `inspect_binary_hardening` | path |  | Inspect static hardening declarations in a local ELF, PE or Mach-O, including every universal slice. |
| `inspect_binary_layout` | path |  | Inspect static ELF section/segment, symbol, relocation, linkage and mitigation facts with artifact SHA-256 Evidence, without launching the… |
| `inspect_byte_entropy` | path |  | Inspect Shannon byte entropy for one explicit local file offline, without execution, extraction or external tools. |
| `inspect_dart_aot` | path |  | Inspect one APK ABI's legacy split VM/isolate Dart AOT snapshot without executing it. |
| `inspect_desktop_application` | path |  | Identify runtime candidates and next probes in a local desktop app directory from bounded listings, headers and metadata. |
| `inspect_devicetree` | path |  | Inspect an explicit local flattened devicetree blob (FDT v16/v17) without execution or external tools. |
| `inspect_electron_fuses` | path |  | Inspect packaged Electron fuse bytes in one local macOS app bundle, Electron Framework binary, Windows PE executable, or Linux ELF executab… |
| `inspect_electron_page` | cdp_endpoint, target_id |  | Passively inspect one Electron file page by supplying its loopback CDP endpoint and target ID. |
| `inspect_elf_notes` | path |  | Inspect one explicit local ELF32/ELF64 image's PT_NOTE program headers and SHT_NOTE sections without executing it or opening a disassembler. |
| `inspect_elf_unwind_ranges` | path |  | Inspect ELF32/64 .eh_frame and .eh_frame_hdr for paged FDE function ranges, associated CIE facts, LSDA/personality pointers, symbol matches… |
| `inspect_erlang_beam` | path |  | Inspect an Erlang BEAM IFF file without executing bytecode or requiring Erlang. |
| `inspect_evm_interface` | path, encoding |  | Infer interface candidates from explicit local flat EVM bytecode using bundled EVMole 0.9.3/WASM; select raw or hex encoding. |
| `inspect_firmware_regions` | path |  | Inspect signature candidates in a local firmware file with Binwalk 3.1.x (verified with 3.1.0). |
| `inspect_go_binary` | path |  | Read embedded Go compiler, module, dependency/replacement and build-setting metadata from a local ELF, PE or selected Mach-O slice without… |
| `inspect_gpu_code_objects` | path |  | Inspect CUDA/HIP code objects in local ELF/PE, fatbins, CUBIN, PTX or Clang HIP bundles without GPU tools or target execution. |
| `inspect_il2cpp_metadata` | path |  | Inspect Unity IL2CPP metadata versions 24/27/29/31/39, optionally linking a selected 64-bit little-endian Mach-O/PE/ELF binary without exec… |
| `inspect_jeb_client` | (none) |  | Inspect the running JEB client serving MCP: engine version, GUI or headless mode, and startup time. |
| `inspect_kernel_build_config` | path |  | Inspect a local Linux kernel image (vmlinux, raw arm64 Image, x86 bzImage/zImage or configs.ko) for the version/builder/compiler banner and… |
| `inspect_kernel_module` | path |  | Inspect an uncompressed local ELF32/64 ET_REL Linux kernel module for ordered .modinfo entries, symbol CRCs, module/export/init/exit sectio… |
| `inspect_keyed_archive` | (none) |  | Inspect one Foundation NSKeyedArchiver plist in the active app bundle as original object-table nodes, class descriptors, named roots, and U… |
| `inspect_macho` | (none) |  | Inspect Mach-O slices, load commands, linkage, build metadata, segments/sections and permissions without launching Hopper. |
| `inspect_managed_artifact` | (none) |  | Inspect PE/CLI identity, classification and metadata inventories from an explicit path or selected managed target without loading or execut… |
| `inspect_managed_members` | (none) |  | Inspect PE/CLI types, members, signatures, CIL hashes/instruction tuples, exception regions, static calls, field accesses and loaded #US st… |
| `inspect_managed_native_boundaries` | (none) |  | Inspect PE/CLI ModuleRef, ImplMap/PInvoke declarations, CLI native-header indicators, and non-IL method implementation flags without loadin… |
| `inspect_model_artifact` | path |  | Inspect GGUF v2/v3 or safetensors metadata and tensor declarations without loading weights or running inference. |
| `inspect_native_api` | procedure |  | Inspect recovered parameter/return boundary types and jump-table dispatch for one native function selected by symbol or address. |
| `inspect_native_data_type` | (none) |  | Inspect one recovered type by exact database category path or defined typed data address. |
| `inspect_native_dispatch_metadata` | (none) |  | Inspect analyzed Objective-C class/method and Swift mangled symbols, with optional exact Objective-C import-pointer binding facts from the… |
| `inspect_native_exports` | path |  | Inspect PE/ELF exports without execution or an analysis engine; use inspect_macho for Mach-O. |
| `inspect_native_initializers` | path |  | List declared initializer/finalizer functions in a local ELF32/64 or selected Mach-O slice without execution. |
| `inspect_native_instruction` | address |  | Inspect bytes, mnemonic, operand tokens, flow and typed incoming/outgoing references at one code/data address. |
| `inspect_native_load_image` | (none) |  | Inspect provider source digests, loaded mappings, relocations, entries and register context without executing or changing the target. |
| `inspect_packet_capture` | path, fields |  | Extract caller-selected TShark fields from a saved packet capture, with display filters, decode-as rules and pass mode preserved. |
| `inspect_packet_fields` | (none) |  | Find protocols or field definitions registered in installed TShark 4.x. |
| `inspect_pcap_capture` | path |  | Summarize a saved pcap/pcapng snapshot: exact packet count, SHA-256, IP endpoints, DNS questions/addresses, TLS SNI, protocols and HTTP URI… |
| `inspect_pcap_client` | (none) |  | Inspect the caller-selected tshark and capinfos binaries: selected commands, selection sources, and versions. |
| `inspect_pe_certificates` | path |  | Inspect a local PE32/PE32+ certificate directory without executing it or verifying signatures. |
| `inspect_pe_imports` | path |  | Inspect local PE32/PE32+ standard and delay-load imports without execution. |
| `inspect_pe_load_config` | path |  | Inspect PE32/PE32+ TLS callbacks and sized load configuration without executing the image. |
| `inspect_pe_resources` | path |  | Inspect a local PE32/PE32+ resource tree without execution: type/name/language identities, empty branches, UTF-16 names, payload RVA/file r… |
| `inspect_playwright_trace` | path |  | Inspect a local Playwright v10 trace ZIP offline, without browser replay or requests to recorded URLs. |
| `inspect_plist` | (none) |  | Parse Info.plist from an open binary or bundle-resource session, or select path within that session. |
| `inspect_python_pyc` | path |  | Inspect local CPython 3.7–3.13 .pyc headers and nested code objects without executing bytecode, invoking Python or recovering source. |
| `inspect_recorded_crash` | path |  | Inspect a saved Linux ELF64 little-endian amd64/AArch64 core without launching its target or attaching to a live PID. |
| `inspect_rust_binary` | path |  | Read the embedded cargo-auditable crate dependencies of a local ELF, PE or selected Mach-O slice without running it or requiring Rust. |
| `inspect_signal_decoders` | (none) |  | List installed sigrok decoder IDs/names, or supply an exact decoder ID to inspect its channel/option help. |
| `inspect_signature` | (none) |  | Inspect the selected Mach-O slice's signing identity, hashes, authorities, requirement, entitlements and hardened-runtime state from a dige… |
| `inspect_sqlite_database` | path |  | Inspect a local SQLite snapshot and sibling WAL without modifying them. |
| `inspect_v8_code_cache` | path |  | Inspect a local bytenode .jsc or compatible V8 code-cache container as static bytes, without V8, bytenode, child processes or decompilation. |
| `inspect_wasm_artifact` | path |  | Validate and inspect local WASM with caller-supplied WABT 1.0.42, without executing it or fetching dependencies. |
| `inspect_web_event_listeners` | cdp_endpoint, target_id, selector |  | Inspect listeners registered directly on the first main-document CSS match in one selected CDP page. |
| `inspect_web_network_capture` | capture_path, format |  | Inspect a saved local HAR 1.2, mitmproxy, Fiddler SAZ or supported aioquic qlog capture without contacting recorded URLs. |
| `inspect_web_page` | cdp_endpoint, target_id |  | Passively inspect one selected page target through CDP without evaluating JavaScript, navigating, clicking, closing, or mutating the page. |
| `inspect_windows_shortcut` | path |  | Inspect a local Windows Shell Link (.lnk) without resolving or executing its target, COM, or network access. |
| `inspect_with_objdump` | operation |  | Inspect a local artifact with caller-selected objdump and GNU-style arguments; the executable implementation/version is unverified. |
| `install_adb_package` | serial, apk_path |  | Install one local APK on the device (`adb install [-r]`), recording the APK's host digest and byte size. |
| `instrument_with_frida` | mode, source_kind |  | Run caller-authored Frida JavaScript against a selected process for one observation window, then detach. |
| `list_adb_devices` | (none) |  | List attached devices exactly as `adb devices -l` reports them: serial, state, transport, model metadata, and an inferred emulator/physical… |
| `list_adb_directory` | serial, device_path |  | List the immediate children of one absolute device directory, including hidden entries: names, kinds, permissions, owner, group, sizes, dat… |
| `list_adb_features` | serial |  | List the device's declared hardware and software features (`pm list features`) for device fingerprinting. |
| `list_adb_packages` | serial |  | List installed packages on one device with each base APK's device path, optionally scoped to third-party or system packages. |
| `list_adb_processes` | serial |  | List running processes exactly as `ps -A` reports them: user, pid, ppid, rss, state, and name. |
| `list_adb_services` | serial |  | List the device's binder services with their interfaces (`service list`). |
| `list_architectures` | (none) |  | List thin/universal Mach-O slices with file offsets, sizes, alignment, coverage and native-tool provenance. |
| `list_bookmarks` | (none) |  | List every bookmark in the selected Hopper document as address and name pairs; unnamed bookmarks retain a null name. |
| `list_browser_targets` | cdp_endpoint |  | List pages exposed by one loopback Chrome DevTools Protocol endpoint, optionally filtered by exact origin. |
| `list_cutter_sessions` | (none) |  | Find live REA bridge sessions in Cutter and return document identity and bridge-directory security status. |
| `list_documents` | (none) |  | List provider program or document identities. |
| `list_electron_targets` | cdp_endpoint |  | List every Electron file:// page target from a selected loopback CDP endpoint. |
| `list_frida_devices` | (none) |  | List Frida devices currently available to this host, optionally connecting to the caller-selected remote Frida endpoint. |
| `list_frida_processes` | (none) |  | List processes observed on a selected Frida device or caller-supplied remote endpoint. |
| `list_javascript_runtime_targets` | inspector_endpoint |  | List every eligible Node/Electron V8 Inspector target from an explicit literal-loopback endpoint. |
| `list_jeb_units` | (none) |  | List project units by stable unit path and type, with optional wildcard filter, parent restriction, and pagination. |
| `list_names` | (none) |  | List every analyzed memory and external symbol as address/value pairs. |
| `list_procedures` | (none) |  | List every analyzed procedure as address/value pairs after provider analysis. |
| `list_segments` | (none) |  | List segments or memory blocks using exclusive end addresses. |
| `list_strings` | (none) |  | List every provider-reported string object or candidate, or filter to one address, as address/value pairs with encoding, terminator status,… |
| `list_unknowns` | (none) | yes | List tracked questions' current revisions in deterministic ID order, with exact status/severity/domain filters. |
| `load_frida_script` | session_id, source_kind |  | Load caller-supplied JavaScript into a Frida session. |
| `mark_build_checkpoint` | computer_id, name |  | Checkpoint the running capture under a unique name; returns acknowledged counts and up to 10 changed files. |
| `match_native_functions` | left, right |  | Pair two retained list_procedures inventories by unique exact symbols, then unique identical observed bytes. |
| `measure_build_task` | bundle, task, model, budget_usd |  | Measure how hard an exported bundle's task is for a model: run it in fresh agentenv computers on this host, each solve the bundle's own ste… |
| `next_address` | (none) |  | Return the next analyzed object address after an explicit address or current cursor. |
| `observe_javascript_runtime` | inspector_endpoint, target_id |  | Passively observe loaded-script and execution-context metadata on one loopback Node/Electron V8 Inspector target, selected by inspector_end… |
| `observe_native_calls` | breakpoints |  | Launch the active Mach-O under LLDB and record selected function/Objective-C method entries; the owned process is killed at max_events or d… |
| `observe_native_ui` | pid, window_id |  | Observe one already-running native app window by PID/window ID, bound to the active Mach-O target. |
| `observe_web_execution` | cdp_endpoint, target_id |  | Instrument one selected CDP page for a finite, externally driven precise coverage window. |
| `observe_web_session` | cdp_endpoint, target_id |  | Arm a CDP observation window of the requested duration while the user operates the page. |
| `open_binary` | path |  | Open a validated local artifact or analysis database and bind its analysis provider. |
| `open_bundle_resources` | path |  | Open a local app bundle for read-only plist, Interface Builder, asset catalog, and keyed archive inspection without resolving or inventing… |
| `open_jeb_project` | path |  | Open or create a JEB project from an artifact file or existing .jdb2 database on the engine host. |
| `prev_address` | (none) |  | Return the previous analyzed object start before an explicit address or current cursor. |
| `procedure_address` | procedure |  | Resolve an unambiguous procedure symbol name or provider-normalized address to its canonical entry address. |
| `procedure_assembly` | procedure |  | Return assembly for one analyzed procedure identified by symbol or hexadecimal address. |
| `procedure_callees` | procedure |  | Return the provider's resolved direct callees for one procedure identified by symbol or address. |
| `procedure_callers` | procedure |  | Return the provider's resolved direct callers for one procedure identified by symbol or address. |
| `procedure_info` | procedure |  | Return provider metadata for one procedure identified by symbol or address: entrypoint, signature, locals, size, block count, and complete… |
| `procedure_pseudo_code` | procedure |  | Decompile one analyzed procedure by symbol or provider-normalized address. |
| `procedure_references` | procedure |  | Return incoming or outgoing reference edges for one procedure. |
| `project_android_application_graph` | inventory_evidence |  | Build a static Android application inventory from the authenticated nested inventory Evidence returned by inspect_artifact for an APK. |
| `project_apple_application_graph` | inventory_evidence |  | Build a static Apple application inventory from the authenticated nested inventory Evidence returned by inspect_artifact for an IPA, .app d… |
| `project_harmony_application_graph` | inventory_evidence |  | Build a static HarmonyOS inventory from the authenticated nested inventory Evidence returned by inspect_artifact for a HAP, HSP or App Pack. |
| `project_managed_application_graph` | (none) |  | Project authenticated managed artifact, member, and native-boundary Evidence, supplied inline or by exact retained reference, into the prov… |
| `pull_adb_file` | serial, device_path, output_directory |  | Pull one absolute device path (a database, shared-preferences XML, or any readable file) into a caller-selected output directory, digesting… |
| `pull_adb_package` | serial, package, output_directory |  | Pull one installed package's complete APK set (base plus every split, as `pm path` reports) from the device into a caller-selected output d… |
| `push_adb_file` | serial, local_path, device_path |  | Push one local file to an absolute device path. |
| `read_adb_logcat` | serial |  | Read a bounded dump of the device log (`logcat -d -t`) for one buffer, optionally restricted to a process id. |
| `read_adb_setting` | serial, namespace, key |  | Read one settings value (`settings get`) from the system, secure, or global namespace. |
| `read_bytes` | address |  | Read analyzed bytes from one provider-normalized virtual address. |
| `read_function_instructions` | procedure |  | Return every raw instruction for one analyzed procedure. |
| `read_guidance_section` | locator | yes | Retrieve a section selected by search_guidance from the installed REA guidance bundle. |
| `reconcile_javascript_runtime` | static_layers, runtime_observations |  | Reconcile verified static JavaScript application graphs with existing passive web/Electron CDP, passive V8 Inspector, or provider-owned act… |
| `record_build_consent` | computer_id, kind, subject, words |  | Record a consent the person gave, in their own words, after you asked them: kind licence when they accepted a licence the app or its instal… |
| `record_unknown` | question, severity, domain, required_authority, required_confidence, required_environment, recommended_probes, relationships |  | Create one deterministic residual unknown and immutable mutation evidence. |
| `recover_javascript_sources` | path, output_directory |  | Recover readable modules from local UTF-8 JavaScript bundles into an absent output_directory, without executing application code. |
| `reset_investigation` | (none) |  | Discard retained Evidence and Unknown revision history, including engine replay/source bindings, while keeping a healthy active engine open. |
| `resolve_adb_packages` | serial, query |  | Find installed packages by case-insensitive package-name substring and return each base APK device path. |
| `resolve_containing_procedure` | address |  | Resolve an arbitrary address, including an interior instruction or exact external entry, to its provider-analyzed containing procedure. |
| `resolve_native_call_targets` | address |  | Resolve one explicit static call site using typed provider call references. |
| `resume_frida_session` | session_id |  | Resume the process created by a paused Frida spawn session. |
| `rizin_debug_command` | session_id, command |  | Run one unrestricted command in a persistent Rizin debugger; it can access target state, plugins, shell, files and network. |
| `rizin_debug_session_status` | session_id |  | Return observed lifecycle state and bounded recent NUL-framed output and process diagnostics for one Rizin debugger session; truncation fie… |
| `search_android_classes` | path, query |  | Search complete top-level decompiler class-name rows in an explicit local APK by case-sensitive substring. |
| `search_bytes` | pattern |  | Find masked byte signatures in initialized analyzed memory. |
| `search_guidance` | query | yes | Find installed REA workflow guidance by query words. |
| `search_procedures` | pattern |  | Find analyzed procedures by literal name (default) or regex, including accepted secondary names. |
| `search_strings` | pattern |  | Find provider-reported strings by literal text (default) or regex. |
| `set_address_name` | address, name |  | Assign an analyst name to one mapped hexadecimal address and report whether the native edit succeeded and exact readback matched. |
| `set_addresses_names` | names |  | Assign analyst names to multiple mapped addresses in one call and return per-address edit/readback success booleans. |
| `set_bookmark` | address |  | Create or update a bookmark at a mapped hexadecimal address and report readback success. |
| `set_comment` | address, comment |  | Write a regular analysis comment at a hexadecimal address and return whether readback matched. |
| `set_inline_comment` | address, comment |  | Write an inline instruction comment at a hexadecimal address and return whether readback matched. |
| `start_adb_activity` | serial, action |  | Start an intent with `am start -W`: one action, optional data URI, optional explicit component, and up to 16 typed extras (string, boolean,… |
| `start_adb_app` | serial, package |  | Start one installed app's resolved launcher activity with `am start -W -n`. |
| `start_build_capture` | computer_id |  | Launch the app under capture on a request-built computer and return its open-window screenshot. |
| `start_build_computer` | source |  | Start a local agentenv computer, installing/downloading app packages as needed; returns computer_id and a first screenshot. |
| `start_frida_session` | mode |  | Attach Frida to one selected process or spawn one selected target. |
| `start_gdb_session` | (none) |  | Start a persistent caller-supplied GDB session and return its session ID. |
| `start_rizin_debug_session` | path, inferior_tty |  | Start a persistent Rizin debugger for one selected target/backend. |
| `stop_adb_app` | serial, package |  | Force-stop every process of one package (`am force-stop`), ending a dynamic-analysis run. |
| `stop_build_capture` | computer_id |  | Close the captured app and finish its capture. |
| `trace_android_references` | path, class_name |  | Trace incoming static using nodes to an exact Android class or selected method overload. |
| `trace_application_feature` | seed, application |  | Trace a typed literal seed through every reachable part of an authenticated JavaScript Application Graph supplied as inline Evidence or exa… |
| `trace_call_path` | start |  | Resolve start and optional goal symbols or addresses, then trace direct callers or callees. |
| `trace_dylib_resolution` | (none) |  | Trace how dyld would resolve each Mach-O dylib load for the active Mach-O, or for every executable in the active .app bundle (the main app,… |
| `trace_feature` | query |  | Search procedure/string inventories for the complete literal query, then query xrefs at matched start addresses. |
| `trace_javascript_semantics` | application, query |  | Trace static JavaScript data-flow, direct call/return, and closure relations from inline application Evidence or an exact same-session reta… |
| `trace_native_ui_action` | action |  | Trace one unique compiled UI action, object ID, native symbol or exact function address through authored connections, encoded or symbolized… |
| `trace_native_values` | procedure |  | Trace static value dependencies across resolved calls from one native procedure: high-p-code def-use, constants, operators, memory/branch o… |
| `trace_web_module_imports` | manifest_path, script_index |  | Resolve native ES imports/re-exports from one script in a local export_web_scripts manifest. |
| `trace_web_source_location` | manifest_path, script_index, source_map, generated_position |  | Map one generated position in an exported script through a caller-paired local source map, verifying manifest/script/map byte identities. |
| `uninstall_adb_package` | serial, package |  | Request package removal for user 0 (`adb shell pm uninstall --user 0`) without data retention. |
| `unload_frida_script` | session_id, script_id |  | Unload one caller-selected Frida script from a live session. |
| `unset_bookmark` | address |  | Remove the bookmark at a mapped hexadecimal address and return whether it is absent. |
| `update_analysis_settings` | changes |  | Atomically set or reset editable runtime defaults for new work. |
| `update_unknown` | unknown_id, expected_revision, status, severity, supporting_evidence_ids, contradicting_evidence_ids, required_authority, required_confidence, required_environment, recommended_probes, relationships, resolution |  | Append a full-state revision to one tracked question, with immutable mutation Evidence. |
| `verify_managed_native_boundaries` | managed_boundaries, native_observations |  | Verify managed P/Invoke/native-boundary declarations against authenticated native export or function Evidence, with inline or exact retaine… |
| `verify_reconstruction` | specification |  | Verify a finite typed behavioral and structural specification against a canonical Evidence bundle. |
| `verify_unknown_resolution` | unknown_id | yes | Check a tracked question's current resolution against bundled Evidence, required authority/confidence/environment and revision integrity. |
| `xrefs` | (none) |  | Return analyzed references to a code or data address. |

### CLI commands (194)

| Command | Summary |
|---|---|
| `address-to-file-offset` | Map one analysis address to a file offset; memory bytes may differ and ranges may not be contiguous |
| `analyze` | Get an overview of an app |
| `analyze-javascript-application` | Statically reconstruct a local JavaScript/Electron application |
| `analyze-web-bundle` | Capture and statically analyze a page bundle, defaulting to the selected target origin |
| `annotate-native-function` | Edit function annotations and return refreshed analysis |
| `build-reconstruction-obligation-ledger` | Generate a deterministic Evidence-backed reconstruction obligation ledger page |
| `capabilities` | List provider capabilities and side effects |
| `capture-adb-screen` | Capture one screen frame as a digested PNG |
| `capture-browser-scenario` | Run one bounded Playwright browser scenario and return Evidence |
| `capture-desktop-application` | Launch a Linux desktop application, watch it while it is used and record its windows and state at checkpoints read from stdin |
| `capture-electron-scenario` | Run one owned Electron scenario with cancellable actions |
| `capture-native-ui-scenario` | Run declarative AX actions or waits in one exact native application window |
| `capture-process` | Capture one caller-selected process scenario |
| `capture-web-screenshot` | Capture one visible page viewport within the supplied origin scope |
| `collect-adb-bugreport` | Collect and digest one device-generated bugreport archive |
| `compare` | Compare two canonical Evidence bundles by record identity; use compare-artifacts for artifact inventory contents |
| `compare-application-versions` | Compare two authenticated JavaScript Application Graph versions |
| `compare-artifacts` | Compare two artifact inventories, including FIT and legacy uImage firmware components, named as {left, right}: complete Evidence or {kind:"… |
| `compare-javascript-export-shapes` | Compare exact static JavaScript export return shapes without execution |
| `compare-managed-members` | Compare managed PE/CLI member inventories by exact declared type, name, and signature; names alone never form a match |
| `compare-process-captures` | Compare two process capture Evidence JSON files |
| `compare-source-to-bundle` | Compare historical source (inline graph or reference {kind:file,path}) with authenticated application Evidence. |
| `compare-static-and-observed-endpoints` | Compare static JavaScript endpoints and HAR Evidence JSON offline; --detail summary with --evidence_output saves full facts for selected in… |
| `compare-wasm-interfaces` | Compare core WASM interfaces from two exact inspection Evidence records |
| `compare-web-captures` | Compare two normalized passive captures or recorded browser scenarios |
| `compare-web-screenshots` | Compare two self-verifying PNG artifact JSON values |
| `cutter-command` | Execute one Rizin command in a selected live Cutter instance |
| `debug-with-gdb` | Run one unrestricted GDB console command in an ephemeral MI session; provide an inferior TTY so a live target can be safely detached |
| `debug-with-rizin` | Run one unrestricted Rizin debugger command in an ephemeral session |
| `decode-android-resources` | Decode one APK's manifest, metadata, and string resources with apktool |
| `decode-interface-builder` | Decode compiled storyboard and nib archives from an app bundle |
| `decode-signal-recording` | Decode an existing signal recording with caller-supplied sigrok |
| `decompile` | Read one part of an app as code. |
| `decompile-all` | Write every function's pseudocode into a directory and return a manifest |
| `decompile-jeb-item` | Decompile one JEB type or method to engine pseudo-code |
| `demangle-swift` | Demangle Swift symbols without Hopper |
| `describe-desktop-application-task` | Describe how a desktop application capture's files changed from the seed checkpoint to the end, with suggested checks and a task draft to c… |
| `discover-webmcp-tools` | Passively discover page-declared WebMCP tools |
| `doctor` | Check whether REA is ready |
| `environment-build` | Build an agent environment bundle from a recorded capture in one offline step: inspect a HAR (or read capture Evidence), project the enviro… |
| `environment-compare` | Compare an environment with probe captures of the application it was captured from: each probe is one call sequence recorded against a fres… |
| `environment-export` | Export an environment manifest and its capture Evidence as an agent environment bundle folder the agentenv framework runs with agent-env run |
| `environment-serve` | Serve an environment manifest as an agent environment over streamable HTTP until SIGINT or SIGTERM: read tools, and write tools whose effec… |
| `evaluate-reconstruction-coverage` | Evaluate inline fail-closed reconstruction coverage |
| `evidence-export` | Validate and atomically export canonical Evidence JSON |
| `evidence-import` | Validate a standalone Evidence bundle and count records and Unknown revisions; does not retain them in an MCP session |
| `execute-rizin-command` | Execute one Rizin command against a local artifact |
| `export-desktop-application` | Export a desktop application capture folder as an agentenv computer app bundle: class, env.toml, skill and seed |
| `export-web-scripts` | Export retained website scripts into an absent directory for static JavaScript analysis |
| `extract-artifact` | Extract all or selected regular artifact contents safely; DMG extraction is unavailable |
| `extract-firmware` | Extract selected firmware bytes and return verified files and provenance |
| `function` | Analyze one complete function with evidence. |
| `guidance` | Search or read the installed REA workflow guidance |
| `guided-workflows` | List or render REA's existing guided workflows |
| `identify-flutter-build` | Identify a Flutter build's Dart snapshot hash and engine facts by pure APK parsing |
| `import-managed-reconstruction` | Import decompiler-produced managed reconstruction against exact static member evidence |
| `import-reference-source` | Import a source tree as historical reference only |
| `inspect` | Inspect an app overview with evidence |
| `inspect-adb-client` | Inspect the caller-selected adb client without contacting devices |
| `inspect-adb-device` | Inspect one device's build identity through a fixed getprop whitelist |
| `inspect-adb-display` | Report the display's declared size and density |
| `inspect-adb-package` | Inspect one installed package's version, installer, and flags through dumpsys |
| `inspect-adb-window` | Report the window manager's current focus declarations |
| `inspect-analysis-view` | Project a selected view of completed Evidence JSON for a supported analysis operation. |
| `inspect-android-class` | Inspect one exact APK class's member inventory |
| `inspect-android-jni-bindings` | Link raw DEX native declarations to static JNI export/table candidates without executing the APK |
| `inspect-android-method` | Decompile one APK method with explicit overload selection |
| `inspect-android-package` | Inspect APK declarations and decoded manifest without executing it |
| `inspect-api-contract` | Inspect local OpenAPI JSON or GraphQL SDL declarations and field bindings offline |
| `inspect-apk-signature` | Inspect declared APK signing schemes, signers and content digests |
| `inspect-apktool-client` | Inspect the caller-selected apktool launcher without decoding anything |
| `inspect-apple-ips` | Inspect an Apple .ips crash report without executing a target |
| `inspect-artifact` | Inspect one artifact and return all available observations and next probes |
| `inspect-asset-catalog` | Inspect compiled Apple asset catalog metadata |
| `inspect-binary-hardening` | Inspect ELF, PE, and Mach-O hardening without executing the image |
| `inspect-binary-layout` | Inspect binary file/linked layout without executing the selected object |
| `inspect-byte-entropy` | Inspect file-wide and block byte entropy without executing the file |
| `inspect-dart-aot` | Inspect one ABI's Dart AOT snapshot: sections, headers, and the string pool |
| `inspect-desktop-application` | Identify desktop runtime candidates from bounded directory and header observations |
| `inspect-desktop-application-state` | Read a desktop application capture folder into the application's state: roles, typed JSON views of each version and kinds of change |
| `inspect-devicetree` | Inspect a flattened devicetree blob without executing it |
| `inspect-electron-fuses` | Inspect packaged Electron fuse bytes without launching the application |
| `inspect-electron-page` | Passively inspect one Electron file page |
| `inspect-elf-notes` | Inspect ELF PT_NOTE and SHT_NOTE identities without executing the image |
| `inspect-elf-unwind-ranges` | Inspect ELF unwind function ranges without executing the image |
| `inspect-erlang-beam` | Inspect Erlang BEAM atoms, exports, imports and Code header without executing bytecode |
| `inspect-evidence-bundle` | Inspect a local Evidence bundle completely, as discovery metadata, as a page of selected complete records, or as direct-link and retained-c… |
| `inspect-evm-interface` | Infer interface candidates from explicit local EVM bytecode |
| `inspect-firmware-regions` | Inspect firmware signature candidates without extracting them |
| `inspect-go-binary` | Inspect embedded Go compiler, modules, build settings and optional static (ptr, len) string literals without target execution |
| `inspect-gpu-code-objects` | Inspect embedded CUDA/HIP targets and selected static kernel metadata |
| `inspect-il2cpp-metadata` | Inventory IL2CPP global-metadata.dat names, owners and string literals, optionally linking method addresses from the native binary |
| `inspect-jeb-client` | Inspect the running JEB MCP client without opening a target |
| `inspect-kernel-build-config` | Inspect a Linux kernel image's version banner and embedded build config without executing it |
| `inspect-kernel-module` | Inspect Linux kernel module metadata without executing the module |
| `inspect-keyed-archive` | Inspect a Foundation keyed archive as an object-reference graph |
| `inspect-macho` | Run inspect_macho without launching Hopper |
| `inspect-managed-artifact` | Inspect PE/CLI identity without loading target code |
| `inspect-managed-members` | Inspect PE/CLI metadata members, signatures, CIL anchors, and ldstr string literals without loading target code |
| `inspect-managed-native-boundaries` | Inspect PE/CLI PInvoke and native implementation boundary declarations without loading target code |
| `inspect-model-artifact` | Inspect GGUF or safetensors headers without loading model weights |
| `inspect-native-api` | Reconstruct one native function API boundary with evidence. |
| `inspect-native-data-type` | Inspect one recovered database type or typed data object. |
| `inspect-native-dispatch-metadata` | Inspect typed Objective-C and Swift dispatch metadata |
| `inspect-native-exports` | Inspect a PE or ELF image's export table without executing it |
| `inspect-native-initializers` | List ELF and Mach-O initializer and finalizer functions without executing the image |
| `inspect-native-instruction` | Inspect a code or data address, its containing Ghidra listing object, and typed incoming references where supported |
| `inspect-native-load-image` | Inspect native load observations and supported snapshot verification |
| `inspect-packet-capture` | Inspect an existing packet capture with caller-supplied TShark |
| `inspect-packet-fields` | Search installed TShark protocol and field definitions |
| `inspect-pcap-capture` | Inspect one pcap/pcapng capture: endpoints, DNS, TLS SNI, and protocol distribution |
| `inspect-pcap-client` | Inspect the caller-selected tshark and capinfos binaries without reading a capture |
| `inspect-pe-certificates` | Inspect PE Authenticode certificate table identities without verifying signatures |
| `inspect-pe-imports` | Inspect PE import and delay-load table identities without executing the image |
| `inspect-pe-load-config` | Inspect PE TLS callbacks and load configuration without executing the image |
| `inspect-pe-resources` | Inspect PE resource identities, payload ranges, hashes and icon-group relationships |
| `inspect-playwright-trace` | Inventory local saved Playwright v10 trace ZIP events offline without launching a browser |
| `inspect-plist` | Parse app plist metadata without launching Hopper |
| `inspect-python-pyc` | Inspect a supported CPython 3.7–3.13 pyc header and marshal code objects without executing bytecode |
| `inspect-recorded-crash` | Inspect supplied core registers/signals and optional debugger mapping evidence |
| `inspect-rust-binary` | Inspect an embedded cargo-auditable Rust dependency list without target execution |
| `inspect-signal-decoders` | Search installed sigrok decoders or selected decoder help |
| `inspect-signature` | Run inspect_signature without launching Hopper |
| `inspect-sqlite-database` | Inspect SQLite schema and optional ordinary-table rows from a local snapshot |
| `inspect-v8-code-cache` | Inspect a V8 code cache header and its embedded printable byte patterns without executing it |
| `inspect-wasm-artifact` | Inspect an explicit local WASM artifact with WABT |
| `inspect-web-event-listeners` | Inspect native listener source locations on the first main-document CSS match |
| `inspect-web-network-capture` | Inspect retained HAR, native mitmproxy, Fiddler SAZ or aioquic qlog records without fetching recorded URLs |
| `inspect-web-page` | Passively inspect one page through CDP, defaulting to its current origin |
| `inspect-windows-shortcut` | Inspect a Windows Shell Link (.lnk) without resolving or executing the target |
| `inspect-with-objdump` | Inspect a local artifact using GNU-style objdump arguments and retain the selected command output as Evidence |
| `install-adb-package` | Install one local APK; --replace requests reinstall mode to keep existing app data |
| `instructions` | Read every raw instruction without decompiling. |
| `instrument-with-frida` | Run one Frida script against a selected process and detach. |
| `list-adb-devices` | List attached devices with serial, state, transport, and inferred kind |
| `list-adb-directory` | List one device directory with kinds, permissions, and sizes |
| `list-adb-features` | List the device's declared hardware and software features |
| `list-adb-packages` | List installed packages on one device with base APK device paths |
| `list-adb-processes` | List running processes exactly as ps -A reports them |
| `list-adb-services` | List the device's binder services and interfaces |
| `list-architectures` | Run list_architectures without launching Hopper |
| `list-browser-targets` | List page targets from a selected loopback CDP browser, optionally filtered by origin |
| `list-cutter-sessions` | List live Cutter instances connected through the REA Python plugin bridge |
| `list-electron-targets` | List local file pages exposed by the selected Electron CDP endpoint |
| `list-frida-devices` | List local Frida devices and an optional remote endpoint |
| `list-frida-processes` | List processes visible through a Frida device |
| `list-javascript-runtime-targets` | List Node/Electron V8 Inspector targets |
| `list-jeb-units` | List JEB project units by path and type with optional filter |
| `list-objdump-architectures` | Capture the selected objdump command response to -i |
| `match-native-functions` | Match two observed native function inventories without executing targets |
| `observe-javascript-runtime` | Passively observe one exact Node/Electron Inspector target |
| `observe-native-calls` | Launch a Mach-O under LLDB and record entries into selected functions or Objective-C methods |
| `observe-native-ui` | Observe one already-running native application window by PID and window ID |
| `observe-web-execution` | Observe precise page execution; resets counters and temporarily disables optimization |
| `observe-web-session` | Observe user-driven page navigation during a chosen window |
| `open-jeb-project` | Open or create a JEB project from an artifact or .jdb2 database |
| `procedure-references` | Inspect incoming or outgoing references for one native procedure. |
| `project-android-application-graph` | Project authenticated APK inventory Evidence into an Android application graph |
| `project-apple-application-graph` | Project authenticated IPA or macOS app inventory Evidence into an Apple application graph |
| `project-harmony-application-graph` | Project authenticated HarmonyOS HAP, HSP, or App Pack inventory Evidence into an application graph |
| `project-managed-application-graph` | Project authenticated managed static Evidence into an application graph |
| `providers` | List configured analysis providers |
| `pull-adb-file` | Pull one device file to a local copy with a SHA-256 digest |
| `pull-adb-package` | Pull one installed package's complete APK set with SHA-256 digests |
| `push-adb-file` | Push one local file to the device; refuses existing targets without --overwrite |
| `read-adb-logcat` | Read a bounded dump of the device log for one buffer |
| `read-adb-setting` | Read one settings value from system, secure, or global |
| `read-bytes` | Read provider memory bytes; Ghidra memory may include loader fixups and differ from file bytes |
| `reconcile-javascript-runtime` | Reconcile static application and passive runtime Evidence JSON |
| `recover-javascript-sources` | Recover readable JavaScript modules with source provenance and verified files |
| `resolve-adb-packages` | Find installed packages by case-insensitive name substring |
| `resolve-native-call-targets` | Resolve one static native call site |
| `search` | Search every analyzed string or procedure name. |
| `search-android-classes` | Search APK class names; empty query inventories all classes |
| `search-bytes` | Find masked bytes; unbounded searches skip unloaded blocks and overlays |
| `setup` | Configure agent integrations and optional analysis providers |
| `start-adb-activity` | Start an intent with am start (action, URI, component, extras) |
| `start-adb-app` | Start one installed app by resolving and launching its launcher activity |
| `stop-adb-app` | Force-stop every process of one package |
| `trace` | Trace a literal feature through analyzed references. |
| `trace-android-references` | Trace APK using nodes for a defined class/method or an externally invoked DEX method |
| `trace-application-feature` | Trace a typed seed through authenticated application Evidence JSON |
| `trace-dylib-resolution` | Trace dyld load-path resolution for a Mach-O or every executable in an app bundle |
| `trace-javascript-semantics` | Trace bounded static semantic relations through authenticated application Evidence |
| `trace-native-ui-action` | Trace a compiled UI action selector to its native handler and direct callees |
| `trace-native-values` | Trace bounded native def-use and call dependencies |
| `trace-web-module-imports` | Trace one captured script's native imports to URLs and captured source candidates |
| `trace-web-source-location` | Trace one retained script position through an explicitly selected local source map |
| `uninstall` | Remove REA-owned agent configuration and skill files |
| `uninstall-adb-package` | Uninstall one package and its data from the device |
| `update` | Update this REA installation and verify the installed release |
| `validate-browser-scenario` | Validate one browser scenario without launching or attaching to a browser |
| `verify-managed-native-boundaries` | Verify managed P/Invoke declarations against authenticated native Evidence |
| `xrefs` | List bounded, untyped references to an analyzed address. |

<!-- generated:end -->
