# Feature Specification: Anthropic System Message Compatibility

**Created**: 2026-08-27
**Status**: Implemented

## Goal

The Anthropic-compatible `/v1/messages` endpoint must accept requests whose
system instruction is supplied either in Anthropic's top-level `system` field
or as a `role: "system"` item inside `messages`, then forward the instruction
to Copilot as one OpenAI-compatible system message.

## Requirements

- Accept `user`, `assistant`, and compatibility `system` roles in incoming messages.
- Remove system-role items from the conversational message list.
- Combine top-level and embedded system instructions without losing either one.
- Preserve existing behavior for standard Anthropic requests.
- Add regression coverage for embedded system messages.

## Out of Scope

- Frontend changes.
- Changes to authentication, model selection, or response translation.
