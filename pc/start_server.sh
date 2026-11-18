#!/usr/bin/env bash
set -eo pipefail
SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_ROOT/InternNav" ]]; then
    PROJECT_DIR="$SCRIPT_ROOT/InternNav"
else
    PROJECT_DIR="${INTERNNAV_ROOT:-/workspace/InternNav}"
fi
if [[ -z "${NAV_INSTRUCTION//[[:space:]]/}" ]]; then
    echo 'NAV_INSTRUCTION에 이동 지시문을 설정하세요.' >&2
    exit 2
fi
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}"
exec python scripts/realworld/http_internvla_server.py \
    --device cuda:0 \
    --model_path "${MODEL_PATH:-checkpoints/Go2_nextdit_finetuned}" \
    --plan_step_gap 4 --host 127.0.0.1 --port 5801 "$@"
