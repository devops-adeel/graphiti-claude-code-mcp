# Graphiti Memory Layer Architecture

## Overview
This memory layer extends Graphiti v0.17.9 with temporal management, cross-domain insights, and memory supersession while respecting Graphiti's immutable episode design.

## Key Architectural Decisions

### 1. Episode Immutability
**Decision**: Never modify existing episodes; create new ones for updates.

**Rationale**: 
- Graphiti episodes are immutable once created
- Preserves complete audit trail
- Enables temporal analysis of knowledge evolution

**Implementation**:
- `supersede_memory()` creates new episodes with metadata linking to old ones
- Status tracked in episode metadata, not as object attributes
- All history preserved for analysis

### 2. Temporal Weighting Layer
**Decision**: Compute temporal scores at search time, not storage time.

**Rationale**:
- Keeps stored data pure and unchanging
- Allows dynamic adjustment of decay factors
- Enables different temporal strategies without data migration

**Implementation**:
```python
# Temporal weight calculated during search
temporal_weight = decay_factor ** age_days
final_score = base_score * temporal_weight * status_weight
```

### 3. Metadata Validation with Pydantic
**Decision**: Use Pydantic models for all metadata validation.

**Rationale**:
- Ensures consistent structure across memories
- Catches errors early in the pipeline
- Makes migration easier if Graphiti adds native fields
- Self-documenting data contracts

**Implementation**:
- `memory_models.py` defines strict schemas
- Each pattern type has its own model
- Validation happens before storage

### 4. SearchResultWrapper Abstraction
**Decision**: Wrap all search results in a consistent interface.

**Rationale**:
- Isolates us from Graphiti API changes
- Provides consistent access to computed fields
- Enables graceful handling of missing attributes

**Implementation**:
```python
class SearchResultWrapper:
    def __init__(self, result, computed_score=None, metadata=None):
        # Wraps EntityEdge or Episode objects
        # Provides unified interface
```

### 5. Version Detection
**Decision**: Detect Graphiti version at runtime and adapt behavior.

**Rationale**:
- Enables compatibility across versions
- Provides clear warnings for untested versions
- Allows conditional feature enablement

**Implementation**:
- Checks for `graphiti_core.__version__`
- Falls back gracefully if not available
- Logs compatibility warnings

## Data Flow

### Writing Memories
1. User calls capture method (e.g., `capture_tdd_cycle`)
2. Pydantic model validates metadata
3. Memory converted to episode format
4. Episode added to Graphiti (immutable)
5. UUID returned for reference

### Searching Memories
1. User queries with search term
2. Graphiti returns EntityEdge results
3. Results wrapped in SearchResultWrapper
4. Temporal weighting applied
5. Status filtering performed
6. Top results returned

### Superseding Memories
1. User provides old memory ID and new content
2. New episode created with supersession metadata
3. Old episode remains unchanged
4. Search results filter/weight based on status

## Compatibility Strategy

### Current Support
- **Graphiti v0.17.9**: Fully tested and supported
- **FalkorDB**: Primary database backend
- **Neo4j**: Secondary support

### Future Compatibility
- Version detection enables conditional logic
- Wrapper classes isolate API changes
- Metadata stored as JSON for flexibility
- Tests verify core assumptions

## Design Principles

1. **Immutability First**: Never modify existing data
2. **Compute at Query Time**: Temporal effects calculated when needed
3. **Fail Gracefully**: Missing attributes get sensible defaults
4. **Preserve History**: All knowledge evolution is traceable
5. **Validate Early**: Catch errors before they reach storage

## Extension Points

### Adding New Memory Types
1. Define Pydantic model in `memory_models.py`
2. Add capture method in `capture.py`
3. Register in MetadataFactory
4. Add tests in `test_compatibility.py`

### Custom Temporal Strategies
- Override `decay_factor` in configuration
- Implement custom weighting in `search_with_temporal_weight`
- Add new status types in MemoryStatus enum

### Integration with Other Systems
- GTD Coach integration via shared group_id
- Cross-domain insights through metadata analysis
- Command pattern recognition for automation

## Performance Considerations

### Token Management
- Automatic batching when results exceed token limits
- Smart truncation of large results
- Configurable max_tokens parameter

### Search Optimization
- Initial query gets 30 results
- Filtering and weighting reduce to top 10
- Pattern-based indexing for common queries

### Caching Strategy
- Singleton pattern for shared instances
- Pattern results cached with TTL
- Connection pooling via Graphiti client

## Error Handling

### Graceful Degradation
- Missing attributes return defaults
- Invalid JSON treated as empty metadata
- Failed searches retry with simplified queries

### User Feedback
- Clear error messages for configuration issues
- Warnings for untested versions
- Info logs for successful operations

## Testing Strategy

### Unit Tests
- Wrapper classes tested in isolation
- Metadata validation tests
- Version detection tests

### Integration Tests
- Mock Graphiti API responses
- Test temporal weighting calculations
- Verify supersession chains

### Compatibility Tests
- Test against different EntityEdge structures
- Verify handling of missing fields
- Test graceful degradation paths

## Future Enhancements

### Planned
- [ ] Batch memory operations for efficiency
- [ ] Advanced pattern recognition
- [ ] Memory compression for old entries
- [ ] Export/import functionality

### Under Consideration
- GraphQL API for complex queries
- Real-time memory synchronization
- Machine learning for pattern detection
- Automated memory gardening

## Maintenance Notes

### Regular Tasks
- Monitor FalkorDB memory usage
- Review supersession chains for cycles
- Update pattern indexes monthly
- Check for Graphiti updates

### Debugging Tips
- Enable DEBUG logging for detailed traces
- Check episode_body for metadata issues
- Verify group_id matches across systems
- Test FalkorDB connection independently

## Conclusion
This architecture provides a robust, extensible memory layer that enhances Graphiti's capabilities while respecting its constraints. The design prioritizes data integrity, temporal awareness, and cross-system compatibility.