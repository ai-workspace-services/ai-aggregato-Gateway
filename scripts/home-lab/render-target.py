#!/usr/bin/env python3
"""Render a non-secret single-node Home-Lab target.

The generated files describe reachability only. They do not contain Vault
values, API keys, OAuth bundles, or passwords.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
from pathlib import Path


DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$")


def address(value: str, label: str) -> str:
    try:
        ipaddress.ip_address(value)
    except ValueError as exc:
        raise SystemExit(f"{label} must be an IPv4 or IPv6 address: {value}") from exc
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--target-ip", required=True, help="SSH and local service address")
    parser.add_argument("--dns-ip", help="Address published by DNS; defaults to target-ip")
    parser.add_argument(
        "--network-mode",
        choices=("public", "private-nat", "xconnect"),
        default="public",
    )
    parser.add_argument("--ssh-user", default="root")
    parser.add_argument("--ssh-port", type=int, default=22)
    parser.add_argument("--tls-mode", choices=("automatic", "runtime-files"))
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not DOMAIN_RE.fullmatch(args.domain):
        raise SystemExit(f"domain is not a DNS hostname: {args.domain}")
    if not args.ssh_user or any(char.isspace() for char in args.ssh_user):
        raise SystemExit("ssh-user must be a non-empty value without whitespace")
    if not 1 <= args.ssh_port <= 65535:
        raise SystemExit("ssh-port must be between 1 and 65535")

    target_ip = address(args.target_ip, "target-ip")
    dns_ip = address(args.dns_ip or target_ip, "dns-ip")

    if args.network_mode == "private-nat" and not args.dns_ip:
        raise SystemExit("private-nat requires --dns-ip for the public DNS address")
    if args.network_mode == "xconnect" and args.dns_ip and args.dns_ip != target_ip:
        raise SystemExit("xconnect expects --dns-ip to equal the XConnect address")

    # Public Caddy may listen on all local interfaces. Private/NAT and
    # XConnect bind to the transport address so the route cannot accidentally
    # expose a different interface.
    bind_address = "" if args.network_mode == "public" else target_ip
    tls_mode = args.tls_mode or ("runtime-files" if args.network_mode == "xconnect" else "automatic")

    args.output_dir.mkdir(parents=True, exist_ok=False)
    inventory = args.output_dir / "inventory.ini"
    manifest = args.output_dir / "ai-gateway-unified.yaml"

    inventory.write_text(
        "[ai_aggregator_gateway]\n"
        "ai-aggregator-gateway "
        f"ansible_host={target_ip} ansible_user={args.ssh_user} "
        f"ansible_port={args.ssh_port}\n",
        encoding="utf-8",
    )

    bind_value = bind_address or "''"
    bind_yaml = f"    caddy_bind_address: {bind_value}\n"
    manifest_text = (
        "apiVersion: gitops.svc.plus/v1alpha1\n"
        "kind: UnifiedAIGateway\n"
        "metadata:\n"
        "  name: ai-gateway-single-node\n"
        "  environment: generated\n"
        "  target: single-node\n"
        "spec:\n"
        "  enabled: true\n"
        f"  host: {args.domain}\n"
        f"  dns_target: {dns_ip}\n"
        "  network:\n"
        f"    mode: {args.network_mode}\n"
        f"    ssh_address: {target_ip}\n"
        f"    verification_address: {target_ip}\n"
        + bind_yaml
        + "  tls:\n"
        f"    mode: {tls_mode}\n"
        "  new_api:\n"
        "    bind_address: 127.0.0.1\n"
        "    port: 3000\n"
    )
    manifest.write_text(manifest_text, encoding="utf-8")

    print(f"network_mode={args.network_mode}")
    print(f"domain={args.domain}")
    print(f"dns_target={dns_ip}")
    print(f"transport_address={target_ip}")
    print(f"tls_mode={tls_mode}")
    print(f"inventory={inventory}")
    print(f"manifest={manifest}")
    print("No credentials were generated or written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
