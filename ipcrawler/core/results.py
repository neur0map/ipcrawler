"""
Results management and storage module.
"""

import json
import gzip
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..models.result import ExecutionResult, ScanResult


class ResultsManager:
    """Manages scan results and output formatting."""
    
    def __init__(self, base_path: str = "results"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def save_result(self, result: ExecutionResult, target: str) -> None:
        """Save a single execution result."""
        target_path = self.base_path / self._sanitize_target(target)
        target_path.mkdir(exist_ok=True)
        
        # Create subdirectories
        success_path = target_path / "success"
        error_path = target_path / "errors"
        machine_path = target_path / "machine"
        readable_path = target_path / "readable"
        
        for path in [success_path, error_path, machine_path, readable_path]:
            path.mkdir(exist_ok=True)
        
        # Save to appropriate directory
        timestamp = result.timestamp.strftime("%Y-%m-%dT%H-%M-%S.%f+00-00")
        
        if result.success:
            success_file = success_path / f"success-{timestamp}.jsonl"
            self._save_jsonl(success_file, result.dict())
        else:
            error_file = error_path / f"error-{timestamp}.jsonl"
            self._save_jsonl(error_file, result.dict())
        
        # Update machine-readable logs
        monthly_file = machine_path / f"full-{result.timestamp.strftime('%Y-%m')}.jsonl"
        self._append_jsonl(monthly_file, result.dict())
    
    def get_results(self, target: str) -> List[ExecutionResult]:
        """Get all results for a target."""
        target_path = self.base_path / self._sanitize_target(target)
        
        if not target_path.exists():
            return []
        
        results = []
        
        # Load from success directory
        success_path = target_path / "success"
        if success_path.exists():
            for file_path in success_path.glob("*.jsonl"):
                results.extend(self._load_jsonl_results(file_path))
        
        # Load from errors directory
        error_path = target_path / "errors"
        if error_path.exists():
            for file_path in error_path.glob("*.jsonl"):
                results.extend(self._load_jsonl_results(file_path))
        
        return sorted(results, key=lambda r: r.timestamp)
    
    def generate_summary(self, target: str) -> ScanResult:
        """Generate summary for a target and create readable files."""
        results = self.get_results(target)
        
        if not results:
            return ScanResult(target=target)
        
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        # Generate and save readable files
        self._generate_readable_files(target, results)
        
        return ScanResult(
            target=target,
            start_time=min(r.timestamp for r in results),
            end_time=max(r.timestamp for r in results),
            total_templates=len(results),
            successful_templates=successful,
            failed_templates=failed,
            results=results
        )
    
    def export_results(self, target: str, format: str = "txt") -> str:
        """Export results in specified format."""
        results = self.get_results(target)
        
        if format == "json":
            return json.dumps([r.dict() for r in results], indent=2)
        elif format == "txt":
            return self._format_text_results(results)
        elif format == "md":
            return self._format_markdown_results(results)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _sanitize_target(self, target: str) -> str:
        """Sanitize target for use as directory name."""
        # Replace unsafe characters with safe ones
        sanitized = target.replace("/", "_").replace(":", "_").replace("?", "_")
        return sanitized[:100]  # Limit length
    
    def _save_jsonl(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Save data to JSONL file."""
        with open(file_path, 'w') as f:
            json.dump(data, f, default=str)
            f.write('\n')
    
    def _append_jsonl(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Append data to JSONL file."""
        with open(file_path, 'a') as f:
            json.dump(data, f, default=str)
            f.write('\n')
    
    def _load_jsonl_results(self, file_path: Path) -> List[ExecutionResult]:
        """Load results from JSONL file."""
        results = []
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        results.append(ExecutionResult(**data))
        except Exception as e:
            print(f"Warning: Failed to load results from {file_path}: {e}")
        
        return results
    
    def _format_text_results(self, results: List[ExecutionResult]) -> str:
        """Format results as plain text."""
        lines = []
        lines.append(f"Results Summary ({len(results)} total)")
        lines.append("=" * 50)
        
        for result in results:
            lines.append(f"Template: {result.template_name}")
            lines.append(f"Tool: {result.tool}")
            lines.append(f"Target: {result.target}")
            lines.append(f"Success: {result.success}")
            lines.append(f"Execution Time: {result.execution_time:.2f}s")
            lines.append(f"Timestamp: {result.timestamp}")
            
            if result.stdout:
                lines.append("STDOUT:")
                lines.append(result.stdout)
            
            if result.stderr:
                lines.append("STDERR:")
                lines.append(result.stderr)
            
            lines.append("-" * 30)
        
        return "\n".join(lines)
    
    def _generate_readable_files(self, target: str, results: List[ExecutionResult]) -> None:
        """Generate readable .txt and .md files."""
        target_path = self.base_path / self._sanitize_target(target)
        readable_path = target_path / "readable"
        readable_path.mkdir(exist_ok=True)
        
        # Generate all scans file (includes all results)
        all_scans_txt = readable_path / "all_scans.txt"
        all_scans_md = readable_path / "all_scans.md"
        
        with open(all_scans_txt, 'w') as f:
            f.write(self._format_text_results(results))
        
        with open(all_scans_md, 'w') as f:
            f.write(self._format_markdown_results(results))
        
        # Generate successful scans only file
        successful_results = [r for r in results if r.success]
        if successful_results:
            successful_txt = readable_path / "successful_scans.txt"
            with open(successful_txt, 'w') as f:
                f.write(self._format_text_results(successful_results))
    
    def _format_markdown_results(self, results: List[ExecutionResult]) -> str:
        """Format results as Markdown."""
        lines = []
        lines.append(f"# Results Summary ({len(results)} total)")
        lines.append("")
        
        for result in results:
            lines.append(f"## {result.template_name}")
            lines.append(f"- **Tool:** {result.tool}")
            lines.append(f"- **Target:** {result.target}")
            lines.append(f"- **Success:** {result.success}")
            lines.append(f"- **Execution Time:** {result.execution_time:.2f}s")
            lines.append(f"- **Timestamp:** {result.timestamp}")
            lines.append("")
            
            if result.stdout:
                lines.append("### Output")
                lines.append("```")
                lines.append(result.stdout)
                lines.append("```")
                lines.append("")
            
            if result.stderr:
                lines.append("### Errors")
                lines.append("```")
                lines.append(result.stderr)
                lines.append("```")
                lines.append("")
        
        return "\n".join(lines)