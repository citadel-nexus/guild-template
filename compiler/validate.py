# ─── CGRF Header ───────────────────────────────────────────────
# File:        compiler/validate.py
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

"""Validate a guild's local constitutional governance package."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
import re
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compiler.schema import check_schema, validate_value
from compiler.yaml_subset import CitadelError, MAX_BYTES, load


SCHEMA_ROOT = Path(__file__).resolve().parents[1] / "schemas"
SECTIONS = (
    "identity", "purpose", "jurisdiction", "reserved_powers", "prohibited_powers",
    "parent_children", "human_authority", "agent_authority", "delegation", "escalation",
    "truth_requirements", "amendment_procedure", "succession", "dissolution",
)
DOCUMENT_SCHEMAS = {
    "governance/guild.yaml": ("constitution", None),
    "governance/hierarchy.yaml": ("hierarchy", None),
    "governance/authority.yaml": ("authority", None),
    "governance/escalation.yaml": ("roles", "escalation"),
    "governance/mandates.yaml": ("mandates", None),
    "roles/human/_template.yaml": ("roles", None),
    "roles/agents/_template.yaml": ("roles", None),
    "contracts/capabilities.yaml": ("capabilities", None),
    "contracts/events/namespace.yaml": ("events", None),
    "contracts/delegation/_template.yaml": ("roles", "delegation"),
    "operations/SLO.yaml": ("mandates", "slos"),
    "operations/cadence.yaml": ("mandates", "cadence"),
    ".bits/srs_registry.yml": ("mandates", "registry"),
    "service.datadog.yaml": ("mandates", "service"),
}
MARKDOWN_FILES = (
    "CONSTITUTION.md", "AGENTS.md", "CLAUDE.md", ".bits/context.md",
    "operations/RUNBOOK.md", "operations/INCIDENTS.md",
)
REQUIRED_FILES = tuple(DOCUMENT_SCHEMAS) + MARKDOWN_FILES
HEADER_FIELDS = (
    "File", "Stage", "SRS", "CAPS", "CK", "Dispatch", "Seat", "Owner", "Created",
    "Depends", "EnumType", "EnumEdges", "DAG Node", "Intent",
)
STAGES = {f"{i:02}_{name}" for i, name in enumerate((
    "WAKE", "RECALL", "ORIENT", "HYPOTHESIZE", "EVIDENCE", "PLAN", "BUILD",
    "TEST", "LEARN", "REVIEW", "COMMIT", "STATUS", "SAVE", "LOOP",
), 1)}


@dataclass
class ValidationResult:
    """Collect parsed documents and actionable diagnostics."""

    root: Path
    documents: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def check_envelope(source: str, relative: str) -> list[str]:
    """Check the top-of-file CGRF envelope without asserting stamp validity."""
    lines = source.splitlines()
    start = 1 if lines and (lines[0] == "<!--" or lines[0].startswith("#!")) else 0
    if len(lines) <= start or not lines[start].startswith("# ─── CGRF Header"):
        return [f"{relative}: missing top-of-file CGRF envelope"]
    fields: dict[str, str] = {}
    errors: list[str] = []
    closed = False
    for offset, line in enumerate(lines[start + 1:start + 24], start + 1):
        if line.startswith("# ───"):
            closed = True
            if relative.endswith(".md") and (offset + 1 >= len(lines) or lines[offset + 1] != "-->"):
                errors.append(f"{relative}: markdown CGRF envelope must close its HTML comment")
            break
        match = re.fullmatch(r"# ([A-Za-z ]+):\s*(.*)", line)
        if not match:
            errors.append(f"{relative}: malformed CGRF field")
            continue
        key, value = match.groups()
        if key in fields:
            errors.append(f"{relative}: duplicate CGRF field {key}")
        fields[key] = value.strip()
    if not closed:
        errors.append(f"{relative}: unterminated CGRF envelope")
    for key in HEADER_FIELDS:
        if not fields.get(key):
            errors.append(f"{relative}: missing CGRF {key}")
    if fields.get("File") != relative:
        errors.append(f"{relative}: CGRF File must match relative path")
    if fields.get("Owner") != "Citadel Nexus Inc.":
        errors.append(f"{relative}: incorrect CGRF legal owner")
    if fields.get("Stage") not in STAGES:
        errors.append(f"{relative}: invalid CGRF stage")
    try:
        date.fromisoformat(fields.get("Created", ""))
    except ValueError:
        errors.append(f"{relative}: invalid CGRF creation date")
    return errors


def read_source(root: Path, relative: str) -> str:
    """Read a bounded local file and reject symlinked governance paths."""
    path = root / relative
    for candidate in (path, *path.parents):
        if candidate == root:
            break
        if candidate.is_symlink():
            raise CitadelError(f"{relative}: symlinks are not allowed")
    if not path.is_file():
        raise CitadelError(f"{relative}: required file missing")
    if path.stat().st_size > MAX_BYTES:
        raise CitadelError(f"{relative}: file exceeds size limit")
    return path.read_text(encoding="utf-8")


def _indexed(items: list[dict[str, Any]], key: str, path: str, errors: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in items:
        if item[key] in result:
            errors.append(f"{path}: duplicate {key} {item[key]}")
        result[item[key]] = item
    return result


def _semantics(result: ValidationResult) -> None:
    docs, errors = result.documents, result.errors
    guild = docs["governance/guild.yaml"]
    guild_id = guild["guild_id"]
    levels = docs["governance/authority.yaml"]["levels"]
    role_docs = [doc for path, doc in docs.items() if path.startswith("roles/")]
    roles = _indexed(role_docs, "role_id", "roles", errors)
    escalation = docs["governance/escalation.yaml"]
    routes = _indexed(escalation["routes"], "id", "escalation", errors)
    slos = _indexed(docs["operations/SLO.yaml"]["slos"], "id", "SLO", errors)
    cadences = _indexed(docs["operations/cadence.yaml"]["cadences"], "id", "cadence", errors)
    _indexed(docs["governance/mandates.yaml"]["mandates"], "id", "mandates", errors)
    _indexed(docs[".bits/srs_registry.yml"]["srs"], "code", "SRS registry", errors)

    def ref(value: str, target: dict[str, Any], context: str) -> None:
        if value not in target:
            errors.append(f"{context}: unknown reference {value}")

    def grant(level: str, capabilities: list[str], context: str) -> None:
        ref(level, levels, context)
        if level not in levels:
            return
        definition = levels[level]
        if capabilities and (definition["approval"] != "approved" or guild["status"] != "ratified"):
            errors.append(f"{context}: capabilities require approved authority and a ratified constitution")
        if set(capabilities) - set(definition["capabilities"]):
            errors.append(f"{context}: capabilities exceed {level}")

    for name, level in levels.items():
        if level["approval"] == "approved" and not level["approved_by"].strip():
            errors.append(f"authority.{name}: approved level requires a human approver")
        elif level["approval"] == "approved":
            ref(level["approved_by"], roles, f"authority.{name}.approved_by")
            if roles.get(level["approved_by"], {}).get("kind") != "human":
                errors.append(f"authority.{name}: approver must be a human role")
        if level["capabilities"] and level["approval"] != "approved":
            errors.append(f"authority.{name}: pending level must have no capabilities")
    ref(escalation["default_route"], routes, "escalation.default_route")
    for route in routes.values():
        ref(route["to_role"], roles, f"escalation.{route['id']}")
        if roles.get(route["to_role"], {}).get("kind") != "human":
            errors.append(f"escalation.{route['id']}: route must terminate at a human role")
    for path, role in docs.items():
        if not path.startswith("roles/"):
            continue
        expected = "human" if path.startswith("roles/human/") else "agent"
        if role["kind"] != expected:
            errors.append(f"{path}: role kind does not match directory")
        grant(role["authority_level"], role["capabilities"], path)
        ref(role["escalation"], routes, f"{path}.escalation")
    for cadence in cadences.values():
        ref(cadence["owner_role"], roles, f"cadence.{cadence['id']}")
    for mandate in docs["governance/mandates.yaml"]["mandates"]:
        ref(mandate["owner_role"], roles, f"mandate.{mandate['id']}.owner_role")
        ref(mandate["cadence"], cadences, f"mandate.{mandate['id']}.cadence")
        for slo in mandate["slos"]:
            ref(slo, slos, f"mandate.{mandate['id']}.slos")

    domain_grants = docs["governance/hierarchy.yaml"]["domain_authority"]
    for entry in domain_grants:
        if entry["owner"] != guild_id:
            errors.append("hierarchy.domain_authority: a guild may declare only its own domain grants")
        grant(entry["authority_level"], entry["capabilities"], f"domain.{entry['domain']}")
    for edge in docs["governance/hierarchy.yaml"]["organizational_hierarchy"]:
        if edge["parent"] == edge["child"]:
            errors.append("hierarchy: self-parent relationship")
        if guild_id not in edge.values():
            errors.append("hierarchy: organizational edge must involve this guild")

    capabilities = docs["contracts/capabilities.yaml"]
    _indexed(capabilities["provides"], "id", "capabilities", errors)
    for contract in capabilities["provides"]:
        if contract["provider"] != guild_id:
            errors.append(f"capability.{contract['id']}: provider must match guild_id")
        grant(contract["authority_level"], [contract["id"]], f"capability.{contract['id']}")
        ref(contract["slo_ref"], slos, f"capability.{contract['id']}.slo_ref")
        if not any(g["domain"] == contract["domain"] and g["authority_level"] == contract["authority_level"]
                   and contract["id"] in g["capabilities"] for g in domain_grants):
            errors.append(f"capability.{contract['id']}: missing explicit domain grant")

    delegations = [doc for path, doc in docs.items() if path.startswith("contracts/delegation/")]
    _indexed(delegations, "delegation_id", "delegations", errors)
    for delegation in delegations:
        context = f"delegation.{delegation['delegation_id']}"
        for key in ("from_role", "to_role"):
            ref(delegation[key], roles, f"{context}.{key}")
        ref(delegation["revocation_route"], routes, f"{context}.revocation_route")
        if delegation["status"] != "active":
            continue
        grant(delegation["authority_level"], delegation["capabilities"], context)
        if not delegation["capabilities"] or not delegation["scope"]:
            errors.append(f"{context}: active delegation requires capabilities and scope")
        if roles.get(delegation["approved_by"], {}).get("kind") != "human":
            errors.append(f"{context}: active delegation requires a human approver")
        for key in ("from_role", "to_role"):
            role = roles.get(delegation[key])
            if role and (set(delegation["capabilities"]) - set(role["capabilities"])
                         or int(delegation["authority_level"][1:]) > int(role["authority_level"][1:])):
                errors.append(f"{context}: delegation exceeds {key} authority")
        for domain in delegation["scope"]:
            if not any(g["domain"] == domain and g["authority_level"] == delegation["authority_level"]
                       and set(delegation["capabilities"]) <= set(g["capabilities"]) for g in domain_grants):
                errors.append(f"{context}: scope lacks an explicit domain grant")
        try:
            expires = datetime.fromisoformat(delegation["expires_at"].replace("Z", "+00:00"))
            if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
                raise ValueError("expired or missing timezone")
        except ValueError:
            errors.append(f"{context}: active delegation needs a future timezone-aware expiry")

    namespace = docs["contracts/events/namespace.yaml"]
    if namespace["owner"] != guild_id:
        errors.append("events.owner: must match guild_id")
    _indexed(namespace["deprecated_aliases"], "alias", "events", errors)
    for alias in namespace["deprecated_aliases"]:
        if alias["canonical"] not in namespace["canonical"]:
            errors.append(f"events.{alias['alias']}: unknown canonical target")
        try:
            date.fromisoformat(alias["sunset"])
        except ValueError:
            errors.append(f"events.{alias['alias']}: invalid sunset date")
    # Import locally to keep the shared overlap primitive available to both CLIs.
    from compiler.graphs import subjects_overlap
    claims = namespace["canonical"] + [a["alias"] for a in namespace["deprecated_aliases"]]
    for index, subject in enumerate(claims):
        for other in claims[:index]:
            if subjects_overlap(subject, other):
                errors.append(f"events: overlapping namespace claims {other} / {subject}")
    if docs["service.datadog.yaml"]["dd-service"] != guild_id:
        errors.append("service.datadog.yaml: dd-service must match guild_id")


def validate_guild(root: Path, schema_root: Path | None = None) -> ValidationResult:
    """Validate required files, schema shape, provenance and local references."""
    root = root.resolve()
    result = ValidationResult(root)
    schemas: dict[str, Any] = {}
    for name in sorted({value[0] for value in DOCUMENT_SCHEMAS.values()}):
        try:
            schema = load((schema_root or SCHEMA_ROOT) / f"{name}.schema.yaml")
            check_schema(schema)
            schemas[name] = schema
        except (CitadelError, OSError, UnicodeError) as exc:
            result.errors.append(f"schema.{name}: {exc}")
    if result.errors:
        return result
    targets = dict(DOCUMENT_SCHEMAS)
    for directory, schema_key in (("roles/human", ("roles", None)),
                                  ("roles/agents", ("roles", None)),
                                  ("contracts/delegation", ("roles", "delegation"))):
        for pattern in ("*.yaml", "*.yml"):
            for path in sorted((root / directory).rglob(pattern)):
                targets[path.relative_to(root).as_posix()] = schema_key
    sources: dict[str, str] = {}
    for relative in (*targets, *MARKDOWN_FILES):
        try:
            source = read_source(root, relative)
            sources[relative] = source
            result.errors.extend(check_envelope(source, relative))
            if relative in targets:
                name, definition = targets[relative]
                schema = schemas[name]
                if definition:
                    if definition not in schema.get("$defs", {}):
                        raise CitadelError(f"schema.{name}: required definition {definition} missing")
                    schema = schema["$defs"][definition]
                doc = load(root / relative)
                result.errors.extend(validate_value(doc, schema, relative))
                result.documents[relative] = doc
        except (CitadelError, OSError, UnicodeError) as exc:
            result.errors.append(f"{relative}: {exc}")
    constitution = sources.get("CONSTITUTION.md", "")
    headings = [m.lower().replace(" ", "_") for m in re.findall(r"^## (.+)$", constitution, re.MULTILINE)]
    if tuple(headings) != SECTIONS:
        result.errors.append("CONSTITUTION.md: expected all 14 constitutional sections in canonical order")
    if result.errors:
        return result
    codes = {entry["code"] for entry in result.documents[".bits/srs_registry.yml"]["srs"]}
    for relative, source in sources.items():
        match = re.search(r"^# SRS:\s*(.+)$", source, re.MULTILINE)
        if match and any(code.strip() not in codes for code in match[1].split(",")):
            result.errors.append(f"{relative}: CGRF SRS is not registered")
    guild = result.documents["governance/guild.yaml"]
    if guild["status"] == "ratified":
        if any(not v.strip() or "PROMPT:" in v for v in guild["constitution"].values()) or "PROMPT:" in constitution:
            result.errors.append("constitution: ratified guild cannot contain unanswered prompts")
    _semantics(result)
    return result


def main(argv: list[str] | None = None) -> int:
    """Print validation diagnostics and return a shell-friendly exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guild", type=Path)
    args = parser.parse_args(argv)
    result = validate_guild(args.guild)
    if result.errors:
        for error in result.errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(f"PASS {args.guild}: structurally valid; runtime authorization is not asserted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
