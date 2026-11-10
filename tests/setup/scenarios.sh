#!/usr/bin/env bash
# Run install.sh scenarios inside the test container; results go to /out/<scenario>/.
# Each scenario records exit, stdout and stderr, plus any evidence files it writes.
set -uo pipefail
INSTALL=/repo/setup/install.sh
REA_MCP=/repo/setup/rea-mcp.sh
OUT=/out
MIRROR=/fakes/mirror
LOCK=/fakes/versions.lock

bash /repo/tests/setup/make_fakes.sh "$MIRROR" "$LOCK" || exit 99
cp "$LOCK" "$OUT/fake-versions.lock"

# run NAME COMMAND...: run with the scenario's environment, record the results.
run() {
  local name="$1"
  shift
  mkdir -p "$OUT/$name"
  "$@" >"$OUT/$name/stdout" 2>"$OUT/$name/stderr"
  echo $? >"$OUT/$name/exit"
}

# A sorted listing of every file under a home, with content hashes (logs excluded).
snapshot() {
  (cd "$1" && find . -path ./logs -prune -o \( -type f -o -type l \) -print | LC_ALL=C sort |
    while read -r f; do printf '%s %s\n' "$(sha256sum "$f" | cut -c1-16)" "$f"; done)
}

fake_env() {
  env ACCEL_HOME="$1" ACCEL_MIRROR="file://$MIRROR" ACCEL_VERSIONS_LOCK="${LOCK_OVERRIDE:-$LOCK}" \
    HOME=/home/tester "${@:2}"
}

mkdir -p /home/tester
touch /tmp/before-install
sleep 1

# 1. A fresh machine: --check reports everything missing and writes nothing.
run check-empty fake_env /accel/empty bash "$INSTALL" --check --json
[ -e /accel/empty ] && echo created >"$OUT/check-empty/home-created"

# 2. Full install on Linux, then --check and a snapshot.
run install fake_env /accel/linux bash "$INSTALL" install
run check-after fake_env /accel/linux bash "$INSTALL" --check --json
run check-text fake_env /accel/linux bash "$INSTALL" --check
snapshot /accel/linux >"$OUT/install/snapshot"
cp /accel/linux/rea.env "$OUT/install/rea.env"
cp /accel/linux/tools/rea/npm-calls.log "$OUT/install/npm-calls.log"
cp /accel/linux/logs/install-*.log "$OUT/install/log" 2>/dev/null

# 3. Nothing outside ACCEL_HOME changed: HOME is still empty, and no system path is newer.
ls -A /home/tester >"$OUT/install/home-contents"
find /etc /usr /opt /root /var -xdev -newer /tmp/before-install -not -path '/var/cache/*' \
  -not -path '/var/log/*' 2>/dev/null >"$OUT/install/outside-writes"

# 4. Re-running changes nothing and exits 0.
run rerun fake_env /accel/linux bash "$INSTALL" install
snapshot /accel/linux >"$OUT/rerun/snapshot"

# 5. The launcher starts REA's MCP server with rea.env loaded, or explains what's missing.
run rea-mcp env ACCEL_HOME=/accel/linux bash "$REA_MCP"
run rea-mcp-missing env ACCEL_HOME=/accel/nothing bash "$REA_MCP"

# 6. verify runs npm run verify:ghidra; a failure exits 5 and shows the log tail.
run verify fake_env /accel/linux bash "$INSTALL" verify
cp /accel/linux/tools/rea/verify-env.log "$OUT/verify/verify-env.log"
run verify-fail fake_env /accel/linux FAKE_VERIFY_FAIL=1 bash "$INSTALL" verify
run verify-not-installed fake_env /accel/empty bash "$INSTALL" verify

# 7. A wrong version is reported, and install fixes it.
sed -i 's/application.version=12.1.4/application.version=12.1.3/' \
  /accel/linux/tools/ghidra/Ghidra/application.properties
run check-wrong-version fake_env /accel/linux bash "$INSTALL" --check --json
run fix-wrong-version fake_env /accel/linux bash "$INSTALL" install ghidra

# 8. A checksum mismatch exits 3 and leaves nothing installed.
sed 's/^\(    linux-x64: \)[0-9a-f]\{64\}$/\1'"$(printf 'f%.0s' $(seq 64))"'/' "$LOCK" >/fakes/bad.lock
LOCK_OVERRIDE=/fakes/bad.lock run checksum fake_env /accel/bad bash "$INSTALL" install node
ls -A /accel/bad/tools >"$OUT/checksum/tools" 2>/dev/null
ls -A /accel/bad/cache/downloads >"$OUT/checksum/downloads" 2>/dev/null

# 9. A download that fails exits 4.
mv "$MIRROR/NationalSecurityAgency" /fakes/hidden-ghidra
run download-fail fake_env /accel/dl bash "$INSTALL" install ghidra
mv /fakes/hidden-ghidra "$MIRROR/NationalSecurityAgency"

# 10. A missing prerequisite (git) exits 2 before anything is written.
mkdir -p /tmp/nogit
for tool in /usr/bin/*; do [ "${tool##*/}" = git ] || ln -sf "$tool" /tmp/nogit/; done
run prereq fake_env /accel/nogit PATH=/tmp/nogit bash "$INSTALL" install
[ -e /accel/nogit ] && echo created >"$OUT/prereq/home-created"

# 11. Unknown components and bad usage exit 1.
run unknown-component fake_env /accel/x bash "$INSTALL" install python
run bad-usage fake_env /accel/x bash "$INSTALL" frobnicate

# 12. Only the requested component is installed.
run only-jdk fake_env /accel/jdk bash "$INSTALL" install jdk
ls -A /accel/jdk/tools >"$OUT/only-jdk/tools"

# 13. Apple Silicon: the arm64 decompiler is built with the spec's make flags.
run arm64 fake_env /accel/arm64 ACCEL_PLATFORM=darwin-arm64 bash "$INSTALL" install
run arm64-check fake_env /accel/arm64 ACCEL_PLATFORM=darwin-arm64 bash "$INSTALL" --check --json
cp /accel/arm64/tools/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp/make-args "$OUT/arm64/make-args"
cp /accel/arm64/rea.env "$OUT/arm64/rea.env"
[ -x /accel/arm64/tools/ghidra/Ghidra/Features/Decompiler/os/mac_arm_64/decompile ] &&
  echo yes >"$OUT/arm64/decompiler-installed"

echo "done" >"$OUT/finished"
