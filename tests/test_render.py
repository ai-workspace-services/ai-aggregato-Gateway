import json
import tempfile
import unittest
from pathlib import Path

from gatewayctl.render import render_manifest
from gatewayctl.validation import load_yaml, validate_manifest


ROOT = Path(__file__).resolve().parents[1]


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_yaml(ROOT / "contracts" / "gateway.yaml")
        for tenant in cls.manifest["tenants"]:
            tenant["enabled"] = True
        validate_manifest(cls.manifest)

    def render(self, adapter):
        with tempfile.TemporaryDirectory(prefix="ai-gateway-test-") as directory:
            result = render_manifest(self.manifest, adapter, directory)
            files = {
                name: (Path(directory) / name).read_text(encoding="utf-8")
                for name in result["files"]
            }
        return result, files

    def test_caddy_is_scoped_to_ai_hosts(self):
        result, files = self.render("caddy")
        self.assertIn("ai.onwalk.net", files["Caddyfile.ai-gateway"])
        self.assertIn("direct.ai.onwalk.net", files["Caddyfile.ai-gateway"])
        self.assertIn("reverse_proxy 127.0.0.1:9080", files["Caddyfile.ai-gateway"])
        self.assertNotIn("remote_ip", files["Caddyfile.ai-gateway"])
        self.assertNotIn("accounts.svc.plus", files["Caddyfile.ai-gateway"])
        self.assertEqual(result["report"]["adapter"], "caddy")

    def test_caddy_targets_selected_apisix_adapter(self):
        manifest = {**self.manifest, "gateway": {**self.manifest["gateway"], "adapter": "apisix"}}
        validate_manifest(manifest)
        with tempfile.TemporaryDirectory(prefix="ai-gateway-test-") as directory:
            render_manifest(manifest, "caddy", directory)
            caddyfile = (Path(directory) / "Caddyfile.ai-gateway").read_text(encoding="utf-8")
        self.assertIn("reverse_proxy 127.0.0.1:9080", caddyfile)

    def test_caddy_direct_mode_routes_each_host_to_its_logical_backend(self):
        manifest = {**self.manifest, "gateway": {**self.manifest["gateway"], "entry_mode": "direct-new-api"}}
        validate_manifest(manifest)
        with tempfile.TemporaryDirectory(prefix="ai-gateway-test-") as directory:
            result = render_manifest(manifest, "caddy", directory)
            caddyfile = (Path(directory) / "Caddyfile.ai-gateway").read_text(encoding="utf-8")
        self.assertIn("ai.onwalk.net {\n    reverse_proxy http://127.0.0.1:3000", caddyfile)
        self.assertIn("direct.ai.onwalk.net {\n    reverse_proxy http://127.0.0.1:4000", caddyfile)
        self.assertEqual(result["report"]["entry_mode"], "direct-new-api")

    def test_kong_bundle_has_separate_new_api_and_litellm_routes(self):
        _, files = self.render("kong")
        self.assertIn("ai-new-api", files["kong.yaml"])
        self.assertIn("ai-litellm", files["kong.yaml"])
        self.assertIn("tenant:personal", files["kong.yaml"])
        self.assertNotIn("name: kong", files["kong.yaml"])

    def test_kong_new_api_route_passes_through_new_api_user_token(self):
        _, files = self.render("kong")
        bundle = __import__("yaml").safe_load(files["kong.yaml"])
        route = next(item for item in bundle["routes"] if item["name"] == "ai-new-api")
        plugins = {item["name"]: item["config"] for item in route["plugins"]}
        self.assertIn("pre-function", plugins)
        self.assertIn("x-api-key", plugins["pre-function"]["access"][0])
        self.assertIn("apikey", plugins["pre-function"]["access"][0])
        self.assertIn("Authorization", plugins["pre-function"]["access"][0])
        self.assertNotIn("key-auth", plugins)
        self.assertNotIn("acl", plugins)

    def test_kong_bundle_declares_gateway_scheduling_capability(self):
        result, files = self.render("kong")
        self.assertIn('"scheduling"', files["capability-report.json"])
        self.assertIn("timeouts", result["report"]["scheduling"])

    def test_apisix_reports_non_equivalent_database_capability(self):
        result, files = self.render("apisix")
        report = json.loads(files["capability-report.json"])
        self.assertEqual(result["report"]["mode"], "standalone-file-driven")
        self.assertIn("postgresql-runtime-config", report["unsupported_or_external"])
        self.assertIn("apisix.yaml", files)
        self.assertIn("consumer-restriction", files["apisix.yaml"])
        self.assertIn("gpt-5.6-luna", files["apisix.yaml"])

    def test_apisix_uses_contract_auth_mode(self):
        manifest = {**self.manifest, "routes": [dict(self.manifest["routes"][0], auth={"mode": "jwt"})]}
        validate_manifest(manifest)
        with tempfile.TemporaryDirectory(prefix="ai-gateway-test-") as directory:
            render_manifest(manifest, "apisix", directory)
            apisix = (Path(directory) / "apisix.yaml").read_text(encoding="utf-8")
        self.assertIn("jwt-auth", apisix)
        self.assertNotIn("key-auth:", apisix)

    def test_apisix_new_api_route_normalizes_client_headers_without_bootstrap_key(self):
        _, files = self.render("apisix")
        bundle = __import__("yaml").safe_load(files["apisix.yaml"])
        route = next(item for item in bundle["routes"] if item["name"] == "ai-new-api")
        plugins = route["plugins"]
        self.assertIn("serverless-pre-function", plugins)
        self.assertNotIn("key-auth", plugins)
        self.assertNotIn("consumer-restriction", plugins)
        self.assertIn("x-api-key", plugins["serverless-pre-function"]["functions"][0])
        self.assertIn("apikey", plugins["serverless-pre-function"]["functions"][0])
        self.assertEqual(plugins["limit-count"]["key"], "remote_addr")
        self.assertIn('/v1/*', route['uris'])

    def test_apisix_preserves_tenant_acl_for_gateway_credentials(self):
        _, files = self.render("apisix")
        bundle = __import__("yaml").safe_load(files["apisix.yaml"])
        route = next(item for item in bundle["routes"] if item["name"] == "ai-litellm")
        self.assertEqual(route["plugins"]["consumer-restriction"]["whitelist"], ["personal"])

    def test_kong_preserves_native_api_path(self):
        _, files = self.render("kong")
        bundle = __import__("yaml").safe_load(files["kong.yaml"])
        self.assertTrue(all(route['strip_path'] is False for route in bundle['routes']))

    def test_kong_does_not_publish_disabled_tenant_routes(self):
        manifest = load_yaml(ROOT / "contracts" / "ai-internal-new-api.yaml")
        with tempfile.TemporaryDirectory() as directory:
            render_manifest(manifest, "kong", directory)
            bundle = __import__("yaml").safe_load((Path(directory) / "kong.yaml").read_text())
        self.assertEqual(bundle['routes'], [])
