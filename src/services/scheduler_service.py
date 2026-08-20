import logging
from datetime import datetime, timezone
from typing import Optional

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    BackgroundScheduler = None

from infrastructure.repositories.contest_repository import ContestRepository

logger = logging.getLogger("app_logger")


def _is_past_or_present(target_dt: Optional[datetime], now_dt: datetime) -> bool:
    """Safely compare datetime objects handling naive, aware, and string datetimes."""
    if target_dt is None:
        return False
    if isinstance(target_dt, str):
        try:
            target_dt = datetime.fromisoformat(target_dt)
        except Exception:
            return False
    if target_dt.tzinfo is not None and now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    elif target_dt.tzinfo is None and now_dt.tzinfo is not None:
        target_dt = target_dt.replace(tzinfo=timezone.utc)
    return target_dt <= now_dt


class SchedulerService:
    _instance = None

    def __init__(self, repository: Optional[ContestRepository] = None):
        self.repository = repository or ContestRepository()
        self.scheduler: Optional[BackgroundScheduler] = None
        self.is_running = False

    @classmethod
    def get_instance(cls, repository: Optional[ContestRepository] = None):
        if cls._instance is None:
            cls._instance = cls(repository=repository)
        return cls._instance

    def check_and_update_statuses(self):
        """Job running periodically to auto-transition Contest and Round statuses."""
        now = datetime.now(timezone.utc)

        # ---------------------------------------------------------------------
        # 1. Contests: upcoming -> ongoing
        # ---------------------------------------------------------------------
        try:
            upcoming_contests = self.repository.get_contests_by_status('upcoming')
            for contest in upcoming_contests:
                try:
                    if contest.start_date and _is_past_or_present(contest.start_date, now):
                        self.repository.update_contest_status(contest.id, 'ongoing')
                        logger.info(f"Auto scheduler changed Contest {contest.id}: upcoming -> ongoing")
                except Exception as e:
                    logger.error(f"Error processing Contest {contest.id} (upcoming -> ongoing): {e}")
        except Exception as e:
            logger.error(f"Error fetching upcoming contests: {e}")

        # ---------------------------------------------------------------------
        # 2. Contests: ongoing -> ended
        # ---------------------------------------------------------------------
        try:
            ongoing_contests = self.repository.get_contests_by_status('ongoing')
            for contest in ongoing_contests:
                try:
                    if contest.end_date and _is_past_or_present(contest.end_date, now):
                        self.repository.update_contest_status(contest.id, 'ended')
                        logger.info(f"Auto scheduler changed Contest {contest.id}: ongoing -> ended")
                except Exception as e:
                    logger.error(f"Error processing Contest {contest.id} (ongoing -> ended): {e}")
        except Exception as e:
            logger.error(f"Error fetching ongoing contests: {e}")

        # ---------------------------------------------------------------------
        # 3. Rounds: upcoming -> ongoing
        # ---------------------------------------------------------------------
        try:
            upcoming_rounds = self.repository.get_rounds_by_status('upcoming')
            for round_obj in upcoming_rounds:
                try:
                    if round_obj.start_date and _is_past_or_present(round_obj.start_date, now):
                        self.repository.update_round_status(round_obj.id, 'ongoing')
                        logger.info(f"Auto scheduler changed Round {round_obj.id}: upcoming -> ongoing")
                except Exception as e:
                    logger.error(f"Error processing Round {round_obj.id} (upcoming -> ongoing): {e}")
        except Exception as e:
            logger.error(f"Error fetching upcoming rounds: {e}")

        # ---------------------------------------------------------------------
        # 4. Rounds: ongoing -> grading
        # ---------------------------------------------------------------------
        try:
            ongoing_rounds = self.repository.get_rounds_by_status('ongoing')
            for round_obj in ongoing_rounds:
                try:
                    if round_obj.end_date and _is_past_or_present(round_obj.end_date, now):
                        self.repository.update_round_status(round_obj.id, 'grading')
                        logger.info(f"Auto scheduler changed Round {round_obj.id}: ongoing -> grading")
                except Exception as e:
                    logger.error(f"Error processing Round {round_obj.id} (ongoing -> grading): {e}")
        except Exception as e:
            logger.error(f"Error fetching ongoing rounds: {e}")

    def init_app(self, app):
        """Initialize APScheduler with Flask application."""
        if BackgroundScheduler is None:
            logger.warning("APScheduler is not installed. Auto Scheduler disabled.")
            return

        if self.is_running or (self.scheduler and self.scheduler.running):
            return

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            func=self.check_and_update_statuses,
            trigger='interval',
            seconds=30,
            id='contest_round_auto_scheduler',
            replace_existing=True
        )

        # Do not start automatically if running in testing mode unless requested
        import os
        is_testing = app.config.get('TESTING', False) or os.environ.get('PYTEST_CURRENT_TEST') is not None
        if not is_testing:
            self.start()

    def start(self):
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            self.is_running = True
            logger.info("Auto Scheduler started successfully.")

    def stop(self):
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Auto Scheduler stopped.")


scheduler_service = SchedulerService.get_instance()
