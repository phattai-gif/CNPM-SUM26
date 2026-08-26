from dotenv import load_dotenv

load_dotenv()
import logging
import os

from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from infrastructure.repositories.contest_repository import (
    ContestRepository,
)


logger = logging.getLogger("app_logger")


class SchedulerService:
    """
    Automatic scheduler for Contest and Round status transitions.

    Contest:
        upcoming -> ongoing
        ongoing  -> ended

    Round:
        upcoming -> ongoing
        ongoing  -> grading

    The scheduler runs periodically using APScheduler.
    """

    _instance = None

    def __init__(
        self,
        repository: Optional[ContestRepository] = None,
    ):
        self.repository = (
            repository
            or ContestRepository()
        )

        self.scheduler: Optional[
            BackgroundScheduler
        ] = None

        self.is_running = False

        self.app = None

    # =========================================================
    # SINGLETON
    # =========================================================

    @classmethod
    def get_instance(
        cls,
        repository: Optional[ContestRepository] = None,
    ):
        """
        Return the singleton SchedulerService instance.
        """

        if cls._instance is None:
            cls._instance = cls(
                repository=repository
            )

        elif repository is not None:
            cls._instance.repository = repository

        return cls._instance

    # =========================================================
    # DATETIME HELPERS
    # =========================================================

    @staticmethod
    def _to_utc_datetime(
        value,
    ) -> Optional[datetime]:
        """
        Convert a datetime/string into a timezone-aware UTC datetime.

        Handles:
        - timezone-aware datetime
        - timezone-naive datetime
        - ISO datetime string
        """

        if value is None:
            return None

        # -----------------------------------------------------
        # Convert string
        # -----------------------------------------------------

        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(
                    value
                )
            except (TypeError, ValueError):
                return None

        if not isinstance(
            value,
            datetime,
        ):
            return None

        # -----------------------------------------------------
        # Naive datetime
        #
        # Project should preferably store UTC timestamps.
        # For legacy naive timestamps, treat them as UTC.
        # -----------------------------------------------------

        if value.tzinfo is None:
            value = value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )

    @classmethod
    def _is_due(
        cls,
        target_datetime,
        now: datetime,
    ) -> bool:
        """
        Return True when target_datetime <= now.
        """

        target = cls._to_utc_datetime(
            target_datetime
        )

        if target is None:
            return False

        return target <= now

    # =========================================================
    # LOGGING
    # =========================================================

    def _log_info(
        self,
        message: str,
    ):
        """
        Log through Flask app logger when available.
        """

        if self.app is not None:
            self.app.logger.info(
                message
            )

        logger.info(message)

    def _log_error(
        self,
        message: str,
        exc_info: bool = False,
    ):
        """
        Log scheduler errors.
        """

        if self.app is not None:
            self.app.logger.error(
                message,
                exc_info=exc_info,
            )

        logger.error(
            message,
            exc_info=exc_info,
        )

    # =========================================================
    # CONTEST STATUS UPDATE
    # =========================================================

    def _update_contest_statuses(
        self,
        now: datetime,
    ):
        """
        Update Contest statuses.

        upcoming -> ongoing
        ongoing  -> ended
        """

        # -----------------------------------------------------
        # upcoming -> ongoing / ended
        # -----------------------------------------------------

        try:
            contests = (
                self.repository
                .get_contests_by_status(
                    "upcoming"
                )
            )

            for contest in contests:
                try:
                    if not self._is_due(
                        contest.start_date,
                        now,
                    ):
                        continue

                    # First transition
                    self.repository.update_contest_status(
                        contest.id,
                        "ongoing",
                    )

                    self._log_info(
                        "Auto Scheduler: "
                        f"Contest {contest.id} "
                        "changed from upcoming to ongoing."
                    )

                    # -------------------------------------------------
                    # Handle contest whose end_date has also passed.
                    # This prevents it from remaining ongoing for
                    # another scheduler cycle.
                    # -------------------------------------------------

                    if self._is_due(
                        contest.end_date,
                        now,
                    ):
                        self.repository.update_contest_status(
                            contest.id,
                            "ended",
                        )

                        self._log_info(
                            "Auto Scheduler: "
                            f"Contest {contest.id} "
                            "changed from ongoing to ended."
                        )

                except Exception as error:
                    self._log_error(
                        "Auto Scheduler: failed to "
                        f"process Contest {contest.id}: "
                        f"{error}",
                        exc_info=True,
                    )

        except Exception as error:
            self._log_error(
                "Auto Scheduler: failed to fetch "
                f"upcoming contests: {error}",
                exc_info=True,
            )

        # -----------------------------------------------------
        # ongoing -> ended
        # -----------------------------------------------------

        try:
            contests = (
                self.repository
                .get_contests_by_status(
                    "ongoing"
                )
            )

            for contest in contests:
                try:
                    if not self._is_due(
                        contest.end_date,
                        now,
                    ):
                        continue

                    self.repository.update_contest_status(
                        contest.id,
                        "ended",
                    )

                    self._log_info(
                        "Auto Scheduler: "
                        f"Contest {contest.id} "
                        "changed from ongoing to ended."
                    )

                except Exception as error:
                    self._log_error(
                        "Auto Scheduler: failed to "
                        f"process Contest {contest.id} "
                        f"(ongoing -> ended): {error}",
                        exc_info=True,
                    )

        except Exception as error:
            self._log_error(
                "Auto Scheduler: failed to fetch "
                f"ongoing contests: {error}",
                exc_info=True,
            )

    # =========================================================
    # ROUND STATUS UPDATE
    # =========================================================

    def _update_round_statuses(
        self,
        now: datetime,
    ):
        """
        Update Round statuses.

        upcoming -> ongoing
        ongoing  -> grading
        """

        # -----------------------------------------------------
        # upcoming -> ongoing / grading
        # -----------------------------------------------------

        try:
            rounds = (
                self.repository
                .get_rounds_by_status(
                    "upcoming"
                )
            )

            for round_obj in rounds:
                try:
                    if not self._is_due(
                        round_obj.start_date,
                        now,
                    ):
                        continue

                    self.repository.update_round_status(
                        round_obj.id,
                        "ongoing",
                    )

                    self._log_info(
                        "Auto Scheduler: "
                        f"Round {round_obj.id} "
                        "changed from upcoming to ongoing."
                    )

                    # -------------------------------------------------
                    # If end_date has already passed, move directly
                    # to grading.
                    # -------------------------------------------------

                    if self._is_due(
                        round_obj.end_date,
                        now,
                    ):
                        self.repository.update_round_status(
                            round_obj.id,
                            "grading",
                        )

                        self._log_info(
                            "Auto Scheduler: "
                            f"Round {round_obj.id} "
                            "changed from ongoing to grading."
                        )

                except Exception as error:
                    self._log_error(
                        "Auto Scheduler: failed to "
                        f"process Round {round_obj.id}: "
                        f"{error}",
                        exc_info=True,
                    )

        except Exception as error:
            self._log_error(
                "Auto Scheduler: failed to fetch "
                f"upcoming rounds: {error}",
                exc_info=True,
            )

        # -----------------------------------------------------
        # ongoing -> grading
        # -----------------------------------------------------

        try:
            rounds = (
                self.repository
                .get_rounds_by_status(
                    "ongoing"
                )
            )

            for round_obj in rounds:
                try:
                    if not self._is_due(
                        round_obj.end_date,
                        now,
                    ):
                        continue

                    self.repository.update_round_status(
                        round_obj.id,
                        "grading",
                    )

                    self._log_info(
                        "Auto Scheduler: "
                        f"Round {round_obj.id} "
                        "changed from ongoing to grading."
                    )

                except Exception as error:
                    self._log_error(
                        "Auto Scheduler: failed to "
                        f"process Round {round_obj.id} "
                        f"(ongoing -> grading): {error}",
                        exc_info=True,
                    )

        except Exception as error:
            self._log_error(
                "Auto Scheduler: failed to fetch "
                f"ongoing rounds: {error}",
                exc_info=True,
            )

    # =========================================================
    # MAIN JOB
    # =========================================================

    def check_and_update_statuses(
        self,
    ):
        """
        Main scheduler job.

        This method is executed every 30 seconds.
        """

        now = datetime.now(
            timezone.utc
        )

        self._log_info(
            "Auto Scheduler: checking "
            "Contest and Round statuses..."
        )

        # -----------------------------------------------------
        # Contest
        # -----------------------------------------------------

        self._update_contest_statuses(
            now
        )

        # -----------------------------------------------------
        # Round
        # -----------------------------------------------------

        self._update_round_statuses(
            now
        )

        self._log_info(
            "Auto Scheduler: status check completed."
        )

    # =========================================================
    # JOB WRAPPER
    # =========================================================

    def _run_job(
        self,
    ):
        """
        Execute scheduler job inside Flask application context.
        """

        if self.app is None:
            self.check_and_update_statuses()
            return

        with self.app.app_context():
            try:
                self.check_and_update_statuses()

            except Exception as error:
                self._log_error(
                    "Auto Scheduler job failed: "
                    f"{error}",
                    exc_info=True,
                )

    # =========================================================
    # INITIALIZE APSCHEDULER
    # =========================================================

    def init_app(
        self,
        app,
    ):
        """
        Initialize APScheduler for Flask.

        The scheduler:
        - runs every 30 seconds
        - does not run during pytest
        - prevents overlapping jobs
        - coalesces missed executions
        """

        self.app = app

        # -----------------------------------------------------
        # Prevent scheduler from starting during tests
        # -----------------------------------------------------

        is_testing = (
            app.config.get(
                "TESTING",
                False,
            )
            or os.environ.get(
                "PYTEST_CURRENT_TEST"
            ) is not None
        )

        if is_testing:
            self._log_info(
                "Auto Scheduler disabled "
                "because application is running in testing mode."
            )
            return

        # -----------------------------------------------------
        # Prevent duplicate scheduler
        # -----------------------------------------------------

        if (
            self.scheduler is not None
            and self.scheduler.running
        ):
            self._log_info(
                "Auto Scheduler is already running."
            )
            return

        # -----------------------------------------------------
        # Create scheduler
        # -----------------------------------------------------

        self.scheduler = BackgroundScheduler(
            timezone="Asia/Ho_Chi_Minh"
        )

        self.scheduler.add_job(
            func=self._run_job,
            trigger="interval",
            seconds=30,
            id="contest_round_auto_scheduler",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        self.start()

    # =========================================================
    # START
    # =========================================================

    def start(self):
        """
        Start APScheduler.
        """

        if self.scheduler is None:
            return

        if self.scheduler.running:
            self.is_running = True
            return

        self.scheduler.start()

        self.is_running = True

        self._log_info(
            "Contest/Round Auto Scheduler started successfully."
        )

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):
        """
        Stop APScheduler safely.
        """

        if (
            self.scheduler is None
            or not self.scheduler.running
        ):
            self.is_running = False
            return

        try:
            self.scheduler.shutdown(
                wait=False
            )

        except Exception as error:
            self._log_error(
                "Auto Scheduler shutdown failed: "
                f"{error}",
                exc_info=True,
            )

        finally:
            self.is_running = False

            self._log_info(
                "Contest/Round Auto Scheduler stopped."
            )


# =============================================================
# GLOBAL SERVICE INSTANCE
# =============================================================

scheduler_service = (
    SchedulerService.get_instance()
)
