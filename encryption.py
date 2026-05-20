import base64

# This is a placeholder for a real encryption service.
# For the purpose of this test, we use simple base64 encoding,
# as the actual encryption logic is not relevant to the UI test.

def encrypt_data(data: str) -> str:
    """Encodes string data using base64."""
    if not isinstance(data, str):
        return ""
    return base64.b64encode(data.encode('utf-8')).decode('utf-8')

def decrypt_data(data: str) -> str:
    """Decodes string data using base64."""
    if not isinstance(data, str):
        return ""
    try:
        return base64.b64decode(data.encode('utf-8')).decode('utf-8')
    except (ValueError, TypeError):
        # Return original data if it's not valid base64
        return data
