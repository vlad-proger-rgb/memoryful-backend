import pytest
from jinja2 import UndefinedError

from app.ai.context import _env, render_user_profile
from app.ai.schemas import UserProfile
from app.ai.utils import load_prompt
from app.enums import Prompt


@pytest.mark.parametrize("prompt", list(Prompt))
def test_every_prompt_has_a_file(prompt: Prompt) -> None:
    assert load_prompt(prompt)


def test_user_profile_renders_every_field() -> None:
    block = render_user_profile(UserProfile(first_name="Ada", age=36, bio="Writes daily."))
    assert "**Name:** Ada" in block
    assert "**Age:** 36" in block
    assert "**Bio:** Writes daily." in block


def test_user_profile_leaves_out_missing_fields() -> None:
    block = render_user_profile(UserProfile(first_name="Ada"))
    assert "**Name:** Ada" in block
    assert "Age" not in block
    assert "Bio" not in block


def test_a_variable_the_template_expects_but_is_not_given_raises() -> None:
    with pytest.raises(UndefinedError):
        _env.get_template("context/user_profile.md.j2").render(name="Ada")
