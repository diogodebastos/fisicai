"""Statistical inference on published pyhf likelihoods."""

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool


def list_patches(workspace_dir: str) -> str:
    """List signal patches available in a downloaded likelihood directory."""
    import pyhf

    patchset_path = _find_one(workspace_dir, "patchset*.json")
    patchset = pyhf.PatchSet(json.loads(patchset_path.read_text()))
    desc = patchset.description or ""
    labels = patchset.metadata.get("labels", [])
    lines = [f"Patchset {patchset_path}: {desc}", f"Patch labels: {labels}", "Patches:"]
    for patch in patchset.patches:
        lines.append(f"  {patch.name}  values={list(patch.values)}")
    return "\n".join(lines)


def compute_cls(
    workspace_dir: str,
    patch_name: str | None = None,
    poi_value: float = 1.0,
) -> str:
    """Compute observed and expected CLs at the given POI for a (patched) workspace."""
    import pyhf

    bkg_path = _find_background_workspace(workspace_dir)
    workspace = pyhf.Workspace(json.loads(bkg_path.read_text()))

    if patch_name:
        patchset_path = _find_one(workspace_dir, "patchset*.json")
        patchset = pyhf.PatchSet(json.loads(patchset_path.read_text()))
        workspace = patchset.apply(workspace, patch_name)

    model = workspace.model()
    data = workspace.data(model)
    cls_obs, cls_exp = pyhf.infer.hypotest(
        poi_value, data, model, test_stat="qtilde", return_expected_set=True
    )

    exp = [float(v) for v in cls_exp]
    excluded = "EXCLUDED at 95% CL" if float(cls_obs) < 0.05 else "not excluded at 95% CL"
    return (
        f"Workspace: {bkg_path}" + (f" + patch {patch_name!r}" if patch_name else "") + "\n"
        f"POI (signal strength mu) = {poi_value}\n"
        f"CLs observed = {float(cls_obs):.5f}  -> {excluded}\n"
        f"CLs expected band (-2s, -1s, median, +1s, +2s) = "
        + ", ".join(f"{v:.5f}" for v in exp)
    )


def _find_background_workspace(workspace_dir: str) -> Path:
    root = Path(workspace_dir)
    for pattern in ("BkgOnly*.json", "*bkgonly*.json", "*background*.json"):
        matches = sorted(root.rglob(pattern))
        if matches:
            return matches[0]
    # fall back to any workspace-shaped json that is not a patchset
    for path in sorted(root.rglob("*.json")):
        if "patchset" in path.name.lower():
            continue
        try:
            spec = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if {"channels", "observations", "measurements"} <= set(spec):
            return path
    raise FileNotFoundError(f"No pyhf workspace JSON found under {workspace_dir}")


def _find_one(workspace_dir: str, pattern: str) -> Path:
    matches = sorted(Path(workspace_dir).rglob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern!r} under {workspace_dir}")
    return matches[0]


@tool(
    "pyhf_list_patches",
    "List the signal patches (model points) in a downloaded published-likelihood directory "
    "containing a patchset.json. Patch names typically encode the signal masses, e.g. "
    "'sbottom_600_280_150'.",
    {"workspace_dir": str},
)
async def pyhf_list_patches(args: dict[str, Any]) -> dict[str, Any]:
    try:
        text = list_patches(args["workspace_dir"])
    except Exception as exc:
        return {"content": [{"type": "text", "text": f"Error: {exc}"}], "is_error": True}
    return {"content": [{"type": "text", "text": text}]}


@tool(
    "pyhf_cls",
    "Compute the observed and expected CLs values for a pyhf workspace at a given signal "
    "strength (default mu=1). Pass the directory containing the background-only workspace "
    "(and patchset.json), and optionally a patch_name selecting the signal point. "
    "CLs < 0.05 means the point is excluded at 95% CL. This runs a real maximum-likelihood "
    "fit and can take up to a few minutes for large workspaces.",
    {"workspace_dir": str, "patch_name": str, "poi_value": float},
)
async def pyhf_cls(args: dict[str, Any]) -> dict[str, Any]:
    try:
        text = compute_cls(
            args["workspace_dir"],
            patch_name=args.get("patch_name") or None,
            poi_value=float(args.get("poi_value") or 1.0),
        )
    except Exception as exc:
        return {"content": [{"type": "text", "text": f"Error: {exc}"}], "is_error": True}
    return {"content": [{"type": "text", "text": text}]}


TOOLS = [pyhf_list_patches, pyhf_cls]
