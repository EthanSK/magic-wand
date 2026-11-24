#!/bin/sh
# Add only this repository's commit-msg check. Preserve other installed hooks.
set -eu
root=$(git rev-parse --show-toplevel)
cd "$root"
if git config --get core.hooksPath >/dev/null; then
    echo "Existing hooksPath: integrate scripts/commit-msg into the existing repository hook." >&2
    exit 1
fi
source="$root/.agents/skills/model-user-requirements/scripts/commit-msg"
target=$(git rev-parse --git-path hooks)/commit-msg
if [ -L "$target" ] && [ "$(readlink "$target")" = "$source" ]; then exit 0; fi
mkdir -p "$(dirname "$target")"
ln -s "$source" "$target"
