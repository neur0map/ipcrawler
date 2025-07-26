"""Master Report Generation Command

"""




    """Command to generate master reports from workspace data"""
    
        """Initialize master report command"""
        self.orchestrator = reporting_orchestrator
    
    def execute(self, workspace_name: str, options: Optional[Dict[str, Any]] = None) -> Optional[Path]:
        """Execute master report generation
        
            
        """
        options = options or {}
        
        
        # Check if workspace exists
        workspace_path = self.orchestrator.workspace_manager.get_workspace_path(workspace_name)
        
        
        
            master_report_path = self.orchestrator.generate_master_report_from_workspace(workspace_name)
            
                # Show file statistics
                file_size = master_report_path.stat().st_size
                    line_count = sum(1 for _ in f)
                
                
                # Check for wordlist recommendations
                wordlists_dir = workspace_path / f"wordlists_for_{workspace_path.name.split('_')[0]}"
                    wordlist_file = wordlists_dir / "recommended_wordlist.txt"
                        wordlist_size = wordlist_file.stat().st_size
                            wordlist_lines = sum(1 for _ in f)
                
                
    
        """Show available workspaces to help user"""
        
        workspaces = self.orchestrator.list_workspaces()
        
        # Group by target
        targets = {}
                targets[workspace.target] = []
        
                status = " (latest)" if workspace.is_symlink else ""
                timestamp = f" [{workspace.timestamp.strftime('%Y-%m-%d %H:%M')}]" if workspace.timestamp else ""
            
        
            example_workspace = workspaces[0].name
            console.print(f"  ipcrawler report master-report --workspace={example_workspace}")
    
    @staticmethod
        """Get command help text
        
        """

  ipcrawler report master-report --workspace=<workspace_name>

  ipcrawler report master-report --workspace=google_com_20250125_143022
  ipcrawler report master-report --workspace=google_com  # Uses latest

