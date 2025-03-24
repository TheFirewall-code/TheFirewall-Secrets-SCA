from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from app.modules.secrets.model.secrets_model import Secrets
from app.modules.repository.models.repository import Repo
from app.modules.groups.models.group_model import Group
from app.modules.scoring.scoring_service import ScoringService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from app.modules.vulnerability.models.vulnerability_model import Vulnerability


async def calculate_score(db: AsyncSession):
    # Step 1: Get all secrets, calculate scores, and normalize them
    # Calculate raw scores for each secret
    secret_query = select(Secrets)
    secret_result = await db.execute(secret_query)
    secrets = secret_result.scalars().all()
    max_score = 1
    for secret in secrets:
        score_raw = await ScoringService.calculate_secret_score_by_id(db, secret.id)
        secret.score_raw = score_raw
        print('Score Raw Secret', score_raw)
        if score_raw > max_score:
            max_score = score_raw
        db.add(secret)

    await db.commit()

    # Maintain max score and normalize scores for secrets
    for secret in secrets:
        score_normalized = await ScoringService.normalize_score(secret.score_raw, max_score)
        secret.score_normalized = score_normalized
        secret.score_normalized_on = datetime.utcnow()  # Update score_normalized_on
        db.add(secret)

    await db.commit()

    # Calculate raw scores for each vulnerability
    vulnerability_query = select(Vulnerability)
    vulnerability_result = await db.execute(vulnerability_query)
    vulnerabilities = vulnerability_result.scalars().all()
    max_score = 1
    for vulnerability in vulnerabilities:
        score_raw = await ScoringService.calculate_vul_score_by_id(db, vulnerability.id)
        vulnerability.score_raw = score_raw
        print('Score Raw Vul', score_raw)
        if score_raw > max_score:
            max_score = score_raw
        db.add(vulnerability)

    await db.commit()

    # Maintain max score and normalize scores for vulnerabilities
    for vulnerability in vulnerabilities:
        score_normalized = await ScoringService.normalize_score(vulnerability.score_raw, max_score)
        vulnerability.score_normalized = score_normalized
        vulnerability.score_normalized_on = datetime.utcnow()  # Update score_normalized_on
        db.add(secret)

    await db.commit()

    # Step 2: Get all repositories and update their scores
    repo_query = select(Repo)
    repo_result = await db.execute(repo_query)
    repos = repo_result.scalars().all()

    for repo in repos:
        normalized_repo_score = await ScoringService.calculate_repo_score_from_normailzed_secret(db, repo.id)
        repo.score_normalized = normalized_repo_score
        repo.score_normalized_on = datetime.utcnow()  # Update score_normalized_on
        db.add(repo)

    await db.commit()

    # Step 3: Get all groups and update their scores
    group_query = select(Group)
    group_result = await db.execute(group_query)
    groups = group_result.scalars().all()

    for group in groups:
        normalized_group_score = await ScoringService.calculate_group_score_from_normalized_secret(db, group.id)
        group.score_normalized = normalized_group_score
        group.score_normalized_on = datetime.utcnow()  # Update score_normalized_on
        db.add(group)

    await db.commit()

    return True
