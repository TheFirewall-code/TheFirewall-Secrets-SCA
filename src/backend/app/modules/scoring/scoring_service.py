from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from app.modules.secrets.model.secrets_model import Secrets
from app.modules.repository.models.repository import Repo
from app.modules.groups.models.group_model import Group
from sqlalchemy import func
from app.modules.vulnerability.models.vulnerability_model import Vulnerability


# Enum for severity scores
SEVERITY_SCORES = {
    "critical": 10,
    "high": 8,
    "medium": 6,
    "low": 4,
    "unknown": 2
}

# SLA durations in days
SLA_DAYS = {
    "critical": 10,
    "high": 15,
    "medium": 30,
    "low": 40,
    "unknown": 60
}


class ScoringService:
    @staticmethod
    def calculate_secret_score(secret, repo) -> float:

        days_open = (datetime.utcnow() - secret.created_at).days

        """Calculate the score for a single secret with weighted risk factors."""
        base_score = SEVERITY_SCORES[secret.severity.value]
        sla = SLA_DAYS[secret.severity.value]

        # Calculate the time decay factor
        time_decay = min(1 + (days_open / sla), 2)  # Capped at 2x

        # Get the risk factor weights from the repo's properties

        # Initialize weights to 0 in case any property is missing
        criticality_weight = repo.criticality.value if repo.criticality else 0
        environment_weight = repo.environment.value if repo.environment else 0
        sensitivity_weight = repo.sensitivity.value if repo.sensitivity else 0
        regulation_weight = repo.regulation.value if repo.regulation else 0

        # Calculate the total risk weight for the repo
        total_weight = (
            0.4 * criticality_weight +
            0.3 * environment_weight +
            0.2 * sensitivity_weight +
            0.1 * regulation_weight
        )

        # Calculate the risk-adjusted score for the secret
        risk_adjusted_score = base_score * time_decay * (1 + total_weight)

        return risk_adjusted_score

    @staticmethod
    def calculate_vulnerability_score(vulnerability, repo) -> float:

        days_open = (datetime.utcnow() - vulnerability.created_at).days

        """Calculate the score for a single secret with weighted risk factors."""
        base_score = SEVERITY_SCORES[vulnerability.severity.lower()]
        sla = SLA_DAYS[vulnerability.severity.lower()]

        # Calculate the time decay factor
        time_decay = min(1 + (days_open / sla), 2)  # Capped at 2x

        # Get the risk factor weights from the repo's properties

        # Initialize weights to 0 in case any property is missing
        criticality_weight = repo.criticality.value if repo.criticality else 0
        environment_weight = repo.environment.value if repo.environment else 0
        sensitivity_weight = repo.sensitivity.value if repo.sensitivity else 0
        regulation_weight = repo.regulation.value if repo.regulation else 0

        # Calculate the total risk weight for the repo
        total_weight = (
                0.4 * criticality_weight +
                0.3 * environment_weight +
                0.2 * sensitivity_weight +
                0.1 * regulation_weight
        )

        # Calculate the risk-adjusted score for the secret
        risk_adjusted_score = base_score * time_decay * (1 + total_weight)

        return risk_adjusted_score

    @staticmethod
    async def calculate_secret_score_by_id(
            db: AsyncSession, secret_id: int) -> float:
        """
        Calculate the score for a specific secret by its ID.
        """
        query = (
            select(Secrets)
            .where(Secrets.id == secret_id)
            .options(
                selectinload(Secrets.repository)
                .selectinload(Repo.criticality),
                selectinload(Secrets.repository)
                .selectinload(Repo.environment),
                selectinload(Secrets.repository)
                .selectinload(Repo.sensitivity),
                selectinload(Secrets.repository)
                .selectinload(Repo.regulation),
            )
        )
        result = await db.execute(query)
        secret = result.scalars().first()

        if not secret:
            raise ValueError(f"Secret with ID {secret_id} not found")

        repo = secret.repository

        # Reuse the `calculate_secret_score` logic
        return ScoringService.calculate_secret_score(secret, repo)

    @staticmethod
    async def calculate_vul_score_by_id(
            db: AsyncSession, vul_id: int) -> float:
        """
        Calculate the score for a specific secret by its ID.
        """
        query = (
            select(Vulnerability)
            .where(Vulnerability.id == vul_id)
            .options(
                selectinload(Vulnerability.repository)
                .selectinload(Repo.criticality),
                selectinload(Vulnerability.repository)
                .selectinload(Repo.environment),
                selectinload(Vulnerability.repository)
                .selectinload(Repo.sensitivity),
                selectinload(Vulnerability.repository)
                .selectinload(Repo.regulation),
            )
        )
        result = await db.execute(query)
        vul = result.scalars().first()

        if not vul:
            raise ValueError(f"Vulnerability with ID {vul_id} not found")

        repo = vul.repository

        # Reuse the `calculate_secret_score` logic
        return ScoringService.calculate_vulnerability_score(vul, repo)

    @staticmethod
    async def calculate_repo_score(db: AsyncSession, repo_id: int) -> float:
        """Calculate the total score for a repo based on all open secrets."""
        # Ensure the repository exists
        repo_query = select(Repo).where(Repo.id == repo_id)
        repo_result = await db.execute(repo_query)
        repo = repo_result.scalars().first()

        if not repo:
            raise ValueError(f"Repository with ID {repo_id} not found")

        # Fetch all secrets for the repository
        secret_query = (
            select(Secrets)
            .where(Secrets.repository_id == repo_id)
            .options(
                selectinload(Secrets.repository)
                .selectinload(Repo.criticality),
                selectinload(Secrets.repository)
                .selectinload(Repo.environment),
                selectinload(Secrets.repository)
                .selectinload(Repo.sensitivity),
                selectinload(Secrets.repository)
                .selectinload(Repo.regulation),
            )
        )
        secret_result = await db.execute(secret_query)
        secrets = secret_result.scalars().all()

        # Fetch all vulnerability for the repository
        vul_query = (
            select(Vulnerability)
            .where(Vulnerability.repository_id == repo_id)
            .options(
                selectinload(Vulnerability.repository)
                .selectinload(Repo.criticality),
                selectinload(Vulnerability.repository)
                .selectinload(Repo.environment),
                selectinload(Vulnerability.repository)
                .selectinload(Repo.sensitivity),
                selectinload(Vulnerability.repository)
                .selectinload(Repo.regulation),
            )
        )
        vul_result = await db.execute(vul_query)
        vulnerabilities = secret_result.scalars().all()

        # Calculate the total score by summing the scores of all secrets
        total_score = 0
        for secret in secrets:
            total_score += ScoringService.calculate_secret_score(secret, repo)
        for vul in vulnerabilities:
            total_score += ScoringService.calculate_vulnerability_score(vul, repo)

        return total_score

    @staticmethod
    async def calculate_repo_score_from_normailzed_secret(
            db: AsyncSession, repo_id: int) -> float:
        """Calculate the average score for a repo based on all open secrets."""
        # Ensure the repository exists
        repo_query = select(Repo).where(Repo.id == repo_id)
        repo_result = await db.execute(repo_query)
        repo = repo_result.scalars().first()

        if not repo:
            raise ValueError(f"Repository with ID {repo_id} not found")

        # Calculate the average score of secrets directly using SQL aggregation
        secret_score_query = (
            select(func.avg(Secrets.score_normalized))
            .where(Secrets.repository_id == repo_id)
        )

        secret_score_result = await db.execute(secret_score_query)
        secret_average_score = secret_score_result.scalar()
        if secret_average_score is None:
            secret_average_score = 0.0


        # Vulnerability
        # Calculate the average score of vulnerability directly using SQL aggregation
        vulnerability_score_query = (
            select(func.avg(Vulnerability.score_normalized))
            .where(Vulnerability.repository_id == repo_id)
        )

        vulnerability_score_result = await db.execute(vulnerability_score_query)
        vulnerability_average_score = vulnerability_score_result.scalar()
        if vulnerability_average_score is None:
            vulnerability_average_score = 0.0

        average_score = 0
        non_zero_scores = [score for score in [secret_average_score, vulnerability_average_score] if score > 0]
        if non_zero_scores:
            average_score = sum(non_zero_scores) / len(non_zero_scores)

        return average_score

    @staticmethod
    async def calculate_group_score(db: AsyncSession, group_id: int) -> float:
        """Calculate the pod (group) score as a weighted average of its repos."""
        query = select(Group).where(
            Group.id == group_id).options(
            selectinload(
                Group.repos))
        result = await db.execute(query)
        group = result.scalars().first()

        if not group:
            raise ValueError(f"Group with ID {group_id} not found")

        # Calculate the score for each repo
        repo_scores = [
            await ScoringService.calculate_repo_score(db, repo.id) for repo in group.repos
        ]

        # Calculate the weighted average pod score
        if len(repo_scores) == 0:
            return 0.0  # Handle empty groups
        pod_score = sum(repo_scores) / len(repo_scores)

        return pod_score

    @staticmethod
    async def calculate_group_score_from_normalized_secret(
            db: AsyncSession, group_id: int) -> float:
        """Calculate the pod (group) score as a weighted average of its repos."""
        query = select(Group).where(
            Group.id == group_id).options(
            selectinload(
                Group.repos))
        result = await db.execute(query)
        group = result.scalars().first()

        if not group:
            raise ValueError(f"Group with ID {group_id} not found")

        # Calculate the score for each repo
        repo_scores = [
            await ScoringService.calculate_repo_score_from_normailzed_secret(db, repo.id) for repo in group.repos
        ]

        # Calculate the weighted average pod score
        if len(repo_scores) == 0:
            return 0.0  # Handle empty groups
        pod_score = sum(repo_scores) / len(repo_scores)

        return pod_score

    @staticmethod
    async def normalize_score(raw_score: float, max_score: float) -> float:
        """Normalize the score to a 0-100 scale."""
        return (raw_score / max_score) * 100 if max_score > 0 else 0.0
