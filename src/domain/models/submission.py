from typing import Optional


class Submission:
    def __init__(
        self,
        id: Optional[int] = None,
        round_id: Optional[int] = None,
        user_id: Optional[int] = None,
        title: str = "",
        story_description: str = "",
        status: str = "submitted",
        final_score: Optional[float] = None,
        submitted_at=None,
        created_at=None,
        updated_at=None,
    ):
        self.id = id
        self.round_id = round_id
        self.user_id = user_id
        self.title = title
        self.story_description = story_description
        self.status = status
        self.final_score = final_score
        self.submitted_at = submitted_at
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return (
            f"Submission(id={self.id}, round_id={self.round_id}, user_id={self.user_id}, "
            f"title={self.title!r}, status={self.status!r})"
        )
