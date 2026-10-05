from asistente.ai.pricing import TokenUsage, has_price, response_cost, transcription_cost


def test_plain_input_and_output() -> None:
    usage = TokenUsage(input_tokens=1_500, output_tokens=80)

    # 1500 x 0.10 + 80 x 0.50 micro-dollars
    assert response_cost("gpt-6-luna", usage) == 190


def test_cache_reads_are_cheaper_and_cache_writes_dearer() -> None:
    read = TokenUsage(input_tokens=1_500, output_tokens=80, cached_tokens=1_200)
    written = TokenUsage(input_tokens=1_500, output_tokens=80, cache_write_tokens=1_200)

    # 300 x 0.10 + 1200 x 0.01 + 80 x 0.50
    assert response_cost("gpt-6-luna", read) == 82
    # 300 x 0.10 + 1200 x 0.125 + 80 x 0.50
    assert response_cost("gpt-6-luna", written) == 220


def test_rounds_up_to_whole_micro_dollars() -> None:
    assert response_cost("gpt-6-luna", TokenUsage(input_tokens=1, output_tokens=0)) == 1


def test_dated_snapshots_share_the_price_but_other_models_do_not() -> None:
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=0)

    assert response_cost("gpt-5.4-nano-2026-03-17", usage) == 200_000
    assert response_cost("gpt-6-luna-pro", usage) is None
    assert has_price("gpt-6-luna")
    assert not has_price("gpt-6-luna-pro")


def test_audio_is_priced_by_the_minute() -> None:
    # 12 s at US$0.003 per minute
    assert transcription_cost("gpt-4o-mini-transcribe", 12) == 600
    assert transcription_cost("gpt-4o-mini-transcribe-2025-12-15", 60) == 3_000
    assert transcription_cost("gpt-transcribe", 1) == 75
    assert transcription_cost("otro-modelo", 60) is None
    assert has_price("gpt-4o-mini-transcribe")
