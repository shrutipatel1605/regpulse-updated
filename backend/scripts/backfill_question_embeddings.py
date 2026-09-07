"""Backfill question_embedding for questions with a NULL embedding.

Sprint 8 started writing ``questions.question_embedding`` for new rows; this
one-off script populates embeddings for questions asked before the change
so ``GET /api/v1/questions/suggestions`` can ANN-search them.

Idempotent — skips rows where ``question_embedding IS NOT NULL``. Safe to
re-run.

Run inside the backend container:
    python scripts/backfill_question_embeddings.py
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

    async with engine.begin() as conn:
        rows = await conn.execute(text("SELECT id, question_text FROM questions " "WHERE question_embedding IS NULL ORDER BY created_at"))
        questions = rows.fetchall()

    print(f"Found {len(questions)} questions without embeddings")
    if not questions:
        await engine.dispose()
        await redis.aclose()
        return

    batch_size = 50
    total = 0
    for i in range(0, len(questions), batch_size):
        batch = questions[i : i + batch_size]
        texts = [row[1] for row in batch]
        ids = [row[0] for row in batch]

        embeddings = await emb_svc.generate(texts)

        async with engine.begin() as conn:
            for qid, emb in zip(ids, embeddings, strict=False):
                vec_str = "[" + ",".join(str(x) for x in emb) + "]"
                await conn.execute(
                    text("UPDATE questions SET question_embedding = CAST(:emb AS vector) " "WHERE id = :id"),
                    {"emb": vec_str, "id": str(qid)},
                )

        total += len(batch)
        print(f"  Embedded {total}/{len(questions)} questions")

    print("Done!")
    await engine.dispose()
    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
