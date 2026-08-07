from database import AsyncSession, select, with_db_session, User, Chat, ChatMember, Message, Attachment, ChatType, AttachmentType

# *TEMP - временная функция (для получения сведений через API)

# Универсальная функция получения объекта по его ID
@with_db_session
async def db_get(session: AsyncSession, class_, uid: int):
    return await session.get(class_, uid)

# Users ----------------------

# Получить пользователя по email (для логина)
@with_db_session
async def get_user_by_email(session: AsyncSession, email: str):
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

# Получить всех пользователей, кроме клиента, username которых похож на user_input
@with_db_session
async def select_users(session: AsyncSession, user_input: str, my_id: int):
    stmt = select(User).where((User.username.contains(user_input)) & (~User.is_private) & (User.id != my_id))
    result = await session.execute(stmt)
    users = result.scalars().all()
    return [{"id": u.id, "username": u.username} for u in users]

# Получить всех пользователей (TEMP)
@with_db_session
async def select_all_users(session: AsyncSession):
    stmt = select(User)
    result = await session.execute(stmt)
    users = result.scalars().all()
    return {"users": [{"id": u.id, "username": u.username} for u in users]}

# Создание нового пользователя (регистрация)
@with_db_session
async def create_user(session: AsyncSession, username: str, email: str, password_hash, remember_user: bool=False):
    new_user = User(username=username, email=email, password_hash=password_hash)
    session.add(new_user)
    await session.flush()
    return new_user

# Chats -----------------------

# Получить все чаты (TEMP)
@with_db_session
async def select_all_chats(session: AsyncSession):
    stmt = select(Chat)
    result = await session.execute(stmt)
    chats = result.scalars().all()
    return {"chats": [{"id": c.id, "name": c.name, "type": c.type} for c in chats]}

# Создание чата 
@with_db_session
async def create_chat(session: AsyncSession, name: str | None, type_: ChatType):
    new_chat = Chat(name=name, type=type_)
    session.add(new_chat)
    await session.flush()
    return new_chat

# ChatMembers -----------------

# Получить всех участников чатов (TEMP)
@with_db_session
async def select_all_chat_members(session: AsyncSession):
    stmt = select(ChatMember)
    result = await session.execute(stmt)
    members = result.scalars().all()
    return {"members": [{"chat_id": m.chat_id, "user_id": m.user_id} for m in members]}

# Получить всех участников чата с chat_id
@with_db_session
async def select_members_in_chat(session: AsyncSession, chat_id):
    stmt = select(ChatMember).where(ChatMember.chat_id == chat_id)
    result = await session.execute(stmt)
    members = result.scalars().all()
    return members

# Добавление участников чата в чат (работает вместе с create_chat)
@with_db_session
async def add_members_to_chat_direct(session: AsyncSession, chat_id: int, uid1: int, uid2: int):
    member1 = ChatMember(chat_id=chat_id, user_id=uid1)
    member2 = ChatMember(chat_id=chat_id, user_id=uid2)
    session.add_all([member1, member2])
    await session.flush()

# Messages -----------------

# Получить все сообщения (TEMP)
@with_db_session
async def select_all_messages(session: AsyncSession):
    stmt = select(Message)
    result = await session.execute(stmt)
    messages = result.scalars().all()
    return {"messages": [{"chat_id": msg.chat_id, "sender_id": msg.sender_id, "content": msg.content} for msg in messages]}

# Создание нового сообщения
async def create_new_message(session: AsyncSession, chat_id: int, sender_id: int, content: str):
    message = Message(chat_id=chat_id, sender_id=sender_id, content=content)
    session.add(message)
    await session.flush()
    return message

# Получить все сообщения чата с chat_id
@with_db_session
async def select_chat_messages(session: AsyncSession, chat_id: int):
    stmt = select(Message).where(Message.chat_id == chat_id)
    result = await session.execute(stmt)
    messages = result.scalars().all()
    return {"messages": [{"chat_id": msg.chat_id, "sender_id": msg.sender_id, "content": msg.content} for msg in messages]}

# Attachments -----------------------
