# Architecture Decision Records (ADRs)

## Purpose
This directory contains Architecture Decision Records (ADRs) for the Stellar Hummingbot Connector v3.0 project. ADRs document significant architectural and technical decisions made during development.

## Format
Each ADR follows the standard format:
- **Status**: Proposed | Accepted | Rejected | Deprecated | Superseded
- **Context**: What is the issue that we're seeing that is motivating this decision?
- **Decision**: What is the change that we're proposing or doing?
- **Consequences**: What becomes easier or more difficult to do because of this change?
- **Alternatives**: What other options were considered?

## Naming Convention
ADRs are numbered sequentially: `ADR-001-decision-title.md`

## Index of Decisions

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](ADR-001-stellar-sdk-v8-adoption.md) | Stellar SDK v8.x Adoption | Accepted | 2025-09-06 |
| [ADR-002](ADR-002-hummingbot-v127-patterns.md) | Modern Hummingbot v1.27+ Patterns | Accepted | 2025-09-06 |
| [ADR-003](ADR-003-enterprise-security-framework.md) | Enterprise Security Framework | Accepted | 2025-09-06 |
| [ADR-004](ADR-004-async-architecture-choice.md) | AsyncIO-Based Architecture | Accepted | 2025-09-06 |

## Process
1. Create new ADR when making significant architectural decisions
2. Start with status "Proposed"
3. Change to "Accepted" when decision is finalized
4. Update index table above
5. Reference ADR in relevant code and documentation