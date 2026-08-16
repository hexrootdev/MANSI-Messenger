from datetime import datetime
from functools import wraps
import enum

import os
from dotenv import load_dotenv

from sqlalchemy import select, String, Integer, Boolean, ForeignKey, Enum, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

load_dotenv()

DATABASE_URL = os.getenv("DB_URL")

engine = create_async_engine(DATABASE_URL, echo=True)

async_session = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False, 
    class_=AsyncSession
)

class ChatType(enum.Enum):
    DIRECT = "direct"
    GROUP = "group"

class AttachmentType(enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(255), nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now() 
    )

class Chat(Base):
    __tablename__ = "chats"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    type: Mapped[ChatType] = mapped_column(Enum(ChatType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now() 
    )

class ChatMember(Base):
    __tablename__ = "chat_members"
    
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )

    chat: Mapped[Chat] = relationship()
    user: Mapped[User] = relationship()

class Message(Base):
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now() 
    )

    chat: Mapped[Chat] = relationship()
    sender: Mapped[User] = relationship()

class Attachment(Base):
    __tablename__ = "attachments"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), nullable=False)
    type: Mapped[AttachmentType] = mapped_column(Enum(AttachmentType), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now() 
    )

    message: Mapped[Message] = relationship()


def with_db_session(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            async with session.begin():
                return await func(session, *args, **kwargs)
    return wrapper


async def create_db():
    async with engine.begin() as conn:
        #await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)