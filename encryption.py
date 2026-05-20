import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_key():
    """
    Loads the encryption key from the ENCRYPTION_KEY environment variable.
    The application will fail to start if the key is not found.
    """
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("FATAL: ENCRYPTION_KEY not found in environment variables. "
                         "Please generate a key and add it to your .env file.")
    return key.encode()

# Load the key and initialize the cipher suite at import time.
# If the key is missing, the app will crash on startup, which is the desired behavior.
try:
    key = load_key()
    cipher_suite = Fernet(key)
except ValueError as e:
    print(e)
    # Exit to prevent the app from running in a broken state.
    exit(1)

def encrypt_data(data: str) -> str:
    """Encrypts a string, returning an empty string if input is empty."""
    if not data:
        return ""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypts a string, returning an empty string if input is empty."""
    if not encrypted_data:
        return ""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()
