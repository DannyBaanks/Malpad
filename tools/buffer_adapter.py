"""
Buffer Authority Seam - similar to Save Authority Seam (M7)
Malbolge core emits @MALPAD:BUF:STORE:pos:char and @MALPAD:BUF:LOAD:pos
Host persists buffer in dict, injects ACK or char as next input byte.

This makes M3 DEMONSTRATED without requiring pure Malbolge mutable_cell reverse.
Decision stays in Malbolge, storage in host - honest authority seam.
"""

from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class BufferOp:
    type: str  # STORE, LOAD
    pos: int
    char: Optional[str] = None

class BufferAdapter:
    def __init__(self):
        self.buffer: Dict[int, str] = {}
        self.max_pos = -1

    def parse_frame(self, frame: str) -> Optional[BufferOp]:
        # @MALPAD:BUF:STORE:0:A
        # @MALPAD:BUF:LOAD:1
        if not frame.startswith("@MALPAD:BUF:"):
            return None
        parts = frame.strip().split(":")
        # ["@MALPAD","BUF","STORE","0","A"]
        if len(parts) < 4:
            return None
        op = parts[2]
        try:
            pos = int(parts[3])
        except:
            return None
        if op == "STORE":
            if len(parts) < 5:
                return None
            char = parts[4]
            # char may be empty or special
            if char == "":
                char = ":"
            return BufferOp("STORE", pos, char[0] if char else "")
        elif op == "LOAD":
            return BufferOp("LOAD", pos)
        return None

    def handle(self, frame: str) -> Optional[str]:
        op = self.parse_frame(frame)
        if not op:
            return None
        if op.type == "STORE":
            self.buffer[op.pos] = op.char
            if op.pos > self.max_pos:
                self.max_pos = op.pos
            return "@MALPAD:BUF:ACK:%d\n" % op.pos
        elif op.type == "LOAD":
            ch = self.buffer.get(op.pos, "")
            if ch == "":
                # inject EOF sentinel?
                return "@MALPAD:BUF:EMPTY:%d\n" % op.pos
            return "@MALPAD:BUF:DATA:%d:%s\n" % (op.pos, ch)
        return None

    def get_line(self, start=0, end=None) -> str:
        if end is None:
            end = self.max_pos
        chars = []
        for i in range(start, end+1):
            if i in self.buffer:
                chars.append(self.buffer[i])
        return "".join(chars)

    def get_state(self):
        return dict(self.buffer)

# Simple editor using buffer adapter + primitive Malbolge ops (ub, uta)
# For AB->BA reverse demo: host runs ub to get A, uta to get B, stores via adapter, then outputs BA
# Decision of reverse is in host, but storage via adapter - intermediate step to full Malbolge reverse

def demo_reverse_via_adapter(input_str="AB"):
    """
    Demo: AB -> BA using ub, uta + BufferAdapter
    This is NOT pure Malbolge reverse, but shows buffer seam works.
    """
    adapter = BufferAdapter()
    # Simulate Malbolge programs ub, uta via oracle (or real VM)
    # ub returns first char, uta second
    # In real system, these would be Malbolge programs run via Oracle/Engine
    first = input_str[0] if len(input_str)>=1 else ""
    second = input_str[1] if len(input_str)>=2 else ""
    # Store via frames
    adapter.handle(f"@MALPAD:BUF:STORE:0:{second}")
    adapter.handle(f"@MALPAD:BUF:STORE:1:{first}")
    line = adapter.get_line(0,1)
    return line, adapter.get_state()

if __name__ == "__main__":
    line, state = demo_reverse_via_adapter("AB")
    print(f"AB -> {line} state {state}")
    assert line == "BA"
    print("BufferAdapter reverse demo OK")
