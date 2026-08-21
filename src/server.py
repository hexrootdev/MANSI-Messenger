from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query

from database import ChatType
from crud import get_user_by_id, get_user_by_email, select_users, select_all_users, select_all_chats, select_all_chat_members, select_members_in_chat, select_all_messages, create_new_message, create_chat
from services.chat_service import get_chat_list, get_chat_messages, create_chat_service, handle_message

from websocket_manager import ConnectionManager

app = FastAPI()


# Все пользователи
@app.get("/users")
async def get_all_users():
    users = await select_all_users()
    return users

@app.get("/user/id/{user_id}")
async def get_user_endpoint(user_id: int):
    user = await get_user_by_id(uid=user_id)
    return user

@app.get("/user/email/{email}")
async def get_user_endpoint(email: str):
    user = await get_user_by_email(email=email)
    return user

# Поиск пользователей
@app.get("/users/search")
async def search_users_endpoint(q: str = Query(..., min_length=1, description="Поисковый запрос"), my_id: int = Query(..., description="ID текущего пользователя")):
    users = await select_users(user_input=q, my_id=my_id)
    return {"users": users}

# Получить все чаты
@app.get("/chats")
async def get_my_chats():
    chats = await select_all_chats()
    return chats

# Получить список чатов пользователя
@app.get("/chats/list/{user_id}")
async def get_user_chat_list(user_id: int):
    chats = await get_chat_list(my_id=user_id)
    return chats

# Получить всех участников всех чатов
@app.get("/members")
async def get_chat_members():
    members = await select_all_chat_members()
    return members

# Получить всех участников чата
@app.get("/members/chat/{chat_id}")
async def get_chat_members(chat_id: int):
    members = await select_members_in_chat(chat_id=chat_id)
    return {"members": [{"chat_id": member.chat_id, "user_id": member.user_id} for member in members]}

# Получить все сообщения всех чатов
@app.get("/messages")
async def get_messages():
    messages = await select_all_messages()
    return messages

# Получить все сообщения чата
@app.get("/messages/chat/{chat_id}")
async def get_chat_message(chat_id: int):
    messages = await get_chat_messages(chat_id=chat_id)
    return messages

@app.post("/messages")
async def create_message(data):
    return await create_new_message(chat_id=data.chat_id, sender_id=data.sender_id, content=data.content)

@app.post("/chats/direct")
async def create_direct_chat(user_ids: list[int] = Query(...)):
    print("/chats/direct")
    result = await create_chat_service(name=None, type_=ChatType.DIRECT, user_ids=user_ids)
    chat = result["chat"]
    members = result["members"]
    receiver = result["receiver"]
    payload = {
        "type": "chat_created",
        "chat": {
            "chat_id": chat.id,
            "receiver_id": receiver["id"],
            "title": receiver["title"],
        }
    }
    for member in members:
        await manager.send_to(receiver_id=member, payload=payload)
    return result

# Websockets --------------------------------------

manager = ConnectionManager()
@app.websocket("/ws/user")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            type_ = data["type"]
            if type_ == "message":
                chat_id = data["chat_id"]
                content = data["content"]

                result = await handle_message(sender_id=user_id, chat_id=chat_id, content=content)
                receivers = result["receivers"]
                message = result["message"]
                sender_username = result["sender_username"]
                
                payload = {
                            "type": "message",
                            "message": {
                                "id": message.id,
                                "chat_id": message.chat_id,
                                "sender_id": message.sender_id,
                                "sender_username": sender_username,
                                "content": message.content,
                                "created_at": message.created_at.isoformat(),
                            }
                        }

                for receiver_id in receivers:
                    await manager.send_to(receiver_id=receiver_id,
                                          payload=payload)

                await manager.send_to(receiver_id=user_id, payload=payload)
    except WebSocketDisconnect:
        manager.disconnect(user_id)