from typing import Optional

from infrastructure.repositories.contest_settings_repository import ContestSettingsRepository


class ContestSettingsService:
    def __init__(self, repository: Optional[ContestSettingsRepository] = None):
        self.repository = repository or ContestSettingsRepository()

    def get_contest_settings(self, contest_id: int):
        return self.repository.get_by_contest_id(contest_id)

    def create_or_update_settings(self, contest_id: int, **kwargs):
        return self.repository.create_or_update(contest_id, **kwargs)

