from infrastructure.repositories.moderator_dashboard_repository import ModeratorDashboardRepository


class ModeratorDashboardService:
    def __init__(self, repository=None):
        self.repository = repository or ModeratorDashboardRepository()

    def _scope(self, user_id, user_role, contest_id=None):
        if user_role == 'admin':
            if contest_id is not None and not self.repository.contest_exists(contest_id):
                raise ValueError('Contest not found')
            return [contest_id] if contest_id is not None else self.repository.all_contest_ids()

        owned_ids = self.repository.contest_ids_for_user(user_id)
        if contest_id is not None:
            if contest_id not in owned_ids:
                raise PermissionError('You do not have access to this contest')
            return [contest_id]
        return owned_ids

    def dashboard(self, user_id, user_role, contest_id=None):
        return self.repository.dashboard_metrics(self._scope(user_id, user_role, contest_id))

    def submissions(self, user_id, user_role, contest_id=None, page=1, per_page=20, status=None, ai_risk=None):
        items, total = self.repository.review_queue(
            self._scope(user_id, user_role, contest_id), page, per_page, status, ai_risk
        )
        return {
            'submissions': items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
            },
        }