#!/usr/bin/env bash
# AI Token Tracker launcher.
# When snap (e.g. VS Code / core20) environment variables leak in, they can clash
# with the system GTK libraries; we clear them. Harmless in a normal terminal.
cd "$(dirname "$0")"
unset LD_LIBRARY_PATH GTK_PATH GIO_MODULE_DIR GDK_PIXBUF_MODULE_FILE \
      GDK_PIXBUF_MODULEDIR LOCPATH GSETTINGS_SCHEMA_DIR
exec .venv/bin/python tracker.py
