# ─── CGRF Header ───────────────────────────────────────────────
# File:        compiler/materialize.py
# Stage:       07_BUILD
# SRS:         SRS-GUILD-BOOTSTRAP-001
# CAPS:        pending
# CK:          pending
# Dispatch:    user-authorized-bootstrap
# Seat:        BITS-CODEGEN
# Owner:       Citadel Nexus Inc.
# Created:     2026-10-05
# Depends:     none
# EnumType:    Service
# EnumEdges:   DEPENDS_ON SRS-GUILD-BOOTSTRAP-001
# DAG Node:    none
# Intent:      Validate guild contracts locally without granting runtime authority.
# ───────────────────────────────────────────────────────────────

"""Generate a validated draft guild skeleton without replacing existing files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compiler.validate import REQUIRED_FILES, SCHEMA_ROOT, read_source, validate_guild
from compiler.yaml_subset import CitadelError


class MaterializeError(CitadelError):
    """Report an unsafe or invalid skeleton generation request."""


def _replace_scalar(source: str, key: str, value: str) -> str:
    return re.sub(rf"^{re.escape(key)}:.*$", lambda _: f"{key}: {json.dumps(value)}", source, flags=re.MULTILINE)


def materialize(destination: Path, guild_id: str, name: str, template: Path | None = None) -> Path:
    """Create a new draft from the bootstrap template and validate before publishing."""
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", guild_id):
        raise MaterializeError("guild-id must use lowercase letters, digits and single hyphens")
    if not name.strip() or any(ord(char) < 32 for char in name):
        raise MaterializeError("name must be nonempty and contain no control characters")
    # Check before resolve(), which would hide a dangling destination symlink.
    if destination.exists() or destination.is_symlink():
        raise MaterializeError("destination already exists; refusing to overwrite")
    destination = destination.absolute()
    if not destination.parent.is_dir():
        raise MaterializeError("destination parent must already exist")
    source_root = (template or SCHEMA_ROOT.parent).resolve()
    if destination.resolve().is_relative_to(source_root):
        raise MaterializeError("destination must be outside the source template")
    template_result = validate_guild(source_root)
    if template_result.errors:
        raise MaterializeError("source template is invalid: " + "; ".join(template_result.errors))
    if template_result.documents["governance/guild.yaml"]["status"] != "draft":
        raise MaterializeError("source must be a draft bootstrap template")
    # An arbitrary instantiated guild may contain approved grants. Never clone them.
    authority = template_result.documents["governance/authority.yaml"]["levels"]
    if any(level["approval"] != "pending" or level["capabilities"] for level in authority.values()):
        raise MaterializeError("source template must have no approved authority")
    template_id = template_result.documents["governance/guild.yaml"]["guild_id"]
    namespace = template_result.documents["contracts/events/namespace.yaml"]
    hierarchy = template_result.documents["governance/hierarchy.yaml"]
    contracts = template_result.documents["contracts/capabilities.yaml"]
    if (hierarchy["organizational_hierarchy"] or hierarchy["domain_authority"]
            or contracts["provides"] or contracts["requires"]
            or namespace["canonical"] != [f"citadel.{template_id}.>"] or namespace["deprecated_aliases"]):
        raise MaterializeError("source must be an isolated draft with only its default namespace reservation")
    template_files = set(REQUIRED_FILES) | set(template_result.documents)
    # Use the compiler's own schemas/toolchain, never an untrusted template's code.
    toolchain = SCHEMA_ROOT.parent
    files = {relative: source_root for relative in sorted(template_files)}
    for directory, pattern in (("schemas", "*.schema.yaml"), ("compiler", "*.py")):
        for path in sorted((toolchain / directory).glob(pattern)):
            files[path.relative_to(toolchain).as_posix()] = toolchain
    files["compiler/README.md"] = toolchain
    stage = Path(tempfile.mkdtemp(prefix=".guild-bootstrap-", dir=destination.parent))
    published = False
    try:
        for relative, origin in files.items():
            text = read_source(origin, relative)
            if relative in template_files:
                # Replace only identity fields; preserve source provenance and policy text.
                for key in ("guild_id", "dd-service", "owner"):
                    text = _replace_scalar(text, key, guild_id)
                if relative == "governance/guild.yaml":
                    text = _replace_scalar(text, "display_name", name)
                if relative == "contracts/events/namespace.yaml":
                    text = text.replace(f"citadel.{template_id}.", f"citadel.{guild_id}.")
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        result = validate_guild(stage, stage / "schemas")
        if result.errors:
            raise MaterializeError("generated skeleton is invalid: " + "; ".join(result.errors))
        # mkdir is exclusive: never replace a destination created concurrently.
        destination.mkdir()
        published = True
        shutil.copytree(stage, destination, dirs_exist_ok=True)
    except (OSError, UnicodeError, CitadelError) as exc:
        if published:
            shutil.rmtree(destination)
        if isinstance(exc, MaterializeError):
            raise
        raise MaterializeError(str(exc)) from exc
    finally:
        shutil.rmtree(stage)
    return destination


def main(argv: list[str] | None = None) -> int:
    """Create a skeleton from command-line inputs and report validation status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--guild-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--template", type=Path)
    args = parser.parse_args(argv)
    try:
        path = materialize(args.destination, args.guild_id, args.name, args.template)
    except (CitadelError, OSError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(f"PASS {path}: draft created with pending authority and no capability grants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
