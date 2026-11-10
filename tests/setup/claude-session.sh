#!/usr/bin/env bash
# Start an interactive Claude Code session in a Linux container, for T-006's live check.
#
#   tests/setup/claude-session.sh          # build the image if needed, then start claude
#   tests/setup/claude-session.sh bash     # a shell in the same container instead
#
# The repo is mounted read-only at /workspace, so the session can't change it. The
# container's home directory lives in the `accel-claude-home` Docker volume: your
# Claude Code login and ~/.accel (REA's install) survive between runs.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
dockerfile="$here/Dockerfile.claude"
tag="accel-claude-session:$(sha256sum "$dockerfile" | cut -c1-12)"

if ! docker image inspect "$tag" >/dev/null 2>&1; then
  echo "Building $tag (a few minutes, once)..." >&2
  docker build -t "$tag" -t accel-claude-session:latest -f "$dockerfile" "$here"
fi

# Git Bash on Windows needs winpty for an interactive terminal, and must not rewrite
# container paths like /workspace into Windows paths.
tty=()
if [ -n "${MSYSTEM:-}" ]; then
  export MSYS_NO_PATHCONV=1
  if command -v winpty >/dev/null 2>&1; then tty=(winpty); fi
fi

exec "${tty[@]}" docker run -it --rm \
  --name accel-claude-session \
  -v "$root:/workspace:ro" \
  -v accel-claude-home:/home/dev \
  "$tag" "$@"
