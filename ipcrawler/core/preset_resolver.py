"""
Preset resolution service for template argument presets.
"""

from typing import List, Optional, Dict, Any
from ..core.config import ConfigManager


class PresetResolver:
    """Resolves preset names to argument lists."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def resolve_preset(self, preset_name: str) -> Optional[List[str]]:
        """
        Resolve a preset name to its argument list.
        
        Args:
            preset_name: Preset name in format 'tool.preset_name' or 'global_preset'
            
        Returns:
            List of arguments from the preset, or None if not found
            
        Raises:
            ValueError: If preset name format is invalid
        """
        if not preset_name:
            return None
            
        # Validate preset name format
        if not self._validate_preset_name(preset_name):
            raise ValueError(f'Invalid preset name format: {preset_name}')
        
        # Get preset from config
        preset_args = self.config_manager.get_preset(preset_name)
        
        if preset_args is None:
            # Check if it's a tool-specific preset that doesn't exist
            if '.' in preset_name:
                tool_name, preset_key = preset_name.split('.', 1)
                available_presets = self.config_manager.list_presets_for_tool(tool_name)
                if available_presets:
                    available_names = list(available_presets.keys())
                    raise ValueError(f'Preset "{preset_key}" not found for tool "{tool_name}". Available presets: {available_names}')
                else:
                    raise ValueError(f'No presets available for tool "{tool_name}"')
            else:
                # Global preset not found
                all_presets = self.config_manager.get_all_presets()
                global_presets = [k for k in all_presets.keys() if '.' not in k]
                if global_presets:
                    raise ValueError(f'Global preset "{preset_name}" not found. Available global presets: {global_presets}')
                else:
                    raise ValueError(f'Global preset "{preset_name}" not found and no global presets available')
        
        # Return a copy to avoid mutation
        return preset_args.copy() if preset_args else None
    
    def get_available_presets(self, tool_name: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get all available presets, optionally filtered by tool.
        
        Args:
            tool_name: Optional tool name to filter presets
            
        Returns:
            Dictionary of preset names to argument lists
        """
        if tool_name:
            return self.config_manager.list_presets_for_tool(tool_name)
        else:
            return self.config_manager.get_all_presets()
    
    def preset_exists(self, preset_name: str) -> bool:
        """
        Check if a preset exists.
        
        Args:
            preset_name: Preset name to check
            
        Returns:
            True if preset exists, False otherwise
        """
        try:
            return self.resolve_preset(preset_name) is not None
        except ValueError:
            return False
    
    def _validate_preset_name(self, preset_name: str) -> bool:
        """
        Validate preset name format.
        
        Args:
            preset_name: Preset name to validate
            
        Returns:
            True if valid format, False otherwise
        """
        import re
        
        # Check basic format constraints
        if not preset_name or len(preset_name) > 100:
            return False
        
        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9_.-]+$', preset_name):
            return False
        
        # If it contains a dot, validate tool.preset format
        if '.' in preset_name:
            parts = preset_name.split('.')
            if len(parts) != 2:
                return False
            tool_name, preset_key = parts
            
            # Validate tool name and preset key separately
            if not tool_name or not preset_key:
                return False
            if len(tool_name) > 20 or len(preset_key) > 50:
                return False
        
        return True
    
    def list_preset_names(self, tool_name: Optional[str] = None) -> List[str]:
        """
        Get list of all preset names.
        
        Args:
            tool_name: Optional tool name to filter presets
            
        Returns:
            List of preset names
        """
        all_presets = self.get_available_presets()
        
        if tool_name:
            # Return tool-specific presets
            tool_presets = all_presets.get(tool_name, {})
            return [f"{tool_name}.{preset}" for preset in tool_presets.keys()]
        else:
            # Return all preset names (global + tool-specific)
            preset_names = []
            
            # Add global presets (keys that don't contain dots and aren't tool sections)
            for key, value in all_presets.items():
                if isinstance(value, list):  # Global preset
                    preset_names.append(key)
                elif isinstance(value, dict):  # Tool section
                    for preset_key in value.keys():
                        preset_names.append(f"{key}.{preset_key}")
            
            return sorted(preset_names)