from app.core.chunking import chunk_text


def test_chunking_is_deterministic():
    text = "A" * 5000

    a = chunk_text(text, chunk_size_chars=1000, overlap_chars=100)
    b = chunk_text(text, chunk_size_chars=1000, overlap_chars=100)

    assert a == b
    assert len(a) > 1
    assert a[0].char_start == 0