import json
from app.modules.secrets.model.secrets_model import Secrets, ScanType
from datetime import datetime
from app.modules.secrets.secret_service import add_secret
from app.utils.mark_severity import mark_severity
from app.utils.clone_repo import get_branches_from_commit
from sqlalchemy.ext.asyncio import AsyncSession


async def store_secrets(
        db: AsyncSession,
        secrets: list,
        repo_id: int,
        scan_type: str,
        pr_id: int = None,
        live_commit_id: int = None,
        pr_scan_id: int = None,
        vc_id: int = None,
        commit: str = None,
        repo_name: str = None,
        live_commit_scan_id: int = None,
        target_dir: str = None,
        author: str = None,
        email: str = None):
    
    print("Storing secrets")
    print("Secret count", len(secrets))
    print("PR scan Id", pr_scan_id)

    secrets_res = []
    secrets_res_new = []

    for secret in secrets:
        try:
            # Determine if it's a PR/commit or repository scan
            if scan_type == "repo_scan":
                print("into repo scan")
                severity = mark_severity(secret.get("RuleID"))
                secret_data = Secrets(
                    description=secret.get("Description"),
                    secret=secret.get("Secret"),
                    file=secret.get("File"),
                    symlink_file=secret.get("SymlinkFile", None),
                    line=f"{secret.get('StartLine', 0)}:{secret.get('EndLine', 0)}",
                    start_line=secret.get("StartLine", 0),
                    end_line=secret.get("EndLine", 0),
                    start_column=secret.get("StartColumn", 0),
                    end_column=secret.get("EndColumn", 0),
                    match=secret.get("Match"),
                    entropy=secret.get("Entropy"),
                    rule=secret.get("RuleID"),
                    fingerprint=secret.get("Fingerprint"),
                    message=secret.get("Message"),
                    commit=secret.get("Commit"),
                    author=secret.get("Author"),
                    email=secret.get("Email"),
                    severity=severity,
                    date=datetime.fromisoformat(secret.get("Date").replace("Z", "")),
                    tags=secret.get("Tags", []),
                    repository_id=repo_id,
                    scan_type=ScanType.REPO_SCAN,
                    live_commit_scan_id=None,
                    vc_id=vc_id
                )
                secret_data.branches = get_branches_from_commit(
                    target_dir, secret_data.commit)

                sec, new = await add_secret(db, secret_data)
                secrets_res.append(sec)
                if new:
                    secrets_res_new.append(sec)

            else:  # PR or commit scan (Trufflehog)
                severity = mark_severity(secret["DetectorName"])
                secret_data = Secrets(
                    description=f"{secret['DetectorName']}:{secret['DecoderName']}",
                    secret=secret['Raw'],
                    file=secret['SourceMetadata']['Data']['Filesystem'].get(
                        'file',
                        None),
                    symlink_file=secret.get(
                        'secUrl',
                        None),
                    match=secret.get(
                        'Raw',
                        None),
                    message=secret['ExtraData'].get(
                        'message',
                            None) if secret['ExtraData'] else None,
                    tags=[
                                secret['ExtraData'].get(
                                    'resource_type',
                                    '')] if secret['ExtraData'] else None,
                    scan_type=ScanType.PR_SCAN if pr_id else ScanType.LIVE_COMMIT,
                    repository_id=repo_id,
                    author=author,
                    email=None,
                    pr_id=pr_id,
                    pr_scan_id=pr_scan_id,
                    live_commit_id=live_commit_id,
                    severity=severity,
                    created_at=datetime.utcnow(),
                    vc_id=vc_id,
                    updated_at=datetime.utcnow(),
                    commit=commit if commit else None,
                    live_commit_scan_id=live_commit_scan_id
                )
                

                # Add secret to database
                try:
                    sec, new = await add_secret(db, secret_data)
                    secrets_res.append(sec)
                    if new:
                        secrets_res_new.append(sec)
                    print("Secret stored successfully")
                except Exception as e:
                    print(f"Error processing secret: {e}")

            
        except Exception as e:
            print(f"Error processing secret: {e}")

    print('Added secrets', len(secrets), len(secrets))
    return secrets_res, secrets_res_new
