import json

import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker
from models import Base, User, Word, UserWordHide
from settings import login, password, db_name
from urllib.parse import quote_plus
from sqlalchemy.sql import func

DSN = f"postgresql://{login}:{quote_plus(password)}@localhost:5432/{db_name}"
engine = sq.create_engine(DSN)
Session = sessionmaker(bind=engine)


class DataBase:
    def __init__(self):
        Base.metadata.create_all(engine)
        self.add_initial_words()

    def add_initial_words(self):
        with open("words.json", "r", encoding="utf-8") as file:
            words = json.load(file)

        session = Session()
        try:
            for word in words:
                rus = word["russian"].strip()
                eng = word["english"].strip()
                exists = (
                    session.query(Word)
                    .filter_by(target_word=eng, translate_word=rus)
                    .first()
                )
                if not exists:
                    session.add(Word(target_word=eng, translate_word=rus))
                session.commit()
        finally:
            session.close()

    def get_or_create_user(self, telegram_id):
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                return user.id, False
            else:
                user = User(telegram_id=telegram_id)
                session.add(user)
                session.commit()
                return user.id, True
        finally:
            session.close()

    def get_random_word(self, user_id=None):
        session = Session()

        try:
            query = session.query(Word)
            if user_id:
                hidden_ids = session.query(UserWordHide.word_id).filter_by(
                    user_id=user_id, hidden=True
                )
                query = query.filter(Word.id.notin_(hidden_ids))
            return query.order_by(func.random()).first()
        finally:
            session.close()

    def get_random_words(self, exclude_word=None, limit=3):
        session = Session()
        try:
            query = session.query(Word)
            if exclude_word:
                query = query.filter(Word.target_word != exclude_word)
            words = query.order_by(func.random()).limit(limit).all()
            return [word.target_word for word in words]
        finally:
            session.close()

    def add_user_word(self, telegram_id, target_word, translate_word):
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id)
                session.add(user)
                session.commit()
            word = Word(
                target_word=target_word,
                translate_word=translate_word,
                created_by_user_id=user.id,
            )
            session.add(word)
            session.commit()
            return word
        finally:
            session.close()

    def delete_user_word(self, telegram_id, target_word):
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                return False

            word = session.query(Word).filter_by(target_word=target_word).first()
            if not word:
                return False

            hide = (
                session.query(UserWordHide)
                .filter_by(user_id=user.id, word_id=word.id)
                .first()
            )
            if hide:
                hide.hidden = True
            else:
                hide = UserWordHide(user_id=user.id, word_id=word.id, hidden=True)
                session.add(hide)

            session.commit()
            return True

        finally:
            session.close()
