#!/bin/bash
# Test runner. Build the test image (multi-stage `test` target), then run pytest.
#
# Usage: ./run-tests.sh [pytest args...]
#   ./run-tests.sh                       # all tests + coverage gate (fails under 90%)
#   ./run-tests.sh tests/test_meme.py    # one file, no coverage gate

set -e

IMAGE_NAME="george_champ_bot_test"

# Mirror the pre-push coverage gate (.pre-commit-config.yaml) on the full run only.
# Targeted runs (args passed) skip coverage so a single file isn't judged against the whole tree
COV_ARGS=(--cov=common --cov=commands --cov=components --cov=GeorgeChampBot
          --cov-report=term-missing --cov-fail-under=90)

docker build --target test -t "$IMAGE_NAME" .
if [ "$#" -eq 0 ]; then
    docker run --rm "$IMAGE_NAME" python3 -m pytest "${COV_ARGS[@]}"
else
    docker run --rm "$IMAGE_NAME" python3 -m pytest "$@"
fi
