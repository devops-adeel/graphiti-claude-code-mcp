#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Setting up 1Password for Graphiti MCP Server${NC}"
echo ""

# Check if op CLI is installed
if ! command -v op &> /dev/null; then
    echo -e "${RED}❌ Error: 1Password CLI (op) is not installed${NC}"
    echo "Install with: brew install --cask 1password-cli"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  Warning: jq is not installed (needed for JSON parsing)${NC}"
    echo "Install with: brew install jq"
    echo ""
fi

# Step 1: Check/Create Langfuse item
echo -e "${BLUE}Step 1: Checking Langfuse/Integration item...${NC}"
if op item get "Langfuse/Integration" --vault=HomeLab &>/dev/null; then
    echo -e "${GREEN}✅ Langfuse/Integration already exists${NC}"
    LANGFUSE_ID=$(op item get "Langfuse/Integration" --vault=HomeLab --format=json | jq -r '.id')
    echo "   Item ID: $LANGFUSE_ID"
else
    echo "Creating Langfuse/Integration item..."
    LANGFUSE_ID=$(op item create \
        --category=PASSWORD \
        --title="Langfuse/Integration" \
        --vault=HomeLab \
        'langfuse-public-key[text]=pk-lf-00689068-a85f-41a1-8e1e-37619595b0ed' \
        'langfuse-secret-key[password]=sk-lf-14e07bbb-ee5f-45a1-abd8-b63d21f95bb9' \
        'langfuse-host[text]=https://langfuse.local' \
        'notes[text]=Langfuse observability platform credentials for MCP Server and trace analysis' \
        --format=json | jq -r '.id')
    
    echo -e "${GREEN}✅ Created Langfuse/Integration with ID: $LANGFUSE_ID${NC}"
    
    # Update .env.1password with actual ID
    if [ -f "secrets/.env.1password" ]; then
        sed -i '' "s|Langfuse-Integration|$LANGFUSE_ID|g" secrets/.env.1password
        echo "   Updated secrets/.env.1password with actual ID"
    fi
fi

echo ""

# Step 2: Check/Create Service Account
echo -e "${BLUE}Step 2: Service Account Setup...${NC}"
SERVICE_TOKEN_FILE="$HOME/.config/graphiti-mcp/service-token"

if [ -f "$SERVICE_TOKEN_FILE" ]; then
    echo -e "${GREEN}✅ Service Account token already exists${NC}"
    echo "   Location: $SERVICE_TOKEN_FILE"
    
    # Verify token works
    source "$SERVICE_TOKEN_FILE"
    if op inject -i secrets/.env.1password >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Token verified and working${NC}"
    else
        echo -e "${YELLOW}⚠️  Token exists but may not be working${NC}"
    fi
else
    echo -e "${YELLOW}Creating new Service Account (requires admin privileges)...${NC}"
    echo -e "${RED}⚠️  IMPORTANT: The token will only be shown ONCE!${NC}"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to cancel..."
    
    # Create service account (max 90 days)
    TOKEN=$(op service-account create "Graphiti MCP Server" \
        --vault HomeLab:read_items \
        --expires-in 90d \
        --format json | jq -r '.token')
    
    # Store token securely
    mkdir -p "$HOME/.config/graphiti-mcp"
    cat > "$SERVICE_TOKEN_FILE" << EOF
#!/bin/bash
# Service Account Token for Graphiti MCP Server
# Created: $(date +%Y-%m-%d)
# Expires: 90 days from creation

export OP_SERVICE_ACCOUNT_TOKEN='$TOKEN'
EOF
    
    chmod 600 "$SERVICE_TOKEN_FILE"
    echo -e "${GREEN}✅ Service Account created and token stored${NC}"
    echo "   Location: $SERVICE_TOKEN_FILE"
fi

echo ""

# Step 3: Verify configuration alignment
echo -e "${BLUE}Step 3: Verifying configuration alignment with GTD Coach...${NC}"

CONFIG_FILE=".env.graphiti"
if [ -f "$CONFIG_FILE" ]; then
    # Check GRAPHITI_GROUP_ID
    if grep -q "GRAPHITI_GROUP_ID=shared_knowledge" "$CONFIG_FILE"; then
        echo -e "${GREEN}✅ GRAPHITI_GROUP_ID correctly set to 'shared_knowledge'${NC}"
    else
        echo -e "${RED}❌ GRAPHITI_GROUP_ID is not 'shared_knowledge'${NC}"
        echo "   Fix with: make fix-config"
    fi
    
    # Check FALKORDB_DATABASE
    if grep -q "FALKORDB_DATABASE=shared_gtd_knowledge" "$CONFIG_FILE"; then
        echo -e "${GREEN}✅ FALKORDB_DATABASE correctly set to 'shared_gtd_knowledge'${NC}"
    else
        echo -e "${RED}❌ FALKORDB_DATABASE is not 'shared_gtd_knowledge'${NC}"
        echo "   Fix with: make fix-config"
    fi
else
    echo -e "${YELLOW}⚠️  .env.graphiti not found${NC}"
fi

echo ""

# Step 4: Final verification
echo -e "${BLUE}Step 4: Final verification...${NC}"

# Source the token
source "$SERVICE_TOKEN_FILE" 2>/dev/null

# Test secret injection
if op inject -i secrets/.env.1password >/dev/null 2>&1; then
    echo -e "${GREEN}✅ All secrets accessible via Service Account${NC}"
    
    # Show what secrets will be available
    echo ""
    echo "Available secrets:"
    echo "  • OPENAI_API_KEY (from FalkorDB/Integration)"
    echo "  • LANGFUSE_PUBLIC_KEY (from Langfuse/Integration)"
    echo "  • LANGFUSE_SECRET_KEY (from Langfuse/Integration)"
    echo "  • LANGFUSE_HOST (from Langfuse/Integration)"
else
    echo -e "${RED}❌ Failed to verify secrets access${NC}"
    echo "Check that:"
    echo "  1. Service Account token is valid"
    echo "  2. All referenced items exist in HomeLab vault"
    echo "  3. You have access to HomeLab vault"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 1Password setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Start with 1Password: make up-secure"
echo "  2. Verify logs: make logs"
echo "  3. Test knowledge sharing with GTD Coach"
echo ""
echo "The Service Account token will work for 90 days without any Touch ID prompts!"