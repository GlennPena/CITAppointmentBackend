from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

# Load environment variables (FERNET key)
load_dotenv()

# Initialize encryption key and Fernet instance
KEY = os.getenv("FERNET_KEY")
if not KEY:
    # Safe fallback to prevent startup/build crashes
    KEY = Fernet.generate_key()
else:
    KEY = KEY.encode()

fernet = Fernet(KEY)

def encrypt(text):
    # Encrypts plain text into secure token
    if not text: return ""
    return fernet.encrypt(text.encode()).decode()

def decrypt(token):
    # Decrypts secure token back to plain text  
    if not token: return ""
    try:
        return fernet.decrypt(token.encode()).decode()
    except Exception:
        return "[Decryption Error]"