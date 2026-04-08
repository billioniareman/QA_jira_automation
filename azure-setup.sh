#!/bin/bash
set -e

# Azure Setup Script for Local Development
# Prerequisites: Azure CLI installed and authenticated (az login)

echo "=========================================="
echo "Azure Setup for AI Chat Agent"
echo "=========================================="

# 1. Check Azure CLI login
echo "[1/7] Checking Azure CLI authentication..."
if ! az account show &>/dev/null; then
    echo "❌ Not authenticated. Running: az login"
    az login
fi

SUBSCRIPTION=$(az account show --query id -o tsv)
echo "✓ Using subscription: $SUBSCRIPTION"

# 2. Prompt for resource group and location
echo ""
echo "[2/7] Resource Group Configuration"
read -p "Enter resource group name (or press Enter to skip Azure setup): " RG_NAME
if [ -z "$RG_NAME" ]; then
    echo "Skipping Azure setup"
    exit 0
fi

read -p "Enter location (default: eastus): " LOCATION
LOCATION=${LOCATION:-eastus}

# Create or get resource group
if az group exists --name "$RG_NAME" &>/dev/null; then
    echo "✓ Using existing resource group: $RG_NAME"
else
    echo "Creating resource group: $RG_NAME"
    az group create --name "$RG_NAME" --location "$LOCATION"
    echo "✓ Resource group created"
fi

# 3. Create or get Azure OpenAI resource
echo ""
echo "[3/7] Azure OpenAI Configuration"
read -p "Enter OpenAI resource name (or press Enter to skip): " OPENAI_RESOURCE
if [ -n "$OPENAI_RESOURCE" ]; then
    if az cognitiveservices account show --name "$OPENAI_RESOURCE" --resource-group "$RG_NAME" &>/dev/null; then
        echo "✓ Using existing OpenAI resource: $OPENAI_RESOURCE"
    else
        echo "Creating OpenAI resource: $OPENAI_RESOURCE"
        az cognitiveservices account create \
            --name "$OPENAI_RESOURCE" \
            --resource-group "$RG_NAME" \
            --kind OpenAI \
            --sku s0 \
            --location "$LOCATION"
        echo "✓ OpenAI resource created"
    fi

    OPENAI_ENDPOINT=$(az cognitiveservices account show \
        --name "$OPENAI_RESOURCE" \
        --resource-group "$RG_NAME" \
        --query properties.endpoint -o tsv)
    OPENAI_KEY=$(az cognitiveservices account keys list \
        --name "$OPENAI_RESOURCE" \
        --resource-group "$RG_NAME" \
        --query key1 -o tsv)

    echo "AZURE_OPENAI_ENDPOINT=$OPENAI_ENDPOINT"
    echo "AZURE_OPENAI_API_KEY=$OPENAI_KEY"
fi

# 4. Create or get PostgreSQL database
echo ""
echo "[4/7] Azure Database for PostgreSQL Configuration"
read -p "Enter PostgreSQL server name (or press Enter to skip): " POSTGRES_SERVER
if [ -n "$POSTGRES_SERVER" ]; then
    if az postgres server show --name "$POSTGRES_SERVER" --resource-group "$RG_NAME" &>/dev/null; then
        echo "✓ Using existing PostgreSQL server: $POSTGRES_SERVER"
    else
        echo "Creating PostgreSQL server: $POSTGRES_SERVER"
        az postgres server create \
            --name "$POSTGRES_SERVER" \
            --resource-group "$RG_NAME" \
            --location "$LOCATION" \
            --admin-user azureuser \
            --admin-password "ChangeMe123!" \
            --sku-name B_Gen5_2 \
            --storage-size 51200
        echo "✓ PostgreSQL server created"
    fi

    POSTGRES_ENDPOINT=$(az postgres server show \
        --name "$POSTGRES_SERVER" \
        --resource-group "$RG_NAME" \
        --query fullyQualifiedDomainName -o tsv)
    echo "DATABASE_URL=postgresql+psycopg://azureuser:password@$POSTGRES_ENDPOINT:5432/qa_knowledge?sslmode=require"
fi

# 5. Create or get Key Vault
echo ""
echo "[5/7] Azure Key Vault Configuration"
read -p "Enter Key Vault name (or press Enter to skip): " KEYVAULT_NAME
if [ -n "$KEYVAULT_NAME" ]; then
    if az keyvault show --name "$KEYVAULT_NAME" --resource-group "$RG_NAME" &>/dev/null; then
        echo "✓ Using existing Key Vault: $KEYVAULT_NAME"
    else
        echo "Creating Key Vault: $KEYVAULT_NAME"
        az keyvault create \
            --name "$KEYVAULT_NAME" \
            --resource-group "$RG_NAME" \
            --location "$LOCATION"
        echo "✓ Key Vault created"
    fi

    KEYVAULT_URL=$(az keyvault show \
        --name "$KEYVAULT_NAME" \
        --resource-group "$RG_NAME" \
        --query properties.vaultUri -o tsv)
    echo "AZURE_KEYVAULT_URL=$KEYVAULT_URL"
fi

# 6. Create Application Insights
echo ""
echo "[6/7] Application Insights Configuration"
read -p "Enter Application Insights name (or press Enter to skip): " APP_INSIGHTS
if [ -n "$APP_INSIGHTS" ]; then
    if az monitor app-insights component show --app "$APP_INSIGHTS" --resource-group "$RG_NAME" &>/dev/null; then
        echo "✓ Using existing Application Insights: $APP_INSIGHTS"
    else
        echo "Creating Application Insights: $APP_INSIGHTS"
        az monitor app-insights component create \
            --app "$APP_INSIGHTS" \
            --resource-group "$RG_NAME" \
            --location "$LOCATION"
        echo "✓ Application Insights created"
    fi

    APP_INSIGHTS_KEY=$(az monitor app-insights component show \
        --app "$APP_INSIGHTS" \
        --resource-group "$RG_NAME" \
        --query instrumentationKey -o tsv)
    echo "AZURE_INSTRUMENTATION_KEY=$APP_INSIGHTS_KEY"
fi

# 7. Create service principal (optional for App Service deployment)
echo ""
echo "[7/7] Service Principal Configuration (Optional)"
read -p "Create service principal for deployments? (y/n): " CREATE_SP
if [ "$CREATE_SP" = "y" ] || [ "$CREATE_SP" = "Y" ]; then
    SP_NAME="qa-chat-agent-sp"
    SP=$(az ad sp create-for-rbac --name "$SP_NAME" --role Contributor --scopes "/subscriptions/$SUBSCRIPTION/resourceGroups/$RG_NAME")
    echo "✓ Service principal created:"
    echo "$SP"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Copy .env.azure.example to .env"
echo "2. Fill in the configuration values above"
echo "3. Run: alembic upgrade head"
echo "4. Run: python main.py"
echo ""
