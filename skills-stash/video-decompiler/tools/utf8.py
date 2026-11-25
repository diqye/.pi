"""Imported by every tool as it starts, for its effect: what the tool prints is UTF-8 whenever it isn't going to a terminal.

An agent reads a tool through a pipe, and on Windows a pipe takes the system's code page. A character outside that code
page (an arrow in a note, a film's words in another script, a transcript) stopped the tool with a traceback as it was
printed, in one case after the record had been written. A terminal is left as it is: it shows any character already.
"""
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure") and not _stream.isatty():
        _stream.reconfigure(encoding="utf-8", errors="replace")
