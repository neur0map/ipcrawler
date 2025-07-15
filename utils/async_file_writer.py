import asyncio
import json
from pathlib import Path
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor


class AsyncFileWriter:
    """Asynchronous file writer with buffering and thread pool execution"""
    
    def __init__(self, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._write_queue: asyncio.Queue = asyncio.Queue()
        self._writer_task: Optional[asyncio.Task] = None
        self._is_running = False
    
    def start(self):
        """Start the async writer task"""
        if not self._is_running:
            self._is_running = True
            self._writer_task = asyncio.create_task(self._writer_loop())
    
    async def stop(self):
        """Stop the async writer task and flush pending writes"""
        if self._is_running:
            self._is_running = False
            # Signal stop by putting None
            await self._write_queue.put(None)
            if self._writer_task:
                await self._writer_task
            self.executor.shutdown(wait=True)
    
    async def _writer_loop(self):
        """Main writer loop that processes write requests"""
        loop = asyncio.get_event_loop()
        
        while self._is_running:
            try:
                # Get write request with timeout
                write_request = await asyncio.wait_for(
                    self._write_queue.get(), timeout=1.0
                )
                
                if write_request is None:
                    break  # Stop signal
                
                # Execute write in thread pool
                await loop.run_in_executor(
                    self.executor,
                    self._execute_write,
                    write_request
                )
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                # Log error but continue processing
                print(f"Error in async writer: {e}")
    
    def _execute_write(self, write_request: dict):
        """Execute the actual file write operation"""
        try:
            file_path = write_request["path"]
            content = write_request["content"]
            mode = write_request.get("mode", "w")
            
            with open(file_path, mode) as f:
                if isinstance(content, (dict, list)):
                    json.dump(content, f, indent=2)
                else:
                    f.write(content)
                    
            # Execute callback if provided
            if "callback" in write_request:
                write_request["callback"](file_path)
                
        except Exception as e:
            # Execute error callback if provided
            if "error_callback" in write_request:
                write_request["error_callback"](e)
            else:
                print(f"Failed to write {file_path}: {e}")
    
    async def write_json(self, path: Path, data: dict, callback: Optional[Callable] = None):
        """Queue a JSON file write operation"""
        await self._write_queue.put({
            "path": path,
            "content": data,
            "mode": "w",
            "callback": callback
        })
    
    async def write_text(self, path: Path, content: str, callback: Optional[Callable] = None):
        """Queue a text file write operation"""
        await self._write_queue.put({
            "path": path,
            "content": content,
            "mode": "w",
            "callback": callback
        })
    
    async def write_files_batch(self, files: list):
        """Write multiple files in batch"""
        for file_info in files:
            await self._write_queue.put(file_info)


# Global instance for convenience
_global_writer: Optional[AsyncFileWriter] = None


async def get_async_writer() -> AsyncFileWriter:
    """Get or create global async writer instance"""
    global _global_writer
    if _global_writer is None:
        _global_writer = AsyncFileWriter()
        _global_writer.start()
    return _global_writer


async def write_results_async(workspace: Path, target: str, data: dict, 
                            generate_text_report: Callable, 
                            generate_html_report: Callable,
                            is_live: bool = False):
    """Asynchronously write all result files"""
    writer = await get_async_writer()
    
    prefix = "live_" if is_live else "scan_"
    
    # Queue all writes
    await writer.write_json(
        workspace / f"{prefix}results.json",
        data
    )
    
    await writer.write_text(
        workspace / f"{prefix}report.txt",
        generate_text_report(target, data, is_live)
    )
    
    await writer.write_text(
        workspace / f"{prefix}report.html",
        generate_html_report(target, data, is_live)
    )