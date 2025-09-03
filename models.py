from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    words = relationship("Word", back_populates="user")


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True)
    target_word = Column(String, nullable=False)
    translate_word = Column(String, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="words")


class UserWordHide(Base):
    __tablename__ = "user_word_hides"
    __table_args__ = (UniqueConstraint("user_id", "word_id", name="uq_user_word_hide"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    hidden = Column(Boolean, default=True)
