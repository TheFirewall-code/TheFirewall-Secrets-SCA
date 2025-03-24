import uuid
import hashlib
import platform
import requests
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import time
from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.modules.vc.vc_service import disable_all_vc
from app.modules.webhookConfig.webhook_config_service import disable_all_webhooks
from app.core.logger import logger
import os

import base64
from sqlalchemy import delete
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from app.modules.licenses.licenses_model import License

license_store = {}
settings.LICENSE_SERVER_VALIDATE_URL = os.getenv("LICENSE_SERVER_VALIDATE_URL", "http://localhost:4000")

import os
from typing import Optional

# Determine a secure storage path based on the OS
SECURE_STORAGE_PATH = os.path.expanduser("~/.config/firewall/license_token.enc")
os.makedirs(os.path.dirname(SECURE_STORAGE_PATH), exist_ok=True)
os.chmod(os.path.dirname(SECURE_STORAGE_PATH), 0o700)

async def save_token(db: AsyncSession, token: str):
    try:
        await db.execute(delete(License))
        
        # Save new token
        new_license = License(id="primary_license", token=token)
        db.add(new_license)
        await db.commit()
        print("Token successfully saved to the database.")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving license token: {str(e)}")

# Retrieve the token from the database
async def get_token(db: AsyncSession) -> Optional[str]:
    try:
        result = await db.execute(select(License).where(License.id == "primary_license"))
        license_entry = result.scalar_one_or_none()
        if license_entry:
            return license_entry.token
        return None
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching license token: {str(e)}")

########################################################################
# 2. Fingerprint Generation
#########################;/......###############################################

def get_machine_fingerprint() -> str:
    """
    Generate a machine fingerprint by hashing several system attributes:
    - Hostname
    - OS (system + release)
    - Architecture
    - Primary MAC address
    """
    hostname = platform.node()
    system = platform.system()
    release = platform.release()
    machine = platform.machine()
    
    # Attempt to retrieve MAC address from uuid.getnode()
    mac_int = uuid.getnode()
    mac_str = ':'.join(f"{(mac_int >> i) & 0xff:02x}" for i in reversed(range(0, 48, 8)))

    raw_data = f"{hostname}-{system}-{release}-{machine}-{mac_str}"
    raw_data_bytes = raw_data.encode("utf-8")
    fingerprint = base64.b64encode(raw_data_bytes).decode('utf-8')
    return fingerprint

def create_license(email: str):
    """
    Request a new license token from the remote server and store it locally.
    Example: POST /licenses/request with {email, hardwareId}.
    """
    hardware_id = get_machine_fingerprint()
    payload = {"email": email, "hardwareId": hardware_id}

    # This is the endpoint on your NestJS server. Adjust if needed.
    url = f"{settings.LICENSE_SERVER_VALIDATE_URL}/licenses/request"

    try:
        # POST the payload (email, hardware) to the server
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()  # Raises HTTPError if response not 200-299
        
        # The server should return JSON with a "licenseKey" or "token" field
        data = response.json()
        if "licenseKey" not in data:
            print("Server did not return a licenseKey field.")
            return False

        return {
            "id": data.get("id")
        }

    except requests.RequestException as e:
        print(f"Error requesting license from {url}: {e}")
        error_message = ""
        status_code = None
        if e.response is not None:
            error_message = e.response.json().get('message')
            status_code = e.response.status_code
        else:
            error_message = str(e)
        raise HTTPException(status_code=status_code, detail=error_message)

async def verify_license(db: AsyncSession, otp: str, license_id: str):
    url = f"{settings.LICENSE_SERVER_VALIDATE_URL}/licenses/verify"
    try:
        # POST the payload (email, hardware) to the server
        payload = { "otp": otp, "license_id": license_id }
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        # The server should return JSON with a "licenseKey" or "token" field
        data = response.json()
        print(data)
        if "licenseKey" not in data:
            print("Server did not return a licenseKey field.")
            return False

        token = data["licenseKey"]
        print(f"Received token from server: {token}")

        # Save token in a file (encrypt in real usage)
        await save_token(db, token)
        print("Token saved locally.")

        # Optionally store in memory
        license_store[token] = {
            "email": data.get('email'),
            "hardware_id": data.get('hardware_id'),
        }
        return True

    except requests.RequestException as e:
        print(f"Error requesting license from {url}: {e}")
        error_message = ""
        status_code = None
        if e.response is not None:
            error_message = e.response.json().get('message')
            status_code = e.response.status_code
        else:
            error_message = str(e)
        raise HTTPException(status_code=status_code, detail=error_message)


async def validate_license(db: AsyncSession) -> bool:
    """
    Check if the locally stored license token is valid:
      - Decodes JWT
      - Checks expiry
      - Verifies hardware ID
    Return True if valid, False otherwise.
    """
    token = await get_token(db)
    if not token:
        print("No token found locally.")
        return False
    
    url = f"{settings.LICENSE_SERVER_VALIDATE_URL}/licenses/validate"
    try:
        payload = {
            "licenseKey": token,
            "hardwareId": get_machine_fingerprint()
        }
        response = requests.post(url, json=payload, timeout=5)
        data = response.json()
        valid = data.get("valid")
        if not valid:
            print(f"Invalid token")
            return False
    except requests.RequestException as e:
        print(f"Unable to validate license from server {url}: {e}")
        
    
    try:
        payload = jwt.get_unverified_claims(token)
        
        # Check hardware ID
        local_hw = get_machine_fingerprint()
        token_hw = payload.get("hardwareId")
        if token_hw != local_hw:
            print(f"Hardware mismatch: token_hw={token_hw}, local_hw={local_hw}")
            return False

        valid = payload.get("hardwareId")

        # Check token expiration (exp claim should be in seconds since epoch)
        exp = payload.get("exp")
        if not exp:
            print("Token does not have an expiration claim.")
            return False

        now_ts = int(time.time())
        if now_ts > exp:
            print(f"Token expired: current time {now_ts} > exp {exp}")
            return False

        print("License is valid locally.")
        return True

    except Exception as e:
        print(f"License token is error. {e}")
        return False

async def validate_license_cron(db: AsyncSession):
    valid = await validate_license(db)
    if not valid:
        logger.warning("License validation failed! Disabling all VC and Webhooks...")

        # try:
        #     await disable_all_vc(db)
        #     logger.info("Successfully disabled all VC configurations.")
        # except Exception as e:
        #     logger.error(f"Failed to disable VC configurations: {e}")

        try:
            await disable_all_webhooks(db)
            logger.info("Successfully disabled all Webhooks.")
        except Exception as e:
            logger.error(f"Failed to disable Webhooks: {e}")

    else:
        logger.info("License validation successful. No action needed.")