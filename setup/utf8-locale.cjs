// setup/utf8-locale.cjs: preloaded through NODE_OPTIONS by `install.sh verify` on Linux.
//
// Java takes its file-name encoding from the locale. REA's verify:ghidra starts its MCP
// server with a hand-built environment that keeps NODE_OPTIONS but drops LANG and
// LC_ALL, so Ghidra can't open the verifier's non-ASCII temp paths. Setting a UTF-8
// locale inside each Node process restores what a normal desktop session provides.
"use strict";
const current = process.env.LC_ALL || process.env.LC_CTYPE || process.env.LANG || "";
if (process.platform === "linux" && !/utf-?8/i.test(current)) {
  process.env.LC_ALL = "C.UTF-8";
}
