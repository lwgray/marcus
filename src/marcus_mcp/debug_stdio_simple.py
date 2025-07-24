"""
Simple debug wrapper for MCP stdio streams to log all JSON-RPC messages.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class DebugStream:
    """Wrapper for stdio streams that logs all data."""
    
    def __init__(self, stream: Any, direction: str, log_file: Path) -> None:
        self.stream = stream
        self.direction = direction
        self.log_file = log_file
        self.message_count = 0
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write header
        with open(self.log_file, 'a') as f:
            f.write(f"=== MCP Debug Log Started at {datetime.now().isoformat()} ===\n")
            f.write(f"Direction: {direction}\n")
            f.write("=" * 50 + "\n")
    
    def _log(self, event_type: str, data: Any) -> None:
        """Log an event."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "direction": self.direction,
            "event_type": event_type,
            "message_count": self.message_count,
            "data": data
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
            f.flush()
    
    async def read(self, n: int = -1) -> bytes:
        """Read from stream and log the data."""
        try:
            data = await self.stream.read(n)
            
            if data:
                self._log("read", {
                    "bytes": len(data),
                    "preview": data[:100].decode('utf-8', errors='replace')
                })
            
            return data
            
        except Exception as e:
            self._log("read_error", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise
    
    async def readline(self) -> bytes:
        """Read a line from stream and log it."""
        try:
            data = await self.stream.readline()
            
            if data:
                line = data.decode('utf-8', errors='replace').rstrip('\n')
                self._log("readline", {"line": line})
                
                # Try to parse as JSON-RPC
                try:
                    json_data = json.loads(line)
                    self.message_count += 1
                    self._log("json_rpc", json_data)
                except json.JSONDecodeError:
                    pass
            
            return data
            
        except Exception as e:
            self._log("readline_error", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise
    
    def write(self, data: bytes) -> Any:
        """Write to stream and log the data."""
        try:
            text = data.decode('utf-8', errors='replace')
            self._log("write", {"text": text})
            
            # Try to parse as JSON-RPC
            lines = text.strip().split('\n')
            for line in lines:
                if line.strip():
                    try:
                        json_data = json.loads(line)
                        self.message_count += 1
                        self._log("json_rpc", json_data)
                    except json.JSONDecodeError:
                        pass
            
            # Write to actual stream
            result = self.stream.write(data)
            
            # Force flush
            if hasattr(self.stream, 'flush'):
                self.stream.flush()
            
            return result
            
        except Exception as e:
            self._log("write_error", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise
    
    def __getattr__(self, name: str) -> Any:
        """Proxy all other attributes to the wrapped stream."""
        return getattr(self.stream, name)


def wrap_stdio_for_debug(read_stream: Any, write_stream: Any) -> tuple[Any, Any]:
    """Wrap stdio streams with debug logging."""
    # Create debug log directory
    log_dir = Path("/Users/lwgray/dev/marcus/logs/mcp_debug")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped log files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    read_log = log_dir / f"mcp_read_{timestamp}.log"
    write_log = log_dir / f"mcp_write_{timestamp}.log"
    
    # Create debug wrappers
    debug_read = DebugStream(read_stream, "read", read_log)
    debug_write = DebugStream(write_stream, "write", write_log)
    
    print("🔍 MCP Debug logging enabled:", file=sys.stderr)
    print(f"   📖 Read log: {read_log}", file=sys.stderr)
    print(f"   ✍️  Write log: {write_log}", file=sys.stderr)
    
    return debug_read, debug_write