import tempfile
import unittest
from pathlib import Path

import yaml

from gatewayctl.render import render_manifest
from gatewayctl.validation import ManifestError, load_yaml, validate_manifest

MANIFEST = Path(__file__).resolve().parents[1] / "contracts/ai-internal-apisix.yaml"


class MultiProviderTests(unittest.TestCase):
    def test_bundle_is_loopback_file_driven_and_disabled(self):
        manifest = load_yaml(MANIFEST)
        validate_manifest(manifest)
        with tempfile.TemporaryDirectory() as directory:
            render_manifest(manifest, "apisix", directory)
            content = (Path(directory) / "apisix.yaml").read_text()
            config = yaml.safe_load(content)
            runtime = yaml.safe_load((Path(directory) / "config.yaml").read_text())
        self.assertTrue(content.endswith("#END\n"))
        self.assertEqual(runtime["deployment"]["role_data_plane"]["config_provider"], "yaml")
        self.assertEqual(runtime["apisix"]["node_listen"][0]["ip"], "127.0.0.1")
        self.assertTrue(all(route["status"] == 0 for route in config["routes"]))
        subscription, official = config["routes"]
        self.assertNotIn("ai-proxy-multi", subscription["plugins"])
        plugin = official["plugins"]["ai-proxy-multi"]
        self.assertEqual(len(plugin["instances"]), 3)
        self.assertFalse(plugin["logging"]["payloads"])
        self.assertEqual(plugin["instances"][0]["auth"]["header"]["Authorization"], "Bearer ${{OPENAI_API_KEY}}")
        self.assertEqual(official["plugins"]["limit-count"]["key"], "consumer_name")

    def test_database_and_etcd_are_rejected(self):
        for field, value in (("runtime_config_backend", "postgresql"), ("etcd", True)):
            manifest = load_yaml(MANIFEST)
            manifest["gateway"][field] = value
            with self.assertRaises(ManifestError):
                validate_manifest(manifest)

    def test_credentials_require_variable_names(self):
        manifest = load_yaml(MANIFEST)
        manifest["routes"][1]["ai_proxy_multi"]["instances"][0]["credential_env"] = "literal-secret"
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_other_renderers_cannot_drop_ai_plugin(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                render_manifest(load_yaml(MANIFEST), "kong", directory)
