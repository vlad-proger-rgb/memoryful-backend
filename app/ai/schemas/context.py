from pydantic import BaseModel


class UserProfile(BaseModel):
    """Minimal user facts used to personalize chat. Cached, so kept small."""

    first_name: str | None = None
    age: int | None = None
    bio: str | None = None

    @property
    def is_empty(self) -> bool:
        return not (self.first_name or self.age or self.bio)
