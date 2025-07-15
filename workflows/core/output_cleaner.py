import re
from typing import Dict, Any


class OutputCleaner:
    """Clean binary and hex data from nmap script outputs"""
    
    @staticmethod
    def clean_script_output(script_data: Dict[str, Any], raw_output: bool = False) -> Dict[str, Any]:
        """Clean script output based on configuration"""
        if raw_output or 'output' not in script_data:
            return script_data
        
        script_id = script_data.get('id', '')
        output = script_data['output']
        
        # Scripts known to have binary data issues
        binary_prone_scripts = [
            'http-comments-displayer',
            'http-server-header',
            'http-favicon',
            'ssl-cert',
            'ssh-hostkey'
        ]
        
        if script_id in binary_prone_scripts:
            output = OutputCleaner._clean_binary_data(output)
        
        # Always clean common patterns
        output = OutputCleaner._clean_common_patterns(output)
        
        # Create cleaned script data
        cleaned_data = script_data.copy()
        cleaned_data['output'] = output
        
        return cleaned_data
    
    @staticmethod
    def _clean_binary_data(text: str) -> str:
        """Remove binary/hex data from text"""
        # Pattern for continuous hex sequences (e.g., \\xAB\\xCD\\xEF)
        hex_pattern = r'(\\x[0-9A-Fa-f]{2}){4,}'
        
        # Pattern for binary garbage (non-printable characters)
        # Keep newlines, tabs, and spaces
        binary_pattern = r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\xFF]+'
        
        # Clean hex sequences first
        text = re.sub(hex_pattern, '[BINARY DATA REMOVED]', text)
        
        # Clean remaining binary data
        text = re.sub(binary_pattern, '[BINARY]', text)
        
        # Clean up multiple consecutive [BINARY] markers
        text = re.sub(r'(\[BINARY[^\]]*\]\s*){2,}', '[BINARY DATA REMOVED]\n', text)
        
        return text
    
    @staticmethod
    def _clean_common_patterns(text: str) -> str:
        """Clean common unwanted patterns"""
        # Remove excessive whitespace while preserving structure
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {4,}', '    ', text)
        
        # Clean corrupted Unicode sequences
        text = re.sub(r'\\u[0-9A-Fa-f]{4}', '', text)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Trim each line
        lines = text.split('\n')
        cleaned_lines = [line.rstrip() for line in lines]
        text = '\n'.join(cleaned_lines)
        
        return text.strip()
    
    @staticmethod
    def clean_port_scripts(port_data: Dict[str, Any], raw_output: bool = False) -> Dict[str, Any]:
        """Clean all scripts in a port entry"""
        if raw_output or 'scripts' not in port_data:
            return port_data
        
        cleaned_port = port_data.copy()
        cleaned_scripts = []
        
        for script in port_data.get('scripts', []):
            cleaned_script = OutputCleaner.clean_script_output(script, raw_output)
            cleaned_scripts.append(cleaned_script)
        
        cleaned_port['scripts'] = cleaned_scripts
        return cleaned_port
    
