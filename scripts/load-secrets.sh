#!/bin/bash
set -euo pipefail

# InboxPilot - Load secrets from OpenBao/Vault
# Usage: ./scripts/load-secrets.sh [dev|prod]

ENVIRONMENT="${1:-dev}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔐 Loading secrets from OpenBao for environment: $ENVIRONMENT"

# Check dependencies
if ! command -v bao &> /dev/null; then
    echo -e "${RED}❌ Error: 'bao' CLI not found${NC}"
    echo "Install OpenBao CLI: https://openbao.org/docs/install/"
    exit 1
fi

# Check authentication
if [ -z "$VAULT_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  VAULT_TOKEN not set${NC}"
    echo "Please authenticate with OpenBao:"
    echo "  export VAULT_TOKEN=\$(bao login -token-only -method=userpass username=myuser)"
    exit 1
fi

# Helper function to get secret field
get_secret() {
    local path="$1"
    local field="$2"
    local value

    value=$(bao kv get -field="$field" "$path" 2>/dev/null || echo "")

    if [ -z "$value" ]; then
        echo -e "${YELLOW}⚠️  Warning: Secret not found: $path/$field${NC}" >&2
        echo ""
    else
        echo "$value"
    fi
}

echo "📥 Fetching secrets from OpenBao at $VAULT_ADDR..."

# Generate .env file
cat > "$PROJECT_ROOT/.env" <<EOF
# Auto-generated from OpenBao on $(date)
# Environment: $ENVIRONMENT
# DO NOT EDIT MANUALLY - Changes will be overwritten by scripts/load-secrets.sh

# =============================================================================
# Common
# =============================================================================
TOKEN_ENCRYPTION_KEY=$(get_secret inboxpilot/common token_encryption_key)
AUTH_SECRET=$(get_secret inboxpilot/common auth_secret)

# =============================================================================
# Database
# =============================================================================
POSTGRES_DB=$(get_secret inboxpilot/database postgres_db)
POSTGRES_USER=$(get_secret inboxpilot/database postgres_user)
POSTGRES_PASSWORD=$(get_secret inboxpilot/database postgres_password)
DATABASE_URL=$(get_secret inboxpilot/database database_url)

# =============================================================================
# Groq AI
# =============================================================================
GROQ_API_KEY=$(get_secret inboxpilot/groq api_key)

# =============================================================================
# OAuth - Microsoft
# =============================================================================
MICROSOFT_CLIENT_ID=$(get_secret inboxpilot/oauth/microsoft client_id)
MICROSOFT_CLIENT_SECRET=$(get_secret inboxpilot/oauth/microsoft client_secret)

# Multi-tenant Microsoft (optionnel)
EXUVIE_MICROSOFT_CLIENT_ID=$(get_secret inboxpilot/oauth/microsoft-clients/exuvie client_id)
COLLEGUE_MICROSOFT_CLIENT_ID=$(get_secret inboxpilot/oauth/microsoft-clients/collegue client_id)

# =============================================================================
# URLs (environment-specific)
# =============================================================================
OAUTH_BASE_URL=$(get_secret inboxpilot/urls/$ENVIRONMENT oauth_base_url)
OAUTH_PUBLIC_URL=$(get_secret inboxpilot/urls/$ENVIRONMENT oauth_public_url)
FRONTEND_BASE_URL=$(get_secret inboxpilot/urls/$ENVIRONMENT frontend_base_url)

# =============================================================================
# OAuth - Gmail
# =============================================================================
GMAIL_OAUTH_CLIENT_FILE=./secrets/google-oauth-client.json

# =============================================================================
# Service Ports
# =============================================================================
OAUTH_PORT=8080
OAUTH_HOST_PORT=8080
FRONTEND_HOST_PORT=3000
EOF

echo "✅ .env file generated"

# Create secrets directory
mkdir -p "$PROJECT_ROOT/secrets"

# Generate google-oauth-client.json from Vault
echo "📥 Fetching Gmail OAuth client config..."
GMAIL_CLIENT_CONFIG=$(get_secret inboxpilot/oauth/gmail client_config)

if [ -n "$GMAIL_CLIENT_CONFIG" ]; then
    echo "$GMAIL_CLIENT_CONFIG" > "$PROJECT_ROOT/secrets/google-oauth-client.json"
    echo "✅ secrets/google-oauth-client.json generated"
else
    echo -e "${YELLOW}⚠️  Gmail OAuth config not found in Vault${NC}"
    echo "   You can create a placeholder or set it manually"
fi

# Set permissions
chmod 600 "$PROJECT_ROOT/.env"
chmod 600 "$PROJECT_ROOT/secrets/google-oauth-client.json" 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ All secrets loaded successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Verify .env file: cat .env"
echo "  2. Start services: docker-compose up -d"
echo "  3. Check logs: docker-compose logs -f"
