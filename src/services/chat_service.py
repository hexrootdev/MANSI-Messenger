from database import AsyncSession, select, with_db_session, User, Chat, ChatMember, Message, Attachment, ChatType, AttachmentType
from crud import db_get, select_members_in_chat, select_chat_messages_with_sender, create_new_message, create_chat, add_members_to_chat_direct
from fastapi import HTTPException

# Получить все чаты в которых есть пользователь по ID
@with_db_session
async def get_chat_list(session: AsyncSession, my_id: int):
    result = []
    stmt = select(ChatMember).where(ChatMember.user_id == my_id)
    query = await session.execute(stmt)
    chats = query.scalars().all()
    for chat in chats:
        members = await select_members_in_chat(session=session, chat_id=chat.chat_id)
        for member in members:
            if member.user_id != my_id:
                receiver = await db_get(session=session, class_=User, uid=member.user_id)
                result.append({
                    "chat_id": chat.chat_id,
                    "receiver_id": receiver.id,
                    "title": receiver.username
                })
    return result

# Получить все сообщения чата 
@with_db_session
async def get_chat_messages(session: AsyncSession, chat_id: int):
    messages = await select_chat_messages_with_sender(session=session, chat_id=chat_id)
    return {
        "messages": [
            {
                "chat_id": message.chat_id,
                "sender_id": message.sender_id,
                "sender_username": username,
                "content": message.content,
            }
            for message, username in messages
        ]
    }

# Создать чат, добавить участников
@with_db_session
async def create_chat_service(session: AsyncSession, name: str | None, type_: ChatType, user_ids: list[int]):
    chat = await create_chat(session=session, name=name, type_=type_)
    if type_ == ChatType.DIRECT:
        if len(user_ids) != 2:
            raise ValueError("DIRECT chat must have exactly 2 users")
        await add_members_to_chat_direct(session=session, chat_id=chat.id, uid1=user_ids[0], uid2=user_ids[1])
    return chat
    
# Получить отправителей сообщений и сообщения
@with_db_session
async def handle_message(session: AsyncSession, sender_id: int, chat_id: int, content: str):
    chat = await db_get(session=session, class_=Chat, uid=chat_id)
    if chat:
        members = await select_members_in_chat(session=session, chat_id=chat.id)
        sender_found = False
        for member in members:
            if member.user_id == sender_id:
                sender_found = True
                break
        receivers = []
        if sender_found:
            for member in members:
                if member.user_id != sender_id:
                    receivers.append(member.user_id)
            message = await create_new_message(session=session, chat_id=chat_id, sender_id=sender_id, content=content)
            sender = await db_get(session=session, class_=User, uid=sender_id)
            return {"receivers": receivers, "message": message, "sender_username": sender.username}
        else:
            raise HTTPException
    else:
        raise HTTPException