"""Prepare the original React Native integration evals for read-only guide trials."""
import json
from pathlib import Path
from run import BASE, git

EVALS = "evals/matrixscan-count-rn"
FOCUSED = {"rn-integration": 1, "toolbar": 3, "toolbar-controlled": 3}
GUIDE_INSTRUCTION = "Use the installed matrixscan-count-rn skill and read its applicable reference before answering."


def prepare(case, project):
    """Copy only the user-provided files and return the frozen task plus its output format."""
    cases = json.loads(git("show", f"{BASE}:{EVALS}/integration-evals.json"))["evals"]
    original = next(item for item in cases if item["id"] == FOCUSED[case])
    project.mkdir(parents=True)
    for name in original["files"]:
        (project / Path(name).name).write_bytes(git("show", f"{BASE}:{EVALS}/{name}"))
    prompt = original["prompt"] + (
        "\n\nReturn the complete updated screen file in a code block and include any "
        "setup steps needed outside the file. The workspace is read-only."
    )
    if case == "toolbar-controlled":
        prompt += "\n\n" + GUIDE_INSTRUCTION
    return prompt
