#!/usr/bin/env bash
# Installs the pre-push git hook for this repository.
# Run once per clone: bash hooks/setup_hooks.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
HOOK_SRC="$SCRIPT_DIR/pre-push"
HOOK_DST="$REPO_ROOT/.git/hooks/pre-push"

if [ ! -f "$HOOK_SRC" ]; then
    echo "ERROR: $HOOK_SRC not found." >&2
    exit 1
fi

cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"

echo "Installed: $HOOK_DST"
echo ""
echo "The pre-push hook will now:"
echo "  1. Check that Ollama is running (http://localhost:11434)"
echo "  2. Run:  python -m pytest eval/ -x -q"
echo "  3. Run:  python eval/baseline.py --check"
echo ""
echo "To skip the hook for a single push: git push --no-verify"
echo "To uninstall:  rm .git/hooks/pre-push"
