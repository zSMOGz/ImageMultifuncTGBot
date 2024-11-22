import telebot
import io

from PIL import Image, ImageOps
from telebot import types
from enum import Enum
from telebot.types import InlineKeyboardButton as Button

TOKEN = ''
bot = telebot.TeleBot(TOKEN)

user_states = {}  # тут будем хранить информацию о действиях пользователя

# набор символов из которых составляем изображение
ascii_symbols_art = '@%#*+=-:. '


class MirrorTypes(Enum):
    HORIZONTAL = 1
    VERTICAL = 2


def resize_image(image, new_width=100):
    width, height = image.size
    ratio = height / width
    new_height = int(new_width * ratio)
    return image.resize((new_width, new_height))


def grayify(image):
    return image.convert("L")


def image_to_ascii(image_stream,
                   new_width=40):
    # Переводим в оттенки серого
    image = Image.open(image_stream).convert('L')

    # меняем размер сохраняя отношение сторон
    width, height = image.size
    aspect_ratio = height / float(width)
    new_height = int(
        aspect_ratio * new_width * 0.55)  # 0,55 так как буквы выше чем шире
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
def pixelate_image(image,
                   pixel_size):
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
def invert_image(image):
    return ImageOps.invert(image)


# Отражение по горизонтали изображения
def mirror_horizontal_image(image):
    return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)


# Отражение по вертикали изображения
def mirror_vertical_image(image):
    return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message,
                 "Отправьте мне изображение, и я подумаю, что можно "
                 + "сделать!")


def process_ascii_symbols_step(message):
    global ascii_symbols_art
    ascii_symbols_art = message.text
    bot.send_message(message.chat.id, "Спасибо, теперь я знаю, чем рисовать "
                     + "ASCII арты!")


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message,
                 "Я получил ваше изображение! "
                 + "Пожалуйста, выберите, что вы хотите сделать:",
                 reply_markup=get_options_keyboard())
    user_states[message.chat.id] = {'photo': message.photo[-1].file_id}

    msg = bot.reply_to(message,
                       "Пожалуйста, введите символы для ASCII арт"
                       + "(От самого тёмного до светлого (@%#*+=-:. ):")
    bot.register_next_step_handler(msg, process_ascii_symbols_step)


def get_options_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    pixelate_btn = Button("Пикселизировать",
                          callback_data="pixelate")
    ascii_btn = Button("ASCII арт",
                       callback_data="ascii")
    invert_btn = Button("Инвертировать",
                        callback_data="invert")
    mirror_horizontal_btn = Button("Отразить по горизонтали",
                                   callback_data="mirror_horizontal")
    mirror_vertical_btn = Button("Отразить по вертикали",
                                 callback_data="mirror_vertical")
    keyboard.add(pixelate_btn,
                 ascii_btn)
    keyboard.add(invert_btn)
    keyboard.add(mirror_horizontal_btn,
                 mirror_vertical_btn)
    return keyboard


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "pixelate":
        bot.answer_callback_query(call.id,
                                  "Пикселизация изображения...")
        pixelate_and_send(call.message)
    elif call.data == "ascii":
        bot.answer_callback_query(call.id,
                                  "Преобразование изображений в ASCII "
                                  + "арт...")
        ascii_and_send(call.message)
    elif call.data == "invert":
        bot.answer_callback_query(call.id,
                                  "Инвертирование изображения...")
        invert_and_send(call.message)
    elif call.data == "mirror_horizontal":
        bot.answer_callback_query(call.id,
                                  "Отражение изображения по "
                                  + "горизонтали...")
        mirror_horizontal_and_send(call.message)
    elif call.data == "mirror_vertical":
        bot.answer_callback_query(call.id,
                                  "Отражение изображения по "
                                  + "вертикали...")
        mirror_vertical_and_send(call.message)


def pixelate_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    pixelated = pixelate_image(image, 20)

    output_stream = io.BytesIO()
    pixelated.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def ascii_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    ascii_art = image_to_ascii(image_stream)
    bot.send_message(message.chat.id,
                     f"```\n{ascii_art}\n```",
                     parse_mode="MarkdownV2")


def invert_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
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
    photo_id = user_states[message.chat.id]['photo']
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


bot.polling(none_stop=True)
