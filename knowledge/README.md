# Knowledge Base System for Stellar Hummingbot Connector

This directory contains the automated knowledge base indexing system that maintains up-to-date documentation and code references for all team agents defined in `team_startup.yaml`.

## Overview

The knowledge base system automatically indexes and maintains references to:

- **Project Documentation** - Core specifications, checklists, and technical designs
- **Source Code** - Stellar connector implementation files
- **Quality Standards** - QA guidelines, test specifications, and acceptance criteria  
- **Security Guidelines** - Security best practices, threat models, and compliance requirements
- **Performance Baselines** - Performance metrics, optimization guides, and SLO definitions
- **DevOps Standards** - CI/CD workflows, deployment strategies, and infrastructure patterns

## Directory Structure

```
knowledge/
├── README.md                    # This file
├── security_best_practices.md  # Security guidelines and threat model
├── performance_baselines.md    # Performance metrics and optimization
├── devops_ci_cd.md             # CI/CD best practices and workflows
├── index/                      # Automated index files
│   ├── metadata.json           # Index metadata and file hashes
│   ├── sdk_docs.json          # Stellar SDK documentation index
│   ├── repo_index.json        # Repository code index
│   ├── security_standards.json # Security guidelines index
│   ├── performance_guides.json # Performance documentation index
│   ├── devops_standards.json   # DevOps standards index
│   ├── project_documentation.json # Core project docs index
│   ├── qa_framework.json       # QA framework index
│   └── architectural_decisions.json # ADR index
└── cache/                      # Cached external resources
```

## Knowledge Base Configuration

Knowledge bases are defined in `team_startup.yaml` under the `knowledge_base` section. Each agent references specific knowledge sources through the `rag.sources` array.

### Knowledge Base Types

1. **Web Resources** (`type: web`)
   - External documentation (Stellar SDK, Hummingbot guides)
   - Automatically cached and indexed

2. **Code Repositories** (`type: code`) 
   - Source code indexing with include/exclude patterns
   - File change tracking and incremental updates

3. **Single Files** (`type: file`)
   - Individual documentation files
   - Hash-based change detection

4. **Multi-File Collections** (`type: multi_file`)
   - Related document collections
   - Combined hash for change detection

5. **Directory Trees** (`type: directory`)
   - Complete directory indexing
   - Recursive file discovery

### Agent Knowledge Mappings

Each agent has access to relevant knowledge sources:

- **ProjectManager**: Project status, checklists, QA guidelines
- **Architect**: Technical designs, decisions, completion reports
- **SecurityEngineer**: Security standards, threat models, tracking data
- **QAEngineer**: QA framework, test specifications, CI workflows
- **Implementer**: Source code, QA guidelines, technical designs
- **DevOpsEngineer**: CI/CD workflows, deployment configurations
- **PerformanceEngineer**: Performance baselines, benchmarking code
- **DocumentationEngineer**: All documentation sources

## Automated Pipeline

### Core Scripts

1. **`scripts/knowledge_base_indexer.py`**
   - Main indexing engine
   - Supports incremental and full rebuilds
   - Generates comprehensive reports

2. **`scripts/knowledge_base_watcher.py`**
   - Real-time file monitoring
   - Automatic re-indexing on changes
   - Debounced updates to prevent thrashing

3. **`scripts/setup_knowledge_base_pipeline.sh`**
   - Complete pipeline setup
   - Dependency installation
   - Service configuration

### Usage Commands

```bash
# Setup the pipeline (run once)
./scripts/setup_knowledge_base_pipeline.sh

# Manual indexing
./scripts/kb-index                    # Quick wrapper
python scripts/knowledge_base_indexer.py --force    # Force rebuild
python scripts/knowledge_base_indexer.py --report   # Generate report

# Real-time monitoring
./scripts/kb-watch                    # Interactive monitoring
python scripts/knowledge_base_watcher.py --verbose  # Detailed logging

# Configuration validation
python scripts/validate_knowledge_base_config.py team_startup.yaml
```

### Automation Options

#### 1. File System Watcher (Recommended)
Real-time monitoring with automatic updates:
```bash
./scripts/kb-watch
```

#### 2. Git Hooks
Automatic indexing on commits:
- Pre-commit: Validates configuration and updates indexes
- Post-commit: Background re-indexing

#### 3. Cron Jobs
Periodic updates:
```bash
# Every 15 minutes
*/15 * * * * /path/to/project/scripts/knowledge_base_cron.sh
```

#### 4. Systemd Service (Linux)
System-level service for continuous monitoring:
```bash
sudo systemctl enable stellar-knowledge-base-watcher
sudo systemctl start stellar-knowledge-base-watcher
```

## CI/CD Integration

The knowledge base system integrates with GitHub Actions via `.github/workflows/knowledge-base-ci.yml`:

### Workflow Triggers
- Changes to `team_startup.yaml`
- Updates to knowledge source files
- Documentation modifications
- Source code changes

### Workflow Steps
1. **Configuration Validation** - Ensures `team_startup.yaml` is valid
2. **Index Updates** - Rebuilds indexes for changed sources
3. **Integrity Validation** - Verifies index completeness and coverage
4. **Performance Benchmarking** - Measures indexing performance
5. **Security Scanning** - Checks for sensitive information exposure

### Automated Commits
The CI pipeline automatically commits updated indexes with standardized commit messages:
```
🤖 Update knowledge base index

Automated update triggered by repository changes.

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Monitoring and Maintenance

### Health Checks

Check if rebuild is needed:
```bash
python scripts/knowledge_base_indexer.py --check-only
echo $?  # 0 = up-to-date, 1 = rebuild needed
```

Generate comprehensive report:
```bash
python scripts/knowledge_base_indexer.py --report
```

### Performance Monitoring

The system tracks:
- **Indexing Duration** - Time to rebuild all indexes
- **File Count** - Number of tracked files per knowledge base  
- **Change Detection** - Files modified since last indexing
- **Coverage Metrics** - Percentage of expected knowledge bases indexed

### Troubleshooting

#### Common Issues

1. **Configuration Errors**
   ```bash
   python scripts/validate_knowledge_base_config.py team_startup.yaml
   ```

2. **Permission Issues**
   ```bash
   chmod +x scripts/*.py scripts/*.sh
   ```

3. **Missing Dependencies**
   ```bash
   pip install pyyaml watchdog
   ```

4. **Index Corruption**
   ```bash
   rm -rf knowledge/index/
   python scripts/knowledge_base_indexer.py --force
   ```

#### Log Locations
- **File Watcher**: `logs/knowledge-base-watcher.log`
- **Cron Jobs**: `logs/knowledge-base-cron.log`
- **CI/CD**: GitHub Actions workflow logs

## Security Considerations

### Access Control
- Knowledge base files use standard file permissions
- No world-writable files allowed
- Automated permission validation in CI

### Sensitive Information
- Automated scanning for secrets and credentials
- No sensitive data in knowledge base files
- Content validation in security workflow

### Integrity Protection
- File hash validation for change detection
- Git-tracked index files for audit trail
- Automated backup in CI/CD artifacts

## Extension and Customization

### Adding New Knowledge Bases

1. **Update Configuration**
   ```yaml
   # In team_startup.yaml
   knowledge_base:
     - id: new_knowledge_base
       type: file
       path: path/to/new/knowledge.md
       description: Description of the knowledge base
   ```

2. **Update Agent Sources**
   ```yaml
   # In relevant agent configuration
   rag:
     sources: [
       "existing_sources",
       "new_knowledge_base"
     ]
   ```

3. **Validate and Test**
   ```bash
   python scripts/validate_knowledge_base_config.py team_startup.yaml
   python scripts/knowledge_base_indexer.py --force
   ```

### Custom Knowledge Base Types

Extend `KnowledgeBaseIndexer` class in `scripts/knowledge_base_indexer.py`:

```python
def _index_custom_knowledge_base(self, kb_config: Dict[str, Any]) -> bool:
    """Index a custom knowledge base type."""
    # Implementation here
    pass

# Register in indexers dictionary
indexers = {
    # ... existing types
    'custom': self._index_custom_knowledge_base
}
```

## Performance Optimization

### Indexing Performance
- Incremental updates based on file hashes
- Parallel processing for large repositories  
- Efficient pattern matching with glob
- Debounced updates to prevent thrashing

### Storage Optimization
- JSON index files with minimal metadata
- Compressed external resource caching
- Automatic cleanup of stale indexes
- Size monitoring and alerts

## Integration with Team Agents

Each agent automatically receives relevant knowledge base content through their configured RAG sources. The system ensures:

- **Relevance** - Each agent only accesses relevant knowledge
- **Freshness** - Automatic updates when source files change
- **Completeness** - Comprehensive coverage of all necessary sources
- **Performance** - Efficient indexing and retrieval

The knowledge base system is designed to be transparent to the agents while providing comprehensive, up-to-date information for informed decision-making and consistent implementation across the project.