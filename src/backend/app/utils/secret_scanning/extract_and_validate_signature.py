import hmac
import hashlib
from fastapi import HTTPException, Request


def extract_and_validate_signature(
        vc_type: str,
        request: Request,
        payload: bytes,
        secret: str) -> bool:
    # Extract signature based on vc_type
    if vc_type.lower() == "github":
        provided_signature = request.headers.get("X-Hub-Signature-256")
    elif vc_type.lower() == "gitlab":
        provided_signature = request.headers.get("X-Gitlab-Token")
    elif vc_type.lower() == "bitbucket":
        provided_signature = request.headers.get("X-Hub-Signature")
    else:
        raise HTTPException(status_code=400, detail="Unsupported vc_type")

    # Validate the extracted signature
    if vc_type.lower() in ["github", "bitbucket"]:
        # Calculate HMAC signature
        mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
        calculated_signature = f"sha256={mac.hexdigest()}"
        return hmac.compare_digest(calculated_signature, provided_signature)
    elif vc_type.lower() == "gitlab":
        # Directly compare token for GitLab
        return secret == provided_signature
    else:
        raise ValueError(
            "Unsupported platform. Use 'github', 'gitlab', or 'bitbucket'.")
