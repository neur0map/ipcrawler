"""Workspace List Command

"""




    """Command to list available workspaces"""
    
        """Initialize workspace list command"""
        self.orchestrator = reporting_orchestrator
    
    def execute(self, target: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> bool:
        """Execute workspace listing
        
            
        """
        options = options or {}
        show_details = options.get('details', False)
        
            workspaces = self.orchestrator.list_workspaces(target)
            
            
            # Show summary
            summary = self.orchestrator.workspace_manager.get_workspace_summary()
            
            
            # Group by target
            targets = {}
                    targets[workspace.target] = []
            
                
                # Sort by timestamp (newest first)
                    key=lambda w: w.timestamp or datetime.min, 
                    reverse=True
                )
                
            
            
    
    def _print_workspace_info(self, workspace, show_details=False):
        """Print information about a single workspace
        
        """
        # Format timestamp
            timestamp_str = workspace.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            timestamp_str = "No timestamp"
        
        # Status indicators
        status_indicators = []
        
        status_str = f" ({', '.join(status_indicators)})" if status_indicators else ""
        
        
            
            # Check for reports
                reports = self._check_available_reports(workspace.path)
    
        """Check what reports are available in workspace
        
            
        """
        reports = []
        
        # Check for master report
        
        # Check for workflow results
        workflow_files = [
            "nmap_fast_01_results.json",
            "nmap_02_results.json",
            "http_03_results.json", 
            "mini_spider_04_results.json",
            "smartlist_05_results.json"
        ]
        
        workflow_count = sum(1 for f in workflow_files if (workspace_path / f).exists())
        
        # Check for wordlist recommendations
        wordlist_dirs = list(workspace_path.glob("wordlists_for_*"))
        
    
    @staticmethod
        """Get command help text
        
        """

  ipcrawler report list-workspaces [--target=<target>] [--details]

  --target=<target>    Filter by target name
  --details           Show detailed information

  ipcrawler report list-workspaces --target=google_com

