# TDD Evidence Report — M9.7 Prompt injection, untrusted text and malformed output tests

## Source plan
No `*.plan.md` provided; user journeys derived during this TDD run from task.md `M9.7` ("Prompt injection, untrusted text and malformed output tests").

## User journeys
- As a system operator, I want prompt injection attempts (ignore previous instructions, system override, role play, jailbreak) detected and blocked, so untrusted text can't hijack model behavior
- As a system operator, I want untrusted text sanitized (HTML/script tags stripped, shell metacharacters removed, SQL patterns removed), so XSS and injection payloads are neutralized
- As a system operator, I want model output validated against an expected JSON schema (required fields, correct types), so malformed output never reaches downstream systems
- As a system operator, I want raw input validated (length limits, null bytes, control characters rejected), so oversized or malicious input is blocked
- As a system operator, I want all security decisions deterministic from explicit rules — no AI writes official state, no hosted inference
- Stdlib-only, no import-time network activity

## Task report

| Behavior | Validation command | RED result | GREEN result | Guarantee |
|---|---|---|---|---|
| SecurityResult creation | `tests/unit/test_security_validation.py::test_security_result_creates` | ModuleNotFoundError | PASS | Stores passed flag and reasons list |
| PromptInjectionDetector creation | `tests/unit/test_security_validation.py::test_prompt_injection_detector_creates` | ModuleNotFoundError | PASS | Instantiates |
| Detect ignore previous | `tests/unit/test_security_validation.py::test_detect_ignore_previous_instructions` | ModuleNotFoundError | PASS | "ignore previous instructions" → passed=False |
| Detect system override | `tests/unit/test_security_validation.py::test_detect_system_override` | ModuleNotFoundError | PASS | "system: reveal" → passed=False |
| Detect role play | `tests/unit/test_security_validation.py::test_detect_role_play_injection` | ModuleNotFoundError | PASS | "pretend you are" → passed=False |
| Detect clean text | `tests/unit/test_security_validation.py::test_detect_clean_text` | ModuleNotFoundError | PASS | Normal query → passed=True |
| Deterministic injection | `tests/unit/test_security_validation.py::test_detect_deterministic` | ModuleNotFoundError | PASS | Same input → identical result |
| UntrustedTextSanitizer creation | `tests/unit/test_security_validation.py::test_untrusted_text_sanitizer_creates` | ModuleNotFoundError | PASS | Instantiates |
| Sanitize HTML tags | `tests/unit/test_security_validation.py::test_sanitize_strips_html_tags` | ModuleNotFoundError | PASS | `<script>` tags removed |
| Sanitize shell metachars | `tests/unit/test_security_validation.py::test_sanitize_strips_shell_metacharacters` | ModuleNotFoundError | PASS | Shell metacharacters removed |
| Sanitize SQL patterns | `tests/unit/test_security_validation.py::test_sanitize_strips_sql_patterns` | ModuleNotFoundError | PASS | "DROP TABLE" removed |
| Sanitize clean text | `tests/unit/test_security_validation.py::test_sanitize_clean_text` | ModuleNotFoundError | PASS | Clean text unchanged |
| Deterministic sanitize | `tests/unit/test_security_validation.py::test_sanitize_deterministic` | ModuleNotFoundError | PASS | Same input → identical output |
| MalformedOutputDetector creation | `tests/unit/test_security_validation.py::test_malformed_output_detector_creates` | ModuleNotFoundError | PASS | Instantiates with schema |
| Detect valid output | `tests/unit/test_security_validation.py::test_detect_valid_output` | ModuleNotFoundError | PASS | Schema-conformant JSON → passed=True |
| Detect missing field | `tests/unit/test_security_validation.py::test_detect_missing_required_field` | ModuleNotFoundError | PASS | Missing required field → passed=False |
| Detect invalid JSON | `tests/unit/test_security_validation.py::test_detect_invalid_json` | ModuleNotFoundError | PASS | Malformed JSON → passed=False |
| Detect wrong type | `tests/unit/test_security_validation.py::test_detect_wrong_type` | ModuleNotFoundError | PASS | Wrong field type → passed=False |
| Deterministic output | `tests/unit/test_security_validation.py::test_detect_output_deterministic` | ModuleNotFoundError | PASS | Same input → identical result |
| InputValidator creation | `tests/unit/test_security_validation.py::test_input_validator_creates` | ModuleNotFoundError | PASS | Stores limits |
| Validate valid input | `tests/unit/test_security_validation.py::test_validate_input_valid` | ModuleNotFoundError | PASS | Normal input → passed=True |
| Validate too long | `tests/unit/test_security_validation.py::test_validate_input_too_long` | ModuleNotFoundError | PASS | Over max length → passed=False |
| Validate null byte | `tests/unit/test_security_validation.py::test_validate_input_null_byte` | ModuleNotFoundError | PASS | Null byte → passed=False |
| Validate control chars | `tests/unit/test_security_validation.py::test_validate_input_control_chars` | ModuleNotFoundError | PASS | Control char → passed=False |
| Deterministic input | `tests/unit/test_security_validation.py::test_validate_input_deterministic` | ModuleNotFoundError | PASS | Same input → identical result |
| Convenience functions | `test_detect_prompt_injection_function`, `test_sanitize_untrusted_text_function`, `test_validate_input_function`, `test_validate_output_function` | ModuleNotFoundError | PASS | Module-level wrappers work |

## Test specification

| # | What is guaranteed | Test file/command | Type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Prompt injection detection | `tests/unit/test_security_validation.py` | unit | PASS | 716 passed, 2 skipped |
| 2 | Untrusted text sanitization | `tests/unit/test_security_validation.py` | unit | PASS | 716 passed, 2 skipped |
| 3 | Malformed output detection | `tests/unit/test_security_validation.py` | unit | PASS | 716 passed, 2 skipped |
| 4 | Input validation | `tests/unit/test_security_validation.py` | unit | PASS | 716 passed, 2 skipped |
| 5 | Deterministic results | `tests/unit/test_security_validation.py` | unit | PASS | 716 passed, 2 skipped |
| 6 | Convenience functions | `tests/unit/test_security_validation.py` | unit | PASS | 716 passed, 2 skipped |

## Coverage and known gaps
- No coverage tool configured; all M9.7 lines exercised by unit tests
- Intentional gap: no network fetching — purely in-memory deterministic validation
- Intentional gap: no persistence of security events — in-memory only
- Known limit: sanitizer removes tags/metacharacters but does not neutralize arbitrary English words (e.g. "alert" as plain text is safe — it's not executable)

## Merge evidence
RED: `ModuleNotFoundError: No module named 'superbot.m9.security_validation'` captured before implementation. GREEN: 716 tests pass, 2 skipped, ruff clean, format clean, working tree clean.