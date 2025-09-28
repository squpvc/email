"""
Encryption utilities for sensitive data like email passwords.
"""
import os
import base64
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..config import SECRET_KEY, SALT_BYTES

logger = logging.getLogger(__name__)

def _get_fernet() -> Fernet:
    """
    Get a Fernet instance for encryption/decryption.
    
    Returns:
        Fernet instance initialized with a key derived from the app secret key
    """
    # Derive a 32-bit URL-safe base64-encoded key from the secret key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT_BYTES,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(SECRET_KEY.encode()))
    return Fernet(key)

def encrypt(data: str) -> str:
    """
    Encrypt a string.
    
    Args:
        data: String to encrypt
        
    Returns:
        Encrypted string
        
    Raises:
        ValueError: If encryption fails
    """
    try:
        fernet = _get_fernet()
        return fernet.encrypt(data.encode()).decode()
    except Exception as e:
        logger.error(f"Error encrypting data: {e}")
        raise ValueError("Failed to encrypt data")

def decrypt(encrypted_data: str) -> str:
    """
    Decrypt a string.
    
    Args:
        encrypted_data: Encrypted string to decrypt
        
    Returns:
        Decrypted string
        
    Raises:
        ValueError: If decryption fails or the token is invalid
    """
    try:
        fernet = _get_fernet()
        return fernet.decrypt(encrypted_data.encode()).decode()
    except (InvalidToken, ValueError) as e:
        logger.error(f"Invalid token or decryption error: {e}")
        raise ValueError("Invalid or corrupted data")
    except Exception as e:
        logger.error(f"Error decrypting data: {e}")
        raise ValueError("Failed to decrypt data")
