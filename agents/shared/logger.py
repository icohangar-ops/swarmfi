"""SwarmFi Structured Logger

Provides colored, structured logging using loguru.
All agents use this for consistent log formatting.
"""

from __future__ import annotations

import sys
from typing import Optional

from loguru import logger

# Remove default loguru handler
logger.remove()

# ANSI color codes for custom formatting
COLORS = {
    "HEADER": "\033[95m",
    "BLUE": "\033[94m",
    "CYAN": "\033[96m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "BOLD": "\033[1m",
    "DIM": "\033[2m",
    "RESET": "\033[0m",
}

# Agent type color mapping
AGENT_COLORS = {
    "PRICE": "\033[94m",       # Blue
    "RISK": "\033[91m",        # Red
    "MARKET_MAKER": "\033[92m", # Green
    "RESOLUTION": "\033[95m",   # Magenta
    "ORCHESTRATOR": "\033[96m", # Cyan
    "CONSENSUS": "\033[93m",    # Yellow
    "STIGMERGY": "\033[93m",    # Yellow
    "CHAIN": "\033[95m",        # Magenta
}


def _colorize_agent(agent_type: str) -> str:
    """Apply color to agent type string.

    Args:
        agent_type: The agent type string.

    Returns:
        Colorized string.
    """
    color = AGENT_COLORS.get(agent_type.upper(), "\033[97m")
    return f"{color}{agent_type}{COLORS['RESET']}"


def _format_record(record: dict) -> str:
    """Custom loguru format string builder.

    Args:
        record: Loguru record dict.

    Returns:
        Formatted log string.
    """
    level = record["level"].name
    agent = record["extra"].get("agent", "SYSTEM")

    # Level colors
    level_colors = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    level_color = level_colors.get(level, "\033[37m")

    # Build format
    agent_str = _colorize_agent(agent)
    time_str = f"{COLORS['DIM']}{record['time']:HH:mm:ss.SSS}{COLORS['RESET']}"
    level_str = f"{level_color}{level:<8}{COLORS['RESET']}"
    name_str = f"{COLORS['BOLD']}{record['name']}{COLORS['RESET']}"

    # Message
    message = record["message"]

    return f"{time_str} │ {level_str} │ {agent_str:<16} │ {name_str:<20} │ {message}\n"


def get_logger(agent_name: str = "SYSTEM") -> "logger":
    """Get a logger instance tagged with an agent name.

    Args:
        agent_name: Name/identifier of the agent using this logger.

    Returns:
        A loguru logger bound with the agent name.
    """
    return logger.bind(agent=agent_name)


def setup_logging(level: str = "INFO") -> None:
    """Configure the global loguru logger.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    logger.add(
        sys.stderr,
        format=_format_record,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=False,
    )


def log_banner(text: str, char: str = "═") -> None:
    """Log a large banner to the console.

    Args:
        text: Banner text.
        char: Character to use for the border.
    """
    width = 72
    border = char * width
    inner = f"{char} {text:^{width - 4}} {char}"
    logger.opt(colors=True).info(
        f"\n{COLORS['BOLD']}{COLORS['CYAN']}{border}{COLORS['RESET']}\n"
        f"{COLORS['BOLD']}{COLORS['CYAN']}{inner}{COLORS['RESET']}\n"
        f"{COLORS['BOLD']}{COLORS['CYAN']}{border}{COLORS['RESET']}"
    )


def log_section(text: str) -> None:
    """Log a section header.

    Args:
        text: Section text.
    """
    logger.opt(colors=True).info(
        f"\n{COLORS['BOLD']}─── {text} {COLORS['CYAN']}{'─' * (60 - len(text))}{COLORS['RESET']}"
    )


def log_kv(key: str, value: str) -> None:
    """Log a key-value pair.

    Args:
        key: The key.
        value: The value.
    """
    logger.opt(colors=True).info(
        f"  {COLORS['DIM']}•{COLORS['RESET']} {COLORS['BOLD']}{key}{COLORS['RESET']}: {value}"
    )


def log_table(headers: list, rows: list) -> None:
    """Log a simple ASCII table.

    Args:
        headers: List of column header strings.
        rows: List of row lists.
    """
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Header
    header_line = " │ ".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
    sep_line = "─┼─".join("─" * w for w in col_widths)

    logger.opt(colors=True).info(f"\n{COLORS['BOLD']}{header_line}{COLORS['RESET']}")
    logger.opt(colors=True).info(f"{COLORS['DIM']}{sep_line}{COLORS['RESET']}")

    # Rows
    for row in rows:
        row_line = " │ ".join(str(c).ljust(w) for c, w in zip(row, col_widths))
        logger.opt(colors=True).info(row_line)


__all__ = [
    "get_logger",
    "setup_logging",
    "log_banner",
    "log_section",
    "log_kv",
    "log_table",
    "logger",
    "COLORS",
]
