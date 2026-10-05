# ─── CGRF Header ───────────────────────────────────────────────
# File:        compiler/graphs.py
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

"""Provide graph and NATS subject checks shared by the compiler commands."""

from __future__ import annotations


def subjects_overlap(left: str, right: str) -> bool:
    """Determine whether two valid NATS patterns can match the same subject."""
    a, b = left.split("."), right.split(".")
    for index in range(min(len(a), len(b))):
        if a[index] == ">" or b[index] == ">":
            return True  # A terminal > consumes at least one remaining token.
        if a[index] != b[index] and a[index] != "*" and b[index] != "*":
            return False
    return len(a) == len(b)


def cycle_nodes(edges: dict[str, set[str]]) -> list[str]:
    """Return nodes in or blocked by cycles using an iterative topological pass."""
    nodes = set(edges) | {node for children in edges.values() for node in children}
    incoming = dict.fromkeys(nodes, 0)
    for children in edges.values():
        for child in children:
            incoming[child] += 1
    ready = sorted(node for node, count in incoming.items() if count == 0)
    while ready:
        node = ready.pop()
        for child in sorted(edges.get(node, set())):
            incoming[child] -= 1
            if incoming[child] == 0:
                ready.append(child)
    return sorted(node for node, count in incoming.items() if count)


def domains_overlap(left: str, right: str) -> bool:
    """Treat a domain and its dot-separated subdomains as overlapping scope."""
    return left == right or left.startswith(right + ".") or right.startswith(left + ".")
