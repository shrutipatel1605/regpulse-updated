"""Backfill embeddings for chunks that have NULL embedding vectors.

Run inside the backend container:
    python scripts/backfill_embeddings.py
"""

import asyncio
import os
import sys

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main() -> None:

    import openai
    import redis.asyncio as aioredis
    from sqlalchemy import text

    from app.config import get_settings
    from app.db import engine
    from app.services.embedding_service import EmbeddingService

    settings = get_settings()
    redis = aioredis.from_url(settings.REDIS_URL)
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    emb_svc = EmbeddingService(openai_client=client, redis=redis)

    # Fetch chunks without embeddings
    async with engine.begin() as conn:
        rows = await conn.execute(text("SELECT id, chunk_text FROM document_chunks WHERE embedding IS NULL ORDER BY id"))
        chunks = rows.fetchall()

    print(f"Found {len(chunks)} chunks without embeddings")
    if not chunks:
        return

    # Batch embed
    batch_size = 50
    total = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [row[1] for row in batch]
        ids = [row[0] for row in batch]

        embeddings = await emb_svc.generate(texts)

        async with engine.begin() as conn:
            for chunk_id, emb in zip(ids, embeddings, strict=False):
                vec_str = "[" + ",".join(str(x) for x in emb) + "]"
                await conn.execute(
                    text("UPDATE document_chunks SET embedding = :emb WHERE id = :id"),
                    {"emb": vec_str, "id": str(chunk_id)},
                )

        total += len(batch)
        print(f"  Embedded {total}/{len(chunks)} chunks")

    print("Done!")
    await engine.dispose()
    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
