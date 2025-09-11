#!/usr/bin/env python3
"""
Knowledge Base File Watcher for Stellar Hummingbot Connector

This script watches for file changes and automatically triggers
knowledge base re-indexing when necessary.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Set, Dict, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from knowledge_base_indexer import KnowledgeBaseIndexer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeBaseEventHandler(FileSystemEventHandler):
    """Handles file system events for knowledge base indexing."""
    
    def __init__(self, indexer: KnowledgeBaseIndexer, debounce_seconds: int = 5):
        super().__init__()
        self.indexer = indexer
        self.debounce_seconds = debounce_seconds
        self.pending_changes: Set[Path] = set()
        self.last_event_time = 0
        
        # Load patterns to watch
        self._load_watch_patterns()
    
    def _load_watch_patterns(self):
        """Load file patterns that should trigger re-indexing."""
        self.watch_patterns = set()
        self.ignore_patterns = {
            '__pycache__',
            '.git',
            '.mypy_cache',
            'venv',
            '.venv',
            'node_modules',
            '.pytest_cache'
        }
        
        # Add patterns from knowledge base configuration
        config = self.indexer.config
        knowledge_bases = config.get('knowledge_base', [])
        
        for kb in knowledge_bases:
            kb_type = kb.get('type', 'file')
            
            if kb_type == 'file':
                path = kb.get('path', '')
                if path:
                    self.watch_patterns.add(path)
            
            elif kb_type == 'multi_file':
                files = kb.get('files', [])
                self.watch_patterns.update(files)
            
            elif kb_type == 'code':
                includes = kb.get('includes', ['*.py'])
                self.watch_patterns.update(includes)
            
            elif kb_type == 'directory':
                path = kb.get('path', '')
                if path:
                    self.watch_patterns.add(f"{path}/**/*")
            
            # Add related files
            related_files = kb.get('related_files', [])
            self.watch_patterns.update(related_files)
        
        logger.info(f"Watching {len(self.watch_patterns)} file patterns")
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should trigger re-indexing."""
        # Check ignore patterns
        for part in file_path.parts:
            if any(ignore in part for ignore in self.ignore_patterns):
                return False
        
        # Check if file matches any watch patterns
        rel_path = file_path.relative_to(self.indexer.project_root)
        
        for pattern in self.watch_patterns:
            if rel_path.match(pattern) or str(rel_path) == pattern:
                return True
        
        # Check for key configuration files
        if file_path.name in ['team_startup.yaml', 'team_startup.yml']:
            return True
        
        return False
    
    def _schedule_indexing(self):
        """Schedule indexing after debounce period."""
        current_time = time.time()
        self.last_event_time = current_time
        
        def delayed_index():
            time.sleep(self.debounce_seconds)
            
            # Check if more recent events occurred
            if time.time() - self.last_event_time < self.debounce_seconds:
                return
            
            if self.pending_changes:
                logger.info(f"Re-indexing triggered by {len(self.pending_changes)} file changes")
                
                try:
                    results = self.indexer.index_all_knowledge_bases()
                    updated_count = sum(1 for updated in results.values() if updated)
                    logger.info(f"Re-indexing completed: {updated_count} knowledge bases updated")
                except Exception as e:
                    logger.error(f"Re-indexing failed: {e}")
                
                self.pending_changes.clear()
        
        # Run in background thread
        import threading
        threading.Thread(target=delayed_index, daemon=True).start()
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        if self._should_process_file(file_path):
            logger.debug(f"File modified: {file_path}")
            self.pending_changes.add(file_path)
            self._schedule_indexing()
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        if self._should_process_file(file_path):
            logger.debug(f"File created: {file_path}")
            self.pending_changes.add(file_path)
            self._schedule_indexing()
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        if self._should_process_file(file_path):
            logger.debug(f"File deleted: {file_path}")
            self.pending_changes.add(file_path)
            self._schedule_indexing()
    
    def on_moved(self, event):
        """Handle file move events."""
        if event.is_directory:
            return
        
        old_path = Path(event.src_path)
        new_path = Path(event.dest_path)
        
        should_process = (
            self._should_process_file(old_path) or 
            self._should_process_file(new_path)
        )
        
        if should_process:
            logger.debug(f"File moved: {old_path} -> {new_path}")
            self.pending_changes.add(old_path)
            self.pending_changes.add(new_path)
            self._schedule_indexing()


class KnowledgeBaseWatcher:
    """Watches file system and manages knowledge base indexing."""
    
    def __init__(self, project_root: Path, config_file: str = "team_startup.yaml"):
        self.project_root = Path(project_root).resolve()
        self.indexer = KnowledgeBaseIndexer(project_root, config_file)
        self.observer = Observer()
        
    def start_watching(self, debounce_seconds: int = 5):
        """Start watching for file changes."""
        event_handler = KnowledgeBaseEventHandler(self.indexer, debounce_seconds)
        
        # Watch project root recursively
        self.observer.schedule(
            event_handler,
            str(self.project_root),
            recursive=True
        )
        
        logger.info(f"Starting file watcher for {self.project_root}")
        self.observer.start()
        
        try:
            # Perform initial indexing
            logger.info("Performing initial indexing...")
            results = self.indexer.index_all_knowledge_bases()
            updated_count = sum(1 for updated in results.values() if updated)
            logger.info(f"Initial indexing completed: {updated_count} knowledge bases updated")
            
            # Keep watching
            logger.info("File watcher started. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Stopping file watcher...")
            self.observer.stop()
        
        self.observer.join()
        logger.info("File watcher stopped")


def main():
    """Main entry point for the knowledge base watcher."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Knowledge Base File Watcher for Stellar Hummingbot Connector'
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
        '--debounce',
        type=int,
        default=5,
        help='Debounce delay in seconds (default: 5)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        watcher = KnowledgeBaseWatcher(args.project_root, args.config)
        watcher.start_watching(args.debounce)
    except Exception as e:
        logger.error(f"Watcher failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()