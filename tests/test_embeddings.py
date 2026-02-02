from app.core.embeddings import embed_texts, embedding_dim


def test_embedding_dim_is_384():
    d = embedding_dim()
    assert d == 384

    v = embed_texts(["hello world"])
    assert v.shape[1] == 384