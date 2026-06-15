#!/bin/bash
# AI Token Tracker — double-click launcher for macOS (Finder runs .command files).
# Runs the app with the project's virtual environment.
cd "$(dirname "$0")"
exec .venv/bin/python tracker.py
