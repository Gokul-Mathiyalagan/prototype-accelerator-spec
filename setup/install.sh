#!/usr/bin/env bash
# setup/install.sh: installs REA and its toolchain under $ACCEL_HOME (spec/02, C5).
#
#   install.sh --check [--json]     report what's installed; exit 0 if ready, 1 if not
#   install.sh install [component]  install what's missing, in order:
#                                   node jdk ghidra ghidra-arm64-decompiler rea env
#   install.sh verify               run REA's Ghidra check (npm run verify:ghidra)
#
# Exit codes: 0 ok, 1 not ready or usage error, 2 missing prerequisite this script
# can't install, 3 checksum mismatch, 4 download failed, 5 build or verify failed.
#
# Every download is checked against setup/versions.lock. ACCEL_MIRROR replaces the
# download host (never the checksum). Nothing is written outside $ACCEL_HOME, sudo is
# never used, and shell profiles are never edited.
#
# Test hooks: ACCEL_VERSIONS_LOCK points at another lock file, and ACCEL_PLATFORM
# overrides platform detection (darwin-arm64, darwin-x64 or linux-x64).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACCEL_HOME="${ACCEL_HOME:-$HOME/.accel}"
LOCK="${ACCEL_VERSIONS_LOCK:-$SCRIPT_DIR/versions.lock}"
TOOLS="$ACCEL_HOME/tools"
DOWNLOADS="$ACCEL_HOME/cache/downloads"
COMPONENTS="node jdk ghidra ghidra-arm64-decompiler rea env"
LOG_FILE=""

# ── Output and failure ─────────────────────────────────────────────────────────

log() {
  printf '%s\n' "$*" >&2
  if [ -n "$LOG_FILE" ]; then printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*" >>"$LOG_FILE"; fi
}

fail() {
  local code="$1"
  shift
  printf 'error: %s\n' "$*" >&2
  if [ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ]; then
    printf '%s error: %s\n' "$(date -u +%H:%M:%S)" "$*" >>"$LOG_FILE"
    printf -- '--- last 50 lines of %s ---\n' "$LOG_FILE" >&2
    tail -n 50 "$LOG_FILE" >&2
  fi
  exit "$code"
}

start_log() {
  mkdir -p "$ACCEL_HOME/logs"
  LOG_FILE="$ACCEL_HOME/logs/install-$(date -u +%Y%m%dT%H%M%SZ).log"
  : >>"$LOG_FILE"
}

# Run a command with its output going only to the log.
quiet() {
  if [ -n "$LOG_FILE" ]; then "$@" >>"$LOG_FILE" 2>&1; else "$@" >/dev/null 2>&1; fi
}

json_string() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\t'/\\t}"
  printf '"%s"' "$s"
}

# ── versions.lock ──────────────────────────────────────────────────────────────

# lock_get node.sha256.linux-x64 prints that value. Two-space indents, `key: value`.
lock_get() {
  local value
  if ! value="$(awk -v want="$1" '
      /^[[:space:]]*(#|$)/ { next }
      {
        match($0, /^ */); depth = RLENGTH / 2
        line = substr($0, RLENGTH + 1)
        colon = index(line, ":")
        if (colon == 0) next
        key = substr(line, 1, colon - 1)
        val = substr(line, colon + 1)
        sub(/^[[:space:]]+/, "", val); sub(/[[:space:]]+#.*$/, "", val)
        sub(/[[:space:]]+$/, "", val); gsub(/^"|"$/, "", val)
        path[depth] = key
        full = path[0]; for (i = 1; i <= depth; i++) full = full "." path[i]
        if (full == want && val != "") { print val; found = 1; exit }
      }
      END { if (!found) exit 1 }' "$LOCK")"; then
    fail 1 "$(basename "$LOCK") has no value for '$1'"
  fi
  printf '%s\n' "$value"
}

# ── Platform and prerequisites ─────────────────────────────────────────────────

detect_platform() {
  if [ -n "${ACCEL_PLATFORM:-}" ]; then
    case "$ACCEL_PLATFORM" in
      darwin-arm64 | darwin-x64 | linux-x64) printf '%s\n' "$ACCEL_PLATFORM"; return ;;
      *) fail 1 "ACCEL_PLATFORM must be darwin-arm64, darwin-x64 or linux-x64" ;;
    esac
  fi
  case "$(uname -s)-$(uname -m)" in
    Darwin-arm64) echo darwin-arm64 ;;
    Darwin-x86_64) echo darwin-x64 ;;
    Linux-x86_64 | Linux-amd64) echo linux-x64 ;;
    *) echo unsupported ;;
  esac
}

# Prints the prerequisites that are missing, space-separated.
missing_prerequisites() {
  local missing="" tool
  for tool in git curl tar unzip; do
    command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"
  done
  if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
    missing="$missing sha256sum"
  fi
  if [ "$PLATFORM" = "darwin-arm64" ]; then
    if [ "$(uname -s)" = "Darwin" ] && ! xcode-select -p >/dev/null 2>&1; then
      missing="$missing xcode-command-line-tools"
    elif ! command -v make >/dev/null 2>&1; then
      missing="$missing make"
    fi
  fi
  printf '%s\n' "${missing# }"
}

require_prerequisites() {
  local missing
  missing="$(missing_prerequisites)"
  if [ "$PLATFORM" = "unsupported" ]; then
    fail 2 "Unsupported platform $(uname -s)-$(uname -m). Use macOS (arm64 or x64) or Linux x64."
  fi
  if [ -n "$missing" ]; then
    local hint="Install them, then re-run."
    case " $missing " in
      *" xcode-command-line-tools "*) hint="Run 'xcode-select --install', then re-run." ;;
    esac
    fail 2 "Missing prerequisites: $missing. $hint"
  fi
}

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

# ACCEL_MIRROR replaces scheme and host, and keeps the path.
mirror_url() {
  if [ -n "${ACCEL_MIRROR:-}" ]; then
    local rest="${1#*://}"
    printf '%s/%s\n' "${ACCEL_MIRROR%/}" "${rest#*/}"
  else
    printf '%s\n' "$1"
  fi
}

# fetch URL FILE_NAME SHA256: download into the cache and verify; prints the path.
fetch() {
  local url dest want got
  url="$(mirror_url "$1")"
  dest="$DOWNLOADS/$2"
  want="$3"
  mkdir -p "$DOWNLOADS"
  rm -f "$dest.part"
  log "Downloading $url"
  if ! quiet curl -fL --retry 3 --retry-delay 2 --silent --show-error -o "$dest.part" "$url"; then
    rm -f "$dest.part"
    fail 4 "Download failed: $url. Check the network or proxy, or set ACCEL_MIRROR."
  fi
  got="$(sha256_of "$dest.part")"
  if [ "$got" != "$want" ]; then
    rm -f "$dest.part"
    fail 3 "Checksum mismatch for $2: expected $want, got $got. Don't retry with another file; tell your platform team."
  fi
  mv "$dest.part" "$dest"
  printf '%s\n' "$dest"
}

# replace_dir STAGED TARGET: swap a fully prepared directory into place.
replace_dir() {
  rm -rf "$2"
  mv "$1" "$2"
}

# ── Components: paths and checks ───────────────────────────────────────────────
# check_<component> sets STATUS (ok, missing or wrong_version) and DETAIL.

node_version() { lock_get node.version; }
jdk_version() { lock_get jdk.version; }

java_home() {
  case "$PLATFORM" in
    darwin-*) printf '%s\n' "$TOOLS/jdk/Contents/Home" ;;
    *) printf '%s\n' "$TOOLS/jdk" ;;
  esac
}

decompiler_path() {
  printf '%s\n' "$TOOLS/ghidra/Ghidra/Features/Decompiler/os/mac_arm_64/decompile"
}

expected_env() {
  printf 'GHIDRA_INSTALL_DIR=%q\n' "$TOOLS/ghidra"
  printf 'JAVA_HOME=%q\n' "$(java_home)"
  printf 'REA_GHIDRA_STARTUP_TIMEOUT_MS=900000\n'
  printf 'REA_GHIDRA_DECOMPILE_TIMEOUT_SECONDS=120\n'
}

check_node() {
  local want found
  want="v$(node_version)"
  if [ ! -x "$TOOLS/node/bin/node" ]; then STATUS=missing; DETAIL="not installed"; return; fi
  found="$("$TOOLS/node/bin/node" --version 2>/dev/null || true)"
  if [ "$found" = "$want" ]; then STATUS=ok; DETAIL="$found"
  else STATUS=wrong_version; DETAIL="found ${found:-unknown}, need $want"; fi
}

check_jdk() {
  local want release found
  want="$(jdk_version)"
  want="${want%%+*}"
  release="$(java_home)/release"
  if [ ! -f "$release" ]; then STATUS=missing; DETAIL="not installed"; return; fi
  found="$(sed -n 's/^JAVA_VERSION="\(.*\)"$/\1/p' "$release")"
  if [ "$found" = "$want" ]; then STATUS=ok; DETAIL="temurin $found"
  else STATUS=wrong_version; DETAIL="found ${found:-unknown}, need $want"; fi
}

check_ghidra() {
  local want props found
  want="$(lock_get ghidra.version)"
  props="$TOOLS/ghidra/Ghidra/application.properties"
  if [ ! -f "$props" ]; then STATUS=missing; DETAIL="not installed"; return; fi
  found="$(sed -n 's/^application\.version=//p' "$props" | tr -d '\r')"
  if [ "$found" = "$want" ]; then STATUS=ok; DETAIL="$found"
  else STATUS=wrong_version; DETAIL="found ${found:-unknown}, need $want"; fi
}

check_ghidra_arm64_decompiler() {
  if [ "$PLATFORM" != "darwin-arm64" ]; then STATUS=ok; DETAIL="not needed on $PLATFORM"; return; fi
  if [ -x "$(decompiler_path)" ]; then STATUS=ok; DETAIL="built"
  else STATUS=missing; DETAIL="not built"; fi
}

check_rea() {
  local want head built
  want="$(lock_get rea.commit)"
  if [ ! -d "$TOOLS/rea/.git" ]; then STATUS=missing; DETAIL="not installed"; return; fi
  head="$(git -C "$TOOLS/rea" rev-parse HEAD 2>/dev/null || true)"
  built="$(cat "$TOOLS/rea/.accel-built" 2>/dev/null || true)"
  if [ "$head" != "$want" ]; then
    STATUS=wrong_version; DETAIL="at ${head:0:7}, need ${want:0:7}"
  elif [ "$built" != "$want" ]; then
    STATUS=missing; DETAIL="checked out at ${want:0:7} but not built"
  else
    STATUS=ok; DETAIL="${want:0:7}"
  fi
}

check_env() {
  local file="$ACCEL_HOME/rea.env"
  if [ ! -f "$file" ]; then STATUS=missing; DETAIL="no $file"; return; fi
  if [ "$(cat "$file")" = "$(expected_env)" ]; then STATUS=ok; DETAIL="$file"
  else STATUS=wrong_version; DETAIL="$file is out of date"; fi
}

check_component() {
  case "$1" in
    ghidra-arm64-decompiler) check_ghidra_arm64_decompiler ;;
    *) "check_$1" ;;
  esac
}

# ── Components: installers ─────────────────────────────────────────────────────

install_node() {
  local version archive stage
  version="$(node_version)"
  archive="$(fetch "https://nodejs.org/dist/v$version/node-v$version-$PLATFORM.tar.gz" \
    "node-v$version-$PLATFORM.tar.gz" "$(lock_get "node.sha256.$PLATFORM")")"
  stage="$TOOLS/.staging-node"
  rm -rf "$stage" && mkdir -p "$stage"
  quiet tar -xzf "$archive" -C "$stage" || fail 5 "Couldn't extract $archive"
  replace_dir "$stage/node-v$version-$PLATFORM" "$TOOLS/node"
  rm -rf "$stage" "$archive"
}

install_jdk() {
  local version os arch file archive stage top
  version="$(jdk_version)"
  case "$PLATFORM" in
    darwin-arm64) os=mac; arch=aarch64 ;;
    darwin-x64) os=mac; arch=x64 ;;
    *) os=linux; arch=x64 ;;
  esac
  file="OpenJDK21U-jdk_${arch}_${os}_hotspot_${version/+/_}.tar.gz"
  archive="$(fetch "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-${version/+/%2B}/$file" \
    "$file" "$(lock_get "jdk.sha256.$PLATFORM")")"
  stage="$TOOLS/.staging-jdk"
  rm -rf "$stage" && mkdir -p "$stage"
  quiet tar -xzf "$archive" -C "$stage" || fail 5 "Couldn't extract $archive"
  top="$(find "$stage" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  [ -n "$top" ] || fail 5 "$file had no top-level folder"
  replace_dir "$top" "$TOOLS/jdk"
  rm -rf "$stage" "$archive"
}

install_ghidra() {
  local url file archive stage top
  url="$(lock_get ghidra.url)"
  file="${url##*/}"
  archive="$(fetch "$url" "$file" "$(lock_get ghidra.sha256)")"
  stage="$TOOLS/.staging-ghidra"
  rm -rf "$stage" && mkdir -p "$stage"
  quiet unzip -q "$archive" -d "$stage" || fail 5 "Couldn't extract $archive"
  top="$(find "$stage" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  [ -n "$top" ] || fail 5 "$file had no top-level folder"
  replace_dir "$top" "$TOOLS/ghidra"
  rm -rf "$stage" "$archive"
}

install_ghidra_arm64_decompiler() {
  local source_dir
  check_ghidra
  [ "$STATUS" = ok ] || fail 5 "Install ghidra before the arm64 decompiler"
  source_dir="$TOOLS/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp"
  [ -d "$source_dir" ] || fail 5 "Ghidra's decompiler source isn't at $source_dir"
  log "Building Ghidra's arm64 decompiler (a few minutes)"
  if ! (cd "$source_dir" && quiet make ghidra_opt ARCH_TYPE="-arch arm64" OSDIR=mac_arm_64); then
    fail 5 "Building the arm64 decompiler failed. Check that Xcode's command-line tools are installed."
  fi
  mkdir -p "$(dirname "$(decompiler_path)")"
  cp "$source_dir/ghidra_opt" "$(decompiler_path)"
  chmod 755 "$(decompiler_path)"
}

install_rea() {
  local repo commit dir
  repo="$(mirror_url "$(lock_get rea.repo)")"
  commit="$(lock_get rea.commit)"
  dir="$TOOLS/rea"
  check_node
  [ "$STATUS" = ok ] || fail 5 "Install node before rea"
  if [ ! -d "$dir/.git" ]; then
    rm -rf "$dir" && mkdir -p "$dir"
    quiet git -C "$dir" init -q
    quiet git -C "$dir" remote add origin "$repo"
  else
    quiet git -C "$dir" remote set-url origin "$repo"
  fi
  log "Fetching REA $commit"
  quiet git -C "$dir" fetch --depth 1 origin "$commit" ||
    fail 4 "Couldn't fetch REA from $repo. Check the network or proxy, or set ACCEL_MIRROR."
  quiet git -C "$dir" -c advice.detachedHead=false checkout -q --force FETCH_HEAD ||
    fail 5 "Couldn't check out REA $commit"
  [ "$(git -C "$dir" rev-parse HEAD)" = "$commit" ] || fail 3 "REA checkout isn't at $commit"
  rm -f "$dir/.accel-built"
  log "Building REA (npm ci, npm run build)"
  if ! (cd "$dir" && with_toolchain quiet npm ci --no-audit --no-fund); then
    fail 5 "npm ci failed for REA. See the log for the failing package."
  fi
  if ! (cd "$dir" && with_toolchain quiet npm run build); then
    fail 5 "npm run build failed for REA."
  fi
  printf '%s\n' "$commit" >"$dir/.accel-built"
}

install_env() {
  local file="$ACCEL_HOME/rea.env"
  expected_env >"$file.tmp"
  mv "$file.tmp" "$file"
}

install_component() {
  case "$1" in
    ghidra-arm64-decompiler) install_ghidra_arm64_decompiler ;;
    *) "install_$1" ;;
  esac
}

# Run a command with the pinned Node and JDK first on PATH, and with npm, git hooks
# and tool caches kept inside $ACCEL_HOME.
with_toolchain() {
  PATH="$TOOLS/node/bin:$(java_home)/bin:$PATH" \
    JAVA_HOME="$(java_home)" \
    HUSKY=0 \
    npm_config_cache="$ACCEL_HOME/cache/npm" \
    npm_config_update_notifier=false \
    XDG_CACHE_HOME="$ACCEL_HOME/cache/xdg" \
    XDG_CONFIG_HOME="$ACCEL_HOME/config" \
    "$@"
}

# ── Commands ───────────────────────────────────────────────────────────────────

command_check() {
  local json="$1" component all_ok=true missing_list="" prereqs next_action
  local names="" statuses="" details=""
  prereqs="$(missing_prerequisites)"
  for component in $COMPONENTS; do
    if [ "$PLATFORM" = "unsupported" ]; then
      STATUS=missing; DETAIL="unsupported platform"
    else
      check_component "$component"
    fi
    if [ "$STATUS" != ok ]; then
      all_ok=false
      missing_list="$missing_list $component"
    fi
    names="$names$component"$'\n'
    statuses="$statuses$STATUS"$'\n'
    details="$details$DETAIL"$'\n'
  done
  if [ "$PLATFORM" = "unsupported" ]; then
    next_action="This platform isn't supported. Use macOS (arm64 or x64) or Linux x64."
  elif [ "$all_ok" = true ]; then
    next_action=""
  elif [ -n "$prereqs" ]; then
    next_action="Install $prereqs, then run setup/install.sh install"
  else
    next_action="Run setup/install.sh install${missing_list}"
  fi

  if [ "$json" = true ]; then
    local first=true i=1 name
    printf '{"ok": %s, "platform": %s, "components": [' "$all_ok" "$(json_string "$PLATFORM")"
    while IFS= read -r name; do
      [ -n "$name" ] || continue
      [ "$first" = true ] || printf ', '
      first=false
      printf '{"name": %s, "status": %s, "detail": %s}' "$(json_string "$name")" \
        "$(json_string "$(printf '%s' "$statuses" | sed -n "${i}p")")" \
        "$(json_string "$(printf '%s' "$details" | sed -n "${i}p")")"
      i=$((i + 1))
    done <<<"$names"
    printf '], "next_action": %s}\n' "$(json_string "$next_action")"
  else
    local i=1 name
    printf 'Platform: %s\n' "$PLATFORM"
    while IFS= read -r name; do
      [ -n "$name" ] || continue
      printf '  %-24s %-14s %s\n' "$name" "$(printf '%s' "$statuses" | sed -n "${i}p")" \
        "$(printf '%s' "$details" | sed -n "${i}p")"
      i=$((i + 1))
    done <<<"$names"
    if [ -n "$next_action" ]; then printf 'Next: %s\n' "$next_action"; else printf 'Ready.\n'; fi
  fi
  [ "$all_ok" = true ]
}

command_install() {
  local requested="$*" component selected=""
  for component in $requested; do
    case " $COMPONENTS " in
      *" $component "*) ;;
      *) fail 1 "Unknown component '$component'. Choose from: $COMPONENTS" ;;
    esac
  done
  for component in $COMPONENTS; do
    if [ -z "$requested" ] || case " $requested " in *" $component "*) true ;; *) false ;; esac; then
      selected="$selected $component"
    fi
  done
  require_prerequisites
  start_log
  log "Installing into $ACCEL_HOME for $PLATFORM (log: $LOG_FILE)"
  mkdir -p "$TOOLS"
  for component in $selected; do
    check_component "$component"
    if [ "$STATUS" = ok ]; then
      log "  $component: already installed ($DETAIL)"
      continue
    fi
    log "  $component: installing ($DETAIL)"
    install_component "$component"
    check_component "$component"
    [ "$STATUS" = ok ] || fail 5 "$component didn't install correctly: $DETAIL"
    log "  $component: installed ($DETAIL)"
  done
  log "Done."
}

command_verify() {
  local component
  for component in $COMPONENTS; do
    check_component "$component"
    [ "$STATUS" = ok ] || fail 1 "$component isn't ready ($DETAIL). Run setup/install.sh install first."
  done
  start_log
  log "Running npm run verify:ghidra in $TOOLS/rea (log: $LOG_FILE)"
  if ! (
    set -a
    # shellcheck source=/dev/null
    . "$ACCEL_HOME/rea.env"
    set +a
    cd "$TOOLS/rea" && with_toolchain quiet npm run verify:ghidra
  ); then
    fail 5 "REA's Ghidra check failed. See the log above."
  fi
  log "REA's Ghidra check passed."
}

usage() {
  sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

main() {
  PLATFORM="$(detect_platform)"
  [ -f "$LOCK" ] || fail 1 "No versions.lock at $LOCK"
  case "${1:-}" in
    --check | check)
      shift
      local json=false
      if [ "${1:-}" = "--json" ]; then json=true; shift; fi
      [ $# -eq 0 ] || fail 1 "--check takes only --json"
      command_check "$json"
      ;;
    install) shift; command_install "$@" ;;
    verify) shift; [ $# -eq 0 ] || fail 1 "verify takes no arguments"; command_verify ;;
    -h | --help | help) usage ;;
    *) usage >&2; exit 1 ;;
  esac
}

main "$@"
