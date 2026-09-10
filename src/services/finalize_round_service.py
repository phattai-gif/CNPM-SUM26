"""
FinalizeRoundService (SRS Section 3.9.5: Finalize Round and Approve Winners)
Handles round finalization, score locking, winner approval, and notifications.
"""
from typing import Optional, Dict, Any, Tuple
from services.score_service import ScoreService
from services.notification_service import NotificationService


class FinalizeRoundService:
    def __init__(
        self,
        score_service: Optional[ScoreService] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        self.score_service = score_service or ScoreService()
        self.notification_service = notification_service or NotificationService()

    def finalize_round(self, round_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Officially close a judging round:
        1. Verify judging completion and validate round is not already finalized.
        2. Calculate weighted scores and rankings.
        3. Lock round status to FINALIZED.
        4. Return leaderboard results.
        """
        return self.score_service.finalize_round(round_id)

    def get_winner_candidates(self, contest_id: int, round_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Get leaderboard candidates for winner approval."""
        return self.score_service.get_winner_candidates(contest_id, round_id)

    def approve_winner(
        self,
        contest_id: int,
        round_id: int,
        submission_id: int,
        decision: str,
        award_title: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Approve or reject a selected winner candidate, publish to archive,
        and send notification to the author.
        """
        result, error = self.score_service.handle_winner_decision(
            contest_id=contest_id,
            round_id=round_id,
            submission_id=submission_id,
            decision=decision,
            award_title=award_title,
            reason=reason,
        )

        if error or not result:
            return result, error

        # Send notification to winner author if approved
        if decision == "approve" and result.get("submission"):
            submission = result["submission"]
            user_id = submission.get("user_id") or getattr(submission, "user_id", None)
            if user_id:
                try:
                    title_text = award_title or "Contest Winner"
                    self.notification_service.create_notification(
                        user_id=user_id,
                        title=f"🏆 Congratulations! Your submission won {title_text}",
                        body=f"Your submission '{submission.get('title', 'Work')}' has been officially approved as a winner.",
                        contest_id=contest_id,
                        notification_type="winner_announcement",
                    )
                except Exception as notif_err:
                    # Best-effort notification
                    print(f"[FinalizeRoundService] Warning sending winner notification: {notif_err}")

        return result, None
