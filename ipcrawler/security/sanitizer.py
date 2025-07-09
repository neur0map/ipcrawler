"""
Command sanitization and safe execution preparation.
"""

import re
import shlex
from typing import List, Dict, Optional
from .validator import ArgumentValidator, TargetValidator


class CommandSanitizer:
    """Sanitizes commands for safe execution."""
    
    @classmethod
    def sanitize_command(cls, tool: str, args: List[str], target: str, wordlist: Optional[str] = None, 
                        preset_args: Optional[List[str]] = None, variables: Optional[Dict[str, str]] = None,
                        chain_variables: Optional[Dict[str, str]] = None) -> List[str]:
        """Sanitize and prepare command for execution."""
        # Validate tool name
        if not re.match(r'^[a-zA-Z0-9_/-]+$', tool):
            raise ValueError(f'Invalid tool name: {tool}')
        
        # Validate and sanitize target
        if not TargetValidator.validate_target(target):
            raise ValueError(f'Invalid target: {target}')
        
        sanitized_target = TargetValidator.sanitize_target(target)
        
        # Combine preset args with template args
        all_args = []
        if preset_args:
            all_args.extend(preset_args)
        if args:
            all_args.extend(args)
        
        # Validate and sanitize arguments
        if not ArgumentValidator.validate_arguments(all_args):
            raise ValueError('Invalid arguments detected')
        
        sanitized_args = [ArgumentValidator.sanitize_argument(arg) for arg in all_args]
        
        # Replace placeholders with sanitized values
        final_args = []
        for arg in sanitized_args:
            processed_arg = arg
            
            # Replace {{target}} placeholder
            if '{{target}}' in processed_arg:
                processed_arg = processed_arg.replace('{{target}}', sanitized_target)
            
            # Replace {{wordlist}} placeholder
            if '{{wordlist}}' in processed_arg and wordlist:
                # Additional security validation for wordlist path
                if cls._validate_wordlist_path(wordlist):
                    processed_arg = processed_arg.replace('{{wordlist}}', wordlist)
                else:
                    raise ValueError('Invalid wordlist path')
            
            # Replace custom variable placeholders
            # Merge chain variables with template variables (chain variables take precedence)
            all_variables = {}
            if variables:
                all_variables.update(variables)
            if chain_variables:
                all_variables.update(chain_variables)
            
            if all_variables:
                for var_name, var_value in all_variables.items():
                    placeholder = f'{{{{{var_name}}}}}'
                    if placeholder in processed_arg:
                        # Validate variable value before substitution
                        if cls._validate_variable_value(var_value):
                            processed_arg = processed_arg.replace(placeholder, var_value)
                        else:
                            raise ValueError(f'Invalid variable value: {var_name}')
            
            final_args.append(processed_arg)
        
        return [tool] + final_args
    
    @classmethod
    def _validate_wordlist_path(cls, path: str) -> bool:
        """Validate wordlist file path for security."""
        # Check for dangerous patterns
        dangerous_patterns = [
            r'[;&|`$()<>]',  # Shell metacharacters
            r'\.\./',        # Directory traversal attempts
            r'^\s*$',        # Empty/whitespace only
            r'[\x00-\x1f\x7f-\x9f]',  # Control characters
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, path):
                return False
        
        # Path length check
        if len(path) > 500:
            return False
        
        return True
    
    @classmethod
    def _validate_variable_value(cls, value: str) -> bool:
        """Validate custom variable value for security."""
        # Check for dangerous patterns
        dangerous_patterns = [
            r'[;&|`$()<>]',  # Shell metacharacters
            r'\.\./',        # Directory traversal attempts
            r'[\x00-\x1f\x7f-\x9f]',  # Control characters
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, value):
                return False
        
        # Value length check
        if len(value) > 500:
            return False
        
        return True
    
    @classmethod
    def prepare_environment(cls, env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare safe environment variables."""
        import os
        
        # Start with essential system environment variables
        safe_env = {
            'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin'),
            'HOME': os.environ.get('HOME', '/tmp'),
            'USER': os.environ.get('USER', 'unknown')
        }
        
        # Add custom environment variables if provided
        if env:
            for key, value in env.items():
                # Validate environment variable name
                if not re.match(r'^[A-Z_][A-Z0-9_]*$', key):
                    continue
                
                # Sanitize value
                sanitized_value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
                if len(sanitized_value) <= 1000:
                    safe_env[key] = sanitized_value
        
        return safe_env
    
    @classmethod
    def validate_command_safety(cls, command: List[str]) -> bool:
        """Final validation of command safety."""
        if not command or len(command) > 51:  # tool + max 50 args
            return False
        
        # Check each component
        for part in command:
            if not ArgumentValidator.validate_argument(part):
                return False
        
        return True