# CLAUDE.md - Claude Code Integration Living Documentation

> ⚠️ **THIS IS A LIVING DOCUMENT** - Update this BEFORE making any architectural decisions or code changes. This document tracks our understanding of Claude Code's actual capabilities vs. assumptions.

## Project Vision

Build a headless, multi-tier research system using Claude Code sub-agents as the intelligence layer, orchestrated by Python for complex research workflows.

## Core Principle: Headless First

Everything MUST work without human interaction:
- No GUI dependencies
- No interactive prompts
- Fully scriptable
- Remote server compatible
- CI/CD pipeline ready

## Confirmed Capabilities ✅

### 1. Basic CLI Operation
- `claude -p "prompt"` works for headless execution
- Sub-agents ARE recognized from `~/.claude/agents/*.md` files
- Agent selection works with syntax: `Use <agent-name> to <task>`

### 2. Sub-Agent Invocation
- Agents CAN be invoked and DO execute
- Agents provide themed/specialized responses based on their descriptions
- Multiple agents can be orchestrated sequentially via shell/Python

## Discovered Limitations 🚨

### 1. Output Format Control ❌
**Finding**: Sub-agents ignore formatting instructions
- JSON-only output: **FAILED**
- Structured templates: **FAILED** 
- Strict formatting rules: **FAILED**

**Evidence**: 
- `json-only` agent ignored all JSON formatting requirements
- `raw-json` agent ignored data-only instructions
- All agents default to conversational, prose-style responses

**Workaround**: Build extraction layer to parse natural language outputs

### 2. Instruction Compliance ⚠️
**Finding**: Agents follow general theme but not specific instructions
- Behavioral themes: **PARTIAL SUCCESS**
- Exact instruction following: **FAILED**
- Output markers/prefixes: **FAILED**

**Evidence**:
- `echo-agent`: Did uppercase (theme) but ignored prefix requirement
- `srim-researcher`: Did research decomposition but ignored format
- `test-agent`: Ignored specific response requirements

**Workaround**: Design agents for behavioral guidance, not strict output

### 3. State Management ❌
**Finding**: No state between invocations
- Each `claude -p` call is stateless
- No context sharing between calls
- No native session management

**Workaround**: Manage state in orchestration layer (Python)

## Architecture Constraints

Given these limitations, our architecture must:

1. **Accept Natural Language Outputs** - Don't fight the conversational nature
2. **Extract Structure Post-Hoc** - Parse outputs rather than enforce formats
3. **Orchestrate Externally** - Python manages state, flow, and data passing
4. **Leverage Behavioral Themes** - Use agents for expertise areas, not formatting

## Current Agent Inventory

| Agent | Purpose | Actual Behavior | Status |
|-------|---------|-----------------|---------|
| test-agent | Verification | Generic responses | ⚠️ Works but ignores instructions |
| echo-agent | Uppercase echo | Partial compliance | ⚠️ Theme works, format doesn't |
| srim-researcher | Research decomposition | Good analysis, wrong format | ✅ Useful despite format |
| json-agent | JSON output | Prose output | ❌ Doesn't work as intended |
| strict-json | Forced JSON | Still prose | ❌ Doesn't work |
| json-only | Non-conversational | Still conversational | ❌ Doesn't work |
| raw-json | Data only | Still conversational | ❌ Doesn't work |

## Open Questions 🤔

1. Are there undocumented flags for `claude` that enforce formats?
2. Can agents access their defined tools (web-search, grep, etc.)?
3. Is there a way to invoke agents programmatically vs. CLI?
4. Do workspace/project flags work in any context?

## Next Actions

1. **Test Tool Access**: Do agents actually use tools like `web-search`?
2. **Build Extraction Layer**: Accept we need NLP/regex to parse outputs
3. **Design Agent Prompts**: Focus on behavioral guidance, not formatting
4. **Document Patterns**: What agent designs work best given constraints?

## Update Log

### 2024-07-28 - Initial Discovery
- Confirmed sub-agents work in headless mode
- Discovered formatting limitations
- Identified need for extraction layer
- Established architectural constraints

### [DATE] - [YOUR UPDATE HERE]
- What did you test?
- What did you discover?
- What workaround did you implement?

---

## How to Update This Document

1. **BEFORE** implementing any solution depending on Claude Code behavior
2. **AFTER** each test that reveals new behavior
3. **WHEN** discovering any limitation or capability
4. **AS** you develop workarounds or patterns

Format for updates:
```markdown
### YYYY-MM-DD - Brief Description
- **Tested**: What you tried
- **Expected**: What you thought would happen  
- **Actual**: What actually happened
- **Workaround**: How you're dealing with it
```

Remember: This document is MORE important than README.md. Update this FIRST.
