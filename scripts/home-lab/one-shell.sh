#!/usr/bin/env bash
set -euo pipefail

# Safe curl | bash entrypoint.
# It installs a pinned checkout and performs only plan unless an explicit
# operation, inventory, and manifest are supplied by the caller.

usage() {
  cat <<'EOF'
Usage:
  curl -fsSL <pinned-raw-url> | bash -s -- [options]

Options:
  --ref REF              Git tag or commit to clone (required for CI/production)
  --install-dir DIR      Destination directory
  --operation OP         plan, stage, or activate (default: plan)
  --inventory FILE       Ansible inventory; required for deployment
  --manifest FILE        GitOps manifest; required for deployment
  --playbook FILE        Explicit Ansible playbook (required for UnifiedAIGateway)
  --limit GROUP          Optional Ansible --limit value
  -h, --help             Show this help

The script never accepts, reads, or prints a client token. Credentials are
loaded by the deployment role from Vault or by the client credential store.
EOF
}

repo="ai-workspace-services/ai-aggregato-Gateway"
ref="${AI_AGGREGATOR_REF:-}"
install_dir="${AI_AGGREGATOR_INSTALL_DIR:-${HOME}/.local/share/ai-aggregato-Gateway}"
operation="${AI_AGGREGATOR_OPERATION:-plan}"
inventory="${AI_AGGREGATOR_INVENTORY:-}"
manifest="${AI_AGGREGATOR_MANIFEST:-}"
playbook="${AI_AGGREGATOR_PLAYBOOK:-}"
limit="${AI_AGGREGATOR_LIMIT:-}"

while (($#)); do
  case "$1" in
    --ref) ref="${2:?missing value for --ref}"; shift 2 ;;
    --install-dir) install_dir="${2:?missing value for --install-dir}"; shift 2 ;;
    --operation) operation="${2:?missing value for --operation}"; shift 2 ;;
    --inventory) inventory="${2:?missing value for --inventory}"; shift 2 ;;
    --manifest) manifest="${2:?missing value for --manifest}"; shift 2 ;;
    --playbook) playbook="${2:?missing value for --playbook}"; shift 2 ;;
    --limit) limit="${2:?missing value for --limit}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$operation" in
  plan|stage|activate) ;;
  *) printf '%s\n' '--operation must be plan, stage, or activate' >&2; exit 2 ;;
esac

command -v git >/dev/null 2>&1 || { printf 'git is required\n' >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { printf 'python3 is required\n' >&2; exit 1; }

if [[ -z "$ref" ]]; then
  printf '%s\n' 'set AI_AGGREGATOR_REF or pass --ref with a reviewed tag/commit' >&2
  exit 2
fi

if [[ -e "$install_dir" ]]; then
  printf 'install directory already exists: %s\n' "$install_dir" >&2
  printf '%s\n' 'choose another --install-dir or remove the directory manually' >&2
  exit 1
fi

mkdir -p "$(dirname -- "$install_dir")"
git clone --depth 1 --branch "$ref" "https://github.com/${repo}.git" "$install_dir"

"$install_dir/scripts/home-lab/install.sh"

if [[ -n "$inventory" || -n "$manifest" || -n "$playbook" ]]; then
  [[ -n "$inventory" && -n "$manifest" ]] || {
    printf '%s\n' '--inventory and --manifest must be provided together' >&2
    exit 2
  }
  export AI_AGGREGATOR_INVENTORY="$inventory"
  export AI_AGGREGATOR_MANIFEST="$manifest"
  export AI_AGGREGATOR_OPERATION="$operation"
  [[ -n "$playbook" ]] && export AI_AGGREGATOR_PLAYBOOK="$playbook"
  [[ -n "$limit" ]] && export AI_AGGREGATOR_LIMIT="$limit"
  "$install_dir/scripts/home-lab/deploy.sh"
else
  printf '%s\n' 'Installation complete; no deployment was executed.'
  printf 'Next: AI_AGGREGATOR_INVENTORY=... AI_AGGREGATOR_MANIFEST=... %s\n' \
    "AI_AGGREGATOR_OPERATION=plan $install_dir/scripts/home-lab/deploy.sh"
fi
