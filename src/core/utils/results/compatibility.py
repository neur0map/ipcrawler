"""Compatibility layer for legacy result management


"""




    """Custom JSON encoder that handles datetime objects and enums."""
    


    """Abstract base class for result formatters."""
    
    @abstractmethod
        """Format scan data into the specific output format."""


    """Formats scan results as JSON."""
    
        """Format scan data as JSON string."""
        return json.dumps(data, indent=2, cls=DateTimeJSONEncoder)


    """Formats scan results as human-readable text report."""
    
        """Generate detailed text report."""
        # Use the centralized text reporter
        temp_reporter = TextReporter(Path.cwd())


# HTMLFormatter completely removed - only TXT and JSON supported


    """Legacy compatibility class that redirects to centralized reporting."""
    
        self.formatters = {
            'json': JSONFormatter(),
            'txt': TextFormatter()
            # HTML formatting completely removed
        }
    
    @staticmethod
        """Create workspace directory for scan results.
        
        """
        console.warning("ResultManager.create_workspace() is deprecated. Use reporting_orchestrator.create_versioned_workspace()", internal=True)
        
        # Redirect to centralized system with versioning enabled
        return reporting_orchestrator.create_versioned_workspace(target, enable_versioning=True)
    
    @staticmethod
        """Sanitize target name for use as directory name, preserving dots for IPs"""
        # Replace only truly invalid filesystem characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', target)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Ensure it's not empty and not too long
            sanitized = 'unknown_target'
            sanitized = sanitized[:50].rstrip('_')
    
    @staticmethod
        """Finalize scan data by sorting ports and removing internal indexes."""
        # Sort ports for each host
                host["ports"].sort(key=lambda p: p.get("port", 0))
        
        # Remove internal index
        
    
                    formats: Optional[List[str]] = None, workflow: str = None) -> None:
        """Save scan results using centralized reporting system.
        
        """
        console.warning("ResultManager.save_results() is deprecated. Use reporting_orchestrator.generate_workflow_reports()", internal=True)
        
        
        # Finalize data before saving
        data = self.finalize_scan_data(data)
        
            # Redirect to centralized orchestrator
            
            console.error(f"Centralized reporting failed: {e}", internal=True)
            # Emergency fallback - save as JSON only
    
        """Emergency fallback JSON save when centralized reporting fails"""
            json_file = workspace / f"{workflow}_results.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, cls=DateTimeJSONEncoder)
            console.warning(f"Emergency save: {json_file}", internal=True)
            console.error(f"Emergency save also failed: {e}", internal=True)
    
        """Fallback to legacy save method if centralized system fails."""
        console.warning("Using legacy save_results method as fallback", internal=True)
        
        # Determine file prefix
        prefix = "scan_"
        
        files_created = []
                console.warning(f"Unknown format: {fmt}", internal=True)
            
            # Determine filename
            if fmt == 'json':
                filename = f"{prefix}results.json"
            elif fmt == 'txt':
                filename = f"{prefix}report.txt"
                console.warning(f"Unhandled format: {fmt}", internal=True)
            
            filepath = workspace / filename
            
                # Format data
                formatted_content = self.formatters[fmt].format(target, data)
                
                # Write file with UTF-8 encoding
                with open(filepath, 'w', encoding='utf-8') as f:
                
                console.success(f"Successfully created: {filepath}", internal=True)
                
                console.error(f"Failed to create {fmt} file: {e}", internal=True)
        
        console.info(f"Legacy method created {len(files_created)} files", internal=True)
    
                               formats: Optional[List[str]] = None) -> None:
        """Asynchronously save scan results (wrapper for compatibility)."""
        # For now, just call the sync version
        # This can be enhanced later to use true async I/O if needed


# Global instance for compatibility
result_manager_compat = ResultManager()