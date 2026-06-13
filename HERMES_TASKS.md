# HERMES_CORE_FORK Task Queue

Unchecked items in this file are eligible for Hermes autonomous coding.
Mark an item from `[ ]` to `[x]` in the same PR when the task is complete.

## Ready

- [ ] Harden delegated subagent execution: eliminate fake tool-call / placeholder output on native child delegate_task path (ROADMAP #5)
- [ ] Reduce PAT reliance: remove GITHUB_TOKEN fallback from autonomy_token_from_env, reserve PAT for admin/emergency only (ROADMAP #6)
- [ ] Expand recipe-backed structured tasks beyond validation/deploy/dependency fixes for cleaner autonomous completion
- [ ] Exercise repeated unattended HERMES_CORE_FORK maintenance cycles
- [ ] Expand external workspace pattern beyond P:\Overwatch_Research and P:\Hermes\infra-ops
- [ ] Add repo-create scope and self-hosted GitHub runner for full end-to-end automation
- [ ] Resume ACP/editor attachment verification when VS Code/Cursor work is back in scope
- [ ] Improve brain_state and hypothesis ledger suppression for better task choice over time
- [x] Add real unchecked task items to repo-local HERMES_TASKS.md files (this file)

## Completed


## Codebase-Derived Tasks

Derived from TODO/FIXME/HACK markers in source files. Each references the originating location.

### ACP Adapter

- [ ] Implement `_result()` to convert todo tool results into ACP native plan updates (`acp_adapter/events.py:39-43`)
- [ ] Wire todo completion events to emit native plan updates after tool completion (`acp_adapter/server.py:1064-1065`)

### Gateway Platforms

- [ ] Fetch real chat name and member count from Yuanbao API instead of placeholders (`gateway/platforms/yuanbao.py:4742`)
- [ ] Resolve XXX Elem from upload result in Yuanbao platform (`gateway/platforms/yuanbao.py:3462`)
- [ ] Fix HACK in yuanbao_proto for ACK response handling (`gateway/platforms/yuanbao_proto.py:62`)

### Agent Core

- [ ] Handle `&#x...;` HTML entity equivalents in message sanitization (`agent/message_sanitization.py:149`)
- [ ] Resolve XXX marker in context_compressor token estimation (`agent/context_compressor.py:258`)
- [ ] XXX placeholder in transports/types for response_item_id (`agent/transports/types.py:30`)

### Kanban System

- [ ] Implement recovery path: promote /blocked tasks to ready when parents complete (`hermes_cli/kanban.py:560`)
- [ ] Implement kanban_specify via auxiliary LLM for task decomposition (`hermes_cli/kanban.py:751-755`)
- [ ] Complete `recompute_ready` logic for blocked->ready transitions (`hermes_cli/kanban_db.py:2461`)
- [ ] Implement specify task command to transition todo -> ready (`hermes_cli/kanban_db.py:2419`)

### CLI & Tools

- [ ] Fix XXX token handling in cli.py display rendering (`cli.py:12424`)
- [ ] Complete deferred tool config for kanban tools (`hermes_cli/tools_config.py:69`)
- [ ] Implement claw migration cleanup for .json, sessions, logs, memory files (`hermes_cli/claw.py:189-645`)

### Scripts & Release

- [ ] Clean up hardcoded email-to-username mappings in release.py (`scripts/release.py:879-1171`)
- [ ] Resolve XXX check in check-windows-footprints.py for None handling (`scripts/check-windows-footguns.py:259`)

### TUI

- [ ] Implement soft-wrapping for SpacerHead cells in Ink renderer (`ui-tui/packages/hermes-ink/src/ink/screen.ts:764`)
- [ ] Follow up on markdown-to-ANSI wrapping with inline markdown preservation (`ui-tui/src/components/markdown.tsx:362`)
- [ ] Resolve XXX placeholder in useMainApp remaining tokens display (`ui-tui/src/app/useMainApp.ts:103`)

