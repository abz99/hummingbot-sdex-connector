#!/usr/bin/env python3
"""
Knowledge Base File Watcher for Stellar Hummingbot Connector

This script watches for file changes and automatically triggers
knowledge base re-indexing when necessary.

Optimized for low CPU usage with:
- Thread pooling instead of creating new threads
- Efficient file filtering
- Rate limiting and backoff
- Process deduplication
"""

import os
import sys
import time
import logging
import asyncio
import signal
import threading
from pathlib import Path
from typing import Set, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from knowledge_base_indexer import KnowledgeBaseIndexer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/abz/projects/stellar-hummingbot-connector-v3/logs/knowledge_base_watcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure logging with process deduplication
def setup_logging():
    pid_file = Path("/tmp/knowledge_base_watcher.pid")
    if pid_file.exists():
        try:
            existing_pid = int(pid_file.read_text().strip())
            os.kill(existing_pid, 0)  # Check if process exists
            logger.error(f"Another watcher process already running (PID: {existing_pid})")
            sys.exit(1)
        except (OSError, ValueError):
            # Process doesn't exist, remove stale PID file
            pid_file.unlink(missing_ok=True)
    
    # Write current PID
    pid_file.write_text(str(os.getpid()))
    
    # Setup signal handlers for cleanup
    def cleanup(signum, frame):
        logger.info(f"Received signal {signum}, cleaning up...")
        pid_file.unlink(missing_ok=True)
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)


class KnowledgeBaseEventHandler(FileSystemEventHandler):
    """Handles file system events for knowledge base indexing."""
    
    def __init__(self, indexer: KnowledgeBaseIndexer, debounce_seconds: int = 10):
        super().__init__()
        self.indexer = indexer
        self.debounce_seconds = debounce_seconds
        self.pending_changes: Set[Path] = set()
        self.last_event_time = 0
        self.indexing_in_progress = False
        self.rate_limit_window = 60  # seconds
        self.max_triggers_per_window = 3
        self.recent_triggers = []
        
        # Use thread pool instead of creating new threads
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="indexer")
        
        # Load patterns to watch - cache for efficiency
        self._load_watch_patterns()
        self._compiled_ignore_patterns = self._compile_ignore_patterns()
    
    def _compile_ignore_patterns(self):
        """Pre-compile ignore patterns for efficient matching."""
        import fnmatch
        ignore_patterns = {
            '__pycache__',
            '.git',
            '.mypy_cache', 
            'venv',
            '.venv',
            'node_modules',
            '.pytest_cache',
            '.log',
            '.tmp',
            '*.pyc',
            '*.pyo',
            '*~',
            '.DS_Store'
        }
        # Pre-compile patterns for faster matching
        return [fnmatch.translate(pattern) for pattern in ignore_patterns]
    
    def _load_watch_patterns(self):
        """Load file patterns that should trigger re-indexing."""
        self.watch_patterns = set()
        
        # Only watch critical files to reduce noise
        critical_files = {
            'stellar_sdex_checklist_v3.md',
            'stellar_sdex_tdd_v3.md', 
            'PROJECT_STATUS.md',
            'team_startup.yaml',
            'team_startup.yml',
            'CLAUDE.md',
            'SESSION_SNAPSHOT.md'
        }
        
        # Add specific Python files only
        config = self.indexer.config
        knowledge_bases = config.get('knowledge_base', [])
        
        for kb in knowledge_bases:
            kb_type = kb.get('type', 'file')
            
            # Skip web knowledge bases from file watching
            if kb_type == 'web':
                continue
                
            if kb_type == 'file':
                path = kb.get('path', '')
                if path and any(critical in path for critical in critical_files):
                    self.watch_patterns.add(path)
            
            elif kb_type == 'multi_file':
                files = kb.get('files', [])
                for file in files:
                    if any(critical in file for critical in critical_files):
                        self.watch_patterns.add(file)
            
            elif kb_type == 'code':
                # Only watch main connector files, not all Python files
                includes = ['hummingbot/connector/exchange/stellar/*.py']
                self.watch_patterns.update(includes)
        
        logger.info(f"Watching {len(self.watch_patterns)} critical file patterns")
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should trigger re-indexing - optimized for performance."""
        import re
        
        # Quick path length check - ignore very deep paths
        if len(file_path.parts) > 10:
            return False
            
        # Fast ignore check using pre-compiled patterns
        file_str = str(file_path)
        for compiled_pattern in self._compiled_ignore_patterns:
            if re.match(compiled_pattern, file_str):
                return False
        
        # Check file extension whitelist first (most files won't match)
        allowed_extensions = {'.md', '.py', '.yaml', '.yml', '.json'}
        if file_path.suffix not in allowed_extensions:
            return False
        
        # Check if file matches any watch patterns
        try:
            rel_path = file_path.relative_to(self.indexer.project_root)
            rel_str = str(rel_path)
            
            # Direct name matching (fastest)
            if file_path.name in {'team_startup.yaml', 'team_startup.yml', 'PROJECT_STATUS.md', 'CLAUDE.md'}:
                return True
                
            # Pattern matching for specific patterns only
            for pattern in self.watch_patterns:
                if rel_path.match(pattern) or rel_str == pattern:
                    return True
                    
        except ValueError:
            # Path is not relative to project root
            return False
        
        return False
    
    def _is_rate_limited(self) -> bool:
        """Check if we're hitting rate limits."""
        current_time = time.time()
        # Clean old triggers
        self.recent_triggers = [t for t in self.recent_triggers if current_time - t < self.rate_limit_window]
        
        if len(self.recent_triggers) >= self.max_triggers_per_window:
            logger.warning(f"Rate limiting: {len(self.recent_triggers)} triggers in {self.rate_limit_window}s")
            return True
        return False
    
    def _schedule_indexing(self):
        """Schedule indexing after debounce period with rate limiting."""
        if self.indexing_in_progress:
            logger.debug("Indexing already in progress, skipping")
            return
            
        if self._is_rate_limited():
            logger.warning("Rate limited, skipping indexing")
            return
        
        current_time = time.time()
        self.last_event_time = current_time
        
        def delayed_index():
            try:
                # Wait for debounce period
                time.sleep(self.debounce_seconds)
                
                # Check if more recent events occurred
                if time.time() - self.last_event_time < self.debounce_seconds - 1:
                    logger.debug("More recent events occurred, skipping indexing")
                    return
                
                if not self.pending_changes:
                    return
                    
                self.indexing_in_progress = True
                self.recent_triggers.append(time.time())
                
                logger.info(f"Re-indexing triggered by {len(self.pending_changes)} file changes")
                
                # Only index local files, skip web knowledge bases to reduce CPU
                results = self.indexer.index_local_knowledge_bases_only()
                updated_count = sum(1 for updated in results.values() if updated)
                
                logger.info(f"Re-indexing completed: {updated_count} local knowledge bases updated")
                self.pending_changes.clear()
                
            except Exception as e:
                logger.error(f"Re-indexing failed: {e}")
            finally:
                self.indexing_in_progress = False
        
        # Use thread pool instead of creating new threads
        self.executor.submit(delayed_index)
    
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
    
    def shutdown(self):
        """Clean shutdown of event handler."""
        logger.info("Shutting down event handler...")
        self.executor.shutdown(wait=True)


class KnowledgeBaseWatcher:
    """Watches file system and manages knowledge base indexing."""
    
    def __init__(self, project_root: Path, config_file: str = "team_startup.yaml"):
        self.project_root = Path(project_root).resolve()
        self.indexer = KnowledgeBaseIndexer(project_root, config_file)
        self.observer = Observer()
        self.event_handler = None
        self.running = False
        
    def start_watching(self, debounce_seconds: int = 30):
        """Start watching for file changes with optimized settings."""
        setup_logging()  # Setup PID file and signal handlers
        
        self.event_handler = KnowledgeBaseEventHandler(self.indexer, debounce_seconds)
        
        # Watch project root recursively but exclude common directories
        self.observer.schedule(
            self.event_handler,
            str(self.project_root),
            recursive=True
        )
        
        logger.info(f"Starting optimized file watcher for {self.project_root} (PID: {os.getpid()})")
        self.observer.start()
        self.running = True
        
        try:
            # Skip initial indexing to reduce startup CPU load
            logger.info("File watcher started (skipping initial indexing for performance)")
            logger.info("Press Ctrl+C to stop watcher")
            
            # Use event-based waiting instead of busy polling
            import threading
            stop_event = threading.Event()
            
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}")
                stop_event.set()
                
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            
            # Efficient waiting with longer intervals
            while self.running and not stop_event.is_set():
                stop_event.wait(timeout=10)  # 10-second intervals instead of 1-second
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up resources."""
        logger.info("Stopping file watcher...")
        self.running = False
        
        if self.event_handler:
            self.event_handler.shutdown()
            
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)  # Don't wait forever
            
        # Clean up PID file
        pid_file = Path("/tmp/knowledge_base_watcher.pid")
        pid_file.unlink(missing_ok=True)
        
        logger.info("File watcher stopped cleanly")


def main():
    """Main entry point for the knowledge base watcher."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Optimized Knowledge Base File Watcher for Stellar Hummingbot Connector'
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
        default=30,
        help='Debounce delay in seconds (default: 30 for lower CPU usage)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--kill-existing',
        action='store_true',
        help='Kill any existing watcher processes before starting'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    if args.kill_existing:
        # Kill existing processes
        try:
            import subprocess
            result = subprocess.run(['pkill', '-f', 'knowledge_base_watcher.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Killed existing watcher processes")
                time.sleep(2)  # Wait for cleanup
        except Exception as e:
            logger.warning(f"Failed to kill existing processes: {e}")
    
    try:
        watcher = KnowledgeBaseWatcher(args.project_root, args.config)
        watcher.start_watching(args.debounce)
    except Exception as e:
        logger.error(f"Watcher failed: {e}")
        # Clean up PID file on error
        pid_file = Path("/tmp/knowledge_base_watcher.pid")
        pid_file.unlink(missing_ok=True)
        sys.exit(1)


if __name__ == '__main__':
    main()