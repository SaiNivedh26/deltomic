import asyncio
from typing import AsyncIterator, TypeVar

T = TypeVar("T")


async def merge_async_iters(*iters: AsyncIterator[T]) -> AsyncIterator[T]:
    """Merge multiple async iterators into a single stream.

    Yields items as they arrive from any of the input iterators.
    Completes when all input iterators are exhausted.
    """
    queue: asyncio.Queue[T | None] = asyncio.Queue()
    active = 0

    async def consume(iter_: AsyncIterator[T]) -> None:
        nonlocal active
        try:
            async for item in iter_:
                await queue.put(item)
        except Exception as e:
            print(f"Error in merge iterator: {e}")
        finally:
            active -= 1
            if active == 0:
                await queue.put(None)

    active = len(iters)
    if active == 0:
        return

    tasks = [asyncio.create_task(consume(it)) for it in iters]

    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)