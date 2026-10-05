# ─── CGRF Header ───────────────────────────────────────────────
# File:        compiler/cross_guild_check.py
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

"""Validate relationships and ownership across a complete set of guilds."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compiler.graphs import cycle_nodes, domains_overlap, subjects_overlap
from compiler.validate import ValidationResult, validate_guild


def check_guilds(roots: list[Path]) -> list[str]:
    """Check unique identities, graph consistency, contracts and namespace claims."""
    errors: list[str] = []
    guilds: dict[str, ValidationResult] = {}
    if not roots:
        return ["at least one guild is required"]
    for root in roots:
        result = validate_guild(root)
        if result.errors:
            errors.extend(f"{root}: {error}" for error in result.errors)
            continue
        guild_id = result.documents["governance/guild.yaml"]["guild_id"]
        if guild_id in guilds:
            errors.append(f"duplicate guild_id: {guild_id}")
        guilds[guild_id] = result
    if errors:
        return errors

    parents: dict[str, set[str]] = {}
    organization: dict[str, set[str]] = {}
    dependencies: dict[str, set[str]] = {}
    declarations: dict[tuple[str, str], set[str]] = {}
    namespaces: list[tuple[str, str]] = []
    domains: list[dict[str, Any]] = []
    for guild_id, result in guilds.items():
        docs = result.documents
        hierarchy = docs["governance/hierarchy.yaml"]
        for edge in hierarchy["organizational_hierarchy"]:
            parent, child = edge["parent"], edge["child"]
            for node in (parent, child):
                if node not in guilds:
                    errors.append(f"hierarchy: unknown guild {node}; supply the complete guild set")
            parents.setdefault(child, set()).add(parent)
            organization.setdefault(parent, set()).add(child)
            declarations.setdefault((parent, child), set()).add(guild_id)
        domains.extend(hierarchy["domain_authority"])
        events = docs["contracts/events/namespace.yaml"]
        namespaces.extend((guild_id, subject) for subject in events["canonical"])
        namespaces.extend((guild_id, alias["alias"]) for alias in events["deprecated_aliases"])
        contracts = docs["contracts/capabilities.yaml"]
        for contract in contracts["provides"]:
            for consumer in contract["consumers"]:
                if consumer not in guilds:
                    errors.append(f"{guild_id}: unknown consumer {consumer}")
        for dependency in contracts["requires"]:
            provider = dependency["guild_id"]
            dependencies.setdefault(guild_id, set()).add(provider)
            if provider not in guilds:
                errors.append(f"{guild_id}: unknown dependency guild {provider}")
                continue
            provided = guilds[provider].documents["contracts/capabilities.yaml"]["provides"]
            contract = next((c for c in provided if c["id"] == dependency["capability_id"]), None)
            if contract is None:
                errors.append(f"{guild_id}: unresolved capability {provider}/{dependency['capability_id']}")
            elif guild_id not in contract["consumers"]:
                errors.append(f"{guild_id}: not an allowed consumer of {provider}/{contract['id']}")

    for child, candidates in sorted(parents.items()):
        if len(candidates) > 1:
            errors.append(f"hierarchy conflict: {child} has multiple parents {sorted(candidates)}")
    for (parent, child), declared_by in sorted(declarations.items()):
        if declared_by != {parent, child}:
            errors.append(f"hierarchy conflict: {parent} -> {child} lacks both endpoints' acknowledgement")
    for label, graph in (("organizational hierarchy", organization), ("capability dependencies", dependencies)):
        cyclic = cycle_nodes(graph)
        if cyclic:
            errors.append(f"circular {label}: {', '.join(cyclic)}")
    for index, (owner, subject) in enumerate(namespaces):
        for other_owner, other_subject in namespaces[:index]:
            if owner != other_owner and subjects_overlap(subject, other_subject):
                errors.append(f"namespace collision: {owner}:{subject} overlaps {other_owner}:{other_subject}")
    for index, claim in enumerate(domains):
        for other in domains[:index]:
            if not domains_overlap(str(claim["domain"]), str(other["domain"])):
                continue
            shared = set(claim["capabilities"]) & set(other["capabilities"])
            if claim["owner"] == other["owner"]:
                conflict = bool(shared) and claim["authority_level"] != other["authority_level"]
            else:
                conflict = bool(claim["exclusive"] or other["exclusive"] or shared)
            if conflict:
                errors.append(f"authority overlap: {claim['owner']}:{claim['domain']} / {other['owner']}:{other['domain']}")
    return sorted(errors)


def main(argv: list[str] | None = None) -> int:
    """Print cross-guild diagnostics and return a nonzero status on conflicts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guilds", nargs="+", type=Path)
    args = parser.parse_args(argv)
    errors = check_guilds(args.guilds)
    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(f"PASS {len(args.guilds)} guild(s): no structural ownership conflicts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
