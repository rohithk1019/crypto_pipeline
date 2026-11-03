#!/bin/bash
# Prints the exact crontab line to use, with absolute paths resolved.
# Why this matters: cron runs with a minimal environment, NOT your shell's
# PATH. "python poll.py" works in your terminal but silently fails (or
# runs the wrong python) under cron. Absolute paths avoid that entirely.

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH="$(which python3)"

echo "Project directory resolved to: $PROJECT_DIR"
echo "Python resolved to: $PYTHON_PATH"
echo ""
echo "Add this line to your crontab (run 'crontab -e' then paste it):"
echo ""
echo "*/5 * * * * cd $PROJECT_DIR && $PYTHON_PATH poll.py >> $PROJECT_DIR/cron.log 2>&1"
echo ""
echo "This runs poll.py every 5 minutes, and appends both stdout and stderr"
echo "to cron.log -- check that file first if a scheduled run doesn't seem"
echo "to have worked, before assuming the script itself is broken."
