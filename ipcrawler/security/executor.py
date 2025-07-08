"""
Secure command execution without shell=True.
"""

import asyncio
import subprocess
import signal
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from ..models.result import ExecutionResult
from .sanitizer import CommandSanitizer


class SecureExecutor:
    """Executes commands securely without shell=True."""
    
    def __init__(self, timeout: int = 60, max_output_size: int = 1024 * 1024):
        self.timeout = timeout
        self.max_output_size = max_output_size
    
    async def execute_template(
        self, 
        template_name: str,
        tool: str, 
        args: Optional[List[str]] = None, 
        target: str = "",
        env: Optional[Dict[str, str]] = None,
        wordlist: Optional[str] = None,
        timeout: Optional[int] = None,
        preset: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
        preset_resolver: Optional[object] = None
    ) -> ExecutionResult:
        """Execute a template safely."""
        start_time = datetime.now()
        execution_timeout = timeout or self.timeout
        
        try:
            # Resolve preset arguments if preset is provided
            preset_args = None
            if preset and preset_resolver:
                preset_args = preset_resolver.resolve_preset(preset)
                if preset_args is None:
                    raise ValueError(f'Preset not found: {preset}')
            
            # Ensure we have either args or preset_args
            if not args and not preset_args:
                raise ValueError('Either args or preset must be provided')
            
            # Sanitize command with preset support
            command = CommandSanitizer.sanitize_command(
                tool, 
                args or [], 
                target, 
                wordlist, 
                preset_args, 
                variables
            )
            safe_env = CommandSanitizer.prepare_environment(env)
            
            # Final safety check
            if not CommandSanitizer.validate_command_safety(command):
                raise ValueError('Command failed final safety validation')
            
            # Execute with security measures
            stdout, stderr, return_code = await self._execute_secure(
                command, safe_env, execution_timeout
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ExecutionResult(
                template_name=template_name,
                tool=tool,
                target=target,
                success=(return_code == 0),
                stdout=stdout,
                stderr=stderr,
                return_code=return_code,
                execution_time=execution_time,
                timestamp=start_time
            )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ExecutionResult(
                template_name=template_name,
                tool=tool,
                target=target,
                success=False,
                stdout='',
                stderr=str(e),
                return_code=-1,
                execution_time=execution_time,
                timestamp=start_time,
                error_message=str(e)
            )
    
    async def _execute_secure(
        self, 
        command: List[str], 
        env: Dict[str, str], 
        timeout: int
    ) -> Tuple[str, str, int]:
        """Execute command with security measures."""
        try:
            # Create subprocess with security settings
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                shell=False,  # NEVER use shell=True
                cwd=None,     # Don't change working directory
                preexec_fn=None,  # No pre-execution function
                start_new_session=True  # Start new session for better isolation
            )
            
            # Wait for completion with timeout
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                
                # Decode output safely
                stdout = stdout_data.decode('utf-8', errors='replace')
                stderr = stderr_data.decode('utf-8', errors='replace')
                
                # Limit output size
                if len(stdout) > self.max_output_size:
                    stdout = stdout[:self.max_output_size] + '\\n[OUTPUT TRUNCATED]'
                if len(stderr) > self.max_output_size:
                    stderr = stderr[:self.max_output_size] + '\\n[OUTPUT TRUNCATED]'
                
                return stdout, stderr, process.returncode
                
            except asyncio.TimeoutError:
                # Kill process on timeout
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass
                
                raise TimeoutError(f'Command timed out after {timeout} seconds')
        
        except Exception as e:
            raise RuntimeError(f'Execution failed: {str(e)}')
    
    async def execute_batch(
        self, 
        templates: List[Dict],
        target: str,
        concurrent_limit: int = 10
    ) -> List[ExecutionResult]:
        """Execute multiple templates concurrently."""
        semaphore = asyncio.Semaphore(concurrent_limit)
        
        async def execute_with_semaphore(template_data):
            async with semaphore:
                return await self.execute_template(
                    template_name=template_data['name'],
                    tool=template_data['tool'],
                    args=template_data['args'],
                    target=target,
                    env=template_data.get('env'),
                    timeout=template_data.get('timeout')
                )
        
        tasks = [execute_with_semaphore(template) for template in templates]
        return await asyncio.gather(*tasks, return_exceptions=True)