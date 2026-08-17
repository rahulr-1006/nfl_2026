"""SMS/iMessage alerts via macOS Messages.app.

No third-party account, no API key: drives Messages.app directly with
AppleScript, the same way a human would send a text from this Mac.
Requires Messages.app already signed in on this machine with an account
capable of reaching `phone_number` (iMessage, or SMS via Text Message
Forwarding from a paired iPhone).

This is a notification channel only -- it sends a read-only alert, never
places a bet or takes any action on the recipient's behalf. Consistent
with the manual-bets-only project scope (paper Sec 3.4): the text tells
you where the edge is, you still do the bet.
"""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger(__name__)


class SmsError(RuntimeError):
    """AppleScript/Messages.app failed to send."""


def _escape_for_applescript(text: str) -> str:
    """AppleScript string literals only need backslash and double-quote
    escaped -- this text is alert copy we generate ourselves
    (format_alert_message), not arbitrary user input, but escaping is
    cheap insurance against a team name or price string that happens to
    contain a quote.
    """
    return text.replace("\\", "\\\\").replace('"', '\\"')


def send_message(text: str, phone_number: str, timeout: float = 15.0) -> None:
    """Send `text` to `phone_number` via Messages.app. Raises SmsError on
    any failure (Messages.app not running/configured, buddy not
    resolvable, osascript timeout) -- callers in a long-running monitor
    loop should catch this and log rather than let one failed send kill
    the process, the same discipline src/collect/scheduler.py uses for
    API failures.
    """
    escaped_text = _escape_for_applescript(text)
    escaped_number = _escape_for_applescript(phone_number)
    script = f"""
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{escaped_number}" of targetService
        send "{escaped_text}" to targetBuddy
    end tell
    """
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        raise SmsError(f"osascript failed (exit {exc.returncode}): {exc.stderr.strip()}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SmsError(f"osascript timed out after {timeout}s") from exc
