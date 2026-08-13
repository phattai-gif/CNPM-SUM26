from typing import Optional, List

try:
    from src.infrastructure.repositories.score_repository import ScoreRepository
    from src.infrastructure.repositories.score_feedback_repository import ScoreFeedbackRepository
    from src.infrastructure.repositories.submission_repository import SubmissionRepository
    from src.infrastructure.repositories.contest_repository import ContestRepository
    from src.infrastructure.models.submission_model import SubmissionModel
    from src.infrastructure.models.criteria_model import CriteriaModel
except ImportError:
    from infrastructure.repositories.score_repository import ScoreRepository
    from infrastructure.repositories.score_feedback_repository import ScoreFeedbackRepository
    from infrastructure.repositories.submission_repository import SubmissionRepository
    from infrastructure.repositories.contest_repository import ContestRepository
    from infrastructure.models.submission_model import SubmissionModel
    from infrastructure.models.criteria_model import CriteriaModel


class ScoreService:
    def __init__(self, score_repo: Optional[ScoreRepository] = None, feedback_repo: Optional[ScoreFeedbackRepository] = None, submission_repo: Optional[SubmissionRepository] = None, contest_repo: Optional[ContestRepository] = None):
        self.score_repo = score_repo or ScoreRepository()
        self.feedback_repo = feedback_repo or ScoreFeedbackRepository()
        self.submission_repo = submission_repo or SubmissionRepository()
        self.contest_repo = contest_repo or ContestRepository()

    def validate_score(self, criteria_id: int, score_value) -> bool:
        # Check criteria exists and validate score within [0, max_score]
        crit = self.contest_repo.get_criteria_by_id(criteria_id)
        if crit is None:
            return False
        try:
            score_num = float(score_value)
        except Exception:
            return False
        if score_num < 0 or score_num > float(crit.max_score):
            return False
        return True

    def submit_score(self, submission_id: int, judge_id: int, criteria_id: int, score_value, comment: Optional[str] = None):
        # Ensure submission exists
        submission = self.submission_repo.get_by_id(submission_id)
        if not submission:
            return None, 'submission_not_found'

        # Validate criteria
        crit = self.contest_repo.get_criteria_by_id(criteria_id)
        if not crit:
            return None, 'criteria_not_found'

        # Validate score value
        try:
            score_num = float(score_value)
        except Exception:
            return None, 'invalid_score'
        if score_num < 0 or score_num > float(crit.max_score):
            return None, 'invalid_score'

        # Create or update score
        model = self.score_repo.create_or_update(submission_id, judge_id, criteria_id, score_num, comment)

        # Recalculate final score for submission if desired: not modifying business rule here.
        # If project has existing final_score calculation, it should be kept. Here we attempt a simple average across judges' weighted criteria if needed.
        try:
            scores = self.score_repo.list_by_submission(submission_id)
            # calculate simple average of scores weighted by criteria weight
            from collections import defaultdict
            judge_scores = defaultdict(list)
            for s in scores:
                judge_scores[s.judge_id].append((s.criteria_id, float(s.score_value)))

            # For each judge, compute average of their scores (simple mean)
            per_judge_avg = []
            for j, vals in judge_scores.items():
                vals_only = [v for (_, v) in vals]
                if vals_only:
                    per_judge_avg.append(sum(vals_only) / len(vals_only))

            if per_judge_avg:
                final = sum(per_judge_avg) / len(per_judge_avg)
                submission.final_score = final
                # persist
                self.submission_repo.update(submission)
        except Exception:
            pass

        return model, None

    def submit_feedback(self, submission_id: int, judge_id: int, summary_feedback: str, final_recommendation: Optional[str] = None):
        submission = self.submission_repo.get_by_id(submission_id)
        if not submission:
            return None, 'submission_not_found'

        model = self.feedback_repo.create_or_update(submission_id, judge_id, summary_feedback, final_recommendation)
        return model, None

    def get_next_previous(self, submission_id: int):
        # determine next and previous submission within same round
        submission = self.submission_repo.get_by_id(submission_id)
        if not submission:
            return None, 'submission_not_found'

        # find submissions in same round ordered by id
        try:
            all_subs = (
                self.submission_repo.session
                .query(SubmissionModel)
                .filter_by(round_id=submission.round_id)
                .order_by(SubmissionModel.id.asc())
                .all()
            )
        except Exception:
            return None, 'db_error'

        ids = [s.id for s in all_subs]
        try:
            idx = ids.index(submission_id)
        except ValueError:
            return None, 'submission_not_found'

        prev_id = ids[idx-1] if idx > 0 else None
        next_id = ids[idx+1] if idx < len(ids)-1 else None

        return {'previous': prev_id, 'next': next_id}, None
