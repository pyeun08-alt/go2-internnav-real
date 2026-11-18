#!/usr/bin/env bash
set -eo pipefail
ROBOT_PACKAGE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$ROBOT_PACKAGE_DIR/onboard/robot_env.sh"
cd "$ROBOT_PACKAGE_DIR/client"
exec python3 http_internvla_client.py "$@"
