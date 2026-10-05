<!--
# ─── CGRF Header ───────────────────────────────────────────────
# File:        compiler/README.md
# Stage:       06_PLAN
# SRS:         SRS-GUILD-BOOTSTRAP-001
# CAPS:        pending
# CK:          pending
# Dispatch:    user-authorized-bootstrap
# Seat:        BITS-CODEGEN
# Owner:       Citadel Nexus Inc.
# Created:     2026-10-05
# Depends:     none
# EnumType:    Doc
# EnumEdges:   DEPENDS_ON SRS-GUILD-BOOTSTRAP-001
# DAG Node:    none
# Intent:      Document compiler contracts, limitations and reproducible validation.
# ───────────────────────────────────────────────────────────────
-->

# Guild governance compiler

Requires Python 3.11+. Uses only the standard library; no package installation,
network access, PyYAML, NATS connection or Datadog credentials are required.
Existing TypeScript SDK scaffolding is independent of this package.

```sh
python -m unittest discover -s tests -p 'test_*.py'
python -m compiler.validate .
python -m compiler.cross_guild_check .
python -m compiler.materialize ../guild-example --guild-id guild-example --name "Example Guild"
python -m compiler.validate ../guild-example
python -m compiler.cross_guild_check . ../guild-example
```

The three entry points also work as `python compiler/validate.py PATH` (and the
corresponding other filenames), including from outside the repository. Exit 0
means PASS; malformed data, missing files and conflicts return 1 with diagnostics.
Argument errors return 2. Validation never executes verification strings.

## Contract layout

The seven `schemas/*.schema.yaml` files use a documented JSON Schema 2020-12
subset. Root schemas cover guild identity plus its fourteen constitutional
sections, hierarchy, authority, a role, mandates, capabilities and event ownership.
`roles.$defs` covers escalation and delegation; `mandates.$defs` covers SLOs,
cadence, the SRS registry and the Datadog service catalog declaration.
The compiler uses the schemas shipped beside its own code, so validating an
external guild does not let that guild choose a weaker contract. Generated
skeletons receive a copy of both compiler and schemas.

Required template files are enumerated in `compiler/validate.py`. Additional
YAML role and delegation files are discovered recursively in their respective
directories. Each must have a path-correct CGRF envelope and a registered SRS.
Missing required files, symlinked governance paths, unknown properties, duplicate
IDs, malformed structures, stale references and unanswered ratified prompts fail.
CGRF checks validate envelope structure and provenance fields, not cryptographic
stamps, CKS/CAPS grades or external dispatch status.

## Supported YAML

Use UTF-8, two spaces per indentation level and one document per file. Supported:

- Block mappings with plain ASCII identifier keys, including `$defs` and hyphens.
- Block sequences, including conventional `- key: value` mapping entries.
- Plain strings, JSON double-quoted strings, YAML single-quoted strings with
  doubled quotes, integers, finite floats, lowercase `true`/`false` and `null`/`~`.
- Single-line JSON arrays and objects, including empty `[]` and `{}`.
- Full-line comments and whitespace-delimited trailing comments outside quotes.

Use quotes for strings containing colon-space, comment markers or leading YAML
indicators. There is no implicit date or yes/no/on/off boolean coercion. Tags,
anchors, aliases, merge keys, directives, document markers, block scalars,
multiline flow values, arbitrary YAML flow syntax, complex/quoted block keys,
non-finite numbers, duplicate keys and tabs are rejected. Documents are limited
to 1 MB and 40 nesting levels. This is an intentionally limited parser, not a
general YAML implementation; unsupported syntax must be rewritten explicitly.

Supported schema validation keywords: `type`, `properties`, `required`,
`additionalProperties` (boolean only), `items`, `enum`, `const`, `pattern`,
`minLength`, `minItems`, `maxItems`, `uniqueItems`, `minimum`, `maximum`.
`$schema`, `title`, `description` and `$defs` are accepted metadata/definitions.
Unknown keywords fail schema compilation. `$ref`, composition and format
keywords are not implemented. The compiler checks dates and references itself.

## Authority and graph semantics

A1-A9 are explicit capability slots. Their production meanings were not supplied;
all start pending and empty. Approval requires a human-role reference. No level
inherits another level's capabilities. A role's numbered level is also its
maximum delegation ceiling, but numbers alone never grant capabilities.
A usable capability must be listed in an approved level and role, within a
ratified constitution. Service contracts additionally require an explicit domain
grant and SLO reference. Active delegations must fit both roles' capabilities
and ceilings, match domain grants, identify a human approver and have a future
UTC-offset-aware expiry. Draft/revoked delegations confer no authority.
These are declaration checks; runtime identity and authorization enforcement
remain the consuming system's responsibility.

Organizational parentage conveys no domain authority. Supply the complete guild
set to cross-check: each relationship requires both endpoints' acknowledgement,
a child may have only one parent, and organizational cycles are rejected.
Dot-separated domains include their subdomains. An exclusive grant conflicts
with any overlapping guild grant. Non-exclusive grants can share a domain only
when capability sets are disjoint. Overlapping grants within a guild cannot
assign the same capability to different authority levels.

Cross-guild service dependencies must resolve to a provided capability and an
explicit consumer allowlist entry. `input_schema` and `output_schema` are opaque
schema identifiers; resolving and validating their payload definitions belongs to
the consuming service. Dependencies must be acyclic. Unknown guilds
are errors; the compiler does not fetch external registries.

Canonical NATS patterns and deprecated aliases both reserve namespace ownership.
A `*` matches one token; a terminal `>` matches one or more tokens. Matching
patterns conflict even if their text differs. Local overlapping reservations
also fail. Each alias must target an exact canonical entry and include a reason
and real sunset date. Sunset does not automatically release ownership; remove
an alias through review after migration. No events are published by this tool.

## Materialization and review

Materialization copies validated template documents (including extra roles and
delegations) plus the running compiler and its schemas. Template-provided compiler
code is never copied. Source drafts must have no approved authority, relationships,
service dependencies or namespace reservations beyond their default namespace. It
excludes `.git`, secrets, `.codex`, SDK source, caches and arbitrary source files.
It requires an unused destination outside the template with an existing parent.
Existing destinations and symlinks are refused. Generation happens in a temporary
staging directory, is validated, then copied into an exclusively created target;
handled copy failures remove the partial target. Abrupt process termination may
leave a partial target, which must be inspected before retrying. Concurrent writes
to the same destination are unsupported.

Guild identity, display name, event namespace and Datadog service identity are
substituted as scalar values, never evaluated as code. CGRF bootstrap provenance
is preserved. Generated output is a draft with no approved grants. Read and
ratify the fourteen constitutional prompts, supply approved capability mappings,
and record operational SRS/dispatch context before using it for live work.
The bootstrap SRS and dispatch marker describe this local creation only; they
do not manufacture a VCC authorization. SLOs are proposed targets and the Datadog
file is a catalog declaration, not proof of deployed or observed telemetry.

Markdown and machine constitutional content require human consistency review;
the compiler checks sections and prompt completion, not semantic equivalence.
