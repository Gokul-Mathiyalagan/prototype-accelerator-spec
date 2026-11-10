# Open decisions

Gokul hasn't decided these yet. Until he does, **the recommendation is the working default**: build to it, but keep it easy to change, and don't hard-code it in more than one place. When one is decided, write an ADR, then remove it from this list.

| # | Decision | Recommendation (working default) | Settled by |
|---|---|---|---|
| 1 | Default model in agent mode | GPT-6.1 Sol from Copilot's picker, matching the platform's model. Compare Claude Sonnet 5.5 in the phase 4 evals. Bring-your-own-key isn't needed. | T-009, T-402 |
| 2 | Ghidra scope | Ghidra 12.1.x with JDK 21 on the machines that run REA, after confirming it's on the approved-software list. Analyze only binaries committed to or built from a repo, never public registry packages, and only when the license allows. | Gokul, phase 0 |
| 3 | Platform language | Python 3.12 monorepo with a uv workspace | Gokul, before T-001 |
| 4 | Languages parsed in v1 | Python and TypeScript/JavaScript; Java later | Gokul, before T-103 |
| 5 | First reference repos | The two EBI Atlas services and the Genie/Cortex app, which together cover API, UI, auth and AI patterns | Gokul, before T-115 |
| 6 | Where approved skills live | A separate `accel-registry` repo with CODEOWNERS; projects pull skills with `accel skills sync` | Gokul, before T-208 |
| 7 | Web workbench | CLI and `accel-mcp` first; the web UI in phase 5 | Gokul |
| 8 | Sandbox for build and run | Local Docker for building target apps, if the laptop allows it; static-only extraction otherwise | Gokul, before T-105 |
| 9 | Brand token source | The brand or design team's token file, never values guessed from code | Gokul, before T-201 |
| 10 | Skill owners | Named owners for security, design and architecture skills before phase 2 starts | Gokul, before T-208 |
