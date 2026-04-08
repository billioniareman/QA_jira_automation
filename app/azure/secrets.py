"""Azure Key Vault secret management."""

import logging
from typing import Optional

from .config import azure_service_manager


logger = logging.getLogger(__name__)


def get_secret_client():
    """Get Azure Key Vault SecretClient."""
    manager = azure_service_manager
    if not manager._initialized:
        manager.initialize()
    return manager.get_key_vault_client()


def get_secret(secret_name: str) -> Optional[str]:
    """
    Retrieve a secret from Azure Key Vault.
    
    Args:
        secret_name: Name of the secret to retrieve
        
    Returns:
        Secret value, or None if not found or Key Vault not configured
    """
    try:
        client = get_secret_client()
        if client is None:
            logger.warning('Key Vault client not initialized')
            return None

        secret = client.get_secret(secret_name)
        logger.info(f'Retrieved secret from Key Vault: {secret_name}')
        return secret.value

    except Exception as e:
        logger.error(f'Failed to retrieve secret {secret_name} from Key Vault: {e}')
        return None
