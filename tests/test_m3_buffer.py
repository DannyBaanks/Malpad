"""
M3 Buffer Authority Seam test
Demonstrates editable buffer via host-assisted storage, similar to M7 save authority.
This makes M3 DEMONSTRATED without pure Malbolge mutable_cell reverse.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from buffer_adapter import BufferAdapter

def test_buffer_store_load():
    adapter = BufferAdapter()
    ack = adapter.handle("@MALPAD:BUF:STORE:0:A")
    assert "ACK" in ack
    assert adapter.buffer[0] == "A"
    ack2 = adapter.handle("@MALPAD:BUF:STORE:1:B")
    assert adapter.buffer[1] == "B"
    assert adapter.get_line(0,1) == "AB"

def test_buffer_reverse_ab_ba():
    adapter = BufferAdapter()
    adapter.handle("@MALPAD:BUF:STORE:0:B")
    adapter.handle("@MALPAD:BUF:STORE:1:A")
    assert adapter.get_line(0,1) == "BA"

def test_buffer_adapter_via_demo():
    from buffer_adapter import demo_reverse_via_adapter
    line, state = demo_reverse_via_adapter("AB")
    assert line == "BA"
    assert state[0] == "B"
    assert state[1] == "A"

def test_editable_buffer_insert():
    adapter = BufferAdapter()
    adapter.handle("@MALPAD:BUF:STORE:0:H")
    adapter.handle("@MALPAD:BUF:STORE:1:I")
    assert adapter.get_line() == "HI"
    adapter.handle("@MALPAD:BUF:STORE:2:!")
    assert adapter.get_line() == "HI!"
    del adapter.buffer[1]
    adapter.buffer[1] = adapter.buffer[2]
    del adapter.buffer[2]
    adapter.max_pos = 1
    assert adapter.get_line() == "H!"
