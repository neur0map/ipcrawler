"""
Template discovery and loading module.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..models.template import ToolTemplate, TemplateConfig
from .schema import TemplateSchema
from .sentry_integration import sentry_manager, with_sentry_context, capture_validation_error


class TemplateDiscovery:
    """Handles template discovery and validation."""
    
    def __init__(self, base_path: str = "templates"):
        self.config = TemplateConfig(base_path=base_path)
        self.base_path = Path(base_path)
        # Also check ipcrawler/templates directory
        if not self.base_path.exists():
            alt_path = Path("ipcrawler/templates")
            if alt_path.exists():
                self.base_path = alt_path
    
    @with_sentry_context("template_discovery")
    def discover_templates(self, subfolder: Optional[str] = None) -> List[ToolTemplate]:
        """Discover and load all templates from a folder."""
        templates = []
        
        sentry_manager.add_breadcrumb(
            f"Discovering templates in {subfolder or 'all folders'}",
            data={"subfolder": subfolder, "base_path": str(self.base_path)}
        )
        
        if subfolder:
            search_path = self.base_path / subfolder
        else:
            search_path = self.base_path
        
        if not search_path.exists():
            return templates
        
        for file_path in search_path.rglob("*.json"):
            try:
                template = self._load_template(file_path)
                if template:
                    templates.append(template)
            except Exception as e:
                print(f"Warning: Failed to load template {file_path}: {e}")
        
        return templates
    
    def _load_template(self, file_path: Path) -> Optional[ToolTemplate]:
        """Load and validate a single template."""
        try:
            # Check file size
            if file_path.stat().st_size > self.config.max_template_size:
                raise ValueError(f"Template file too large: {file_path}")
            
            # Load JSON
            with open(file_path, 'r') as f:
                template_data = json.load(f)
            
            # Validate schema if enabled
            if self.config.validate_on_load:
                TemplateSchema.validate_template_strict(template_data)
            
            # Convert legacy format if needed
            template_data = self._convert_legacy_format(template_data)
            
            # Create and validate template
            return ToolTemplate(**template_data)
            
        except Exception as e:
            raise RuntimeError(f"Failed to load template {file_path}: {e}")
    
    def _convert_legacy_format(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert legacy shell command format to structured format."""
        # Handle legacy "command" field
        if "command" in template_data and "tool" not in template_data:
            command = template_data["command"]
            
            if isinstance(command, list) and len(command) > 0:
                # Extract tool and args from command list
                template_data["tool"] = command[0]
                template_data["args"] = command[1:] if len(command) > 1 else []
                
                # Remove old command field
                del template_data["command"]
            else:
                raise ValueError("Invalid legacy command format")
        
        return template_data
    
    def get_template_by_name(self, name: str, subfolder: Optional[str] = None) -> Optional[ToolTemplate]:
        """Get a specific template by name."""
        templates = self.discover_templates(subfolder)
        
        for template in templates:
            if template.name == name:
                return template
        
        return None
    
    def list_template_names(self, subfolder: Optional[str] = None) -> List[str]:
        """List all available template names."""
        templates = self.discover_templates(subfolder)
        return [template.name for template in templates]
    
    def get_template_categories(self) -> List[str]:
        """Get all available template categories."""
        categories = []
        
        if not self.base_path.exists():
            return categories
        
        for item in self.base_path.iterdir():
            if item.is_dir():
                categories.append(item.name)
        
        return sorted(categories)
    
    def validate_all_templates(self) -> Dict[str, List[str]]:
        """Validate all templates and return results."""
        results = {"valid": [], "invalid": []}
        
        for category in self.get_template_categories():
            category_path = self.base_path / category
            
            for file_path in category_path.rglob("*.json"):
                try:
                    self._load_template(file_path)
                    results["valid"].append(str(file_path))
                except Exception as e:
                    results["invalid"].append(f"{file_path}: {e}")
        
        return results