# Superbot Current Context, Decision Register and Evidence

**Snapshot date:** 2026-10-28 (Asia/Kolkata).  
**Truth labels:** `CONFIRMED` = user explicitly selected; `MEASURED` = user-supplied local output; `OPEN` = undecided; `PROPOSAL` = option only; `SUPERSEDED` = historical, not current.

## 1. Purpose and status

Superbot is a new standalone local-first AI trading research/backtesting/internal-simulation application to be built with OpenCode. Do not extend GoldMasters. The user's latest request authorizes building from this Markdown specification pack; an earlier POC-only restriction is superseded for application development. This **does not authorize live trading or demo trading**.

No complete application is built or verified in this session. The only supplied local test results concern a tiny synthetic baseline POC.

## 2. Confirmed product decisions

| Area | Decision | Status |
|---|---|---|
| Product | Standalone Superbot, not based on GoldMasters | CONFIRMED |
| Objective | Research, signals, historical testing and internal simulation; no live execution | CONFIRMED |
| Assets | Gold, Silver, Bitcoin, Ethereum, US Oil | CONFIRMED |
| Timeframes | M5, M15, H1, H4 | CONFIRMED |
| Initial source | XM MT5 read-only; confirm actual symbols/metadata in Market Watch | CONFIRMED; exact symbols OPEN |
| AI | Local-only; ₹0 hosted inference budget; English-only | CONFIRMED |
| Runtime | Benchmark Ollama vs llama.cpp on laptop and desktop | CONFIRMED; winner OPEN |
| Architecture | Local-first, Python-first, modular, Windows-native | CONFIRMED |
| App database | Local PostgreSQL | CONFIRMED; suitability/config need laptop test |
| OHLCV history | Benchmark Parquet and alternatives | OPEN |
| Strategy families | Trend/pullback; liquidity sweep/market structure; quantitative/statistical | CONFIRMED |
| Strategy structure | Shared framework with separately versioned strategies/configs, not ten LLM strategy agents | CONFIRMED |
| Simulation | Event-driven simulator is primary validation; fast sweeps are secondary | CONFIRMED |
| AI authority | AI proposes/reviews; deterministic services validate; risk gates decide | CONFIRMED |
| Promotion | Deterministic eligible promotion to internal simulation; human approval for each release-stage promotion; no live | CONFIRMED |
| Scheduler | Configurable intervals only while app runs; prevent overlap/duplicates | CONFIRMED |
| UI | Quant-terminal dashboard: markets/data, jobs, strategy/validation, risk, audit/experiments | CONFIRMED |
| Remote access | Authenticated, role-limited private VPN (e.g. Tailscale); no public exposure | CONFIRMED |
| Backup | Daily local + encrypted cloud, 30-day retention, integrity checks, monthly restore test | CONFIRMED; provider/key management OPEN |
| Migration | Laptop first, desktop later; migrate DB/config/data manifests, reinstall/revalidate dependencies/models | CONFIRMED |
| Repository licences | User says previous repo licence review is clear as of 2026-10-28 | CONFIRMED for previously reviewed list; record exact adopted components and versions |

## 3. Risk and validation decisions

- Combined open-risk cap: 5%.
- Daily loss limit: 3% of starting daily equity.
- Portfolio drawdown halt: 10% from relevant equity peak; pause new entries and require human-approved resume after checks pass.
- Strategy OOS max drawdown: 15%.
- Normal minimum 100 completed OOS trades; at least 3 chronological walk-forward windows.
- OOS PF >=1.20; Sharpe >=1.0; Sortino >=1.5.
- At least 2 of 3 windows positive net return; every window within DD limit.
- Positive OOS net return after available estimated costs required before internal simulation. Disclose unavailable components.
- Cost-adjusted validation + 2x cost stress required before any future demo readiness.
- Count all trials; reserve untouched final test data; use multiple-testing controls where feasible.
- Neighboring params must establish stable region; numerical definition OPEN.
- Leakage fails. Robustness failure blocks promotion; revised version restarts lifecycle.
- After 3 failed validation attempts, disable/archive that strategy version and preserve evidence. A material change creates a new version and restarts validation.
- Balanced candidate scorecard: returns, drawdown, risk-adjusted performance, trade count and robustness.

## 4. Adaptive risk decisions

- Risk per trade is adaptive/strategy-specific below central cap; deterministic sizing from cash budget, stop distance and verified instrument specs.
- Four lifecycle evidence tiers at 0.25x/0.50x/0.75x/1.00x base risk.
- Monthly risk reviews; max 10% relative increase per review, not percentage points; minimum new evidence needed.
- If evidence insufficient or criteria fail, fall back to highest currently supported tier.
- Volatility measure: ATR relative to price. Reduce allocation as volatility rises inside configured bounds; block entries above configured maximum or when unreliable.
- Shared correlation group budgets and configurable group/strategy concentration caps.
- Competing signals ranked by tier, signal quality, expected risk-adjusted return and correlation impact; tie-break lower risk-capacity use. Resize if feasible; otherwise reject.
- After risk/daily/portfolio breach pause new entries and alert; existing simulated positions continue under current stops/exits.

**Open numeric inputs:** per-trade max cap/floors; ATR thresholds/floors/ceilings/max; tier trade counts/elapsed periods; deterioration thresholds; correlation estimator/window/groups; reserve formula; daily equity boundary/resume details.

## 5. Data and simulation rules

- OHLCV bars only initially for five instruments/four timeframes, as actually available.
- Longest reliable permitted free/broker history; preserve acquired data unless an explicit storage-constraint policy is necessary.
- Originals immutable; cleaned/derived datasets separately versioned.
- Preserve source identity/timestamps; UTC canonical timestamps and verified XM server-time/candle boundaries.
- Gaps/duplicates/suspicious/stale data or missing/stale specs block affected work.
- Never silently merge multiple providers.
- Market fill at next candle open with modeled spread/slippage; ambiguous same-bar SL/TP resolves stop-first; stop gap uses worse opening price plus cost; limit fills conservative with configurable trade-through.
- Verified contract/tick/volume/session constraints required; never guess typical values.
- Strategy version defines break-even, trailing, partial exit, holding period and reverse-signal behavior.
- Stable signal identity, dedup, expiry/invalidation; stale pending entry revalidated after data resumes.

## 6. Agent governance

- Deterministic orchestrator owns dependency/lifecycle flow.
- Versioned structured messages validated at every handoff.
- Agents have scoped read-only market access. Only deterministic services write official strategy versions, experiment records, risk settings and lifecycle state.
- Role-based permissions; no unrestricted agent tools.
- High-impact agent conflicts may be repeated within configured limits; unresolved conflict blocks the dependent decision.
- Model failure: bounded retries, qualified fallback if safe, otherwise skip dependent task and mark incomplete.
- News/sentiment later; free permitted APIs/RSS only; record source/time/instrument/category/sentiment/confidence/supporting text. Missing/stale news blocks news-dependent decisions only; never controls risk/order.

## 7. Candidate repository list — candidates, not mandatory integrations

- `nautechsystems/nautilus_trader`: first event-driven engine POC.
- `QuantConnect/Lean`: first event-driven engine POC.
- Custom deterministic Python baseline: comparison control.
- `StockSharp/StockSharp`: assess only if a necessary broker/data capability justifies C# integration.
- `TauricResearch/TradingAgents`: agent workflow patterns, not risk authority.
- `AI4Finance-Foundation/FinRobot`: optional agent/research component.
- `microsoft/qlib`: optional quant research/ML.
- `AI4Finance-Foundation/FinRL` and `tensortrade-org/tensortrade`: later RL only if justified and resource-tested.
- `Lumiwealth/lumibot`, `mementum/backtrader`: alternatives; do not stack frameworks by default.
- `polakowo/vectorbt`: possible fast parameter sweeps, not the sole authoritative event-driven validator.
- `shiyu-coder/Kronos`: optional future forecasting experiment, not a core engine.
- `virattt/ai-hedge-fund`: educational/reference only unless a specific component proves useful.
- `aayxshkumar/ai-hedge-fund`: unaudited fork; no wholesale import without unique justification/source review.
- `tradingview/lightweight-charts`: optional dashboard chart layer with attribution/version recorded.

Additional repos may be researched if a capability gap remains. Before use inspect official source, current commit/release, licence, dependency set, tests, maintenance, security, compatibility and source commit. License clearance does not prove functional fit.

## 8. Tool/plugin discovery checklist

Previously reported OpenCode MCP/tools: Context7, GitHub, OpenCode Console, Playwright, Ruflo, Sequential Thinking, Stitch, Supabase and Terminal. Previously reported plugins/skills: ECC, GSD-Core, OpenCode DCP, Ponytail, Supermemory and Vercel; other context also mentioned Superpowers, Supabase and Playwright. This list can be stale. At M0 inspect the active setup and use only tools verified to be installed/available and relevant.

ECC loops are important. Inspect exact ECC version and commands. Use installed loop/quality/review/security commands if present; otherwise follow the manual ECC loop in `rules.md`. `AGENTS.md` is included because OpenCode recognizes it as a project instruction file.

## 9. User-measured baseline POC

`py --version` → Python 3.14.7.  
`py superbot_poc.py --warmups 1 --repetitions 5` → correctness `PASS`, seven synthetic checks, report time `2026-10-28T12:30:05.417727+00:00`.

- Fixture: 10 bars; SHA-256 `e94d14955d1ad1a425c58c17be60aaec3904a77fcbb38d458ced86068a6a33bd`.
- Median runtime 29.784 ms per 2,000 tiny iterations; runs: 54.8336, 25.7248, 30.3061, 28.4241, 29.7840 ms.
- Median `tracemalloc` peak 160 bytes (Python allocations, not process RSS).
- Checks: OHLCV validity/chronology; next-bar-open entry; stop-first ambiguity; explicit spread/commission; adverse stop-gap; deterministic portfolio/daily loss/DD gates; signal timestamp before entry.
- Script scope limitations: synthetic fixture only, no MT5/broker metadata, not full portfolio simulator, no partial fills/multi-position accounting/swaps, no engine comparison, not for live/demo trading.

Hardware evidence from PowerShell:
- `TotalPhysicalMemory`: 7,983,263,744 bytes (~7.44 GiB).
- `FreePhysicalMemory`: 2,109,516 KiB (~2.01 GiB) at that moment; snapshot only.
- `TotalVisibleMemorySize`: 7,796,156 KiB.
- `py` source `C:\WINDOWS\py.exe`; Windows 10 build 19045; baseline reported 2 logical CPUs.

Resource monitor 1: 9 MB/10 samples/CPU 0.08, likely measured launcher; do not reuse as workload memory. Monitor 2: exit 0, Python child sampled peak 25.77 MB, 5 samples; CPU cumulative sample values were wrongly summed and are not CPU time. Sampling is too short. A process-tree monitor and representative workload are still required. No full engine/PostgreSQL/MT5/model/app tested on laptop from this evidence.

## 10. Standardized POC questionnaire defaults

The POC plan uses the following selected defaults for fair engine/storage/runtime comparisons: comprehensive measurements (runtime, peak process-tree RAM, CPU, disk I/O, throughput, startup, failure rate and effect on critical services); one warm-up plus five measured repetitions, with more only if pre-defined noise criteria justify it; small correctness fixture plus representative historical dataset and an optional larger stress dataset if the laptop can support it; strict known-fixture/event accounting/cost/risk/causality/leakage tests before performance ranking; reproducible retention of configs, data hashes/manifests, commits, machine metrics, logs, raw outputs, tests and limitations. These are the execution defaults recorded after the user's “Proceed”; OpenCode must record deviations and reasons.

## 11. Open decision register

1. Engine/combination: custom baseline vs NautilusTrader vs LEAN; choose by comparable evidence and weighted score.
2. OHLCV storage format and partitioning.
3. Frontend/UI framework, API/web framework, charting and desktop packaging.
4. Ollama vs llama.cpp and qualified local model/version/quantization on each machine.
5. Per-tier minimum trades and elapsed time; tier advancement protocol.
6. Numerical ATR risk curve, floors/ceilings/max volatility.
7. Correlation computation/window/group definitions, group caps and reserve formula.
8. Per-trade hard risk caps, weaker-tier caps, money/FX conversion method when required.
9. Daily-equity boundary/recovery; verify XM server timezone.
10. Metric annualization/risk-free conventions; robust-region numeric definition; deterioration thresholds.
11. Cost inputs when broker data omits them; disclose missing costs and block as required.
12. Cloud backup provider, key management and bandwidth/capacity.
13. Authentication implementation/private VPN setup.
14. News-source list and implementation phase.
15. Job intervals/resource thresholds: configurable, not hard-coded without decision.
16. Stable signal identity and precise OB/FVG definitions if included.

Resolve only when needed for the next task. Build safe testable contracts in parallel where possible. Do not invent numbers to clear blockers.

## 12. Next actions

1. Extract pack at new repository root. — DONE (spec files present at C:\SuperBot root + superbot_opencode_spec_pack/; duplicates noted, no overwrite)
2. Start OpenCode using `START_PROMPT.md`. — DONE (OpenCode v2.1.2 active)
3. Perform M0 reconnaissance; verify repository/config/ECC/MCP/skill availability and preserve current work. — DONE (see section 13)
4. Update this file and `task.md` with actual findings. — IN PROGRESS
5. Start M1 only after repository/tool baseline is documented. — PENDING

## 13. M1 Foundation — M1.1 / M1.3 (2026-10-28)

### Completed (commit 5954dc9 "M1.1: package layout, validated config profiles, ADR-001")

**Package/layout (M1.1 + ADR-001):**
- `src/superbot/` package with `__init__.py` (`__version__ = "0.1.0"`), stdlib-only import (no network/MT5/database/model at import time).
- `pyproject.toml`: setuptools backend (`where = ["src"]`), no runtime dependencies, dev deps pytest/ruff; pytest `testpaths = ["tests"]`, `pythonpath = ["src"]`; ruff line-length 100.
- `tests/unit/test_config.py`: 4 tests (profile enum values; valid profiles accepted; invalid profile rejected; demo-readiness rejected in V1).
- `docs/adr/0001-package-layout.md`: records src-layout decision, rationale, alternatives (flat layout, editable-install requirement rejected), consequences.
- `.gitignore`: Python/Windows/runtime data, secrets, spec-pack zips excluded.

**Config/profiles (M1.3):**
- `src/superbot/config.py`: `Profile` enum (`research`, `internal-simulation`); `SuperbotConfig` frozen dataclass validating profile in `__post_init__`; `InvalidConfigError`; `demo-readiness` explicitly rejected as not a V1 profile; no secrets stored.

**Verification:**
- `py -m pytest tests/ -q` → 4 passed.
- `py -m ruff check src/ tests/` → All checks passed.
- `py -m ruff format --check src/ tests/` → 3 files already formatted.
- Working tree clean after commit.

### In progress / next
- `M1.2` Define versioned canonical contracts from `schema.md` — DONE: InstrumentSpec (§2) and OHLCVBar (§3) contracts with enums, Decimal-or-null fields, OHLC/time/interval validation, tests pass, ruff clean.
- `M1.4` Structured logs/correlation IDs + secret-redaction tests — DONE: `src/superbot/observability/logging.py` (contextvar correlation ID, JsonFormatter, CorrelationFilter, `redact_secrets`, secret-key allowlist); 14 tests pass, ruff clean. Secrets never logged (schema.md §19 / PRD §14).
- Next: `M1.5` supervisor/health model and controlled startup/shutdown skeleton.

## 12. M0 Reconnaissance Findings (2026-10-28)

### Repository
- C:\SuperBot is NOT a git repo (no `.git` directory). Git 2.55.0.windows.3 installed. No branch/commit to record yet. Git initialization is a pending M1 foundation decision (not done blindly during reconnaissance).
- Spec pack files present at C:\SuperBot root: AGENTS.md, PRD.md, context.md, architecture.md, rules.md, task.md, schema.md, design.md, Debug.md, memory.md, agents.md, START_PROMPT.md, README.md, MANIFEST.json. Same files also under superbot_opencode_spec_pack/ plus superbot_opencode_spec_pack.zip and superbot_poc_kit.zip.
- superbot_poc_kit/ contains superbot_poc.py, README.md, results/ (baseline JSONs).
- No existing application code, no tests, no pyproject.toml/setup.cfg/pytest.ini at C:\SuperBot root. No application code modified during reconnaissance.
- AGENTS.md at root matches spec pack agents.md (governance: AI proposes, deterministic verifies, risk decides; shared versioned strategy framework, not ten LLM agents).

### OpenCode / tooling
- OpenCode v2.1.2 (`opencode --version`). Config at C:\Users\wasim\.claude\settings.json.
- MCP servers configured (mcp_config.json): `serena` (npx serena-slim --setup), `github` (npx @modelcontextprotocol/server-github; GITHUB_PERSONAL_ACCESS_TOKEN empty = not active). Context7/GitHub/Playwright/Supabase plugins are installed but MCP-level activation must be verified per use.
- Installed plugins (installed_plugins.json): supabase 0.1.15, playwright fbe07fb6ce7d, context7 fbe07fb6ce7d, superpowers 6.4.1, github fbe07fb6ce7d, claude-code-setup 1.0.0, sentry-cli 0.46.0, sentry 1.4.0, **ecc 2.2.2**, context-mode 1.0.169, caveman 2.7.0, code-review fbe07fb6ce7d, openviking-memory 0.6.4, claude-mem-cowork 0.1.3, headroom 0.39.1, vercel 0.50.0, day-trader-skill 2.0.0.
- Enabled plugins: day-trader-skill@day-trader-skill = true only.
- ECC commands present (plugin commands dir): loop-start, loop-status, quality-gate, harness-audit, security-scan, code-review, python-review, pr, plan, etc. Verified as files; active registration in this session not yet confirmed. quality-gate = file formatter (ruff format for .py) driven by hook stdin JSON, not CLI args. harness-audit = node scripts/harness-audit.js. security-scan = npx ecc-agentshield scan. No `C:\Users\wasim\.claude\commands` directory.
- Skills installed (~.claude/skills): archify, caveman, code-review, diagnosing-bugs, find-docs, find-skills, frontend-design, git-guardrails-claude-code, graphify, learned, megacave, prototype, research, scaffold-exercises, skill-creator, tdd, vercel-*, web-design-guidelines, wizard, writing-*, etc.
- Agents installed (~.claude/agents): many role-based .md files. None Superbot-specific.
- Caveman mode: full. Hooks use caveman-proxy native-hook across SessionStart/UserPromptSubmit/PreToolUse/PostToolUse/etc.

### Python / dependencies (Python 3.14.7)
- py.exe at C:\WINDOWS\py.exe; pip 26.2.1; pytest 9.1.1; ruff 0.17.2.
- psycopg 3.3.6, psycopg-binary 3.3.6, SQLAlchemy 2.1.4 — import OK.
- ollama 0.6.3 — imports (no __version__ attribute).
- **metatrader5 5.0.6231 — pip shows installed at Python314 site-packages but `import metatrader5` raises ModuleNotFoundError.** Blocks MT5 read-only discovery until resolved (mirrors C:\Bot project note: "live MT5 blocked by unimportable metatrader5 package").
- streamlit 1.66.1, fastapi 0.143.0 available.
- **goldmasters-contracts 0.1.0 installed but PROHIBITED — must not be used or derived from.** six-agent-trading-desk 0.1.0 at C:\Bot is a separate project; not touched.

### Hardware / services
- Windows 10 build 19045, ~7.44 GiB RAM (~2.01 GiB free at snapshot), 2 logical CPU threads, HDD.
- PostgreSQL 18 service RUNNING; psql 18.0.6.0 at C:\Program Files\PostgreSQL\18\bin\psql.exe.

### Baseline POC re-verified
- `py superbot_poc.py --warmups 1 --repetitions 5` → correctness `status: PASS`; 7 synthetic checks (OHLCV validity/chronology; next-bar-open entry; stop-first ambiguous SL/TP; explicit spread/commission; stop-gap worse-open fill; portfolio/daily-loss/drawdown gates; signal timestamp before entry).
- Fixture 10 bars, SHA-256 e94d14955d1ad1a425c58c17be60aaec3904a77fcbb38d458ced86068a6a33bd.
- This run: median runtime 28.877 ms / 2,000 iterations; range 3.83 ms; median tracemalloc peak 160 bytes (Python allocations, not process RSS).
- Saved report: C:\SuperBot\superbot_poc_kit\results\baseline_20261028T131428Z.json.
- Limitations: synthetic fixture only, no MT5/broker metadata, not a full portfolio simulator, no engine comparison, not for live/demo trading.

### OPEN decisions / blockers carried forward
- Engine winner (custom baseline vs NautilusTrader vs LEAN): OPEN.
- OHLCV storage format (Parquet vs alternatives): OPEN.
- UI/API/chart/packaging stack: OPEN.
- Ollama vs llama.cpp and qualified local model: OPEN.
- metatrader5 import failure: BLOCKER for M2.5 MT5 discovery; not resolved.
- No git repo: pending M1 foundation decision.
- No existing app code/tests/config: M1 foundation required before any implementation.

### Evidence boundary
- Only the synthetic baseline POC is proven tested. No engine, full MT5 link, PostgreSQL app integration, local model runtime, or complete app is tested on this laptop. No unverified PASS status claimed.
