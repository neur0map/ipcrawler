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
    
    def __init__(self, base_path: str = "results", config_manager=None):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self.config_manager = config_manager
        self._current_run_numbers = {}  # Track current run number per target
    
    def start_new_scan_session(self, target: str) -> None:
        """Start a new scan session for a target (creates new run number)."""
        sanitized_target = self._sanitize_target(target)
        # Clear any existing run number to force generation of new one
        if sanitized_target in self._current_run_numbers:
            del self._current_run_numbers[sanitized_target]
    
    def save_result(self, result: ExecutionResult, target: str) -> None:
        """Save a single execution result and update readable files incrementally."""
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
        
        # Update readable files incrementally
        self._update_readable_files_incremental(target)
    
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
            return self._format_readable_json_results(results)
        elif format == "jsonl":
            # Raw JSONL format (one object per line)
            return "\n".join(json.dumps(r.dict(), default=str) for r in results)
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
            
            # Handle skipped sudo plugins
            if result.return_code == -2:
                lines.append("Status: SKIPPED (requires sudo)")
                lines.append(f"Reason: {result.error_message}")
            else:
                lines.append(f"Success: {result.success}")
            
            lines.append(f"Execution Time: {result.execution_time:.2f}s")
            lines.append(f"Timestamp: {result.timestamp}")
            
            if result.stdout:
                lines.append("STDOUT:")
                # Filter CTF noise from stdout
                filtered_stdout = "\n".join(self._filter_ctf_noise(result.stdout.splitlines()))
                lines.append(filtered_stdout)
            
            if result.stderr:
                lines.append("STDERR:")
                lines.append(result.stderr)
            
            lines.append("-" * 30)
        
        return "\n".join(lines)
    
    def _generate_readable_files(self, target: str, results: List[ExecutionResult]) -> None:
        """Generate readable .txt, .md, and .json files with run-based separation."""
        target_path = self.base_path / self._sanitize_target(target)
        readable_path = target_path / "readable"
        readable_path.mkdir(exist_ok=True)
        
        # Use tracked run number for this target, or get next available
        sanitized_target = self._sanitize_target(target)
        if sanitized_target not in self._current_run_numbers:
            self._current_run_numbers[sanitized_target] = self._get_next_run_number(readable_path)
        
        run_number = self._current_run_numbers[sanitized_target]
        
        # Generate all scans files with run number
        all_scans_txt = readable_path / f"all_scans_{run_number}.txt"
        all_scans_md = readable_path / f"all_scans_{run_number}.md"
        all_scans_json = readable_path / f"all_scans_{run_number}.json"
        
        with open(all_scans_txt, 'w') as f:
            f.write(self._format_text_results(results))
        
        with open(all_scans_md, 'w') as f:
            f.write(self._format_markdown_results(results))
        
        with open(all_scans_json, 'w') as f:
            f.write(self._format_readable_json_results(results))
        
        # Generate raw results files (successful scans only)
        successful_results = [r for r in results if r.success]
        if successful_results:
            raw_results_txt = readable_path / f"raw_results_{run_number}.txt"
            raw_results_json = readable_path / f"raw_results_{run_number}.json"
            
            with open(raw_results_txt, 'w') as f:
                f.write(self._format_text_results(successful_results))
            
            with open(raw_results_json, 'w') as f:
                f.write(self._format_readable_json_results(successful_results))
    
    def _format_markdown_results(self, results: List[ExecutionResult]) -> str:
        """Format results as Markdown."""
        lines = []
        lines.append(f"# Results Summary ({len(results)} total)")
        lines.append("")
        
        for result in results:
            lines.append(f"## {result.template_name}")
            lines.append(f"- **Tool:** {result.tool}")
            lines.append(f"- **Target:** {result.target}")
            
            # Handle skipped sudo plugins
            if result.return_code == -2:
                lines.append("- **Status:** SKIPPED (requires sudo)")
                lines.append(f"- **Reason:** {result.error_message}")
            else:
                lines.append(f"- **Success:** {result.success}")
            
            lines.append(f"- **Execution Time:** {result.execution_time:.2f}s")
            lines.append(f"- **Timestamp:** {result.timestamp}")
            lines.append("")
            
            if result.stdout:
                lines.append("### Output")
                lines.append("```")
                # Filter CTF noise from stdout
                filtered_stdout = "\n".join(self._filter_ctf_noise(result.stdout.splitlines()))
                lines.append(filtered_stdout)
                lines.append("```")
                lines.append("")
            
            if result.stderr:
                lines.append("### Errors")
                lines.append("```")
                lines.append(result.stderr)
                lines.append("```")
                lines.append("")
        
        return "\n".join(lines)
    
    def _format_readable_json_results(self, results: List[ExecutionResult]) -> str:
        """Format results as readable JSON with proper indentation and structure."""
        # Create a structured output for better readability
        structured_results = {
            "scan_summary": {
                "total_results": len(results),
                "successful_scans": sum(1 for r in results if r.success),
                "failed_scans": sum(1 for r in results if not r.success and r.return_code != -2),
                "skipped_scans": sum(1 for r in results if r.return_code == -2),
                "scan_time_range": {
                    "start": min(r.timestamp for r in results).isoformat() if results else None,
                    "end": max(r.timestamp for r in results).isoformat() if results else None
                },
                "targets": list({r.target for r in results}),
                "tools_used": list({r.tool for r in results})
            },
            "results": []
        }
        
        # Add individual results with organized structure
        for result in results:
            result_data = {
                "template_info": {
                    "name": result.template_name,
                    "tool": result.tool,
                    "target": result.target
                },
                "execution": {
                    "success": result.success,
                    "timestamp": result.timestamp.isoformat(),
                    "execution_time_seconds": round(result.execution_time, 2),
                    "return_code": result.return_code,
                    "status": "skipped" if result.return_code == -2 else ("success" if result.success else "failed")
                },
                "output": {
                    "stdout": self._filter_ctf_noise(result.stdout.splitlines()) if result.stdout else None,
                    "stderr": result.stderr.splitlines() if result.stderr else None,
                    "error_message": result.error_message if result.error_message else None
                }
            }
            
            # Remove None values for cleaner output
            result_data["output"] = {k: v for k, v in result_data["output"].items() if v is not None}
            
            structured_results["results"].append(result_data)
        
        # Use the configured JSON formatting from output.toml
        return json.dumps(structured_results, indent=2, sort_keys=True, default=str)
    
    def _filter_ctf_noise(self, lines: List[str]) -> List[str]:
        """Filter out CTF-irrelevant noise from tool output based on configuration."""
        if not lines:
            return lines
        
        # Check if CTF filtering is enabled
        if not self._is_ctf_filtering_enabled():
            return lines
        
        filtered_lines = []
        skip_fingerprint = False
        
        for line in lines:
            # Filter nmap service fingerprints if enabled
            if self._should_filter_nmap_fingerprints():
                if "NEXT SERVICE FINGERPRINT" in line:
                    skip_fingerprint = True
                    continue
                
                if line.startswith("SF:") or line.startswith("SF-"):
                    continue
                
                if skip_fingerprint and not line.startswith("SF"):
                    if line.strip() == "" or "Service detection performed" in line:
                        skip_fingerprint = False
                    else:
                        continue
            
            # Filter submission prompts if enabled
            if self._should_filter_submission_prompts():
                if any(prompt in line for prompt in [
                    "please submit the following fingerprints",
                    "submit.cgi?new-service",
                    "Please report any incorrect results"
                ]):
                    continue
            
            # Filter debug output if enabled
            if self._should_filter_debug_output():
                if any(debug_pattern in line.lower() for debug_pattern in [
                    "debug:", "verbose:", "trace:", "[debug]", "[verbose]"
                ]):
                    continue
            
            # Filter tool noise if enabled (keep only valuable findings)
            if self._should_filter_submission_prompts():  # Reuse this setting for tool noise
                # Skip gobuster progress and status lines, keep only findings
                if any(noise_pattern in line for noise_pattern in [
                    "===============================================================",
                    "Gobuster v",
                    "by OJ Reeves",
                    "https://github.com/OJ/gobuster",
                    "===============================================================",
                    "[+] Url:",
                    "[+] User Agent:",
                    "[+] Timeout:",
                    "[+] Threads:",
                    "[+] Wordlist:",
                    "Progress:",
                    "Error:"
                ]):
                    continue
                    
                # Keep only lines that contain actual findings (Status: 200, Found:, etc.)
                if line.startswith("Found:") or "Status: 200" in line or "Status: 403" in line:
                    # This is a valuable finding - keep it
                    pass
                elif line.strip() and not any(keeper in line for keeper in ["Found:", "Status:"]):
                    # This might be gobuster noise if it doesn't contain findings
                    if "gobuster" in line.lower() or line.startswith("="):
                        continue
                
                # Filter curl verbose headers for vhost checks (keep only valuable info)
                if any(curl_noise in line for curl_noise in [
                    "Content-Type: text/html",
                    "Content-Length:",
                    "Connection: keep-alive",
                    "Server: ",
                    "Access-Control-Allow-Origin:",
                    "Access-Control-Allow-Credentials:",
                    "Date: "
                ]):
                    continue
            
            # Filter version banners if enabled
            if self._should_filter_version_banners():
                if any(banner_pattern in line for banner_pattern in [
                    "Starting Nmap", "Nmap done:", "( https://nmap.org )"
                ]):
                    continue
            
            # Keep lines that pass all filters
            if not skip_fingerprint:
                filtered_lines.append(line)
        
        return filtered_lines
    
    def _is_ctf_filtering_enabled(self) -> bool:
        """Check if CTF filtering is enabled in configuration."""
        if not self.config_manager:
            return True  # Default to enabled if no config
        return self.config_manager.get_config_value("output", "export.enable_ctf_filtering", True)
    
    def _should_filter_nmap_fingerprints(self) -> bool:
        """Check if nmap fingerprint filtering is enabled."""
        if not self.config_manager:
            return True  # Default to enabled
        return self.config_manager.get_config_value("output", "export.filter_nmap_fingerprints", True)
    
    def _should_filter_submission_prompts(self) -> bool:
        """Check if submission prompt filtering is enabled."""
        if not self.config_manager:
            return True  # Default to enabled
        return self.config_manager.get_config_value("output", "export.filter_submission_prompts", True)
    
    def _should_filter_version_banners(self) -> bool:
        """Check if version banner filtering is enabled."""
        if not self.config_manager:
            return False  # Default to disabled
        return self.config_manager.get_config_value("output", "export.filter_version_banners", False)
    
    def _should_filter_debug_output(self) -> bool:
        """Check if debug output filtering is enabled."""
        if not self.config_manager:
            return True  # Default to enabled
        return self.config_manager.get_config_value("output", "export.filter_debug_output", True)
    
    def _get_next_run_number(self, readable_path: Path) -> int:
        """Get the next run number based on existing files."""
        max_run = 0
        
        # Check for existing all_scans_* files
        for file_path in readable_path.glob("all_scans_*.txt"):
            try:
                # Extract run number from filename
                filename = file_path.stem  # Remove .txt extension
                run_part = filename.split("_")[-1]  # Get last part after underscore
                run_num = int(run_part)
                max_run = max(max_run, run_num)
            except (ValueError, IndexError):
                continue
        
        return max_run + 1
    
    def _update_readable_files_incremental(self, target: str) -> None:
        """Update readable files incrementally as results come in."""
        try:
            # Get all current results
            results = self.get_results(target)
            if not results:
                return
            
            # Generate readable files with current results
            self._generate_readable_files(target, results)
            
        except Exception as e:
            # Don't break execution if readable file generation fails
            print(f"Warning: Failed to update readable files: {e}")