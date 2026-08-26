from collections.abc import AsyncIterator

from langsmith import traceable


@traceable(name="TTFT", run_type="chain")
async def _first_non_empty_chunk(stream: AsyncIterator[str]) -> str | None:
    async for chunk in stream:
        if chunk:
            return chunk
    return None


@traceable(
    name="answer_generation",
    run_type="chain",
    reduce_fn=lambda chunks: {"chunk_count": len(chunks)},
)
async def stream_with_ttft(stream: AsyncIterator[str]) -> AsyncIterator[str]:
    first_chunk = await _first_non_empty_chunk(stream)
    if first_chunk is not None:
        yield first_chunk

    async for chunk in stream:
        if chunk:
            yield chunk
