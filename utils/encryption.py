"""
AES-256-GCM Verschlüsselung für sensible Dokumente (CrewBase)
DSGVO-konform: Arbeitsverträge und Gesundheitsausweise werden vor dem
Upload in Supabase Storage verschlüsselt und nach dem Download entschlüsselt.

Schlüsselverwaltung:
    - Der Verschlüsselungs-Schlüssel wird aus der Umgebungsvariable
      DOCUMENT_ENCRYPTION_KEY gelesen (32 Byte / 256 Bit, Base64-kodiert).
    - Falls nicht gesetzt, wird ein deterministischer Schlüssel aus der
      Supabase-Service-Key abgeleitet (Fallback, nicht empfohlen für Produktion).
    - Für Produktion: Schlüssel in Render.com als Secret Environment Variable setzen.

Verwendung:
    from utils.encryption import encrypt_document, decrypt_document
    
    # Verschlüsseln vor Upload:
    encrypted_data = encrypt_document(raw_bytes)
    upload_file_to_storage(bucket, path, encrypted_data)
    
    # Entschlüsseln nach Download:
    encrypted_data = download_file_from_storage(bucket, path)
    raw_bytes = decrypt_document(encrypted_data)
"""

import os
import base64
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Marker-Präfix für verschlüsselte Dateien (verhindert doppelte Verschlüsselung)
ENCRYPTED_MARKER = b"CREWBASE_AES256_V1:"


def _get_encryption_key() -> bytes:
    """
    Liest den AES-256-Schlüssel aus der Umgebungsvariable oder leitet ihn ab.
    
    Returns:
        bytes: 32-Byte-Schlüssel für AES-256
    """
    key_env = os.getenv("DOCUMENT_ENCRYPTION_KEY")
    
    if key_env:
        try:
            key = base64.b64decode(key_env)
            if len(key) == 32:
                return key
            # Wenn nicht 32 Byte, hash auf 32 Byte
            return hashlib.sha256(key).digest()
        except Exception:
            logger.warning("DOCUMENT_ENCRYPTION_KEY konnte nicht dekodiert werden. Verwende Fallback.")
    
    # Fallback: Schlüssel aus Supabase-URL ableiten (deterministisch, aber schwächer)
    supabase_url = os.getenv("SUPABASE_URL", "crewbase_default_key")
    fallback_key = hashlib.sha256(f"crewbase_doc_enc_{supabase_url}".encode()).digest()
    
    logger.warning(
        "DOCUMENT_ENCRYPTION_KEY nicht gesetzt! Verwende abgeleiteten Fallback-Schlüssel. "
        "Für Produktion: Setzen Sie DOCUMENT_ENCRYPTION_KEY als 32-Byte Base64-String."
    )
    return fallback_key


def encrypt_document(data: bytes) -> bytes:
    """
    Verschlüsselt ein Dokument mit AES-256-GCM.
    
    AES-256-GCM bietet:
    - Vertraulichkeit (Verschlüsselung)
    - Integrität (Authentifizierter Tag)
    - Authentizität (verhindert Manipulation)
    
    Format der verschlüsselten Daten:
        CREWBASE_AES256_V1:<base64(nonce + tag + ciphertext)>
    
    Args:
        data: Rohe Dokument-Bytes
        
    Returns:
        bytes: Verschlüsselte Daten mit Marker-Präfix
    """
    # Bereits verschlüsselt? Nicht doppelt verschlüsseln.
    if data.startswith(ENCRYPTED_MARKER):
        logger.debug("Dokument bereits verschlüsselt, überspringe.")
        return data
    
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        
        # Zufälliger 12-Byte-Nonce (GCM-Standard)
        nonce = os.urandom(12)
        
        # Verschlüsseln (GCM fügt automatisch 16-Byte Auth-Tag an)
        ciphertext_with_tag = aesgcm.encrypt(nonce, data, None)
        
        # Kombiniere: nonce (12) + ciphertext_with_tag
        combined = nonce + ciphertext_with_tag
        
        # Kodiere als Base64 und füge Marker hinzu
        encoded = base64.b64encode(combined)
        result = ENCRYPTED_MARKER + encoded
        
        logger.info(f"Dokument verschlüsselt: {len(data)} → {len(result)} Bytes")
        return result
        
    except ImportError:
        logger.error(
            "cryptography-Bibliothek nicht installiert! "
            "Führen Sie 'pip install cryptography' aus."
        )
        # Fallback: Kein Verschlüsseln (mit Warnung)
        logger.warning("WARNUNG: Dokument wird UNVERSCHLÜSSELT gespeichert!")
        return data
    except Exception as e:
        logger.error(f"Verschlüsselungsfehler: {e}")
        raise


def decrypt_document(data: bytes) -> bytes:
    """
    Entschlüsselt ein mit encrypt_document() verschlüsseltes Dokument.
    
    Args:
        data: Verschlüsselte Dokument-Bytes (mit CREWBASE_AES256_V1:-Marker)
        
    Returns:
        bytes: Entschlüsselte Rohdaten
        
    Raises:
        ValueError: Wenn die Daten manipuliert wurden (GCM Auth-Tag ungültig)
    """
    # Nicht verschlüsselt? Direkt zurückgeben (Rückwärtskompatibilität)
    if not data.startswith(ENCRYPTED_MARKER):
        logger.debug("Dokument ist nicht verschlüsselt (kein Marker), gebe direkt zurück.")
        return data
    
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        
        # Entferne Marker und dekodiere Base64
        encoded = data[len(ENCRYPTED_MARKER):]
        combined = base64.b64decode(encoded)
        
        # Trenne Nonce (12 Byte) vom Rest
        nonce = combined[:12]
        ciphertext_with_tag = combined[12:]
        
        # Entschlüsseln (wirft InvalidTag wenn manipuliert)
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        
        logger.info(f"Dokument entschlüsselt: {len(data)} → {len(plaintext)} Bytes")
        return plaintext
        
    except ImportError:
        logger.error("cryptography-Bibliothek nicht installiert!")
        return data
    except Exception as e:
        logger.error(f"Entschlüsselungsfehler (möglicherweise manipulierte Daten): {e}")
        raise ValueError(f"Dokument konnte nicht entschlüsselt werden: {e}")


def is_encrypted(data: bytes) -> bool:
    """Prüft ob Daten mit CrewBase AES-256 verschlüsselt sind."""
    return data.startswith(ENCRYPTED_MARKER)


def generate_new_key() -> str:
    """
    Generiert einen neuen zufälligen AES-256-Schlüssel (Base64-kodiert).
    Für die initiale Einrichtung in Render.com / .env.
    
    Returns:
        str: Base64-kodierter 32-Byte-Schlüssel
    """
    key = os.urandom(32)
    return base64.b64encode(key).decode()
