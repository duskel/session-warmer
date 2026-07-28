"""session-warmer: keep Claude / Codex CLI usage windows aligned to your day.

A scheduler (not a server) that sends one tiny prompt at each 5-hour window
boundary so the window opens at a predictable local time, detects when a limit
has been hit, and stops wasting pings until the reported reset.
"""

__version__ = "0.1.0"
