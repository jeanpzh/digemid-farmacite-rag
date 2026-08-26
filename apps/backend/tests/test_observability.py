import asyncio

from app.services.observability import stream_with_ttft


def test_stream_with_ttft_skips_empty_chunks_but_preserves_all_answer_text():
    async def chunks():
        yield ""
        yield "primero"
        yield ""
        yield "segundo"

    async def collect():
        return [chunk async for chunk in stream_with_ttft(chunks())]

    assert asyncio.run(collect()) == ["primero", "segundo"]
