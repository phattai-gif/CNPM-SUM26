from collections import defaultdict
import sys
from typing import Optional

try:
    from infrastructure.models.app import SubmissionModel
    from infrastructure.repositories.score_repository import ScoreRepository
    from infrastructure.repositories.score_feedback_repository import (
        ScoreFeedbackRepository,
    )
    from infrastructure.repositories.submission_repository import (
        SubmissionRepository,
    )
    from infrastructure.repositories.contest_repository import (
        ContestRepository,
    )
except ImportError:
    from infrastructure.models.app import SubmissionModel
    from infrastructure.repositories.score_repository import ScoreRepository
    from infrastructure.repositories.score_feedback_repository import (
        ScoreFeedbackRepository,
    )
    from infrastructure.repositories.submission_repository import (
        SubmissionRepository,
    )
    from infrastructure.repositories.contest_repository import (
        ContestRepository,
    )


class ScoreService:
    def __init__(
        self,
        score_repo: Optional[ScoreRepository] = None,
        feedback_repo: Optional[ScoreFeedbackRepository] = None,
        submission_repo: Optional[SubmissionRepository] = None,
        contest_repo: Optional[ContestRepository] = None,
    ):
        self.score_repo = score_repo or ScoreRepository()
        self.feedback_repo = feedback_repo or ScoreFeedbackRepository()
        self.submission_repo = (
            submission_repo or SubmissionRepository()
        )
        self.contest_repo = contest_repo or ContestRepository()

    def validate_score(
        self,
        criteria_id: int,
        score_value,
    ) -> bool:
        criteria = self.contest_repo.get_criteria_by_id(criteria_id)

        if criteria is None:
            return False

        try:
            score = float(score_value)
            max_score = float(criteria.max_score)
        except (TypeError, ValueError):
            return False

        return 0 <= score <= max_score

    def submit_score(
        self,
        submission_id: int,
        judge_id: int,
        criteria_id: int,
        score_value,
        comment: Optional[str] = None,
    ):
        submission = self.submission_repo.get_by_id(submission_id)

        if submission is None:
            return None, "submission_not_found"

        criteria = self.contest_repo.get_criteria_by_id(criteria_id)

        if criteria is None:
            return None, "criteria_not_found"

        try:
            score = float(score_value)
            max_score = float(criteria.max_score)
        except (TypeError, ValueError):
            return None, "invalid_score"

        if not 0 <= score <= max_score:
            return None, "invalid_score"

        model = self.score_repo.create_or_update(
            submission_id=submission_id,
            judge_id=judge_id,
            criteria_id=criteria_id,
            score_value=score,
            comment=comment,
        )

        self._recalculate_final_score(submission)

        return model, None

    def _recalculate_final_score(
        self,
        submission: SubmissionModel,
    ) -> None:
        scores = self.score_repo.list_by_submission(submission.id)

        if not scores:
            submission.final_score = None
            self.submission_repo.update(submission)
            return

        judge_scores = defaultdict(list)

        for score in scores:
            criteria = self.contest_repo.get_criteria_by_id(
                score.criteria_id
            )

            if criteria is None:
                continue

            try:
                weight = float(criteria.weight or 0)
                score_value = float(score.score_value)
            except (TypeError, ValueError):
                continue

            if weight <= 0:
                continue

            judge_scores[score.judge_id].append(
                (score_value, weight)
            )

        judge_averages = [
            self._calculate_weighted_average(values)
            for values in judge_scores.values()
        ]

        judge_averages = [
            value
            for value in judge_averages
            if value is not None
        ]

        if judge_averages:
            submission.final_score = (
                sum(judge_averages) / len(judge_averages)
            )
        else:
            submission.final_score = None

        self.submission_repo.update(submission)

    @staticmethod
    def _calculate_weighted_average(values):
        if not values:
            return None

        total_weight = sum(
            weight for _, weight in values
        )

        if total_weight <= 0:
            return None

        weighted_total = sum(
            score * weight
            for score, weight in values
        )

        return weighted_total / total_weight

    def finalize_round(self, round_id: int):
        """
        Chá»‘t Ä‘iá»ƒm vÃ²ng thi.

        Quy trÃ¬nh:
        1. Kiá»ƒm tra vÃ²ng thi tá»“n táº¡i.
        2. Kiá»ƒm tra vÃ²ng Ä‘Ã£ FINALIZED chÆ°a.
        3. Láº¥y tiÃªu chÃ­ cá»§a vÃ²ng.
        4. Láº¥y submission thuá»™c vÃ²ng.
        5. TÃ­nh tá»•ng Ä‘iá»ƒm cho tá»«ng submission.
        6. Xáº¿p háº¡ng tá»« cao xuá»‘ng tháº¥p.
        7. NgÆ°á»i cÃ³ cÃ¹ng Ä‘iá»ƒm sáº½ cÃ¹ng háº¡ng.
        8. LÆ°u final_score cho submission.
        9. Cáº­p nháº­t tráº¡ng thÃ¡i vÃ²ng thÃ nh FINALIZED.
        10. Tráº£ káº¿t quáº£ Ä‘á»ƒ há»‡ thá»‘ng cÃ´ng bá»‘.
        """

        round_obj = self.contest_repo.get_round_by_id(round_id)

        if round_obj is None:
            return None, "round_not_found"

        status = getattr(round_obj, "status", None)

        if status is not None:
            status_value = getattr(
                status,
                "value",
                status
            )

            if str(status_value).upper() == "FINALIZED":
                return None, "round_already_finalized"

        criteria_list = (
            self.contest_repo.get_criteria_by_round_id(
                round_id
            )
            or []
        )

        criteria_map = {
            criterion.id: criterion
            for criterion in criteria_list
        }

        try:
            all_submissions = self.submission_repo.list()
        except TypeError:
            try:
                all_submissions = self.submission_repo.list(
                    round_id=round_id
                )
            except TypeError:
                all_submissions = []

        submissions = [
            submission
            for submission in (all_submissions or [])
            if getattr(submission, "round_id", None) == round_id
        ]

        results = []

        for submission in submissions:
            scores = self.score_repo.list_by_submission(
                submission.id
            ) or []

            weighted_values = []

            for score in scores:
                criteria = criteria_map.get(
                    score.criteria_id
                )

                if criteria is None:
                    continue

                try:
                    weight = float(
                        criteria.weight or 0
                    )

                    score_value = float(
                        score.score_value
                    )
                except (TypeError, ValueError):
                    continue

                if weight <= 0:
                    continue

                weighted_values.append(
                    (
                        score_value,
                        weight,
                    )
                )

            total_score = self._calculate_weighted_average(
                weighted_values
            )

            if total_score is None:
                total_score = 0.0

            total_score = round(total_score, 2)

            submission.final_score = total_score

            results.append(
                {
                    "user_id": submission.user_id,
                    "submission_id": submission.id,
                    "total_score": total_score,
                }
            )

        results.sort(
            key=lambda item: item["total_score"],
            reverse=True
        )

        previous_score = None
        current_rank = 0

        for index, result in enumerate(
            results,
            start=1
        ):
            current_score = result["total_score"]

            if (
                previous_score is None
                or current_score != previous_score
            ):
                current_rank = index

            result["rank"] = current_rank

            previous_score = current_score

        for submission in submissions:
            self.submission_repo.update(submission)

        self.contest_repo.update_round(
            round_id,
            {
                "status": "FINALIZED"
            }
        )

        return {
            "message": "Round finalized successfully",
            "round_id": round_id,
            "status": "FINALIZED",
            "results": results,
        }, None


    def submit_feedback(
        self,
        submission_id: int,
        judge_id: int,
        summary_feedback: str,
        final_recommendation: Optional[str] = None,
    ):
        submission = self.submission_repo.get_by_id(
            submission_id
        )

        if submission is None:
            return None, "submission_not_found"

        model = self.feedback_repo.create_or_update(
            submission_id=submission_id,
            judge_id=judge_id,
            summary_feedback=summary_feedback,
            final_recommendation=final_recommendation,
        )

        return model, None

    

    def _get_ordered_submissions(
        self,
        submission_id: int,
    ):
        submission = self.submission_repo.get_by_id(
            submission_id
        )

        if submission is None:
            return None, None, "submission_not_found"

        try:
            submissions = (
                self.submission_repo.session
                .query(SubmissionModel)
                .filter_by(
                    round_id=submission.round_id
                )
                .order_by(
                    SubmissionModel.id.asc()
                )
                .all()
            )
        except Exception:
            return None, None, "db_error"

        return submission, submissions, None

    @staticmethod
    def _serialize_submission(
        submission: SubmissionModel,
    ):
        return {
            "id": submission.id,
            "round_id": submission.round_id,
            "user_id": submission.user_id,
            "title": submission.title,
            "story_description": (
                submission.story_description
            ),
            "status": submission.status,
            "final_score": (
                float(submission.final_score)
                if submission.final_score is not None
                else None
            ),
        }

    def get_next_submission(
        self,
        submission_id: int,
    ):
        return self._get_adjacent_submission(
            submission_id,
            direction=1,
        )

    def get_previous_submission(
        self,
        submission_id: int,
    ):
        return self._get_adjacent_submission(
            submission_id,
            direction=-1,
        )

    def get_next_previous(self, submission_id: int):
        submission, submissions, error = self._get_ordered_submissions(
            submission_id
        )
        if error:
            return None, error

        current_index = next(
            (
                index
                for index, item in enumerate(submissions)
                if item.id == submission_id
            ),
            None,
        )
        if current_index is None:
            return None, "submission_not_found"

        return {
            "previous": (
                submissions[current_index - 1].id
                if current_index > 0
                else None
            ),
            "next": (
                submissions[current_index + 1].id
                if current_index < len(submissions) - 1
                else None
            ),
        }, None

    def _get_adjacent_submission(
        self,
        submission_id: int,
        direction: int,
    ):
        submission, submissions, err = (
            self._get_ordered_submissions(
                submission_id
            )
        )

        if err:
            return None, err

        current_index = next(
            (
                index
                for index, item in enumerate(submissions)
                if item.id == submission_id
            ),
            None,
        )

        if current_index is None:
            return None, "submission_not_found"

        target_index = current_index + direction

        if (
            target_index < 0
            or target_index >= len(submissions)
        ):
            return None, None

        return (
            self._serialize_submission(
                submissions[target_index]
            ),
            None,
        )


    sys.modules.setdefault("src.services.score_service", sys.modules[__name__])

