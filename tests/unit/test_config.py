import pytest
from pydantic import ValidationError

from tests.factories import TEST_BOT_TOKEN, make_settings


def test_parses_comma_separated_user_ids() -> None:
    settings = make_settings(allowed_user_ids=" 111, 222 ,333 ")

    assert settings.allowed_user_ids == frozenset({111, 222, 333})


@pytest.mark.parametrize("raw_ids", ["", " , ", "-5", "0"])
def test_rejects_empty_or_invalid_user_ids(raw_ids: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(allowed_user_ids=raw_ids)


def test_rejects_malformed_token_without_leaking_it() -> None:
    bad_token = "definitely-not-a-token-but-maybe-a-secret"

    with pytest.raises(ValidationError) as exc_info:
        make_settings(bot_token=bad_token)

    assert bad_token not in str(exc_info.value)


def test_secrets_are_hidden_in_repr() -> None:
    settings = make_settings()

    assert TEST_BOT_TOKEN not in repr(settings)
    assert settings.bot_token.get_secret_value() == TEST_BOT_TOKEN


def test_rejects_unknown_timezone() -> None:
    with pytest.raises(ValidationError):
        make_settings(timezone="Mars/Olympus_Mons")


def test_exposes_timezone_object() -> None:
    settings = make_settings()

    assert settings.tz.key == "America/Argentina/Buenos_Aires"


def test_ai_is_off_without_key_or_budget() -> None:
    assert not make_settings().ai_enabled
    assert not make_settings(openai_api_key="  ").ai_enabled
    assert not make_settings(openai_api_key="sk-test", ai_daily_limit=0).ai_enabled
    assert make_settings(openai_api_key="sk-test").ai_enabled


def test_secret_values_include_the_openai_key() -> None:
    settings = make_settings(openai_api_key="sk-test-secret")

    assert settings.secret_values() == [TEST_BOT_TOKEN, "sk-test-secret"]
    assert "sk-test-secret" not in repr(settings)
