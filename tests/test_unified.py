import copy

import pytest
import yaml

from gatewayctl.unified import stage, validate


@pytest.fixture
def spec():
    return {
        "host": "ai-internal.onwalk.net", "cross_backend_fallback": False,
        "new_api": {"bind_address": "127.0.0.1", "port": 3000},
    }


@pytest.fixture
def bundle():
    return {"routes": [{
        "id": "new-api", "host": "ai-internal.onwalk.net", "uri": "/*",
        "upstream": {"nodes": {"127.0.0.1:3000": 1}},
        "plugins": {
            "key-auth": {"hide_credentials": True}, "consumer-restriction": {"whitelist": ["personal"]},
            "ip-restriction": {"whitelist": ["10.79.0.0/24"]}, "limit-count": {"count": 60},
            "proxy-rewrite": {"headers": {"set": {"Authorization": "Bearer fixture-only"}}},
        },
    }]}


def test_security_preserved_and_no_cross_backend_fallback(spec, bundle):
    original = copy.deepcopy(bundle)
    out, runtime = stage(bundle, {"plugins": ["key-auth"]}, spec, {"cpa-test": "must-not-be-embedded"})
    assert bundle == original and len(out["routes"]) == 2
    route = next(route for route in out["routes"] if route["id"] == "unified-ai-gateway")
    console = next(route for route in out["routes"] if route["id"] == "new-api-console")
    assert route["upstream"]["nodes"] == {"127.0.0.1:3000": 1}
    assert route["plugins"]["ip-restriction"] == original["routes"][0]["plugins"]["ip-restriction"]
    assert route["plugins"]["limit-count"]["key"] == "remote_addr"
    assert route["plugins"]["limit-count"]["key_type"] == "var"
    assert route["plugins"]["forward-auth"]["uri"] == "http://127.0.0.1:3000/api/usage/token"
    assert route["plugins"]["forward-auth"]["request_headers"] == ["Authorization"]
    assert route["plugins"]["forward-auth"]["allow_degradation"] is False
    assert route["plugins"]["forward-auth"]["status_on_error"] == 503
    assert "key-auth" not in route["plugins"] and "consumer-restriction" not in route["plugins"]
    assert "serverless-pre-function" in runtime["plugins"]
    assert console["uri"] == "/*" and console["host"] == spec["host"]
    assert console["upstream"]["nodes"] == {"127.0.0.1:3000": 1}
    assert console["plugins"]["ip-restriction"]["whitelist"] == ["10.79.0.0/24"]
    assert "key-auth" not in console["plugins"]
    normalize = route["plugins"]["serverless-pre-function"]["functions"][0]
    assert "Authorization" in normalize and "x-api-key" in normalize and "apikey" in normalize
    assert "must-not-be-embedded" not in str(out)
    assert "ai-proxy-multi" not in route["plugins"]
    second, runtime = stage(out, runtime, spec)
    assert second == out


def test_model_catalog_is_not_rendered_or_owned_by_apisix(spec, bundle):
    out, _ = stage(bundle, {"plugins": []}, spec)
    assert {route["id"] for route in out["routes"]} == {"unified-ai-gateway", "new-api-console"}


def test_console_fails_closed_without_explicit_vpn_allowlist(spec, bundle):
    bundle["routes"][0]["plugins"]["ip-restriction"]["whitelist"] = []
    with pytest.raises(ValueError, match="VPN allowlist"):
        stage(bundle, {"plugins": []}, spec, {"cpa-test": "fixture"})


def test_new_api_must_be_loopback_or_private(spec):
    spec["new_api"]["bind_address"] = "8.8.8.8"
    with pytest.raises(ValueError, match="private"):
        validate(spec)


@pytest.mark.parametrize("change", ["public", "fallback", "secret", "model-catalog"])
def test_reject_invalid_routing(spec, change):
    if change == "public":
        spec["new_api"]["bind_address"] = "8.8.8.8"
    elif change == "fallback":
        spec["cross_backend_fallback"] = True
    elif change == "secret":
        spec["new_api"]["api_key"] = "fixture-secret"
    else:
        spec["models"] = [{"id": "fixture-model", "backend": "cpa-test"}]
    with pytest.raises(ValueError):
        validate(spec)
