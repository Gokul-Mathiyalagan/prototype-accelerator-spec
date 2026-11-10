#!/usr/bin/env bash
# Live install inside the container: real downloads, REA build, verify:ghidra, and an MCP
# initialize round trip through rea-mcp.sh. Results go to /out. ACCEL_HOME is a Docker
# volume, so re-runs reuse what's installed.
set -uo pipefail
export ACCEL_HOME=/accel/home
INSTALL=/repo/setup/install.sh

step() {
  local name="$1"
  shift
  echo "== $name" >&2
  "$@" >"/out/$name.stdout" 2>"/out/$name.stderr"
  echo $? >"/out/$name.exit"
}

step install bash "$INSTALL" install
step rerun bash "$INSTALL" install
step check bash "$INSTALL" --check --json
step verify bash "$INSTALL" verify

# MCP over stdio: newline-delimited JSON-RPC. Send initialize and read one reply.
initialize='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"accel-live-test","version":"0"}}}'
step mcp bash -c "printf '%s\n' '$initialize' | timeout 120 bash /repo/setup/rea-mcp.sh | head -n 1"
echo "finished" >/out/finished
