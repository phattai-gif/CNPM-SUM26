from collections import defaultdict
import sys
from typing import Optional

try:
    from infrastructure.models.app import SubmissionModel
    from infrastructure.models.app import SubmissionFileModel
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
    from infrastructure.models.app import SubmissionFileModel
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

    def _get_review_lock_state(
        self,
        submission_id: int,
        judge_id: int,
    ):
        submission = self.submission_repo.get_by_id(submission_id)

        if submission is None:
            return {
                "is_locked": False,
                "lock_reason": None,
                "feedback_finalized": False,
                "round_finalized": False,
                "round_status": None,
            }

        round_obj = self.contest_repo.get_round_by_id(
            submission.round_id
        )
        round_status = (
            getattr(round_obj, "status", None)
            if round_obj is not None
            else None
        )
        round_finalized = (
            str(round_status).upper() == "FINALIZED"
            if round_status is not None
            else False
        )

        feedback = self.feedback_repo.get_by_submission_judge(
            submission_id=submission_id,
            judge_id=judge_id,
        )
        feedback_finalized = bool(
            getattr(feedback, "is_finalized", False)
        )

        lock_reason = None
        if round_finalized:
            lock_reason = "round_finalized"
        elif feedback_finalized:
            lock_reason = "feedback_finalized"

        return {
            "is_locked": bool(round_finalized or feedback_finalized),
            "lock_reason": lock_reason,
            "feedback_finalized": feedback_finalized,
            "round_finalized": round_finalized,
            "round_status": round_status,
        }

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

        lock_state = self._get_review_lock_state(
            submission_id=submission_id,
            judge_id=judge_id,
        )
        if lock_state["is_locked"]:
            return None, lock_state["lock_reason"]

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

    def get_winner_candidates(self, contest_id: int, round_id: int):
        """Return leaderboard rows from the finalized score data for organizer approval."""
        contest = self.contest_repo.get_contest_by_id(contest_id)
        round_obj = self.contest_repo.get_round_by_id(round_id)

        if contest is None:
            return None, "contest_not_found"

        if round_obj is None:
            return None, "round_not_found"

        if getattr(round_obj, "contest_id", None) != contest_id:
            return None, "round_not_in_contest"

        session = getattr(self.submission_repo, "session", None) or getattr(self.contest_repo, "session", None)
        if session is None:
            return None, "database_unavailable"

        from infrastructure.models.app import SubmissionModel, UserModel, SubmissionFileModel

        rows = (
            session.query(SubmissionModel, UserModel, SubmissionFileModel)
            .join(UserModel, SubmissionModel.user_id == UserModel.id)
            .outerjoin(SubmissionFileModel, SubmissionFileModel.submission_id == SubmissionModel.id)
            .filter(SubmissionModel.round_id == round_id)
            .filter(SubmissionModel.status != "draft")
            .all()
        )

        candidates = []
        for submission, user, submission_file in rows:
            final_score = float(submission.final_score) if submission.final_score is not None else 0.0
            image_url = None
            if submission_file is not None:
                image_url = getattr(submission_file, "thumbnail_url", None) or getattr(submission_file, "image_hd_url", None)

            candidates.append({
                "submission_id": submission.id,
                "user_id": submission.user_id,
                "title": submission.title,
                "author_name": getattr(user, "full_name", None) or getattr(user, "username", None) or "Anonymous",
                "final_score": round(final_score, 2),
                "status": submission.status,
                "image_url": image_url,
                "submitted_at": submission.submitted_at,
            })

        candidates.sort(key=lambda item: (-float(item["final_score"]), int(item["submission_id"])))

        previous_score = None
        current_rank = 0
        for index, candidate in enumerate(candidates, start=1):
            current_score = float(candidate["final_score"])
            if previous_score is None or current_score != previous_score:
                current_rank = index
            candidate["rank"] = current_rank
            previous_score = current_score

        return {
            "success": True,
            "contest_id": contest_id,
            "round_id": round_id,
            "winner_candidates": candidates,
            "leaderboard": candidates,
        }, None

    def handle_winner_decision(
        self,
        contest_id: int,
        round_id: int,
        submission_id: int,
        decision: str,
        award_title: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        """Approve or reject a selected winner candidate and publish to archive when approved."""
        if decision not in {"approve", "reject"}:
            return None, "invalid_decision"

        contest = self.contest_repo.get_contest_by_id(contest_id)
        round_obj = self.contest_repo.get_round_by_id(round_id)
        if contest is None:
            return None, "contest_not_found"
        if round_obj is None:
            return None, "round_not_found"
        if getattr(round_obj, "contest_id", None) != contest_id:
            return None, "round_not_in_contest"

        submission = self.submission_repo.get_by_id(submission_id)
        if submission is None:
            return None, "submission_not_found"
        if getattr(submission, "round_id", None) != round_id:
            return None, "submission_not_in_round"

        session = getattr(self.submission_repo, "session", None) or getattr(self.contest_repo, "session", None)
        if session is None:
            return None, "database_unavailable"

        from infrastructure.models.app import DigitalArchiveExhibitModel

        if decision == "approve":
            submission.status = "winner"
            self.submission_repo.update(submission)

            archive = (
                session.query(DigitalArchiveExhibitModel)
                .filter_by(contest_id=contest_id, submission_id=submission_id)
                .first()
            )

            final_award_title = (award_title or reason or "Winner").strip() or "Winner"
            if archive is None:
                archive = DigitalArchiveExhibitModel(
                    contest_id=contest_id,
                    submission_id=submission_id,
                    award_title=final_award_title,
                    display_order=0,
                )
                session.add(archive)
            else:
                archive.award_title = final_award_title
                archive.display_order = getattr(archive, "display_order", 0) or 0

            session.commit()
            session.refresh(archive)

            payload = {
                "success": True,
                "decision": "approve",
                "submission": {
                    "id": submission.id,
                    "status": submission.status,
                    "final_score": float(submission.final_score) if submission.final_score is not None else None,
                    "title": submission.title,
                },
                "archive": {
                    "id": archive.id,
                    "contest_id": archive.contest_id,
                    "submission_id": archive.submission_id,
                    "award_title": archive.award_title,
                    "display_order": archive.display_order,
                    "published_at": archive.published_at.isoformat() if archive.published_at else None,
                },
            }
            return payload, None

        submission.status = "rejected"
        self.submission_repo.update(submission)

        archive = (
            session.query(DigitalArchiveExhibitModel)
            .filter_by(contest_id=contest_id, submission_id=submission_id)
            .first()
        )
        if archive is not None:
            session.delete(archive)
            session.commit()

        return {
            "success": True,
            "decision": "reject",
            "submission": {
                "id": submission.id,
                "status": submission.status,
                "final_score": float(submission.final_score) if submission.final_score is not None else None,
                "title": submission.title,
            },
            "archive": None,
        }, None

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

        leaderboard = []
        for item in results:
            leaderboard.append({
                "rank": item["rank"],
                "submission_id": item["submission_id"],
                "user_id": item["user_id"],
                "final_score": item["total_score"],
                "total_score": item["total_score"],
            })

        # Enrich leaderboard entries with a representative image URL (thumbnail if available)
        try:
            from infrastructure.models.app import SubmissionFileModel as _SFile
            session = getattr(self.submission_repo, "session", None)

            for entry in leaderboard:
                entry_image = None
                try:
                    if session is not None:
                        file_row = (
                            session
                            .query(_SFile)
                            .filter_by(submission_id=entry.get("submission_id"))
                            .order_by(_SFile.id.asc())
                            .first()
                        )
                        if file_row is not None:
                            # prefer thumbnail when available
                            entry_image = getattr(file_row, "thumbnail_url", None) or getattr(file_row, "image_hd_url", None)
                except Exception:
                    entry_image = None

                entry["image_url"] = entry_image
        except Exception:
            # best-effort only; do not fail leaderboard if enrichment fails
            pass

        return {
            "message": "Round finalized successfully",
            "round_id": round_id,
            "status": "FINALIZED",
            "round": {
                "id": round_id,
                "status": "FINALIZED",
            },
            "results": results,
            "leaderboard": leaderboard,
        }, None

    def calculate_submission_score(
        self,
        submission_id: int,
    ):
        submission = self.submission_repo.get_by_id(submission_id)

        if submission is None:
            return None, "submission_not_found"

        self._recalculate_final_score(submission)

        return submission, None

    def is_judge_assigned(
        self,
        submission_id: int,
        judge_id: int,
        user_role: str = "judge",
    ) -> bool:
        if isinstance(user_role, str) and user_role.lower() == "admin":
            return True

        try:
            submission = self.submission_repo.get_by_id(submission_id)
            if submission is None:
                return True

            from infrastructure.models.app import JudgeAssignmentModel
            session = getattr(self.submission_repo, "session", None)
            if not session:
                session = getattr(self.contest_repo, "session", None)

            if session:
                round_assignments = (
                    session.query(JudgeAssignmentModel)
                    .filter(
                        JudgeAssignmentModel.round_id == submission.round_id
                    )
                    .all()
                )

                if round_assignments:
                    assigned = any(
                        a.judge_id == judge_id
                        and (
                            a.submission_id is None
                            or a.submission_id == submission_id
                        )
                        for a in round_assignments
                    )
                    return assigned
        except Exception:
            pass

        return True


    def submit_feedback(
        self,
        submission_id: int,
        judge_id: int,
        summary_feedback: str,
        final_recommendation: Optional[str] = None,
        is_finalized: bool = False,
    ):
        submission = self.submission_repo.get_by_id(
            submission_id
        )

        if submission is None:
            return None, "submission_not_found"

        lock_state = self._get_review_lock_state(
            submission_id=submission_id,
            judge_id=judge_id,
        )
        if lock_state["round_finalized"]:
            return None, "round_finalized"
        if lock_state["feedback_finalized"] and not is_finalized:
            return None, "feedback_finalized"
        if lock_state["feedback_finalized"] and is_finalized:
            return None, "feedback_finalized"

        model = self.feedback_repo.create_or_update(
            submission_id=submission_id,
            judge_id=judge_id,
            summary_feedback=summary_feedback,
            final_recommendation=final_recommendation,
            is_finalized=is_finalized,
        )

        return model, None

    def get_submission_review_data(
        self,
        submission_id: int,
        judge_id: int,
        user_role: str = "judge",
    ):
        submission = self.submission_repo.get_by_id(submission_id)

        if submission is None:
            return None, "submission_not_found"

        if not self.is_judge_assigned(
            submission_id=submission_id,
            judge_id=judge_id,
            user_role=user_role,
        ):
            return None, "not_assigned"

        round_obj = self.contest_repo.get_round_by_id(
            submission.round_id
        )

        image_url = None
        media_assets = {
            "main_image_url": None,
            "negative_film_url": None,
            "contact_sheet_url": None,
        }
        proof_attachments = []

        try:
            file_rows = (
                self.submission_repo.session
                .query(SubmissionFileModel)
                .filter_by(submission_id=submission_id)
                .order_by(SubmissionFileModel.id.asc())
                .all()
            )

            file_urls = []
            for file_row in file_rows or []:
                candidate_url = getattr(file_row, "image_hd_url", None)
                if candidate_url and candidate_url not in file_urls:
                    file_urls.append(candidate_url)

            if file_urls:
                image_url = file_urls[0]
                media_assets["main_image_url"] = file_urls[0]
            if len(file_urls) > 1:
                media_assets["negative_film_url"] = file_urls[1]
            if len(file_urls) > 2:
                media_assets["contact_sheet_url"] = file_urls[2]
            if len(file_urls) > 3:
                proof_attachments = [
                    {
                        "label": f"Proof Attachment {index + 1}",
                        "url": file_urls[index],
                    }
                    for index in range(3, len(file_urls))
                ]
        except Exception:
            image_url = None
            media_assets = {
                "main_image_url": None,
                "negative_film_url": None,
                "contact_sheet_url": None,
            }
            proof_attachments = []

        criteria_list = (
            self.contest_repo.get_criteria_by_round_id(
                submission.round_id
            )
            or []
        )

        all_scores = self.score_repo.list_by_submission(
            submission_id
        ) or []

        judge_scores = [
            score
            for score in all_scores
            if score.judge_id == judge_id
        ]

        score_map = {
            score.criteria_id: score
            for score in judge_scores
        }

        feedback = self.feedback_repo.get_by_submission_judge(
            submission_id=submission_id,
            judge_id=judge_id,
        )
        lock_state = self._get_review_lock_state(
            submission_id=submission_id,
            judge_id=judge_id,
        )

        criteria_payload = []
        scored_values = []
        max_values = []

        for criterion in criteria_list:
            try:
                weight = float(criterion.weight or 0)
            except (TypeError, ValueError):
                weight = 0.0

            try:
                max_score = float(criterion.max_score or 0)
            except (TypeError, ValueError):
                max_score = 0.0

            score_model = score_map.get(criterion.id)
            existing_score = None
            existing_comment = None

            if score_model is not None:
                try:
                    existing_score = float(score_model.score_value)
                except (TypeError, ValueError):
                    existing_score = None
                existing_comment = score_model.comment

            if existing_score is not None and weight > 0:
                scored_values.append((existing_score, weight))

            if weight > 0:
                max_values.append((max_score, weight))

            criteria_payload.append({
                "id": criterion.id,
                "round_id": criterion.round_id,
                "name": criterion.name,
                "description": criterion.description,
                "max_score": max_score,
                "weight": weight,
                "score_value": existing_score,
                "comment": existing_comment,
            })

        provisional_total = self._calculate_weighted_average(scored_values)
        maximum_total = self._calculate_weighted_average(max_values)

        next_previous, error = self.get_next_previous(submission_id)

        if error:
            next_previous = {
                "previous": None,
                "next": None,
            }

        return {
            "submission": self._serialize_submission(submission),
            "image_url": image_url,
            "media_assets": media_assets,
            "proof_attachments": proof_attachments,
            "round": None if round_obj is None else {
                "id": round_obj.id,
                "contest_id": round_obj.contest_id,
                "round_number": round_obj.round_number,
                "title": round_obj.title,
                "status": round_obj.status,
            },
            "criteria": criteria_payload,
            "feedback": None if feedback is None else {
                "id": feedback.id,
                "summary_feedback": feedback.summary_feedback,
                "final_recommendation": feedback.final_recommendation,
                "is_finalized": bool(getattr(feedback, "is_finalized", False)),
            },
            "review_state": {
                "is_locked": lock_state["is_locked"],
                "lock_reason": lock_state["lock_reason"],
                "feedback_finalized": lock_state["feedback_finalized"],
                "round_finalized": lock_state["round_finalized"],
                "round_status": lock_state["round_status"],
            },
            "provisional_total": (
                round(provisional_total, 2)
                if provisional_total is not None
                else None
            ),
            "maximum_total": (
                round(maximum_total, 2)
                if maximum_total is not None
                else None
            ),
            "next_previous": next_previous,
            "progress": {
                "scored_count": len(scored_values),
                "criteria_count": len(criteria_payload),
            },
        }, None

    

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

