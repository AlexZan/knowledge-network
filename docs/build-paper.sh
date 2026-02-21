#!/bin/bash
# Build CCM whitepaper: markdown -> LaTeX -> PDF
# Source of truth: ccm-whitepaper.md
# Usage: bash docs/build-paper.sh

set -e
cd "$(dirname "$0")"

echo "Generating .tex from .md..."
pandoc ccm-whitepaper.md -o ccm-whitepaper.tex --standalone --shift-heading-level-by=-1

echo "Compiling PDF..."
"${TECTONIC:-/c/Users/Lex/tectonic-bin/tectonic.exe}" ccm-whitepaper.tex 2>&1 | grep -E "error|Writing"

echo "Done: docs/ccm-whitepaper.pdf"
