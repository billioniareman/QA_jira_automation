"""Azure service initialization and management."""

import logging
from typing import Optional

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.keyvault.secrets import SecretClient

from config import settings


logger = logging.getLogger(__name__)


class AzureServiceManager:
    """Manages Azure service clients (identity, Key Vault, etc.)."""

    def __init__(self):
        self.credential: Optional[object] = None
        self.key_vault_client: Optional[SecretClient] = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize Azure service clients based on environment settings."""
        if self._initialized:
            return

        try:
            # Determine credential strategy
            if settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET and settings.AZURE_TENANT_ID:
                # Use service principal (app authentication)
                logger.info('Initializing Azure with service principal credentials')
                self.credential = ClientSecretCredential(
                    tenant_id=settings.AZURE_TENANT_ID,
                    client_id=settings.AZURE_CLIENT_ID,
                    client_secret=settings.AZURE_CLIENT_SECRET,
                )
            else:
                # Use default Azure credential chain (managed identity, local development)
                logger.info('Initializing Azure with DefaultAzureCredential')
                self.credential = DefaultAzureCredential()

            # Initialize Key Vault client if URL provided
            if settings.AZURE_KEYVAULT_URL:
                self.key_vault_client = SecretClient(
                    vault_url=settings.AZURE_KEYVAULT_URL,
                    credential=self.credential,
                )
                logger.info(f'Key Vault client initialized: {settings.AZURE_KEYVAULT_URL}')

            self._initialized = True
            logger.info('Azure services initialized successfully')

        except Exception as e:
            logger.error(f'Failed to initialize Azure services: {e}')
            if settings.ENVIRONMENT == 'production':
                raise

    def get_credential(self) -> object:
        """Get Azure credential for authenticated API calls."""
        if not self._initialized:
            self.initialize()
        return self.credential

    def get_key_vault_client(self) -> Optional[SecretClient]:
        """Get Key Vault client for secret retrieval."""
        if not self._initialized:
            self.initialize()
        return self.key_vault_client


# Global instance
azure_service_manager = AzureServiceManager()


def init_azure_services() -> None:
    """Initialize all Azure services (call once at app startup)."""
    azure_service_manager.initialize()
