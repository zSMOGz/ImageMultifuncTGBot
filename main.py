import telebot
import io

from PIL import Image, ImageOps
from telebot import types
from enum import Enum
from telebot.types import InlineKeyboardButton as Button
import random

from config import (
    TOKEN,
    MAX_WIDTH_STICKER,
    DEFAULT_ASCII_WIDTH,
    DEFAULT_PIXEL_SIZE,
    MAX_MESSAGE_LENGTH,
    HEATMAP_COLD_COLOR,
    HEATMAP_HOT_COLOR,
    MESSAGES,
    BUTTON_LABELS,
    CALLBACKS,
    CALLBACK_ANSWERS,
    ASCII_SYMBOLS,
    JOKES,
    COMPLEMENTS,
    COIN_RESULTS,
    IMAGE_FORMATS,
    IMAGE_PARAMS,
    MESSAGE_PARAMS,
    BOT_PARAMS,
    STATE_KEYS
)

from typing import Dict, Optional, Tuple, Union, Callable, Any
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup

bot = telebot.TeleBot(TOKEN)

# Типы для состояний пользователя
UserState = Dict[int, Dict[str, str]]
user_states: UserState = {}

# набор символов из которых составляем изображение
ascii_symbols_art = ASCII_SYMBOLS


class MirrorTypes(Enum):
    HORIZONTAL = 1
    VERTICAL = 2


def resize_image(image: Image.Image, new_width: int = 100) -> Image.Image:
    """
    Изменяет размер изображения с сохранением пропорций.
    
    Args:
        image: Исходное изображение
        new_width: Новая ширина изображения
        
    Returns:
        Изображение с измененным размером
    """
    width, height = image.size
    ratio = height / width
    new_height = int(new_width * ratio)
    return image.resize((new_width, new_height))


def resize_for_sticker(image, new_width=100):
    width, height = image.size

    if height > width:
        new_height = MAX_WIDTH_STICKER
        ratio = width / height
        new_width = int(new_height * ratio)
    else:
        new_width = MAX_WIDTH_STICKER
        ratio = height / width
        new_height = int(new_width * ratio)

    return image.resize((new_width, new_height))


def grayify(image):
    return image.convert("L")


def image_to_ascii(image_stream: io.BytesIO, new_width: int = DEFAULT_ASCII_WIDTH) -> str:
    """
    Преобразует изображение в ASCII-арт.
    
    Args:
        image_stream: Поток с изображением
        new_width: Желаемая ширина ASCII-арта в символах
        
    Returns:
        Строка с ASCII-артом
    """
    image = Image.open(image_stream).convert(IMAGE_PARAMS['COLOR_MODE_L'])
    width, height = image.size
    aspect_ratio = height / float(width)
    new_height = int(aspect_ratio * new_width * IMAGE_PARAMS['ASPECT_RATIO_MULTIPLIER'])
    img_resized = image.resize((new_width, new_height))

    img_str = pixels_to_ascii(img_resized)
    img_width = img_resized.width

    max_characters = 4000 - (new_width + 1)
    max_rows = max_characters // (new_width + 1)

    ascii_art = ""
    for i in range(0, min(max_rows * img_width, len(img_str)), img_width):
        ascii_art += img_str[i:i + img_width] + "\n"

    return ascii_art


def pixels_to_ascii(image):
    pixels = image.getdata()
    characters = ""
    for pixel in pixels:
        characters += ascii_symbols_art[pixel * len(ascii_symbols_art) // 256]
    return characters


# Огрубляем изображение
def pixelate_image(image: Image.Image, pixel_size: int) -> Image.Image:
    """
    Пикселизует изображение с заданным размером пикселя.
    
    Args:
        image: Исходное изображение
        pixel_size: Размер пикселя
        
    Returns:
        Пикселизованное изображение
    """
    image = image.resize(
        (image.size[0] // pixel_size, image.size[1] // pixel_size),
        Image.NEAREST
    )
    image = image.resize(
        (image.size[0] * pixel_size, image.size[1] * pixel_size),
        Image.NEAREST
    )
    return image


# Инвертирование изображения
def invert_image(image: Image.Image) -> Image.Image:
    """
    Инвертирует цвета изображения.
    
    Args:
        image: Исходное изображение
        
    Returns:
        Изображение с инвертированными цветами
    """
    return ImageOps.invert(image)


# Отражение по горизонтали изображения
def mirror_horizontal_image(image: Image.Image) -> Image.Image:
    """
    Отражает изображение по горизонтали.
    
    Args:
        image: Исходное изображение
        
    Returns:
        Отраженное по горизонтали изображение
    """
    return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)


# Отражение по вертикали изображения
def mirror_vertical_image(image: Image.Image) -> Image.Image:
    """
    Отражает изображение по вертикали.
    
    Args:
        image: Исходное изображение
        
    Returns:
        Отраженное по вертикали изображение
    """
    return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)


# Тепловая карта изображения
def convert_to_heatmap_image(image: Image.Image) -> Image.Image:
    """
    Преобразует изображение в тепловую карту.
    
    Args:
        image: Исходное изображение
        
    Returns:
        Изображение в виде тепловой карты
    """
    image = image.convert(IMAGE_PARAMS['COLOR_MODE_L'])
    return ImageOps.colorize(image, HEATMAP_COLD_COLOR, HEATMAP_HOT_COLOR)


# Случайная шутка
def get_random_joke():
    return random.choice(JOKES)


# Случайный комплемент
def get_random_complements():
    return random.choice(COMPLEMENTS)


def flip_coin():
    return random.choice(COIN_RESULTS)


class ImageHandlers:
    @staticmethod
    def handle_photo(message: Message) -> None:
        bot.reply_to(message, MESSAGES['PHOTO_RECEIVED'],
                     reply_markup=get_photo_options_keyboard())
        user_states[message.chat.id] = {
            STATE_KEYS['PHOTO']: message.photo[-1].file_id
        }

    @staticmethod
    def pixelate_and_send(message: Message) -> None:
        if image := get_image_from_message(message):
            pixelated = pixelate_image(image, 20)
            send_image(message.chat.id, pixelated)


class TextHandlers:
    @staticmethod
    def handle_start(message):
        bot.reply_to(message, MESSAGES['START'])

    @staticmethod
    def handle_text_commands(message):
        bot.reply_to(message,
                     MESSAGES['CHOOSE_ACTION'],
                     reply_markup=get_text_options_keyboard())

    @staticmethod
    def random_joke_and_send(message):
        joke = get_random_joke()
        bot.send_message(message.chat.id, joke)

    @staticmethod
    def random_complement_and_send(message):
        complement = get_random_complements()
        bot.send_message(message.chat.id, complement)

    @staticmethod
    def flip_coin_and_send(message):
        result = flip_coin()
        bot.send_message(message.chat.id, f"Монетка показала: {result}")


class CallbackHandlers:
    HandlerType = Tuple[Callable[[Message], None], str]
    HandlersDict = Dict[str, HandlerType]

    @staticmethod
    def handle_callback(call: CallbackQuery) -> None:
        handlers: CallbackHandlers.HandlersDict = {
            "pixelate": (ImageHandlers.pixelate_and_send, MESSAGES['PIXELATE']),
            "ascii": (ascii_and_send, MESSAGES['ASCII']),
            "invert": (invert_and_send, MESSAGES['INVERT']),
            "mirror_horizontal": (mirror_horizontal_and_send, MESSAGES['MIRROR_H']),
            "mirror_vertical": (mirror_vertical_and_send, MESSAGES['MIRROR_V']),
            "convert_to_heatmap": (convert_to_heatmap_and_send, MESSAGES['HEATMAP']),
            "random_joke": (TextHandlers.random_joke_and_send, MESSAGES['JOKE']),
            "random_component": (TextHandlers.random_complement_and_send, MESSAGES['COMPLEMENT']),
            "flip_coin": (TextHandlers.flip_coin_and_send, MESSAGES['FLIP_COIN'])
        }

        if call.data in handlers:
            handler, answer_text = handlers[call.data]
            bot.answer_callback_query(call.id, answer_text)
            handler(call.message)


# Регистрация обработчиков
@bot.message_handler(commands=['start', 'help'])
def start_command(message):
    TextHandlers.handle_start(message)

@bot.message_handler(commands=['text'])
def text_command(message):
    TextHandlers.handle_text_commands(message)

@bot.message_handler(content_types=['photo'])
def photo_message(message):
    ImageHandlers.handle_photo(message)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    CallbackHandlers.handle_callback(call)


def process_ascii_symbols_step(message: Message) -> None:
    """Обрабатывает ввод символов для ASCII арта"""
    global ascii_symbols_art
    ascii_symbols_art = message.text
    bot.send_message(message.chat.id, MESSAGES['ASCII_SYMBOLS_THANKS'])


def get_photo_options_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с опциями для фото"""
    keyboard = types.InlineKeyboardMarkup()
    pixelate_btn = Button(BUTTON_LABELS['PIXELATE'],
                          callback_data=CALLBACKS['PIXELATE'])
    ascii_btn = Button(BUTTON_LABELS['ASCII'],
                       callback_data=CALLBACKS['ASCII'])
    invert_btn = Button(BUTTON_LABELS['INVERT'],
                        callback_data=CALLBACKS['INVERT'])
    mirror_horizontal_btn = Button(BUTTON_LABELS['MIRROR_H'],
                                   callback_data=CALLBACKS['MIRROR_H'])
    mirror_vertical_btn = Button(BUTTON_LABELS['MIRROR_V'],
                                 callback_data=CALLBACKS['MIRROR_V'])
    convert_to_heatmap_btn = Button(BUTTON_LABELS['HEATMAP'],
                                    callback_data=CALLBACKS['HEATMAP'])
    keyboard.add(pixelate_btn,
                 ascii_btn)
    keyboard.add(invert_btn)
    keyboard.add(mirror_horizontal_btn,
                 mirror_vertical_btn)
    keyboard.add(convert_to_heatmap_btn)
    return keyboard


def get_text_options_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    random_joke_btn = Button(BUTTON_LABELS['JOKE'],
                             callback_data=CALLBACKS['JOKE'])
    random_component_btn = Button(BUTTON_LABELS['COMPLEMENT'],
                                  callback_data=CALLBACKS['COMPLEMENT'])
    flip_coin_btn = Button(BUTTON_LABELS['FLIP_COIN'],
                           callback_data=CALLBACKS['FLIP_COIN'])
    keyboard.add(random_joke_btn, random_component_btn)
    keyboard.add(flip_coin_btn)
    return keyboard


def ascii_and_send(message):
    photo_id = user_states[message.chat.id][STATE_KEYS['PHOTO']]
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    ascii_art = image_to_ascii(image_stream)
    bot.send_message(
        message.chat.id,
        f"{MESSAGE_PARAMS['CODE_BLOCK']}\n{ascii_art}\n{MESSAGE_PARAMS['CODE_BLOCK']}",
        parse_mode=MESSAGE_PARAMS['PARSE_MODE']
    )


def invert_and_send(message):
    photo_id = user_states[message.chat.id][STATE_KEYS['PHOTO']]
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    image_inverted = invert_image(image)

    output_stream = io.BytesIO()
    image_inverted.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def mirror_horizontal_and_send(message):
    mirror_and_send(message, MirrorTypes.HORIZONTAL)


def mirror_vertical_and_send(message):
    mirror_and_send(message, MirrorTypes.VERTICAL)


def mirror_and_send(message, mirror_type: MirrorTypes):
    photo_id = user_states[message.chat.id][STATE_KEYS['PHOTO']]
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)

    if mirror_type == MirrorTypes.HORIZONTAL:
        image_mirrored = mirror_horizontal_image(image)
    else:
        image_mirrored = mirror_vertical_image(image)

    output_stream = io.BytesIO()
    image_mirrored.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def convert_to_heatmap_and_send(message):
    photo_id = user_states[message.chat.id][STATE_KEYS['PHOTO']]
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    image_converted = convert_to_heatmap_image(image)

    output_stream = io.BytesIO()
    image_converted.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def get_image_from_message(message: Message) -> Optional[Image.Image]:
    """Получает изображение из сообщения"""
    try:
        photo_id = user_states[message.chat.id][STATE_KEYS['PHOTO']]
        file_info = bot.get_file(photo_id)
        downloaded_file = bot.download_file(file_info.file_path)
        return Image.open(io.BytesIO(downloaded_file))
    except Exception:
        return None


def send_image(chat_id: int, image: Image.Image, 
               format: str = IMAGE_FORMATS['JPEG']) -> None:
    """Отправляет изображение в чат"""
    output_stream = io.BytesIO()
    image.save(output_stream, format=format)
    output_stream.seek(0)
    bot.send_photo(chat_id, output_stream)


bot.polling(none_stop=BOT_PARAMS['NONE_STOP'])
