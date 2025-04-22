from cryptography.fernet import Fernet

from app.core.config import settings

secret_key = settings.ENCRYPTION_KEY
cipher_suite = Fernet(secret_key)

def encrypt_sensitive_data(data: str) -> str:
    """
    Encrypts a string for secure logging.

    Args:
        data (str): The sensitive data to be encrypted.

    Returns:
        str: The encrypted string, encoded in Base64 format.
    """
    return cipher_suite.encrypt(data.encode()).decode()
