# DeepSeek V4 Flash Prompt Optimization

## Intent
Maximize prefix cache efficiency (>90%) through deterministic prompt layout.

## Prompt Structure
```
[MOST STATIC - System Instructions]  <- Cached
[Immutable Domain Rules]             <- Cached  
[Spec Contract Schema]               <- Cached
[MOST DYNAMIC - Current Context]     <- NOT cached
[Stack Trace / Error Log]            <- NOT cached
```

## Cache Optimization Rules
1. System instructions must be identical across all calls
2. Never interpolate variables into the system prompt section
3. Place frequently changing data at the END of the prompt
4. Use deterministic delimiters between sections
5. Avoid gratuitous whitespace changes

## Template
```python
SYSTEM_PROMPT = "You are EMASDEP Engineer Agent..."  # Frozen, never changes
DOMAIN_RULES = "All code must pass python 3.12 strict..."  # Semi-static
SCHEMA = json.dumps(spec_contract)  # Updated per pipeline

CURRENT_TASK = task.description  # Changes every call === LAST ELEMENT
ERROR_LOG = last_error  # Changes every call === LAST ELEMENT
```
