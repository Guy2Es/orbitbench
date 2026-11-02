# src/orbitbench/harness/prompt.py
"""The system prompt: the same for every model; only the tool list differs between conditions."""

BASE = (
    "You are a mission-analysis engineer. You are given one task. Solve it, then end your reply with the "
    "<final_answer> block described in the task. That block is the only thing that is graded: what you say "
    "elsewhere is not read. If the task cannot be solved as stated, answer with status 'ill_posed' and a reason."
)

TOOLS = {
    "A": "You have no tools: no interpreter, no calculator, no network. Work the answer out in your reply.",
    "B": "You have a Python interpreter with numpy, scipy and sgp4. It has no network access.",
    "C": ("You have a Python interpreter with numpy, scipy and sgp4, and no network access. You also have "
          "the tools of a GMAT mission-analysis server, which can propagate orbits and run differential "
          "correctors."),
}


def system_prompt(condition: str) -> str:
    return f"{BASE}\n\n{TOOLS[condition]}"
