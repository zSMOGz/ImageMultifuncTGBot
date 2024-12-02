import telebot
import io

from PIL import Image, ImageOps
from telebot import types
from enum import Enum
from telebot.types import InlineKeyboardButton as Button
import random

TOKEN = ''
MAX_WIDTH_STICKER = 512
JOKES = ["""Почему комедии Аристофана были такие смешные? 
Есть два варианта:  либо потому что ори и 100 фан, 
либо потому что, кто не смеётся, будет аристофан.""",
         """- Третий разряд по шахматам!
- Чёрт, это самые бессмысленные пытки, которые я видел!
- Ты прав, они не колятся. Неси топор!""",
         """- Этот кроссовок - президент Франции.
- Почему?
- Мокр он...""",
         """- Я занимаюсь пилатесом...
- Если ты пила Tess, не значит, что ты занималась пилатесом""",
         """Хотелось бы отдохнуть 100 лет, ведь я - чила век.""",
         """Молоко ультравпастьтебевсованное."""]
COMPLEMENTS = ["""Ты красивый, как мусор в лучах закатного солнца""",
               """У тебя такая нежная кожа, как будто поженились поверхность
луны и наждачка""",
               """Твои волосы словно лунный свет - они повсюду""",
               """Ты похож на пакет""",
               """Видела тебя вчера в ресторане, ты так очаровательно пытался 
купить просрочку"""]

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


# Тепловая карта изображения
def convert_to_heatmap_image(image):
    # Преобразуем изображение в оттенки серого
    image = image.convert('L')

    return ImageOps.colorize(image, (0, 0, 255), (255, 0, 0))


# Случайная шутка
def get_random_joke():
    return random.choice(JOKES)


# Случайный комплемент
def get_random_complements():
    return random.choice(COMPLEMENTS)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message,
                 "Отправьте мне изображение, и я подумаю, что можно "
                 + "сделать!")


@bot.message_handler(commands=['text'])
def send_welcome(message):
    bot.reply_to(message,
                 "Выберите, что вы хотите сделать:",
                 reply_markup=get_text_options_keyboard())


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
                 reply_markup=get_photo_options_keyboard())
    user_states[message.chat.id] = {'photo': message.photo[-1].file_id}

    msg = bot.reply_to(message,
                       "Пожалуйста, введите символы для ASCII арт"
                       + "(От самого тёмного до светлого (@%#*+=-:. ):")
    bot.register_next_step_handler(msg, process_ascii_symbols_step)


def get_photo_options_keyboard():
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
    convert_to_heatmap_btn = Button("Преобразовать в тепловую карту ",
                                    callback_data="convert_to_heatmap")
    keyboard.add(pixelate_btn,
                 ascii_btn)
    keyboard.add(invert_btn)
    keyboard.add(mirror_horizontal_btn,
                 mirror_vertical_btn)
    keyboard.add(convert_to_heatmap_btn)
    return keyboard


def get_text_options_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    random_joke_btn = Button("Случайная шутка",
                             callback_data="random_joke")
    random_component_btn = Button("Случайный комплемент",
                                  callback_data="random_component")
    keyboard.add(random_joke_btn, random_component_btn)
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
    elif call.data == "convert_to_heatmap":
        bot.answer_callback_query(call.id,
                                  "Преобразование изображения в"
                                  + "тепловую карту...")
        convert_to_heatmap_and_send(call.message)
    elif call.data == "random_joke":
        bot.answer_callback_query(call.id,
                                  "Случайная шутка...")
        random_joke_and_send(call.message)
    elif call.data == "random_component":
        bot.answer_callback_query(call.id,
                                  "Случайная комплемент...")
        random_complement_and_send(call.message)


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


def convert_to_heatmap_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    image_converted = convert_to_heatmap_image(image)

    output_stream = io.BytesIO()
    image_converted.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def random_joke_and_send(message):
    joke = get_random_joke()
    bot.send_message(message.chat.id, joke)


def random_complement_and_send(message):
    complement = get_random_complements()
    bot.send_message(message.chat.id, complement)


bot.polling(none_stop=True)
