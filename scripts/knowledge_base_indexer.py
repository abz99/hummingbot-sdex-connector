#!/usr/bin/env python3
"""
Knowledge Base Indexer for Stellar Hummingbot Connector

This script automatically indexes and updates knowledge base sources
based on repository changes and team_startup.yaml configuration.
"""

import os
import sys
import json
import yaml
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeBaseIndexer:
    """Manages knowledge base indexing and updates."""
    
    def __init__(self, project_root: Path, config_file: str = "team_startup.yaml"):
        self.project_root = Path(project_root).resolve()
        self.config_file = self.project_root / config_file
        self.index_dir = self.project_root / "knowledge" / "index"
        self.metadata_file = self.index_dir / "metadata.json"
        
        # Ensure index directory exists
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.config = self._load_config()
        self.metadata = self._load_metadata()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load team_startup.yaml configuration."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_file}: {e}")
            return {}
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load existing metadata or create new."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load metadata: {e}")
        
        return {
            'last_updated': None,
            'knowledge_bases': {},
            'file_hashes': {},
            'index_version': '1.0'
        }
    
    def _save_metadata(self):
        """Save metadata to file."""
        self.metadata['last_updated'] = datetime.now(timezone.utc).isoformat()
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"Metadata saved to {self.metadata_file}")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _get_file_list(self, patterns: List[str], excludes: List[str] = None) -> Set[Path]:
        """Get list of files matching patterns."""
        files = set()
        excludes = excludes or []
        
        for pattern in patterns:
            if pattern.startswith('./'):
                pattern = pattern[2:]
            
            if pattern == './':
                # Index entire repository
                for root, dirs, file_list in os.walk(self.project_root):
                    # Remove excluded directories from traversal
                    dirs[:] = [d for d in dirs if not any(
                        d.startswith(ex.rstrip('/')) for ex in excludes
                    )]
                    
                    for file in file_list:
                        file_path = Path(root) / file
                        rel_path = file_path.relative_to(self.project_root)
                        
                        # Check if file should be excluded
                        if not any(rel_path.match(ex) for ex in excludes):
                            files.add(file_path)
            else:
                # Use glob patterns
                for file_path in self.project_root.rglob(pattern):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(self.project_root)
                        if not any(rel_path.match(ex) for ex in excludes):
                            files.add(file_path)
        
        return files
    
    def _index_file_knowledge_base(self, kb_config: Dict[str, Any]) -> bool:
        """Index a single file knowledge base."""
        kb_id = kb_config['id']
        file_path = self.project_root / kb_config['path']
        
        if not file_path.exists():
            logger.warning(f"Knowledge base file not found: {file_path}")
            return False
        
        current_hash = self._calculate_file_hash(file_path)
        stored_hash = self.metadata['file_hashes'].get(str(file_path), "")
        
        if current_hash == stored_hash:
            logger.info(f"Knowledge base {kb_id} unchanged, skipping")
            return False
        
        # Create index entry
        index_entry = {
            'id': kb_id,
            'type': kb_config['type'],
            'path': str(file_path),
            'description': kb_config.get('description', ''),
            'last_indexed': datetime.now(timezone.utc).isoformat(),
            'hash': current_hash,
            'related_files': kb_config.get('related_files', [])
        }
        
        # Save index entry
        index_file = self.index_dir / f"{kb_id}.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_entry, f, indent=2, ensure_ascii=False)
        
        # Update metadata
        self.metadata['knowledge_bases'][kb_id] = index_entry
        self.metadata['file_hashes'][str(file_path)] = current_hash
        
        logger.info(f"Indexed knowledge base: {kb_id}")
        return True
    
    def _index_multi_file_knowledge_base(self, kb_config: Dict[str, Any]) -> bool:
        """Index a multi-file knowledge base."""
        kb_id = kb_config['id']
        files = kb_config.get('files', [])
        
        indexed_files = []
        total_hash = hashlib.sha256()
        
        for file_pattern in files:
            file_path = self.project_root / file_pattern
            if file_path.exists():
                file_hash = self._calculate_file_hash(file_path)
                total_hash.update(file_hash.encode())
                indexed_files.append({
                    'path': str(file_path),
                    'hash': file_hash,
                    'exists': True
                })
            else:
                logger.warning(f"File not found for {kb_id}: {file_path}")
                indexed_files.append({
                    'path': str(file_path),
                    'hash': None,
                    'exists': False
                })
        
        current_hash = total_hash.hexdigest()
        stored_hash = self.metadata['knowledge_bases'].get(kb_id, {}).get('hash', "")
        
        if current_hash == stored_hash:
            logger.info(f"Multi-file knowledge base {kb_id} unchanged, skipping")
            return False
        
        # Create index entry
        index_entry = {
            'id': kb_id,
            'type': kb_config['type'],
            'description': kb_config.get('description', ''),
            'files': indexed_files,
            'last_indexed': datetime.now(timezone.utc).isoformat(),
            'hash': current_hash
        }
        
        # Save index entry
        index_file = self.index_dir / f"{kb_id}.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_entry, f, indent=2, ensure_ascii=False)
        
        # Update metadata
        self.metadata['knowledge_bases'][kb_id] = index_entry
        
        logger.info(f"Indexed multi-file knowledge base: {kb_id}")
        return True
    
    def _index_code_knowledge_base(self, kb_config: Dict[str, Any]) -> bool:
        """Index a code repository knowledge base."""
        kb_id = kb_config['id']
        includes = kb_config.get('includes', ['*.py'])
        excludes = kb_config.get('excludes', [])
        
        files = self._get_file_list(includes, excludes)
        
        # Calculate combined hash of all files
        total_hash = hashlib.sha256()
        indexed_files = []
        
        for file_path in sorted(files):
            if file_path.exists():
                file_hash = self._calculate_file_hash(file_path)
                total_hash.update(f"{file_path}:{file_hash}".encode())
                indexed_files.append({
                    'path': str(file_path.relative_to(self.project_root)),
                    'absolute_path': str(file_path),
                    'hash': file_hash,
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc).isoformat()
                })
        
        current_hash = total_hash.hexdigest()
        stored_hash = self.metadata['knowledge_bases'].get(kb_id, {}).get('hash', "")
        
        if current_hash == stored_hash:
            logger.info(f"Code knowledge base {kb_id} unchanged, skipping")
            return False
        
        # Create index entry
        index_entry = {
            'id': kb_id,
            'type': kb_config['type'],
            'description': kb_config.get('description', ''),
            'path': kb_config.get('path', './'),
            'includes': includes,
            'excludes': excludes,
            'files': indexed_files,
            'file_count': len(indexed_files),
            'last_indexed': datetime.now(timezone.utc).isoformat(),
            'hash': current_hash
        }
        
        # Save index entry
        index_file = self.index_dir / f"{kb_id}.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_entry, f, indent=2, ensure_ascii=False)
        
        # Update metadata
        self.metadata['knowledge_bases'][kb_id] = index_entry
        
        logger.info(f"Indexed code knowledge base: {kb_id} ({len(indexed_files)} files)")
        return True
    
    def _index_directory_knowledge_base(self, kb_config: Dict[str, Any]) -> bool:
        """Index a directory knowledge base."""
        kb_id = kb_config['id']
        dir_path = self.project_root / kb_config['path']
        
        if not dir_path.exists():
            logger.warning(f"Directory not found for {kb_id}: {dir_path}")
            return False
        
        files = []
        total_hash = hashlib.sha256()
        
        for file_path in dir_path.rglob('*'):
            if file_path.is_file():
                file_hash = self._calculate_file_hash(file_path)
                total_hash.update(f"{file_path}:{file_hash}".encode())
                files.append({
                    'path': str(file_path.relative_to(self.project_root)),
                    'absolute_path': str(file_path),
                    'hash': file_hash,
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc).isoformat()
                })
        
        current_hash = total_hash.hexdigest()
        stored_hash = self.metadata['knowledge_bases'].get(kb_id, {}).get('hash', "")
        
        if current_hash == stored_hash:
            logger.info(f"Directory knowledge base {kb_id} unchanged, skipping")
            return False
        
        # Create index entry
        index_entry = {
            'id': kb_id,
            'type': kb_config['type'],
            'description': kb_config.get('description', ''),
            'path': str(dir_path),
            'files': files,
            'file_count': len(files),
            'related_files': kb_config.get('related_files', []),
            'last_indexed': datetime.now(timezone.utc).isoformat(),
            'hash': current_hash
        }
        
        # Save index entry
        index_file = self.index_dir / f"{kb_id}.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_entry, f, indent=2, ensure_ascii=False)
        
        # Update metadata
        self.metadata['knowledge_bases'][kb_id] = index_entry
        
        logger.info(f"Indexed directory knowledge base: {kb_id} ({len(files)} files)")
        return True
    
    def _index_web_knowledge_base(self, kb_config: Dict[str, Any]) -> bool:
        """Index a web knowledge base (placeholder for external URLs)."""
        kb_id = kb_config['id']
        
        # For web resources, we just track the URLs
        index_entry = {
            'id': kb_id,
            'type': kb_config['type'],
            'url': kb_config.get('url', ''),
            'description': kb_config.get('description', ''),
            'includes': kb_config.get('includes', []),
            'last_indexed': datetime.now(timezone.utc).isoformat(),
            'hash': hashlib.sha256(kb_config.get('url', '').encode()).hexdigest()
        }
        
        # Save index entry
        index_file = self.index_dir / f"{kb_id}.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_entry, f, indent=2, ensure_ascii=False)
        
        # Update metadata
        self.metadata['knowledge_bases'][kb_id] = index_entry
        
        logger.info(f"Indexed web knowledge base: {kb_id}")
        return True
    
    def index_knowledge_base(self, kb_config: Dict[str, Any]) -> bool:
        """Index a single knowledge base based on its type."""
        kb_type = kb_config.get('type', 'file')
        
        indexers = {
            'file': self._index_file_knowledge_base,
            'multi_file': self._index_multi_file_knowledge_base,
            'code': self._index_code_knowledge_base,
            'directory': self._index_directory_knowledge_base,
            'web': self._index_web_knowledge_base
        }
        
        indexer = indexers.get(kb_type)
        if not indexer:
            logger.error(f"Unknown knowledge base type: {kb_type}")
            return False
        
        try:
            return indexer(kb_config)
        except Exception as e:
            logger.error(f"Failed to index knowledge base {kb_config.get('id', 'unknown')}: {e}")
            return False
    
    def index_all_knowledge_bases(self, force: bool = False) -> Dict[str, bool]:
        """Index all knowledge bases defined in configuration."""
        knowledge_bases = self.config.get('knowledge_base', [])
        results = {}
        
        logger.info(f"Indexing {len(knowledge_bases)} knowledge bases...")
        
        if force:
            logger.info("Force mode enabled - rebuilding all indexes")
            self.metadata['file_hashes'] = {}
            self.metadata['knowledge_bases'] = {}
        
        for kb_config in knowledge_bases:
            kb_id = kb_config.get('id', 'unknown')
            logger.info(f"Processing knowledge base: {kb_id}")
            results[kb_id] = self.index_knowledge_base(kb_config)
        
        self._save_metadata()
        return results
    
    def index_local_knowledge_bases_only(self, force: bool = False) -> Dict[str, bool]:
        """Index only local knowledge bases (skip web sources for performance)."""
        knowledge_bases = self.config.get('knowledge_base', [])
        results = {}
        
        local_kbs = [kb for kb in knowledge_bases if kb.get('type') != 'web']
        logger.info(f"Indexing {len(local_kbs)} local knowledge bases (skipping web sources)...")
        
        if force:
            logger.info("Force mode enabled - rebuilding local indexes")
            # Only clear local KB metadata, keep web KB data
            for kb_config in local_kbs:
                kb_id = kb_config.get('id', 'unknown')
                if kb_id in self.metadata['knowledge_bases']:
                    del self.metadata['knowledge_bases'][kb_id]
        
        for kb_config in local_kbs:
            kb_id = kb_config.get('id', 'unknown')
            logger.debug(f"Processing local knowledge base: {kb_id}")
            results[kb_id] = self.index_knowledge_base(kb_config)
        
        self._save_metadata()
        return results
    
    def get_changed_files(self) -> Set[Path]:
        """Get list of files that have changed since last indexing."""
        changed_files = set()
        
        # Check all tracked files for changes
        for file_path_str, stored_hash in self.metadata['file_hashes'].items():
            file_path = Path(file_path_str)
            if file_path.exists():
                current_hash = self._calculate_file_hash(file_path)
                if current_hash != stored_hash:
                    changed_files.add(file_path)
            else:
                # File was deleted
                changed_files.add(file_path)
        
        return changed_files
    
    def should_rebuild_index(self) -> bool:
        """Check if index should be rebuilt based on file changes."""
        if not self.metadata['last_updated']:
            return True
        
        changed_files = self.get_changed_files()
        return len(changed_files) > 0
    
    def generate_index_report(self) -> Dict[str, Any]:
        """Generate a comprehensive index report."""
        report = {
            'project_root': str(self.project_root),
            'last_updated': self.metadata['last_updated'],
            'index_version': self.metadata['index_version'],
            'knowledge_base_count': len(self.metadata['knowledge_bases']),
            'tracked_file_count': len(self.metadata['file_hashes']),
            'knowledge_bases': {}
        }
        
        for kb_id, kb_data in self.metadata['knowledge_bases'].items():
            report['knowledge_bases'][kb_id] = {
                'type': kb_data.get('type', 'unknown'),
                'description': kb_data.get('description', ''),
                'last_indexed': kb_data.get('last_indexed'),
                'file_count': kb_data.get('file_count', 1)
            }
        
        return report


def main():
    """Main entry point for the knowledge base indexer."""
    parser = argparse.ArgumentParser(
        description='Knowledge Base Indexer for Stellar Hummingbot Connector'
    )
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path.cwd(),
        help='Project root directory (default: current directory)'
    )
    parser.add_argument(
        '--config',
        default='team_startup.yaml',
        help='Configuration file name (default: team_startup.yaml)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force rebuild all indexes'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check if rebuild is needed, don\'t rebuild'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate and display index report'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize indexer
    try:
        indexer = KnowledgeBaseIndexer(args.project_root, args.config)
    except Exception as e:
        logger.error(f"Failed to initialize indexer: {e}")
        sys.exit(1)
    
    if args.report:
        report = indexer.generate_index_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    
    if args.check_only:
        should_rebuild = indexer.should_rebuild_index()
        print(f"Rebuild needed: {should_rebuild}")
        sys.exit(0 if not should_rebuild else 1)
    
    # Index knowledge bases
    try:
        results = indexer.index_all_knowledge_bases(force=args.force)
        
        updated_count = sum(1 for updated in results.values() if updated)
        total_count = len(results)
        
        logger.info(f"Indexing completed: {updated_count}/{total_count} knowledge bases updated")
        
        if args.verbose:
            for kb_id, updated in results.items():
                status = "UPDATED" if updated else "UNCHANGED"
                logger.info(f"  {kb_id}: {status}")
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()