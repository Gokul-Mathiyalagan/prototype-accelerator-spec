# Prototype Accelerator: instructions for GitHub Copilot

This is the Prototype Accelerator platform repo. It turns existing codebases into reviewed skills, and runs an AI-assisted delivery process for new projects.

- To install or repair REA (Reverse Engineer Anything) and its toolchain, use `/accel-setup`. Never install REA, Node, a JDK or Ghidra by hand, and never use `sudo`; `setup/install.sh` installs pinned, checksum-verified versions under `~/.accel`.
- MCP servers here are local only: `rea` (through `setup/rea-mcp.sh`) and `accel`. Don't add remote MCP servers.
- Model calls in product code go only through `accel_core.gateway` (Azure OpenAI). Don't add other model SDKs or endpoints.
- Secrets and personal data are redacted before any model sees code, HAR files or logs. Don't paste them into chat.
- Design input is HTML wireframes only.
