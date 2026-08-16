import aiohttp

async def get_user_request(user_id: int):
    async with aiohttp.ClientSession() as session:
        url = f"http://127.0.0.1:8000/user/id/{user_id}"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data
            return []

async def search_users(query: str, my_id: int):
    async with aiohttp.ClientSession() as session:
        url = f"http://127.0.0.1:8000/users/search?q={query}&my_id={my_id}"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("users", [])
            return []    

async def get_chat_list_request(user_id: int):
    async with aiohttp.ClientSession() as session:
        url = f"http://127.0.0.1:8000/chats/list/{user_id}"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data
            return []

async def get_messages_chat(chat_id: int):
    async with aiohttp.ClientSession() as session:
        url = f"http://127.0.0.1:8000/messages/chat/{chat_id}"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("messages", [])
            return []

async def create_direct_chat_request(name: str | None, user_ids: list[int]):
    async with aiohttp.ClientSession() as session:
        url = f"http://127.0.0.1:8800/chats/direct"
        async with session.post(url, params={
            "name": name,
            "user_ids": user_ids,
        }) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data
            return []