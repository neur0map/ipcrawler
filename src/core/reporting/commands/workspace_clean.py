"""Workspace Cleanup Command

"""




    """Command to clean up old workspaces"""
    
        """Initialize workspace clean command"""
        self.orchestrator = reporting_orchestrator
    
    def execute(self, target: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> bool:
        """Execute workspace cleanup
        
            
        """
        options = options or {}
        keep_count = options.get('keep_count', 5)
        dry_run = options.get('dry_run', False)
        
                # Clean specific target
                # Clean all targets
                
    
        """Clean workspaces for a specific target
        
            
        """
        
        
        workspaces = self.orchestrator.list_workspaces(target)
        timestamped_workspaces = [w for w in workspaces if w.is_timestamped]
        
        if len(timestamped_workspaces) <= keep_count:
            console.print(f"   ✅ No cleanup needed ({len(timestamped_workspaces)} workspaces <= {keep_count})")
        
        # Show what will be removed
        to_remove = timestamped_workspaces[keep_count:]
        
            timestamp_str = workspace.timestamp.strftime("%Y-%m-%d %H:%M:%S") if workspace.timestamp else "Unknown"
        
        
        # Confirm removal
        confirm = input(f"Remove {len(to_remove)} workspace(s)? [y/N]: ").lower().strip()
        
        # Perform cleanup
        removed_paths = self.orchestrator.clean_old_workspaces(target, keep_count)
        
        
        # Show disk space saved (approximate)
        total_size = 0
                    total_size += sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        
            size_mb = total_size / (1024 * 1024)
        
    
        """Clean workspaces for all targets
        
            
        """
        
        
        # Get all unique targets
        all_workspaces = self.orchestrator.list_workspaces()
        targets = set(w.target for w in all_workspaces if w.is_timestamped)
        
        
        
        total_to_remove = 0
        cleanup_plan = {}
        
            target_workspaces = [w for w in all_workspaces if w.target == target and w.is_timestamped]
            
                to_remove = target_workspaces[keep_count:]
                cleanup_plan[target] = to_remove
                total_to_remove += len(to_remove)
        
        if total_to_remove == 0:
        
        # Show cleanup plan
        
        
        # Confirm removal
        confirm = input(f"Remove {total_to_remove} workspace(s) across {len(cleanup_plan)} target(s)? [y/N]: ").lower().strip()
        
        # Perform cleanup for each target
        total_removed = 0
            removed_paths = self.orchestrator.clean_old_workspaces(target, keep_count)
            total_removed += len(removed_paths)
        
    
    @staticmethod
        """Get command help text
        
        """

  ipcrawler report clean-workspaces [--target=<target>] [--keep=<count>] [--dry-run]

  --target=<target>    Clean only specified target
  --keep=<count>      Number of workspaces to keep per target (default: 5)
  --dry-run           Show what would be removed without deleting

  ipcrawler report clean-workspaces --target=google_com --keep=3
  ipcrawler report clean-workspaces --keep=10

