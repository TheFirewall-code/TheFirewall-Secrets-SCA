from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.core.config import settings
from app.core.db import Base

# Import your models here
from app.modules.user.models.user import User
from app.modules.vc.models.vc import VC
from app.modules.repository.models.repository import Repo
from app.modules.repository.models.repository_scan import RepositoryScan
from app.modules.webhookConfig.models.webhookConfig import WebhookConfig
from app.modules.pr.models.pr import PR
from app.modules.pr.models.pr_scan import PRScan
from app.modules.live_commits.models.live_commits import LiveCommit
from app.modules.live_commits.models.live_commits_scan import LiveCommitScan
from app.modules.secrets.model.secrets_model import Secrets
from app.modules.slack_integration.model.model import SlackIntegration
from app.modules.incidents.models.incident_model import Incidents
from app.modules.incidents.models.activity_model import Activity
from app.modules.incidents.models.comment_model import Comments
from app.modules.scoring.model.model import BusinessCriticality, Environment, DataSensitivity, RegulatoryRequirement
from app.modules.groups.models.group_model import Group
from app.modules.whitelist.model.whitelist_model import Whitelist, WhitelistComment
from app.modules.vulnerability.models.vulnerability_model import Vulnerability
from app.modules.jiraAlerts.models.model import JiraAlert
from app.modules.licenses.licenses_model import License

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def get_url():
    return f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

config.set_main_option("sqlalchemy.url", get_url())


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
