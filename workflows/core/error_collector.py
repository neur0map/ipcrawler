"""
Centralized error collection system for IPCrawler workflows.

This module provides thread-safe error collection, JSON-based storage,
error aggregation, and analysis features for comprehensive error management.
"""

import json
import datetime
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from collections import defaultdict, Counter
import hashlib

from .exceptions import IPCrawlerError, ErrorSeverity, ErrorCategory, ErrorContext


class ErrorEntry:
    """Individual error entry with metadata"""
    
    def __init__(self, error: IPCrawlerError, occurrence_id: str = None):
        self.error = error
        self.occurrence_id = occurrence_id or self._generate_occurrence_id()
        self.first_seen = datetime.datetime.now()
        self.last_seen = self.first_seen
        self.occurrence_count = 1
        self.error_hash = self._generate_error_hash()
    
    def _generate_occurrence_id(self) -> str:
        """Generate unique occurrence ID"""
        timestamp = datetime.datetime.now().isoformat()
        return hashlib.md5(f"{timestamp}{id(self)}".encode()).hexdigest()[:12]
    
    def _generate_error_hash(self) -> str:
        """Generate hash for error deduplication"""
        key = f"{self.error.error_code}_{self.error.message}_{self.error.context.workflow_name}_{self.error.context.operation}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def update_occurrence(self):
        """Update occurrence information for duplicate errors"""
        self.last_seen = datetime.datetime.now()
        self.occurrence_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "occurrence_id": self.occurrence_id,
            "error_hash": self.error_hash,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "occurrence_count": self.occurrence_count,
            "error": self.error.to_dict()
        }


class ErrorStats:
    """Error statistics and analysis"""
    
    def __init__(self, errors: List[ErrorEntry]):
        self.errors = errors
        self.total_errors = len(errors)
        self.total_occurrences = sum(e.occurrence_count for e in errors)
        
    def by_severity(self) -> Dict[str, int]:
        """Group errors by severity"""
        stats = defaultdict(int)
        for error_entry in self.errors:
            stats[error_entry.error.severity.value] += error_entry.occurrence_count
        return dict(stats)
    
    def by_category(self) -> Dict[str, int]:
        """Group errors by category"""
        stats = defaultdict(int)
        for error_entry in self.errors:
            stats[error_entry.error.category.value] += error_entry.occurrence_count
        return dict(stats)
    
    def by_workflow(self) -> Dict[str, int]:
        """Group errors by workflow"""
        stats = defaultdict(int)
        for error_entry in self.errors:
            workflow = error_entry.error.context.workflow_name
            stats[workflow] += error_entry.occurrence_count
        return dict(stats)
    
    def by_error_code(self) -> Dict[str, int]:
        """Group errors by error code"""
        stats = defaultdict(int)
        for error_entry in self.errors:
            stats[error_entry.error.error_code] += error_entry.occurrence_count
        return dict(stats)
    
    def most_frequent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequent errors"""
        sorted_errors = sorted(
            self.errors, 
            key=lambda e: e.occurrence_count, 
            reverse=True
        )
        
        return [
            {
                "error_code": e.error.error_code,
                "message": e.error.message,
                "workflow": e.error.context.workflow_name,
                "occurrences": e.occurrence_count,
                "severity": e.error.severity.value,
                "category": e.error.category.value
            }
            for e in sorted_errors[:limit]
        ]
    
    def recent_errors(self, hours: int = 24) -> List[ErrorEntry]:
        """Get errors from the last N hours"""
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
        return [e for e in self.errors if e.last_seen >= cutoff]
    
    def critical_errors(self) -> List[ErrorEntry]:
        """Get critical errors only"""
        return [e for e in self.errors if e.error.severity == ErrorSeverity.CRITICAL]


class ErrorCollector:
    """
    Centralized error collection system with JSON storage.
    
    Features:
    - Thread-safe error collection
    - JSON-based persistent storage
    - Error deduplication and aggregation
    - Statistical analysis
    - Workspace integration
    """
    
    def __init__(self, workspace_dir: str = "workspaces"):
        self.workspace_dir = Path(workspace_dir)
        self.errors_file = self.workspace_dir / "errors.json"
        self.summary_file = self.workspace_dir / "error_summary.json"
        self._lock = threading.Lock()
        self._errors_cache: Dict[str, ErrorEntry] = {}
        self._ensure_workspace_exists()
        # Temporarily disable loading existing errors to avoid potential issues
        # self._load_existing_errors()
    
    def _ensure_workspace_exists(self):
        """Ensure workspace directory exists"""
        try:
            self.workspace_dir.mkdir(exist_ok=True)
        except PermissionError:
            # Fallback to temp directory
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "ipcrawler_workspaces"
            temp_dir.mkdir(exist_ok=True)
            self.workspace_dir = temp_dir
            self.errors_file = self.workspace_dir / "errors.json"
            self.summary_file = self.workspace_dir / "error_summary.json"
    
    def _load_existing_errors(self):
        """Load existing errors from JSON file"""
        if not self.errors_file.exists():
            return
        
        try:
            with open(self.errors_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for error_data in data.get('errors', []):
                # Reconstruct ErrorEntry from JSON
                error_dict = error_data['error']
                
                # Create IPCrawlerError from dict (simplified reconstruction)
                context = ErrorContext(**error_dict['context']) if error_dict.get('context') else None
                
                error = IPCrawlerError(
                    message=error_dict['message'],
                    error_code=error_dict['error_code'],
                    severity=ErrorSeverity(error_dict['severity']),
                    category=ErrorCategory(error_dict['category'])
                )
                error.context = context
                error.timestamp = datetime.datetime.fromisoformat(error_dict['timestamp'])
                
                # Create ErrorEntry
                entry = ErrorEntry(error, error_data['occurrence_id'])
                entry.error_hash = error_data['error_hash']
                entry.first_seen = datetime.datetime.fromisoformat(error_data['first_seen'])
                entry.last_seen = datetime.datetime.fromisoformat(error_data['last_seen'])
                entry.occurrence_count = error_data['occurrence_count']
                
                self._errors_cache[entry.error_hash] = entry
                
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If we can't load existing errors, start fresh
            print(f"Warning: Could not load existing errors: {e}")
            self._errors_cache = {}
    
    def collect_error(self, error: IPCrawlerError) -> str:
        """
        Collect an error with deduplication.
        
        Returns:
            str: Occurrence ID of the error entry
        """
        with self._lock:
            # Create temporary entry to generate hash
            temp_entry = ErrorEntry(error)
            error_hash = temp_entry.error_hash
            
            if error_hash in self._errors_cache:
                # Update existing error
                existing_entry = self._errors_cache[error_hash]
                existing_entry.update_occurrence()
                occurrence_id = existing_entry.occurrence_id
            else:
                # Add new error
                self._errors_cache[error_hash] = temp_entry
                occurrence_id = temp_entry.occurrence_id
            
            # Persist to disk
            self._save_errors()
            
            return occurrence_id
    
    def collect_from_exception(
        self, 
        exc: Exception, 
        workflow_name: str, 
        operation: str,
        target: Optional[str] = None,
        **parameters
    ) -> str:
        """
        Collect error from generic exception.
        
        Converts generic exceptions to IPCrawlerError and collects them.
        """
        from .exceptions import handle_exception
        
        ipc_error = handle_exception(
            exc, workflow_name, operation, target, **parameters
        )
        
        return self.collect_error(ipc_error)
    
    def get_errors(
        self, 
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        workflow: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ErrorEntry]:
        """Get errors with optional filtering"""
        with self._lock:
            errors = list(self._errors_cache.values())
            
            # Apply filters
            if severity:
                errors = [e for e in errors if e.error.severity == severity]
            
            if category:
                errors = [e for e in errors if e.error.category == category]
            
            if workflow:
                errors = [e for e in errors if e.error.context.workflow_name == workflow]
            
            # Sort by last seen (most recent first)
            errors.sort(key=lambda e: e.last_seen, reverse=True)
            
            # Apply limit
            if limit:
                errors = errors[:limit]
            
            return errors
    
    def get_stats(self) -> ErrorStats:
        """Get error statistics"""
        with self._lock:
            return ErrorStats(list(self._errors_cache.values()))
    
    def clear_errors(self, before_date: Optional[datetime.datetime] = None):
        """Clear errors, optionally before a specific date"""
        with self._lock:
            if before_date:
                # Remove errors before the specified date
                to_remove = [
                    hash_key for hash_key, entry in self._errors_cache.items()
                    if entry.last_seen < before_date
                ]
                for hash_key in to_remove:
                    del self._errors_cache[hash_key]
            else:
                # Clear all errors
                self._errors_cache.clear()
            
            self._save_errors()
    
    def _save_errors(self):
        """Save errors to JSON file"""
        try:
            # Prepare data for JSON serialization
            data = {
                "metadata": {
                    "last_updated": datetime.datetime.now().isoformat(),
                    "total_errors": len(self._errors_cache),
                    "total_occurrences": sum(e.occurrence_count for e in self._errors_cache.values())
                },
                "errors": [entry.to_dict() for entry in self._errors_cache.values()]
            }
            
            # Write to file with atomic operation
            temp_file = self.errors_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            # Atomic move
            temp_file.replace(self.errors_file)
            
            # Generate summary
            self._generate_summary()
            
        except (OSError, PermissionError) as e:
            print(f"Warning: Could not save errors to {self.errors_file}: {e}")
    
    def _generate_summary(self):
        """Generate error summary for quick analysis"""
        try:
            stats = self.get_stats()
            
            summary = {
                "generated_at": datetime.datetime.now().isoformat(),
                "overview": {
                    "total_unique_errors": stats.total_errors,
                    "total_occurrences": stats.total_occurrences,
                    "critical_errors": len(stats.critical_errors()),
                    "recent_errors_24h": len(stats.recent_errors(24))
                },
                "by_severity": stats.by_severity(),
                "by_category": stats.by_category(),
                "by_workflow": stats.by_workflow(),
                "most_frequent": stats.most_frequent_errors(5)
            }
            
            with open(self.summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
                
        except (OSError, PermissionError) as e:
            print(f"Warning: Could not save error summary: {e}")
    
    def generate_report(self, output_file: Optional[Path] = None) -> str:
        """Generate human-readable error report"""
        stats = self.get_stats()
        
        report_lines = []
        report_lines.append("# IPCrawler Error Report")
        report_lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Overview
        report_lines.append("## Overview")
        report_lines.append(f"- Total unique errors: {stats.total_errors}")
        report_lines.append(f"- Total occurrences: {stats.total_occurrences}")
        report_lines.append(f"- Critical errors: {len(stats.critical_errors())}")
        report_lines.append(f"- Recent errors (24h): {len(stats.recent_errors(24))}")
        report_lines.append("")
        
        # By severity
        report_lines.append("## Errors by Severity")
        for severity, count in sorted(stats.by_severity().items()):
            report_lines.append(f"- {severity.upper()}: {count}")
        report_lines.append("")
        
        # By category
        report_lines.append("## Errors by Category")
        for category, count in sorted(stats.by_category().items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"- {category}: {count}")
        report_lines.append("")
        
        # Most frequent errors
        report_lines.append("## Most Frequent Errors")
        for i, error in enumerate(stats.most_frequent_errors(10), 1):
            report_lines.append(f"{i}. [{error['error_code']}] {error['message']}")
            report_lines.append(f"   Workflow: {error['workflow']}, Occurrences: {error['occurrences']}")
            report_lines.append("")
        
        report_content = "\n".join(report_lines)
        
        # Save to file if specified
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
            except (OSError, PermissionError) as e:
                print(f"Warning: Could not save report to {output_file}: {e}")
        
        return report_content


# Global error collector instance
_error_collector: Optional[ErrorCollector] = None


def get_error_collector() -> ErrorCollector:
    """Get the global error collector instance"""
    global _error_collector
    if _error_collector is None:
        _error_collector = ErrorCollector()
    return _error_collector


def collect_error(error: IPCrawlerError) -> str:
    """Convenience function to collect an error"""
    collector = get_error_collector()
    return collector.collect_error(error)


def collect_exception(
    exc: Exception,
    workflow_name: str,
    operation: str,
    target: Optional[str] = None,
    **parameters
) -> str:
    """Convenience function to collect an exception"""
    collector = get_error_collector()
    return collector.collect_from_exception(
        exc, workflow_name, operation, target, **parameters
    )