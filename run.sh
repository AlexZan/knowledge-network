#!/usr/bin/env bash
cd "$(dirname "$0")"
LD_LIBRARY_PATH=/nix/store/cf1a53iqg6ncnygl698c4v0l8qam5a2q-gcc-14.3.0-lib/lib PYTHONPATH=src /tmp/oi-venv/bin/python -m oi.cli "$@"
