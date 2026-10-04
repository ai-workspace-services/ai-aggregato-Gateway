#!/usr/bin/env bash
set -euo pipefail

base_url="${AI_GATEWAY_BASE_URL:-https://ai-internal.onwalk.net}"
resolve_args=()
if [[ -n "${AI_GATEWAY_RESOLVE:-}" ]]; then
  resolve_args+=(--resolve "$AI_GATEWAY_RESOLVE")
fi

status_code() {
  curl --silent --show-error --http1.1 \
    "${resolve_args[@]}" \
    -o /dev/null -w '%{http_code}' "$@"
}

unauthenticated="$(status_code "$base_url/v1/models")"
[[ "$unauthenticated" == 401 || "$unauthenticated" == 403 ]] || {
  printf 'expected unauthenticated /v1/models to return 401/403, got %s\n' "$unauthenticated" >&2
  exit 1
}

if [[ -n "${AI_GATEWAY_CLIENT_TOKEN:-}" ]]; then
  authenticated="$(status_code -H "Authorization: Bearer ${AI_GATEWAY_CLIENT_TOKEN}" "$base_url/v1/models")"
  [[ "$authenticated" =~ ^2[0-9][0-9]$ ]] || {
    printf 'authenticated /v1/models failed with HTTP %s\n' "$authenticated" >&2
    exit 1
  }
  printf 'authenticated /v1/models: HTTP %s\n' "$authenticated"

  if [[ -n "${AI_GATEWAY_SMOKE_MODEL:-}" ]]; then
    curl --silent --show-error --fail-with-body --http1.1 \
      "${resolve_args[@]}" \
      -H "Authorization: Bearer ${AI_GATEWAY_CLIENT_TOKEN}" \
      -H 'Content-Type: application/json' \
      "$base_url/v1/chat/completions" \
      -d "$(python3 - "$AI_GATEWAY_SMOKE_MODEL" <<'PY'
import json
import sys
print(json.dumps({
    "model": sys.argv[1],
    "messages": [{"role": "user", "content": "Reply exactly: hello"}],
    "max_tokens": 16,
}))
PY
)" >/dev/null
    printf 'smoke request passed for configured model\n'
  fi
fi

printf 'AI Gateway authentication checks passed for %s\n' "$base_url"
