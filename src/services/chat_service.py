from database import AsyncSession, select, with_db_session, User, Chat, ChatMember, Message, Attachment, ChatType, AttachmentType
from crud import db_get, select_members_in_chat, create_new_message
from fastapi import HTTPException

# Получить все чаты в которых есть пользователь по ID
@with_db_session
async def get_chat_list(session: AsyncSession, my_id: int):
    result = []
    stmt = select(ChatMember).where(ChatMember.user_id == my_id)
    query = await session.execute(stmt)
    chats = query.scalars().all()
    for chat in chats:
        members = await select_members_in_chat(chat_id=chat.chat_id)
        for member in members:
            if member.user_id != my_id:
                receiver = await db_get(class_=User, uid=member.user_id)
                result.append({
                    "chat_id": chat.chat_id,
                    "receiver_id": receiver.id,
                    "title": receiver.username
                })
    return result

@with_db_session
async def handle_message(session: AsyncSession, sender_id: int, chat_id: int, content: str):
    chat = await db_get(session=session, class_=Chat, uid=chat_id)
    if chat:
        members = await select_members_in_chat(session=session, chat_id=chat.chat_id)
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
            return {"receivers": receivers, "message": message}
        else:
            raise HTTPException
    else:
        raise HTTPException