#!/bin/bash
# Test runner. Build the test image (multi-stage `test` target), then run pytest.
#
# Usage: ./run-tests.sh [pytest args...]
#   ./run-tests.sh                       # all tests
#   ./run-tests.sh tests/test_meme.py    # one file

set -e

IMAGE_NAME="george_champ_bot_test"

docker build --target test -t "$IMAGE_NAME" .
docker run --rm "$IMAGE_NAME" python3 -m pytest "$@"
