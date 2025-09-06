# ADR-001: Stellar SDK v8.x Adoption

## Status
**Accepted** - 2025-09-06

## Context
The project requires integration with the Stellar network for DEX operations. Multiple Stellar SDK versions are available, with significant differences in capabilities and API design. The choice of SDK version fundamentally impacts:

- Available Stellar features (Soroban smart contracts, latest SEP standards)
- API patterns and development experience
- Long-term maintenance and upgrade path
- Integration complexity with modern Hummingbot patterns

**Key Requirements:**
- Full Soroban smart contract support for AMM operations
- Latest SEP standards (SEP-10, SEP-24, SEP-31) for compliance
- Modern async/await patterns for high-performance trading
- Production-grade error handling and resilience

## Decision
**Adopt Stellar Python SDK v8.x** as the primary blockchain interface layer.

**Implementation Pattern:**
```python
from stellar_sdk import ServerAsync, SorobanServer, TransactionBuilder
from stellar_sdk.sep import stellar_web_authentication
from stellar_sdk.contract import Contract
```

## Consequences

### Positive ✅
- **Full Soroban Support**: Native smart contract integration for AMM pools and custom trading logic
- **Latest Features**: Access to newest Stellar protocol features and optimizations
- **SEP Compliance**: Built-in support for regulatory compliance standards
- **Async Performance**: Native async/await support for high-throughput trading operations
- **Future-Proof**: Aligned with Stellar ecosystem direction and ongoing development

### Negative ⚠️
- **Breaking Changes Risk**: v8.x may have API changes compared to older versions
- **Documentation Gap**: Newer versions may have less community documentation
- **Dependency Complexity**: More complex dependency tree with additional features
- **Migration Effort**: Requires careful migration patterns if upgrading existing code

## Alternatives Considered

1. **Stellar SDK v7.x** 
   - ❌ Limited Soroban support
   - ❌ Missing latest SEP standards
   - ✅ More stable/mature documentation

2. **Custom Stellar Integration**
   - ❌ Massive development effort
   - ❌ Missing protocol-level optimizations
   - ❌ Maintenance burden

3. **Multiple SDK Approach**
   - ❌ Increased complexity
   - ❌ Potential version conflicts
   - ❌ Testing matrix explosion

## Implementation Notes
- Pin to specific v8.x minor version for stability: `stellar-sdk>=8.0,<8.1`
- Implement comprehensive error handling for SDK API changes
- Create abstraction layer to isolate SDK-specific code
- Maintain upgrade path documentation for future SDK versions

## References
- [Stellar SDK v8 Release Notes](https://stellar-sdk.readthedocs.io/)
- [stellar_sdex_tdd_v3.md](../../stellar_sdex_tdd_v3.md) - Technical implementation details
- [stellar_sdex_checklist_v3.md](../../stellar_sdex_checklist_v3.md) - Integration requirements