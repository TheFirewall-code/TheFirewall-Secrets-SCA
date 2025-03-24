import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.modules.repository.models.repository_scan import ScanStatusEnum
from app.core.logger import logger
from app.modules.repository.repository_service import *
from app.modules.repository.models.repository_scan import RepositoryScan


class RepositoryWorker:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.running = False

    async def scan_pending_repos(self):
        try:
            logger.info("Starting pending repo scans")

            if self.running:
                logger.info("Worker already running, skipping")
                return  # Return early if already running

            self.running = True
            
            # Fetch pending repository scans
            pending_scans = await self.db.execute(
                select(RepositoryScan).filter(RepositoryScan.status.in_([ScanStatusEnum.PENDING])).limit(250)
            )
            pending_repos = pending_scans.scalars().all()

            if not pending_repos:
                logger.info("No pending repository scans found.")
                self.running = False
                return

            logger.info(f"Starting scan for {len(pending_repos)} repositories.")

            # Start scanning each pending repository
            for scan in pending_repos:
                try:
                    logger.info(f"Starting scan for repository {scan.repository_id}")
                    await scan_repo_by_id(self.db, scan.repository_id)
                except Exception as e:
                    logger.error(f"Failed to scan repository {scan.repository_id}: {e}")

            self.running = False

        except Exception as e:
            self.running = False
            logger.error(f"An error occurred while scanning pending repositories: {e}")

    async def start_worker(self):
        await self.scan_pending_repos()
