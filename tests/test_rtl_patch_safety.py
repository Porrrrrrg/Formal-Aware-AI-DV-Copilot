from __future__ import annotations

from pathlib import Path

import pytest

from tools.apply_rtl_patch import apply_rtl_patch
from tools.rtl_patch_safety import PatchSafetyError, validate_patch_paths


def write_unit(path: Path, value: str = "assign y = a;\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "module unit(input logic a, output logic y);\n"
        f"  {value}"
        "endmodule\n",
        encoding="utf-8",
    )
    return path


def patch_for(path: str, old: str = "assign y = a;", new: str = "assign y = !a;") -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1,3 +1,3 @@\n"
        " module unit(input logic a, output logic y);\n"
        f"-  {old}\n"
        f"+  {new}\n"
        " endmodule\n"
    )


def test_rejects_path_traversal(tmp_path: Path) -> None:
    rtl = write_unit(tmp_path / "rtl" / "unit.sv")

    with pytest.raises(PatchSafetyError, match="traversal"):
        validate_patch_paths(patch_for("../evil.sv"), [rtl], tmp_path)


def test_rejects_non_rtl_file(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("hello\n", encoding="utf-8")

    with pytest.raises(PatchSafetyError, match="not an RTL file"):
        validate_patch_paths(
            "diff --git a/README.md b/README.md\n"
            "--- a/README.md\n"
            "+++ b/README.md\n"
            "@@ -1 +1 @@\n"
            "-hello\n"
            "+goodbye\n",
            [readme],
            tmp_path,
        )


def test_applies_patch_to_scratch_and_preserves_original(tmp_path: Path) -> None:
    rtl = write_unit(tmp_path / "rtl" / "unit.sv")
    scratch = tmp_path / "scratch"

    manifest = apply_rtl_patch(
        unified_diff=patch_for("rtl/unit.sv"),
        allowed_patch_files=[rtl],
        scratch_dir=scratch,
        repo_root=tmp_path,
    )

    assert "assign y = a;" in rtl.read_text(encoding="utf-8")
    scratch_file = scratch / "rtl" / "unit.sv"
    assert "assign y = !a;" in scratch_file.read_text(encoding="utf-8")
    assert Path(str(manifest["manifest_path"])).is_file()
    assert manifest["apply_in_place"] is False


def test_apply_in_place_requires_acknowledgement(tmp_path: Path) -> None:
    rtl = write_unit(tmp_path / "rtl" / "unit.sv")

    with pytest.raises(PatchSafetyError, match="acknowledge"):
        apply_rtl_patch(
            unified_diff=patch_for("rtl/unit.sv"),
            allowed_patch_files=[rtl],
            scratch_dir=tmp_path / "scratch",
            repo_root=tmp_path,
            apply_in_place=True,
            acknowledge_risk=False,
        )
