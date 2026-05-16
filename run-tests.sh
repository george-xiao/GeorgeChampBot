#!/bin/bash
# Test runner. Primarily invoked by the slash-command-tester skill
# (.claude/skills/slash-command-tester.md) during slash command development,
# but also safe to run manually any time.
#
# Build the test image (multi-stage `test` target), then run pytest.
#
# Usage: ./run-tests.sh [pytest args...]
#   ./run-tests.sh                       # all tests
#   ./run-tests.sh tests/test_meme.py    # one file
#   SNAPSHOT_UPDATE=1 ./run-tests.sh     # (re)capture snapshots

set -e

IMAGE_NAME="george_champ_bot_test"

# Git Bash on Windows rewrites POSIX-looking args (e.g. -v /...:/tests/snapshots)
# into Windows-style paths. Disable that for the docker invocation.
export MSYS_NO_PATHCONV=1

docker build --target test -t "$IMAGE_NAME" .

docker run --rm \
    -v "$(pwd)/tests/snapshots:/tests/snapshots" \
    -e SNAPSHOT_UPDATE="${SNAPSHOT_UPDATE:-}" \
    "$IMAGE_NAME" \
    python3 -m pytest "$@"
