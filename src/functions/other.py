from typing import Callable

def make_handler(func: Callable, **kwargs) -> Callable:
    async def handler(e):
        await func(e, **kwargs)
    return handler


