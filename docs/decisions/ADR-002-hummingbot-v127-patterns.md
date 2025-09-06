# ADR-002: Modern Hummingbot v1.27+ Patterns

## Status
**Accepted** - 2025-09-06

## Context
Hummingbot has evolved significantly in recent versions, introducing modern patterns for connector development. The project must decide between using legacy connector patterns or adopting the latest architectural improvements.

**Key Evolution Areas:**
- AsyncThrottler for advanced rate limiting
- WebAssistants for connection management  
- Modern order lifecycle management
- Enhanced error handling patterns
- Improved monitoring and observability integration

**Legacy vs Modern Trade-offs:**
- Legacy: Well-documented, battle-tested, simpler
- Modern: Better performance, more features, future-aligned

## Decision
**Adopt Hummingbot v1.27+ modern connector patterns** throughout the codebase.

**Core Components:**
- **AsyncThrottler**: Advanced rate limiting and request batching
- **WebAssistants**: Modern HTTP client management with connection pooling
- **Modern OrderTracker**: Enhanced order lifecycle with detailed state management
- **Structured Logging**: Comprehensive observability integration

## Consequences

### Positive ✅
- **Performance**: Significant improvements in throughput and latency
- **Reliability**: Better error handling and connection resilience  
- **Observability**: Rich metrics and logging for production operations
- **Future-Proof**: Aligned with Hummingbot roadmap and community direction
- **Maintainability**: Cleaner separation of concerns and testability

### Negative ⚠️
- **Learning Curve**: Team must understand new patterns and APIs
- **Documentation**: Less community examples for newest patterns
- **Migration Risk**: Potential breaking changes in future Hummingbot versions
- **Complexity**: More sophisticated patterns require deeper understanding

## Alternatives Considered

1. **Legacy Hummingbot Patterns (v1.20-)**
   - ✅ Well-documented with many examples
   - ✅ Simpler implementation
   - ❌ Performance limitations
   - ❌ Missing modern features

2. **Hybrid Approach**
   - ❌ Inconsistent patterns across codebase
   - ❌ Maintenance complexity
   - ❌ Testing complications

3. **Custom Framework**
   - ❌ Massive development effort
   - ❌ Loss of Hummingbot ecosystem benefits
   - ❌ Maintenance burden

## Implementation Strategy

### Phase 1: Core Infrastructure
```python
# Modern WebAssistant pattern
class StellarWebAssistant:
    def __init__(self):
        self.throttler = AsyncThrottler(rate_limits)
        self.session_manager = WebAssistantsFactory()
```

### Phase 2: Order Management
```python
# Enhanced order tracking
class StellarOrderTracker:
    async def track_order_lifecycle(self, order_id: str):
        # Modern state management with detailed tracking
```

### Phase 3: Integration Testing
- Comprehensive integration tests with modern patterns
- Performance benchmarking against legacy approaches
- Load testing with production-like scenarios

## Migration Path
1. **New Development**: Use modern patterns exclusively
2. **Existing Code**: Refactor incrementally during maintenance
3. **Critical Path**: Prioritize high-impact components first
4. **Testing**: Maintain compatibility during transition

## References
- [Hummingbot v1.27+ Documentation](https://docs.hummingbot.org/)
- [stellar_sdex_tdd_v3.md](../../stellar_sdex_tdd_v3.md) - Implementation patterns
- [Hummingbot Connector Guidelines](https://docs.hummingbot.org/developers/connectors/)