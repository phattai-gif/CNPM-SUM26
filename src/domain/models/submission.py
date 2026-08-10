from typing import Optional


class Submission:
    def __init__(
        self,
        id: Optional[int] = None,
        user_id: Optional[int] = None,
        contest_id: Optional[int] = None,
        title: str = "",
        description: str = "",
        status: str = "pending",
        file_url: Optional[str] = None,
        created_at=None,
        updated_at=None,
    ):
        self.id = id
        self.user_id = user_id
        self.contest_id = contest_id
        self.title = title
        self.description = description
        self.status = status
        self.file_url = file_url
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return (
            f"Submission(id={self.id}, user_id={self.user_id}, contest_id={self.contest_id}, "
            f"title={self.title!r}, status={self.status!r})"
        )
