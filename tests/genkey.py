from cryptography.fernet import Fernet
import os
key = Fernet.generate_key().decode()
with open(os.path.join(os.path.dirname(__file__), '..', '.env'), 'w') as f:
    f.write(f'SECRET_KEY=test-secret-key-for-e2e-testing-only-1234567\n')
    f.write(f'ENCRYPTION_KEY={key}\n')
print(key)
