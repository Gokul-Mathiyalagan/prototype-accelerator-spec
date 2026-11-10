#!/usr/bin/env bash
# Build a fake download mirror and a matching versions.lock for install.sh tests.
#   make_fakes.sh MIRROR_DIR LOCK_FILE
# The mirror mimics the real URL paths (host stripped), so ACCEL_MIRROR=file://MIRROR_DIR
# exercises the same download, checksum and extract code as a real install.
set -euo pipefail
mirror="$1"
lock="$2"
work="$(mktemp -d)"
node_v=24.22.1
jdk_v=21.0.13+9
ghidra_v=12.1.4
ghidra_zip=ghidra_12.1.4_PUBLIC_20260921.zip

sha() { sha256sum "$1" | awk '{print $1}'; }

# Fake node and npm. npm records each call and emulates ci, build and verify:ghidra.
fake_node() {
  local dir="$work/node-v$node_v-$1"
  mkdir -p "$dir/bin"
  cat >"$dir/bin/node" <<EOF
#!/usr/bin/env bash
if [ "\${1:-}" = "--version" ]; then echo v$node_v; exit 0; fi
printf 'node %s\n' "\$*"
printf 'GHIDRA_INSTALL_DIR=%s\n' "\${GHIDRA_INSTALL_DIR:-}"
printf 'REA_GHIDRA_STARTUP_TIMEOUT_MS=%s\n' "\${REA_GHIDRA_STARTUP_TIMEOUT_MS:-}"
printf 'LC_ALL=%s\n' "\${LC_ALL:-}"
EOF
  cat >"$dir/bin/npm" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s|HUSKY=%s|cache=%s\n' "$*" "${HUSKY:-}" "${npm_config_cache:-}" >>npm-calls.log
case "$*" in
  ci*) mkdir -p node_modules ;;
  "run build") touch build-done ;;
  "run verify:ghidra")
    for line in $(seq 1 60); do echo "verify output line $line"; done
    [ -z "${FAKE_VERIFY_FAIL:-}" ] || { echo "fake verify failure"; exit 1; }
    [ -d "$GHIDRA_INSTALL_DIR/Ghidra" ] || { echo "no ghidra"; exit 1; }
    "$JAVA_HOME/bin/java" -version ;;
  *) echo "fake npm: unexpected $*"; exit 1 ;;
esac
EOF
  chmod 755 "$dir/bin/node" "$dir/bin/npm"
  mkdir -p "$mirror/dist/v$node_v"
  tar -czf "$mirror/dist/v$node_v/node-v$node_v-$1.tar.gz" -C "$work" "node-v$node_v-$1"
}

# Fake Temurin JDK. macOS archives put the JDK under Contents/Home.
fake_jdk() {
  local platform="$1" os="$2" arch="$3" root home
  root="$work/jdk-$platform/jdk-$jdk_v"
  home="$root"
  [ "$os" = mac ] && home="$root/Contents/Home"
  mkdir -p "$home/bin"
  printf 'JAVA_VERSION="%s"\n' "${jdk_v%%+*}" >"$home/release"
  printf '#!/usr/bin/env bash\necho "openjdk version %s"\n' "${jdk_v%%+*}" >"$home/bin/java"
  chmod 755 "$home/bin/java"
  local dir="$mirror/adoptium/temurin21-binaries/releases/download/jdk-$jdk_v"
  mkdir -p "$dir"
  tar -czf "$dir/OpenJDK21U-jdk_${arch}_${os}_hotspot_${jdk_v/+/_}.tar.gz" -C "$work/jdk-$platform" "jdk-$jdk_v"
}

# Fake Ghidra, with decompiler "source" whose Makefile records how it was called.
fake_ghidra() {
  local root="$work/ghidra_${ghidra_v}_PUBLIC"
  mkdir -p "$root/Ghidra/Features/Decompiler/src/decompile/cpp"
  printf 'application.name=Ghidra\napplication.version=%s\n' "$ghidra_v" >"$root/Ghidra/application.properties"
  # shellcheck disable=SC2016 # $(ARCH_TYPE) and $(OSDIR) are make variables
  printf 'ghidra_opt:\n\tprintf "%%s %%s\\n" "$(ARCH_TYPE)" "$(OSDIR)" >make-args\n\tprintf "#!/bin/sh\\n" >ghidra_opt\n' \
    >"$root/Ghidra/Features/Decompiler/src/decompile/cpp/Makefile"
  local dir="$mirror/NationalSecurityAgency/ghidra/releases/download/Ghidra_${ghidra_v}_build"
  mkdir -p "$dir"
  (cd "$work" && zip -qr "$dir/$ghidra_zip" "ghidra_${ghidra_v}_PUBLIC")
}

# Fake REA: a bare git repo at the mirror's morluto/rea path.
fake_rea() {
  local src="$work/rea"
  mkdir -p "$src/scripts"
  printf '{"name": "rea-agents", "version": "0.0.0-fake"}\n' >"$src/package.json"
  printf '// fake REA entry point\n' >"$src/scripts/rea.mjs"
  git -C "$src" init -q
  git -C "$src" add -A
  git -C "$src" commit -qm "fake REA"
  mkdir -p "$mirror/morluto"
  git clone -q --bare "$src" "$mirror/morluto/rea"
  git -C "$src" rev-parse HEAD
}

fake_node linux-x64
fake_node darwin-arm64
fake_jdk linux-x64 linux x64
fake_jdk darwin-arm64 mac aarch64
fake_ghidra
rea_commit="$(fake_rea)"

jdk_dir="$mirror/adoptium/temurin21-binaries/releases/download/jdk-$jdk_v"
cat >"$lock" <<EOF
schema_version: 1
rea:
  repo: https://github.com/morluto/rea
  commit: $rea_commit
node:
  version: "$node_v"
  sha256:
    darwin-arm64: $(sha "$mirror/dist/v$node_v/node-v$node_v-darwin-arm64.tar.gz")
    darwin-x64: eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
    linux-x64: $(sha "$mirror/dist/v$node_v/node-v$node_v-linux-x64.tar.gz")
jdk:
  vendor: temurin
  version: "$jdk_v"
  sha256:
    darwin-arm64: $(sha "$jdk_dir/OpenJDK21U-jdk_aarch64_mac_hotspot_${jdk_v/+/_}.tar.gz")
    darwin-x64: eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
    linux-x64: $(sha "$jdk_dir/OpenJDK21U-jdk_x64_linux_hotspot_${jdk_v/+/_}.tar.gz")
ghidra:
  version: $ghidra_v
  url: https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${ghidra_v}_build/$ghidra_zip
  sha256: $(sha "$mirror/NationalSecurityAgency/ghidra/releases/download/Ghidra_${ghidra_v}_build/$ghidra_zip")
EOF
rm -rf "$work"
