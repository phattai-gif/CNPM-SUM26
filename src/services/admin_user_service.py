from infrastructure.repositories.admin_user_repository import AdminUserRepository


VALID_ROLES = {'admin', 'organizer', 'participant', 'judge'}
VALID_STATUSES = {'active', 'locked'}


class AdminUserService:
    def __init__(self, repository=None):
        self.repository = repository or AdminUserRepository()

    def list_users(self, page=1, per_page=20, search=None, role=None, status=None):
        if role and role not in VALID_ROLES:
            raise ValueError('Role must be one of: admin, organizer, participant, judge')
        if status and status not in VALID_STATUSES:
            raise ValueError('Status must be one of: active, locked')
        return self.repository.list_users(page, per_page, search, role, status)

    def get_user(self, user_id):
        return self.repository.get_user(user_id)

    def change_role(self, actor_id, user_id, role):
        if role not in VALID_ROLES:
            raise ValueError('Role must be one of: admin, organizer, participant, judge')
        if actor_id == user_id:
            raise ValueError('An admin cannot change their own role')
        return self.repository.set_role(user_id, role)

    def change_status(self, actor_id, user_id, status):
        if status not in VALID_STATUSES:
            raise ValueError('Status must be one of: active, locked')
        if actor_id == user_id:
            raise ValueError('An admin cannot change their own status')
        return self.repository.set_status(user_id, status)