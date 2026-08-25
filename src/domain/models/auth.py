from datetime import date


class Auth:
    def __init__(self, username: str, password: str, passwordcomfirm: str, email: str,
                 role: str = 'participant', full_name: str = None, id: int = None,
                 avatar_url: str = None, bio: str = None, created_at = None):
        self.id = id
        self.username = username
        self.password = password
        self.passwordcomfirm = passwordcomfirm
        self.email = email
        self.role = role
        self.full_name = full_name
        self.avatar_url = avatar_url
        self.bio = bio
        self.created_at = created_at
