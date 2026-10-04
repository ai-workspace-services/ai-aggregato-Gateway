#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
venv_dir="${AI_AGGREGATOR_VENV:-$repo_root/.venv}"

AI_AGGREGATOR_REQUIRE_ANSIBLE=false \
  "$repo_root/scripts/home-lab/bootstrap.sh"

python3 -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install --upgrade pip
"$venv_dir/bin/pip" install -e "${repo_root}[test]"

printf 'Installed gatewayctl in %s\n' "$venv_dir"
printf 'Activate with: source %s/bin/activate\n' "$venv_dir"
printf 'Credentials remain in the local credential store/Vault; they are not written by this script.\n'
