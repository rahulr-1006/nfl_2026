import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.notify.sms import SmsError, send_message


def test_send_message_invokes_osascript_with_escaped_text():
    with patch("src.notify.sms.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        send_message('Edge found: "great" price', "+15551234567")

    args = mock_run.call_args
    assert args[0][0][0] == "osascript"
    script = args[0][0][2]
    assert '\\"great\\"' in script  # the quote inside the message was escaped
    assert "+15551234567" in script
    assert args[1]["check"] is True


def test_send_message_raises_sms_error_on_process_failure():
    with patch("src.notify.sms.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, ["osascript"], stderr="buddy not found")
        with pytest.raises(SmsError):
            send_message("hello", "+15551234567")


def test_send_message_raises_sms_error_on_timeout():
    with patch("src.notify.sms.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(["osascript"], 15.0)
        with pytest.raises(SmsError):
            send_message("hello", "+15551234567")
