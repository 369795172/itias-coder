"""PyInstaller entry script (must use absolute imports).

Frozen bootstrap (issue #14): any startup exception writes a crash log
(ITIAS-Coder-crash-YYYYmmdd-HHMMSS.log) next to the exe and surfaces a
user-visible error instead of a silent double-click flash-crash. Normal
``SystemExit`` (e.g. ``--selftest`` exit codes) is re-raised untouched.
"""

import os
import sys
import traceback
from datetime import datetime

MESSAGE_TITLE = "ITIAS Coder"


def _crash_log_candidates():
    """Directories to try, best first: exe dir (frozen) or cwd, then %APPDATA%."""
    if getattr(sys, "frozen", False):
        directories = [os.path.dirname(sys.executable)]
    else:
        directories = [os.getcwd()]
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            directories.append(os.path.join(appdata, "ITIAS-Coder"))
    return directories


def _write_crash_log(text):
    """Write the crash log; return its path, or None when every target failed.

    Only OSError per candidate is tolerated here; the caller wraps this call
    in its own try/except so a logging failure never masks the crash itself.
    """
    filename = "ITIAS-Coder-crash-%s.log" % datetime.now().strftime("%Y%m%d-%H%M%S")
    for directory in _crash_log_candidates():
        try:
            os.makedirs(directory, exist_ok=True)
            path = os.path.join(directory, filename)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            return path
        except OSError:
            continue
    return None


def _show_crash_message(text, log_path):
    """Report the crash to stderr (+ MessageBox on Windows). Never raises."""
    try:
        if log_path is not None:
            print("ITIAS Coder crashed. Crash log: %s" % log_path, file=sys.stderr)
        else:
            print("ITIAS Coder crashed (crash log could not be written).", file=sys.stderr)
        print(text, file=sys.stderr)
        if sys.platform == "win32":
            import ctypes

            msg = "ITIAS Coder failed to start.\n\n"
            if log_path is not None:
                msg += "Crash log: %s\n\n" % log_path
            msg += text
            ctypes.windll.user32.MessageBoxW(0, msg, MESSAGE_TITLE, 0x10)
    except Exception:
        pass


def main():
    try:
        from itias_coder.main import run

        run()
    except SystemExit:
        raise
    except Exception:
        text = traceback.format_exc()
        try:
            log_path = _write_crash_log(text)
        except Exception:
            log_path = None
        _show_crash_message(text, log_path)
        sys.exit(1)


if __name__ == "__main__":
    main()
