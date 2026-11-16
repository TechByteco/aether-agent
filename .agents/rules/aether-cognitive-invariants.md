---
trigger: always_on
description: Mandatory invariants for AETHER cognitive memory, voice synthesis, interface debouncing, and local model inference.
---

# AETHER Cognitive & System Invariants

## 1. Episodic Memory & FTS5 Retrieval
- When querying SQLite FTS5 for conversational episodes, NEVER pass raw multi-word prompts directly into `MATCH`.
- Always tokenize the query, remove conversational stop-words (`what`, `the`, `and`, `please`, `tell`, etc.), and join meaningful terms with `OR` to enable BM25 relevance scoring without strict all-token matching failures.

## 2. Text-to-Speech (TTS) Sanitation
- When cleaning text for voice synthesis (pyttsx3 or Web Speech API), NEVER strip raw numeric digits (`\d+`).
- Only strip bracketed citation markers (e.g. `\[\d+\]` or `\(\d+\)`). Preserve all numbers, timestamps, percentages, and calculations intact.

## 3. Web Speech Recognition Debouncing
- When configuring browser-native `SpeechRecognition`, always set `continuous = true`.
- Implement a silence debounce timer of >= 1.8 seconds before auto-submitting transcribed speech, allowing the user to speak multi-clause sentences naturally.

## 4. ChatML Role Alternation & Ollama Parameters
- Local chat models (Llama 3.2, etc.) require strict role alternation (`system` -> `user` -> `assistant` -> `user`). Never inject consecutive `user` turns into `messages`.
- In `ollama-python`, pass `keep_alive` as a top-level argument to `ollama.chat(...)`, not inside the `options` dictionary.


## 5. Autonomous Learned Runtime Invariants
- [Invariant] Before executing external tool 'nonexistent_tool_xyz', verify its existence in PATH or use native Python standard library fallbacks.
- [Invariant] Always verify file existence via tool_find_files or tool_inspect_directory before attempting surgical reads or edits.
- [Invariant] Always verify directory topology and file integrity before reading configuration files via tool_read_file or its subclasses.
- [Invariant] Always inspect and validate tool arguments at runtime to prevent tool execution on non-existent or misaligned file configurations.
- [Invariant] Tool tool_execute_command: Verify parameter types and guard against 'tool_execute_command() got an unexpected keyword argument 'task''.
- [Invariant] Never execute task without specified task parameter.
- [Invariant] Never inject task arguments into native tool execution dictionaries without explicit task type validation.
