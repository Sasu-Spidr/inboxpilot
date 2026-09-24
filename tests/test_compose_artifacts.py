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

    frontend = services["frontend"]
    assert "env_file" not in frontend
    assert frontend["environment"]["BAO_AGENT_ADDR"].endswith("bao-agent-frontend:8100}")
    assert "TURNSTILE_SITE_KEY" in frontend["environment"]
    assert not {
        "DATABASE_URL",
        "AUTH_SECRET",
        "TOKEN_ENCRYPTION_KEY",
        "TURNSTILE_SECRET_KEY",
        "SIGNUP_ACCESS_CODE",
    } & set(frontend["environment"])


def test_python_runtime_no_longer_depends_on_google_secret_files():
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    settings_text = (ROOT / "config/settings.yaml").read_text(encoding="utf-8")
    connector_text = (ROOT / "gmail_connector.py").read_text(encoding="utf-8")
    oauth_text = (ROOT / "oauth_server.py").read_text(encoding="utf-8")
    deploy_text = (ROOT / "scripts/deploy_via_context.sh").read_text(encoding="utf-8")

    assert "from_client_secrets_file" not in connector_text
    assert "from_client_secrets_file" not in oauth_text
    assert "credentials_file" not in settings_text
    assert "google-oauth-client.json" not in compose_text
    assert "google-oauth-client.json" not in deploy_text


def test_frontend_runtime_preloads_openbao_secrets_without_worker_key():
    resolver_text = (ROOT / "frontend/lib/baoSecrets.ts").read_text(encoding="utf-8")
    instrumentation_text = (ROOT / "frontend/instrumentation.ts").read_text(encoding="utf-8")
    auth_text = (ROOT / "frontend/lib/auth.ts").read_text(encoding="utf-8")
    db_text = (ROOT / "frontend/lib/db.ts").read_text(encoding="utf-8")
    abuse_text = (ROOT / "frontend/lib/antiAbuse.ts").read_text(encoding="utf-8")
    labels_route_text = (ROOT / "frontend/app/api/settings/labels/route.ts").read_text(encoding="utf-8")

    for name in ("DATABASE_URL", "AUTH_SECRET", "TURNSTILE_SECRET_KEY", "SIGNUP_ACCESS_CODE"):
        assert name in resolver_text
    assert "TOKEN_ENCRYPTION_KEY" not in resolver_text
    assert "bao-agent-frontend:8100" in resolver_text
    assert "await preload()" in instrumentation_text
    assert 'secret("AUTH_SECRET")' in auth_text
    assert 'secret("DATABASE_URL")' in db_text
    assert 'secret("TURNSTILE_SECRET_KEY")' in abuse_text
    assert 'secret("SIGNUP_ACCESS_CODE")' in abuse_text
    assert "process.env.AUTH_SECRET" not in auth_text
    assert "process.env.DATABASE_URL" not in db_text
    assert "process.env.TOKEN_ENCRYPTION_KEY" not in labels_route_text
    assert "X-Internal-Sync-Key" not in labels_route_text

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
    assert "type=raw,value=${{ github.sha }}" in workflow_text
    assert "type=ref,event=branch" in workflow_text
    assert "cache-to: type=gha,mode=max" in workflow_text
    assert "Verify hardened ${{ matrix.name }} image runtime" in workflow_text
    assert "--read-only --cap-drop ALL" in workflow_text
    assert "tests/test_security_operations.py" in workflow_text


def test_ci_deploys_dev_through_the_reusable_workflow():
    ci_text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    ci = yaml.safe_load(ci_text)
    deploy = ci["jobs"]["deploy-dev"]

    assert deploy["needs"] == ["build"]
    assert deploy["uses"] == "./.github/workflows/deploy.yml"
    assert deploy["with"] == {
        "environment": "dev",
        "project": "spidr-mail-dev",
        "overlay": "docker-compose.dev.yml",
        "image_tag": "${{ github.sha }}",
    }
    assert deploy["secrets"] == "inherit"
    assert "refs/heads/dev" in deploy["if"]


def test_reusable_deployment_uses_remote_context_health_checks_and_rollback():
    workflow_text = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
    script_text = (ROOT / "scripts/deploy_via_context.sh").read_text(encoding="utf-8")

    assert "workflow_call:" in workflow_text
    for input_name in ("environment", "project", "overlay", "image_tag"):
        assert f"{input_name}:" in workflow_text
    assert 'docker context create vps --docker "host=ssh://' in workflow_text
    assert "docker login ghcr.io" in workflow_text
    assert "docker context rm -f vps" in workflow_text
    assert "environment: ${{ inputs.environment }}" in workflow_text
    assert "89.116.111.236" not in workflow_text
    assert "/opt/spidr-mail" not in workflow_text

    assert 'docker --context "$DOCKER_CONTEXT" compose' in script_text
    assert "bao-agent-frontend bao-agent-worker" in script_text
    assert "previous_image=" in script_text
    assert 'deploy_tag "$previous_tag"' in script_text
    assert "docker login" not in script_text
    assert "scp " not in script_text


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
        assert agent["user"] == "100:1000"
        assert agent["read_only"] is True
        assert agent["cap_drop"] == ["ALL"]
        assert agent["security_opt"] == ["no-new-privileges:true"]
        assert agent["volumes"][0]["read_only"] is True

    assert frontend_agent["healthcheck"]["test"][-1].endswith(
        "/v1/secret/data/inboxpilot/frontend"
    )
    assert worker_agent["healthcheck"]["test"][-1].endswith(
        "/v1/secret/data/inboxpilot/groq"
    )

    assert services["frontend"]["depends_on"]["bao-agent-frontend"]["condition"] == "service_healthy"
    assert services["mail-agent"]["depends_on"]["bao-agent-worker"]["condition"] == "service_healthy"
    assert services["oauth-onboarding"]["depends_on"]["bao-agent-worker"]["condition"] == "service_healthy"


def test_all_application_services_are_hardened_and_non_root():
    compose = load_compose("docker-compose.yml")
    services = compose["services"]

    expected_users = {
        "frontend": "1000:1000",
        "mail-agent": "10001:10001",
        "oauth-onboarding": "10001:10001",
    }
    for service_name, expected_user in expected_users.items():
        service = services[service_name]
        assert service["user"] == expected_user
        assert service["read_only"] is True
        assert service["cap_drop"] == ["ALL"]
        assert service["security_opt"] == ["no-new-privileges:true"]
        assert service["tmpfs"]

    assert "USER 10001:10001" in (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "USER node" in (ROOT / "frontend/Dockerfile").read_text(encoding="utf-8")


def test_runtime_compose_does_not_publish_host_ports():
    compose = load_compose("docker-compose.yml")
    dev = load_compose("docker-compose.dev.yml")
    prod = load_compose("docker-compose.prod.yml")
    for definition in (compose, dev, prod):
        for service in definition.get("services", {}).values():
            assert "ports" not in service


def test_manual_deployment_can_target_dev_without_touching_prod():
    workflow_text = (ROOT / ".github/workflows/publish-and-deploy.yml").read_text(encoding="utf-8")

    assert "target:" in workflow_text
    assert "inputs.target == 'dev' || inputs.target == 'all'" in workflow_text
    assert "inputs.target == 'prod'" in workflow_text
    assert workflow_text.count("uses: ./.github/workflows/deploy.yml") == 2
    assert "environment: dev" in workflow_text
    assert "environment: prod" in workflow_text
    assert "Build and push OpenBao agent image" in workflow_text


def test_production_release_uses_the_reusable_deployer_with_guards():
    workflow_text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert 'tags: ["v*"]' in workflow_text
    assert "deploy_prod:" in workflow_text
    assert "validate-prod-release:" in workflow_text
    assert 'git merge-base --is-ancestor "$release_commit" origin/main' in workflow_text
    assert "push:refs/tags/v*" in workflow_text
    assert "workflow_dispatch:refs/heads/main" in workflow_text
    assert "deploy-prod:" in workflow_text
    assert "environment: prod" in workflow_text
    assert "project: spidr-mail" in workflow_text
    assert "overlay: docker-compose.prod.yml" in workflow_text
    assert "image_tag: ${{ github.sha }}" in workflow_text
