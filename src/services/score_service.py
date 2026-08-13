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

    def finalize_round(self, round_id: int):
        """
        Chốt điểm một vòng thi.
        1. Kiểm tra vòng thi có tồn tại hay không.
        2. Kiểm tra vòng thi đã được chốt hay chưa.
        3. Tính tổng điểm cho từng thí sinh.
        4. Xếp hạng thí sinh theo tổng điểm từ cao xuống thấp.
        5. Lưu/cập nhật kết quả và cập nhật trạng thái vòng thi thành FINALIZED.
        """
        round_obj = self.contest_repo.get_round_by_id(round_id)
        if not round_obj:
            return None, 'round_not_found'

        if getattr(round_obj, 'status', '').upper() == 'FINALIZED':
            return None, 'round_already_finalized'

        try:
            from infrastructure.models.submission_model import SubmissionModel
            from infrastructure.models.round_model import RoundModel
        except ImportError:
            from src.infrastructure.models.submission_model import SubmissionModel
            from src.infrastructure.models.round_model import RoundModel

        session = getattr(self.submission_repo, 'session', None) or getattr(self.contest_repo, 'session', None)

        if session is not None:
            try:
                subs = session.query(SubmissionModel).filter_by(round_id=round_id).all()
            except Exception:
                subs = []
        else:
            all_subs = self.submission_repo.list()
            subs = [s for s in all_subs if s.round_id == round_id]

        criteria_list = self.contest_repo.get_criteria_by_round_id(round_id)
        crit_map = {}
        for c in criteria_list:
            w = float(c.weight) if hasattr(c, 'weight') and c.weight is not None else 1.0
            crit_map[c.id] = w if w > 0 else 1.0

        candidates = []
        for sub in subs:
            scores = self.score_repo.list_by_submission(sub.id)
            if scores:
                from collections import defaultdict
                judge_scores = defaultdict(list)
                for s in scores:
                    s_val = float(s.score_value) if s.score_value is not None else 0.0
                    w = crit_map.get(s.criteria_id, 1.0)
                    judge_scores[s.judge_id].append((s_val, w))

                per_judge_weighted_avg = []
                for j_id, s_list in judge_scores.items():
                    tot_w = sum(w for (_, w) in s_list)
                    if tot_w > 0:
                        j_score = sum(val * w for (val, w) in s_list) / tot_w
                    else:
                        j_score = sum(val for (val, _) in s_list) / len(s_list)
                    per_judge_weighted_avg.append(j_score)

                if per_judge_weighted_avg:
                    total_score = round(sum(per_judge_weighted_avg) / len(per_judge_weighted_avg), 2)
                elif sub.final_score is not None:
                    total_score = float(sub.final_score)
                else:
                    total_score = 0.0
            elif sub.final_score is not None:
                total_score = float(sub.final_score)
            else:
                total_score = 0.0

            sub.final_score = total_score
            sub.status = 'evaluated'
            if session is not None:
                session.add(sub)

            sub_time = getattr(sub, 'submitted_at', None)
            from datetime import datetime
            fallback_dt = datetime.max
            candidates.append({
                'user_id': sub.user_id,
                'submission_id': sub.id,
                'total_score': total_score,
                'submitted_at': sub_time or fallback_dt,
            })

        if session is not None:
            try:
                session.commit()
            except Exception:
                try: session.rollback()
                except Exception: pass

        candidates.sort(key=lambda x: (-x['total_score'], x['submitted_at'], x['user_id']))

        results = []
        for idx, item in enumerate(candidates):
            if idx > 0 and item['total_score'] == candidates[idx - 1]['total_score']:
                rank = results[-1]['rank']
            else:
                rank = idx + 1

            results.append({
                'user_id': item['user_id'],
                'submission_id': item['submission_id'],
                'total_score': item['total_score'],
                'rank': rank
            })

        if session is not None:
            try:
                r_model = session.query(RoundModel).filter_by(id=round_id).first()
                if r_model:
                    r_model.status = 'FINALIZED'
                    session.commit()
            except Exception:
                try: session.rollback()
                except Exception: pass
                self.contest_repo.update_round(round_id, {'status': 'FINALIZED'})
        else:
            self.contest_repo.update_round(round_id, {'status': 'FINALIZED'})

        return {
            'message': 'Round finalized successfully',
            'round_id': round_id,
            'status': 'FINALIZED',
            'results': results
        }, None
