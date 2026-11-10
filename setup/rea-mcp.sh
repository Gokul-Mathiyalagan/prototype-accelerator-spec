#!/usr/bin/env bash
# setup/rea-mcp.sh: starts the local REA MCP server that /accel-setup installed.
# MCP uses stdout, so every message here goes to stderr.
set -euo pipefail
ACCEL_HOME="${ACCEL_HOME:-$HOME/.accel}"
node="$ACCEL_HOME/tools/node/bin/node"
rea="$ACCEL_HOME/tools/rea/scripts/rea.mjs"

if [ ! -f "$ACCEL_HOME/rea.env" ] || [ ! -x "$node" ] || [ ! -f "$rea" ] ||
  [ ! -f "$ACCEL_HOME/tools/rea/.accel-built" ]; then
  echo "REA isn't set up in $ACCEL_HOME. Run /accel-setup in Copilot Chat, or setup/install.sh install." >&2
  exit 1
fi

set -a
# shellcheck source=/dev/null
source "$ACCEL_HOME/rea.env"
set +a
# Java takes file-name encoding from the locale; REA needs UTF-8 for non-ASCII paths.
case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in
  *UTF-8* | *utf-8* | *UTF8* | *utf8*) ;;
  *) if [ "$(uname -s)" = Linux ]; then export LC_ALL=C.UTF-8; fi ;;
esac
exec "$node" "$rea" mcp
