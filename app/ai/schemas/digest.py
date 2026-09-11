from typing import Annotated

from pydantic import BaseModel, Field, create_model

from app.schemas.font_awesome import FAIcon


class DigestSection(BaseModel):
    description: str
    icon: FAIcon | None = None
    content: str


class WeekDigestDraft(BaseModel):
    title: str
    summary: str
    sections: list[DigestSection]


def bounded_week_digest_draft(max_sections: int) -> type[WeekDigestDraft]:
    """Cap sections in the schema, so the model writes fewer instead of us dropping extras."""
    plural = "section" if max_sections == 1 else "sections"
    return create_model(
        "WeekDigestDraft",
        __base__=WeekDigestDraft,
        sections=(
            Annotated[
                list[DigestSection],
                # Gemini's converter drops maxItems but keeps the description, so say it twice.
                Field(
                    max_length=max_sections,
                    description=(
                        f"At most {max_sections} {plural}, and fewer is better. "
                        "An empty list beats a section that only recaps a day."
                    ),
                ),
            ],
            ...,
        ),
    )
