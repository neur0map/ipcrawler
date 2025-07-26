"""Subprocess utilities for async command execution"""

import asyncio
import logging
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path


class ProcessManager:
    """Manages async subprocess execution with common patterns"""
    
    @staticmethod
    async def execute_command(
        cmd: List[str],
        timeout: Optional[float] = None,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Tuple[int, str, str]:
        """Execute command and return (returncode, stdout, stderr)
        
        Args:
            cmd: Command and arguments as list
            timeout: Command timeout in seconds
            cwd: Working directory
            env: Environment variables
            
        Returns:
            Tuple of (return_code, stdout_string, stderr_string)
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env
            )
            
            if timeout:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            else:
                stdout, stderr = await process.communicate()
            
            return (
                process.returncode,
                stdout.decode('utf-8', errors='ignore'),
                stderr.decode('utf-8', errors='ignore')
            )
            
        except asyncio.TimeoutError:
            try:
                process.kill()
                await process.wait()
            except:
                pass
            raise
        except Exception as e:
            logging.error(f"Command execution failed: {e}")
            raise


    @staticmethod
    async def execute_with_progress(
        cmd: List[str],
        progress_queue: Optional[asyncio.Queue] = None,
        progress_message: str = "command_complete",
        **kwargs
    ) -> Tuple[int, str, str]:
        """Execute command and send progress notification
        
        Args:
            cmd: Command and arguments
            progress_queue: Queue to send progress updates
            progress_message: Message to send on completion
            **kwargs: Additional arguments for execute_command
            
        Returns:
            Tuple of (return_code, stdout_string, stderr_string)
        """
        result = await ProcessManager.execute_command(cmd, **kwargs)
        
        if progress_queue:
            try:
                await progress_queue.put(progress_message)
            except:
                pass  # Ignore queue errors
        
        return result


    @staticmethod
    async def execute_with_semaphore(
        semaphore: asyncio.Semaphore,
        cmd: List[str],
        **kwargs
    ) -> Tuple[int, str, str]:
        """Execute command with semaphore control
        
        Args:
            semaphore: Semaphore for concurrency control
            cmd: Command and arguments
            **kwargs: Additional arguments for execute_command
            
        Returns:
            Tuple of (return_code, stdout_string, stderr_string)
        """
        async with semaphore:
            return await ProcessManager.execute_command(cmd, **kwargs)


    @staticmethod
    async def execute_batch_with_semaphore(
        commands: List[List[str]],
        max_concurrent: int = 5,
        **kwargs
    ) -> List[Tuple[int, str, str]]:
        """Execute multiple commands with concurrency control
        
        Args:
            commands: List of command lists to execute
            max_concurrent: Maximum concurrent processes
            **kwargs: Additional arguments for execute_command
            
        Returns:
            List of results in same order as input commands
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        tasks = [
            ProcessManager.execute_with_semaphore(semaphore, cmd, **kwargs)
            for cmd in commands
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)


class CommandBuilder:
    """Helper class for building common command patterns"""
    
    @staticmethod
    def with_timeout(cmd: List[str], timeout_seconds: int) -> List[str]:
        """Wrap command with timeout"""
        return ["timeout", str(timeout_seconds)] + cmd
    
    @staticmethod
    def with_output_redirect(cmd: List[str], output_file: str, append: bool = False) -> List[str]:
        """Add output redirection to command"""
        redirect = ">>" if append else ">"
        return cmd + [redirect, output_file]
    
    @staticmethod
    def suppress_stderr(cmd: List[str]) -> List[str]:
        """Suppress stderr output"""
        return cmd + ["2>/dev/null"]


def register_process_cleanup(process: asyncio.subprocess.Process, process_list: Optional[List] = None):
    """Register process for cleanup tracking
    
    Args:
        process: The subprocess to track
        process_list: Optional list to append process to
    """
    if process_list is not None:
        try:
            process_list.append(process)
        except:
            pass  # Ignore if process_list is not available