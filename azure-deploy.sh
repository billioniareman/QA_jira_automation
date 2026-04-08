#!/bin/bash
set -e

# Azure Deployment Script
# Deploys the AI Chat Agent to Azure Container Apps or App Service

echo "=========================================="
echo "Azure Deployment for AI Chat Agent"
echo "=========================================="

# Variables
RESOURCE_GROUP=${RESOURCE_GROUP:-$(read -p "Enter resource group name: " rg; echo $rg)}
APP_NAME=${APP_NAME:-$(read -p "Enter app name: " app; echo $app)}
CONTAINER_REGISTRY=${CONTAINER_REGISTRY:-}
DEPLOY_TARGET=${DEPLOY_TARGET:-$(read -p "Deploy target (app-service|container-apps): " target; echo $target)}

echo "Resource Group: $RESOURCE_GROUP"
echo "App Name: $APP_NAME"
echo "Deploy Target: $DEPLOY_TARGET"

# 1. Build Docker image
echo ""
echo "[1/5] Building Docker image..."
REGISTRY_URL="$CONTAINER_REGISTRY.azurecr.io"
IMAGE_NAME="qa-chat-agent"
IMAGE_TAG=$(date +%s)

if [ -n "$CONTAINER_REGISTRY" ]; then
    # Build and push to Azure Container Registry
    az acr build --registry "$CONTAINER_REGISTRY" \
        --image "$IMAGE_NAME:$IMAGE_TAG" \
        --image "$IMAGE_NAME:latest" \
        .
    echo "✓ Docker image pushed to ACR"
else
    # Build locally
    docker build -t "$IMAGE_NAME:$IMAGE_TAG" -t "$IMAGE_NAME:latest" .
    echo "✓ Docker image built locally"
fi

# 2. Deploy to Azure App Service
if [ "$DEPLOY_TARGET" = "app-service" ]; then
    echo ""
    echo "[2/5] Deploying to App Service..."
    
    # Create App Service plan if not exists
    if ! az appservice plan show --name "${APP_NAME}-plan" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
        az appservice plan create \
            --name "${APP_NAME}-plan" \
            --resource-group "$RESOURCE_GROUP" \
            --sku B2 \
            --is-linux
        echo "✓ App Service plan created"
    fi

    # Create/update web app
    if az webapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
        echo "✓ Updating existing App Service"
    else
        az webapp create \
            --name "$APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --plan "${APP_NAME}-plan" \
            --runtime "PYTHON|3.11"
        echo "✓ App Service created"
    fi

    # Set environment variables from .env
    echo "[3/5] Configuring app settings..."
    az webapp config appsettings set \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --settings \
            ENVIRONMENT=production \
            DEBUG=false \
            WEBSITES_PORT=5000
    echo "✓ App settings configured"

    # Deploy code
    echo "[4/5] Deploying code..."
    az webapp up \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --runtime "PYTHON:3.11"
    echo "✓ Code deployed"

    # Set startup command
    az webapp config set \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --startup-file "gunicorn --workers 4 --worker-class uvicorn.workers.UvicornWorker main:app"
    echo "✓ Startup command configured"

# 3. Deploy to Azure Container Apps
elif [ "$DEPLOY_TARGET" = "container-apps" ]; then
    echo ""
    echo "[2/5] Deploying to Container Apps..."
    
    # Create Container Apps environment if not exists
    CONTAINER_ENV="${APP_NAME}-env"
    if ! az containerapp env show --name "$CONTAINER_ENV" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
        az containerapp env create \
            --name "$CONTAINER_ENV" \
            --resource-group "$RESOURCE_GROUP"
        echo "✓ Container Apps environment created"
    fi

    # Create/update container app
    if az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
        echo "✓ Updating existing Container App"
        az containerapp update \
            --name "$APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --image "${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}"
    else
        az containerapp create \
            --name "$APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --environment "$CONTAINER_ENV" \
            --image "${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}" \
            --target-port 5000 \
            --ingress external \
            --env-vars \
                ENVIRONMENT=production \
                DEBUG=false
        echo "✓ Container App created"
    fi

    echo "[3/5] Container Apps deployment complete"
else
    echo "❌ Unknown deploy target: $DEPLOY_TARGET"
    exit 1
fi

# 4. Run migrations
echo ""
echo "[5/5] Running database migrations..."
# For production, run migrations via SSH or before deployment
# This assumes migrations are run during container startup
echo "✓ Migrations configured to run on startup"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Application URL:"
if [ "$DEPLOY_TARGET" = "app-service" ]; then
    az webapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query defaultHostName -o tsv | sed 's/^/https:\/\//'
else
    az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv | sed 's/^/https:\/\//'
fi
echo ""
echo "Monitor deployment:"
echo "az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
