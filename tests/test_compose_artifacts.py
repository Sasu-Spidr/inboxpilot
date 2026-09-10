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

    for service_name, service in services.items():
        assert "build" not in service
        for volume in service.get("volumes", []):
            source = volume.split(":", 1)[0] if isinstance(volume, str) else volume.get("source", "")
            assert not source.startswith(".")
            if service_name.startswith("bao-agent-"):
                assert source.startswith("${INBOXPILOT_BOOTSTRAP_ROOT")
            else:
                assert not source.startswith("/")

    assert "inboxpilot_runtime_secrets" not in compose.get("volumes", {})
    for service_name in ("mail-agent", "oauth-onboarding"):
        service = services[service_name]
        assert "env_file" not in service
        assert service["environment"]["BAO_AGENT_ADDR"].endswith("bao-agent-worker:8100}")
        assert not {
            "GROQ_API_KEY",
            "TOKEN_ENCRYPTION_KEY",
            "MICROSOFT_CLIENT_ID",
            "MICROSOFT_CLIENT_SECRET",
            "GMAIL_OAUTH_CLIENT_FILE",
        } & set(service["environment"])
        assert all("/app/secrets" not in str(volume) for volume in service.get("volumes", []))


def test_python_runtime_no_longer_depends_on_google_secret_files():
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    settings_text = (ROOT / "config/settings.yaml").read_text(encoding="utf-8")
    connector_text = (ROOT / "gmail_connector.py").read_text(encoding="utf-8")
    oauth_text = (ROOT / "oauth_server.py").read_text(encoding="utf-8")
    deploy_text = (ROOT / "scripts/deploy_remote_images.sh").read_text(encoding="utf-8")

    assert "from_client_secrets_file" not in connector_text
    assert "from_client_secrets_file" not in oauth_text
    assert "credentials_file" not in settings_text
    assert "google-oauth-client.json" not in compose_text
    assert "google-oauth-client.json" not in deploy_text

def test_local_build_override_restores_all_application_builds():
    compose = load_compose("docker-compose.build.yml")
    assert set(compose["services"]) == {
        "bao-agent-frontend",
        "bao-agent-worker",
        "frontend",
        "mail-agent",
        "oauth-onboarding",
    }
    assert "build" in compose["services"]["frontend"]
    assert "build" in compose["services"]["mail-agent"]
    assert "build" not in compose["services"]["oauth-onboarding"]
    assert compose["services"]["mail-agent"]["image"] == compose["services"]["oauth-onboarding"]["image"]
    assert "build" in compose["services"]["bao-agent-frontend"]
    assert "build" not in compose["services"]["bao-agent-worker"]
    assert compose["services"]["bao-agent-frontend"]["image"] == compose["services"]["bao-agent-worker"]["image"]


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


def test_ci_publishes_all_images_after_tests_on_main_and_dev():
    workflow_text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)
    build = workflow["jobs"]["build"]
    images = {
        entry["name"]: entry
        for entry in build["strategy"]["matrix"]["include"]
    }

    # PyYAML 1.1 parses the unquoted key `on` as True.
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers["push"]["branches"]) == {"main", "dev"}
    assert build["needs"] == ["test"]
    assert build["if"] == "github.event_name != 'pull_request'"
    assert build["permissions"] == {"contents": "read", "packages": "write"}
    assert set(images) == {"backend", "frontend", "bao-agent"}
    assert images["bao-agent"]["dockerfile"] == "./deploy/Dockerfile.agent"
    assert "docker/metadata-action@v5" in workflow_text
    assert "type=sha" in workflow_text
    assert "type=ref,event=branch" in workflow_text
    assert "cache-to: type=gha,mode=max" in workflow_text


def test_bao_agent_image_is_version_pinned_and_packages_its_config():
    dockerfile = (ROOT / "deploy/Dockerfile.agent").read_text(encoding="utf-8")
    agent_config = (ROOT / "deploy/agent.hcl").read_text(encoding="utf-8")

    assert "FROM openbao/openbao:" in dockerfile
    assert "openbao/openbao:latest" not in dockerfile
    assert "COPY deploy/agent.hcl /etc/bao/agent.hcl" in dockerfile
    assert 'CMD ["agent", "-config=/etc/bao/agent.hcl"]' in dockerfile
    assert 'method "approle"' in agent_config
    assert 'role_id_file_path                   = "/bootstrap/role_id"' in agent_config
    assert 'secret_id_file_path                 = "/bootstrap/secret_id"' in agent_config
    assert "remove_secret_id_file_after_reading = false" in agent_config
    assert "api_proxy" in agent_config
    assert "use_auto_auth_token = true" in agent_config
    assert 'address     = "0.0.0.0:8100"' in agent_config
    # The server address must come from the container's BAO_ADDR: an address
    # in the config would override it.
    config_lines = [line for line in agent_config.splitlines() if not line.lstrip().startswith("#")]
    assert not any(line.lstrip().startswith("vault") for line in config_lines)


def test_bao_agents_are_network_isolated_and_not_published():
    compose = load_compose("docker-compose.yml")
    services = compose["services"]
    frontend_agent = services["bao-agent-frontend"]
    worker_agent = services["bao-agent-worker"]

    assert frontend_agent["networks"] == ["bao_frontend"]
    assert worker_agent["networks"] == ["bao_worker"]
    assert "ports" not in frontend_agent
    assert "ports" not in worker_agent
    assert frontend_agent["environment"]["BAO_ADDR"].startswith("${BAO_ADDR:?")
    assert worker_agent["environment"]["BAO_ADDR"].startswith("${BAO_ADDR:?")
    assert services["frontend"]["networks"] == ["default", "bao_frontend"]
    assert services["mail-agent"]["networks"] == ["default", "bao_worker"]
    assert services["oauth-onboarding"]["networks"] == ["default", "bao_worker"]
    assert "bao_worker" not in services["frontend"]["networks"]
    assert "bao_frontend" not in services["mail-agent"]["networks"]
    assert "bao_frontend" not in services["oauth-onboarding"]["networks"]

    for agent in (frontend_agent, worker_agent):
        assert agent["read_only"] is True
        assert agent["cap_drop"] == ["ALL"]
        assert agent["security_opt"] == ["no-new-privileges:true"]
        assert agent["volumes"][0]["read_only"] is True
        assert agent["healthcheck"]["test"][-1].endswith("/v1/sys/health")

    assert services["frontend"]["depends_on"]["bao-agent-frontend"]["condition"] == "service_healthy"
    assert services["mail-agent"]["depends_on"]["bao-agent-worker"]["condition"] == "service_healthy"
    assert services["oauth-onboarding"]["depends_on"]["bao-agent-worker"]["condition"] == "service_healthy"


def test_manual_deployment_can_target_dev_without_touching_prod():
    workflow_text = (ROOT / ".github/workflows/publish-and-deploy.yml").read_text(encoding="utf-8")

    assert "target:" in workflow_text
    assert "inputs.target == 'dev' || inputs.target == 'all'" in workflow_text
    assert "inputs.target == 'prod'" in workflow_text
    assert "BAO_ADDR: ${{ vars.BAO_ADDR }}" in workflow_text
    assert "Build and push OpenBao agent image" in workflow_text
