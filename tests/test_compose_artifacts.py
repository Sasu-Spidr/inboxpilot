from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_compose(name: str) -> dict:
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


def test_runtime_compose_uses_images_and_named_volumes_only():
    compose = load_compose("docker-compose.yml")
    services = compose["services"]

    assert services["mail-agent"]["image"].startswith("ghcr.io/sasu-spidr/inboxpilot:")
    assert services["oauth-onboarding"]["image"].startswith("ghcr.io/sasu-spidr/inboxpilot:")
    assert services["frontend"]["image"].startswith("ghcr.io/sasu-spidr/inboxpilot-frontend:")

    for service in services.values():
        assert "build" not in service
        for volume in service.get("volumes", []):
            source = volume.split(":", 1)[0] if isinstance(volume, str) else volume.get("source", "")
            assert not source.startswith(".")
            assert not source.startswith("/")

def test_local_build_override_restores_all_application_builds():
    compose = load_compose("docker-compose.build.yml")
    assert set(compose["services"]) == {"frontend", "mail-agent", "oauth-onboarding"}
    assert "build" in compose["services"]["frontend"]
    assert "build" in compose["services"]["mail-agent"]
    assert "build" not in compose["services"]["oauth-onboarding"]
    assert compose["services"]["mail-agent"]["image"] == compose["services"]["oauth-onboarding"]["image"]


def test_traefik_overrides_are_versioned_without_embedded_basic_auth():
    dev = load_compose("docker-compose.dev.yml")
    prod = load_compose("docker-compose.prod.yml")
    dev_text = (ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")
    prod_text = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "inboxpilot-dev.mallow-hub.tech" in dev_text
    assert "TRAEFIK_BASIC_AUTH_HASH" in dev_text
    assert "$apr1$" not in dev_text
    assert "inboxpilot.mallow-hub.tech" in prod_text
    for override in (dev, prod):
        for service_name in ("frontend", "mail-agent", "oauth-onboarding"):
            assert "IMAGE_TAG is required" in override["services"][service_name]["image"]
