"""M11.1 — Select UI/API/chart stack using inspection + ADR.

Deterministic stack-selection module documenting the chosen UI framework,
API framework, chart library and packaging for the local quant dashboard.

Selected stack (recorded in docs/adr/0004-ui-api-chart-stack.md):
- UI framework: Streamlit — Python-native, localhost-only binding, no build step,
  rich component ecosystem, suitable for internal research workstations.
- API framework: FastAPI — Python, async, localhost binding, automatic OpenAPI
  docs, validated request/response models.
- Chart library: Plotly — Python-native, integrates with Streamlit, no separate
  JS build step, deterministic offline rendering.
- Packaging: pip via pyproject.toml.

Stdlib-only; no import-time network/database activity.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StackDecision:
    """Record of inspecting one stack component.

    Captures the official URL, inspected version/commit, license, runtime,
    requirements, suitability, accept/reject decision and reason — per
    architecture.md §10 and design.md §6.
    """

    component: str  # "ui_framework" | "api_framework" | "chart_library" | "packaging"
    name: str
    version: str
    license: str
    runtime: str
    requirements: list[str]
    suitability: str  # "high" | "medium" | "low"
    accept: bool
    reason: str
    url: str = ""


@dataclass(frozen=True)
class UIStack:
    """The selected stack: UI framework, API framework, chart library, packaging."""

    ui_framework: str
    api_framework: str
    chart_library: str
    packaging: str


@dataclass(frozen=True)
class UIStackSelection:
    """The stack decision plus rationale and ADR reference."""

    stack: UIStack
    rationale: str
    adr_path: str = "docs/adr/0004-ui-api-chart-stack.md"


# Selected stack (rationale in docs/adr/0004-ui-api-chart-stack.md).
ui_stack = UIStack(
    ui_framework="streamlit",
    api_framework="fastapi",
    chart_library="plotly",
    packaging="pip",
)

ui_stack_selection = UIStackSelection(
    stack=ui_stack,
    rationale=(
        "Python-first, localhost-only, no build step. Streamlit binds locally by "
        "default and suits internal research workstations; FastAPI provides async, "
        "validated local API with OpenAPI docs; Plotly renders charts offline and "
        "integrates with Streamlit without a JS build step. All three are pip-"
        "installable, kept offline-capable, and do not expose unauthenticated public "
        "endpoints."
    ),
)


def load_ui_stack() -> UIStack:
    """Return the selected UI/API/chart stack."""
    return ui_stack


def load_ui_stack_selection() -> UIStackSelection:
    """Return the selected stack with rationale."""
    return ui_stack_selection


def load_stack_decision(
    component: str,
    name: str,
    version: str,
    license: str,
    runtime: str,
    requirements: list[str],
    suitability: str,
    accept: bool,
    reason: str,
    url: str = "",
) -> StackDecision:
    """Record inspection of one stack component (helper for ADR evidence)."""
    return StackDecision(
        component=component,
        name=name,
        version=version,
        license=license,
        runtime=runtime,
        requirements=list(requirements),
        suitability=suitability,
        accept=accept,
        reason=reason,
        url=url,
    )


def load_adr() -> str:
    """Read the ADR file documenting this stack decision."""
    adr_path = "docs/adr/0004-ui-api-chart-stack.md"
    try:
        with open(adr_path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


__all__ = [
    "StackDecision",
    "UIStack",
    "UIStackSelection",
    "load_adr",
    "load_stack_decision",
    "load_ui_stack",
    "load_ui_stack_selection",
    "ui_stack",
    "ui_stack_selection",
]
