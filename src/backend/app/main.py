from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


from app.core.db import Base, get_db
from app.core.config import settings
from app.core.db import engine

from app.modules.user.user_service import create_user, get_user_by_username
from app.modules.user.schemas.user_schema import UserCreate
from app.modules.user.models.user import User
from app.modules.scoring.repository_property_service import RepositoryPropertyService

# Import routers and models
from app.modules.user import user_controller
from app.modules.auth import auth_controller
from app.modules.vc import vc_controller
from app.modules.webhookConfig import webhook_config_controller
from app.modules.repository import respository_controller, repository_scan_worker
from app.modules.secrets import secret_controller
from app.modules.pr import pr_controller
from app.modules.live_commits import live_commits_controller
from app.modules.whitelist import whitelist_controller
from app.modules.incidents import incidents_controller
from app.modules.groups import groups_controller
from app.modules.slack_integration import slack_integration_controller
from app.modules.scoring import scoring_controller, repository_property_controller
from app.modules.scoring.scoring_cron import calculate_score
from app.modules.webhook import webhook_controller
from app.modules.jiraAlerts import jiraAlerts_controller
from app.modules.vulnerability import vulnerability_controller
from app.modules.whitelist.whitelist_service import sca_whitelist_fix_cron
from app.modules.licenses import licenses_controller
from app.modules.licenses.licesses_service import validate_license_cron

from app.utils.error_handling import add_error_middleware

scheduler = AsyncIOScheduler()


async def scan_repositories():
    async for db in get_db():
        worker = repository_scan_worker.RepositoryWorker(db)
        await worker.start_worker()


def start_scheduler():
    scheduler.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)


    async for db in get_db():
        try:
            if isinstance(db, AsyncSession):
                try:
                    admin_user = await get_user_by_username(db, "admin")
                    if not admin_user:
                        admin_user_data = UserCreate(
                            username="admin",
                            password="admin",
                            user_email="admin@firewall.org",
                            role="admin",
                            active=True
                        )
                        await create_user(db, admin_user_data, User())
                except Exception as e:
                    print("Admin user already exists. Skipping creation.")

                await RepositoryPropertyService.init_default_values(db)
                scheduler.add_job(calculate_score, CronTrigger(minute="*/30"), args=[db])
                scheduler.add_job(sca_whitelist_fix_cron, CronTrigger(hour="*/3"), args=[db])
                scheduler.add_job(validate_license_cron, CronTrigger(minute="*/1"), args=[db])
                
                start_scheduler()
            break
        finally:
            await db.close()

    yield  # Yields control back to FastAPI

    await engine.dispose()

app = FastAPI(lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add error handling middleware
add_error_middleware(app)

# # Include routers
app.include_router(user_controller.router)
app.include_router(auth_controller.router)
app.include_router(vc_controller.router)
app.include_router(webhook_config_controller.router)
app.include_router(secret_controller.router)
app.include_router(respository_controller.router)
app.include_router(pr_controller.router)
app.include_router(live_commits_controller.router)
app.include_router(whitelist_controller.router)
app.include_router(incidents_controller.router)
app.include_router(groups_controller.router)
app.include_router(slack_integration_controller.router)
app.include_router(scoring_controller.router)
app.include_router(repository_property_controller.router)
app.include_router(webhook_controller.router)
app.include_router(jiraAlerts_controller.router)
app.include_router(vulnerability_controller.router)
app.include_router(licenses_controller.router)

# Root endpoint
@app.get("/")
async def root():
    return {"status": "200 OK"}

# Health check endpoint
@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        # Check database connection with a lightweight query
        await db.execute(text("SELECT 1"))
        return {"status": "Database connected"}
    except Exception as e:
        return {"status": "Database not connected", "detail": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.RELOAD)  # Set port to 3000
