import random

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from db_words import DataBase

from settings import bot_token

print("Start telegram bot...")

state_storage = StateMemoryStorage()
bot = TeleBot(bot_token, state_storage=state_storage)
db = DataBase()

buttons = []


def show_hint(*lines):
    return "\n".join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


def build_markup(texts):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for t in texts:
        markup.add(types.KeyboardButton(t))
    return markup


class Command:
    ADD_WORD = "Добавить слово ➕"
    DELETE_WORD = "Удалить слово🔙"
    NEXT = "Дальше ⏭"

HELP_TEXT = """
Принцип работы бота:

1. Бот показывает слово на английском и несколько вариантов перевода на русском.
2. Выбирайте правильный вариант:
   - ✅ Правильный ответ: бот подтверждает и предлагает "Дальше ⏭".
   - ❌ Неправильный ответ: бот отмечает крестиком и дает попробовать снова.
3. Можно добавлять свои слова и скрывать слова для себя.

Команды и кнопки:

/start - запуск бота
/cards - показать карточки со словами
Дальше ⏭ - перейти к следующему слову
Добавить слово ➕ - добавить новое слово
Удалить слово🔙 - скрыть слово для себя
/help - показать эту справку
"""


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()
    adding_word = State()
    adding_translation = State()


@bot.message_handler(commands=["cards", "start"])
def create_cards(message):
    user_id, is_new = db.get_or_create_user(message.from_user.id)
    if is_new:
        bot.send_message(
            message.chat.id,
            "Привет 👋 Давай попрактикуемся в английском языке. "
            "Тренировки можешь проходить в удобном для себя темпе."
            "Для вызова справки по использованию бота напиши команду /help",
        )

    word = db.get_random_word(user_id=user_id)
    target_word = word.target_word
    translate = word.translate_word
    others = db.get_random_words(exclude_word=target_word, limit=3)
    options = [target_word] + others
    random.shuffle(options)
    btn_texts = options + [Command.NEXT, Command.ADD_WORD, Command.DELETE_WORD]
    markup = build_markup(btn_texts)

    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["target_word"] = target_word
        data["translate_word"] = translate
        data["buttons"] = btn_texts
    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(message.chat.id, HELP_TEXT)


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data.get("target_word")

        if not target_word:
            bot.send_message(
                message.chat.id,
                "Сейчас нет активного слова для удаления, нажми 'Дальше ⏭'",
            )
            return

        user_id = message.from_user.id
        delete = db.delete_user_word(user_id, target_word)

        if delete:
            bot.send_message(message.chat.id, f"Слово '{target_word}' удалено!")
        else:
            bot.send_message(message.chat.id, "Слово не найдено или нельзя удалить")


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    bot.set_state(message.from_user.id, MyStates.adding_word, message.chat.id)
    bot.send_message(message.chat.id, "Введите слово на английском:")


@bot.message_handler(state=MyStates.adding_word)
def get_english_word(message):
    bot.set_state(message.from_user.id, MyStates.adding_translation, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["new_target_word"] = message.text
    bot.send_message(message.chat.id, "Теперь введите перевод:")


@bot.message_handler(state=MyStates.adding_translation)
def get_translation(message):
    user_id = message.from_user.id
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data["new_target_word"]
        translate_word = message.text

    db.add_user_word(user_id, target_word, translate_word)
    bot.send_message(message.chat.id, f"Слово '{target_word}' добавлено!")
    bot.delete_state(user_id, message.chat.id)


@bot.message_handler(func=lambda message: True, content_types=["text"])
def message_reply(message):
    text = message.text

    if text in (Command.ADD_WORD, Command.NEXT, Command.DELETE_WORD):
        return

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data.get("target_word")
        translate_word = data.get("translate_word")
        buttons = data.get("buttons", [])

        if not target_word or not translate_word:
            bot.send_message(message.chat.id, "Нажмите /start или /cards, чтобы начать")
            return

        if text == target_word:
            hint = show_hint("Отлично!❤", show_target(data))
            buttons = [Command.NEXT, Command.ADD_WORD, Command.DELETE_WORD]

        else:
            updated = []
            for btn in buttons:
                if btn == text and not btn.endswith("❌"):
                    updated.append(btn + "❌")

                else:
                    updated.append(btn)
            buttons = updated

            hint = show_hint(
                "Допущена ошибка!",
                f"Попробуй ещё раз вспомнить слово 🇷🇺{translate_word}",
            )

        data["buttons"] = buttons

    markup = build_markup(buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)
