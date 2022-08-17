import os
from dotenv import load_dotenv
import telebot
import requests
import urllib

load_dotenv()
API_KEY = os.getenv('API_KEY')
DEEPL_KEY = os.getenv('DEEPL_KEY')
GOOGLE_SEARCH_KEY = os.getenv('GOOGLE_SEARCH_KEY')
USERS = [int(x) for x in os.getenv('USERS').split(',')]
bot = telebot.TeleBot(API_KEY)

def validate_user(message):
    if message.chat.id in USERS:
        pass
    else:
        bot.send_message(message.chat.id, 'Invalid account')
        raise Exception('Invalid account')

def translate(text, fromLang, toLang):
    # https://www.deepl.com/docs-api/introduction/
    url = "https://api-free.deepl.com/v2/translate"
    params = {
        'text': text,
        'source_lang': fromLang,
        'target_lang': toLang,
        'auth_key': DEEPL_KEY
    }
    response = requests.post(url, params=params)
    return response.json()['translations'][0]['text']

############
# translate
@bot.message_handler(commands=['tocn'])
def translate_to_chinese(message):
    validate_user(message)
    try:
        text = message.text[len('/tocn'):]
        response = translate(text, 'EN', 'ZH')
        bot.send_message(message.chat.id, response)
    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))

@bot.message_handler(commands=['toen'])
def translate_to_english(message):
    validate_user(message)
    try:
        text = message.text[len('/toen'):]
        response = translate(text, 'ZH', 'EN-GB')
        bot.send_message(message.chat.id, response)
    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))

@bot.message_handler(commands=['translate'])
def translate_usage(message):
    validate_user(message)
    url = "https://api-free.deepl.com/v2/usage"
    params = {
        'auth_key': DEEPL_KEY
    }
    response = requests.post(url, params=params).json()
    parsed_response = "/toch: From English to Chinese\n/toen: From Chinese to English\n"
    parsed_response += "=Translate usage:\n"
    parsed_response += "Used " + str(response['character_count']) + "\n"
    parsed_response += "Limit: " + str(response['character_limit']) + "\n"
    parsed_response += str((response['character_count'] / response['character_limit'])*100) + "%"
    bot.send_message(message.chat.id, parsed_response)

############
# GPT-3
@bot.message_handler(commands=['gpt'])
def gpt_help(message):
    validate_user(message)


############
# ucl
@bot.message_handler(commands=['ucl'])
def ucl_help(message):
    validate_user(message)
    # https://uclapi.com/
    help_message = "/ucl: Get UCL help\n"
    help_message += "/ucls <query>: Search UCL\n"
    help_message += "Other functions will be added soon"
    bot.send_message(message.chat.id, help_message)

@bot.message_handler(commands=['ucls'])
def ucl_search(message):
    # https://programmablesearchengine.google.com/controlpanel/overview?cx=55098824b39c44e98
    validate_user(message)
    try:
        q = "UCL"+message.text[len('/ucls'):]
        google_raw_q = "https://www.google.com/search?q=" + urllib.parse.quote(q)
        bot.send_message(message.chat.id, google_raw_q)

        url = "https://www.googleapis.com/customsearch/v1"
        cx = "55098824b39c44e98"
        params = {
            'key': GOOGLE_SEARCH_KEY,
            'cx': cx,
            'q': q
        }
        response = requests.get(url, params=params).json()
        bot.send_message(message.chat.id, response['items'][1]['link'])
        bot.send_message(message.chat.id, response['items'][0]['link'])
        # display best result LAST: reachable by my thumb
    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))
############
# /start /help
@bot.message_handler(commands=['start', 'help'])
def greet(message):
    from telebot import types
    validate_user(message)

    response = "Hi there, try these commands:\n"
    response += "/help - show this message\n"
    response += "====Translate====\n"
    response += "(/translate - show translate help and usage)\n"
    response += "====GPT-3====\n"
    response += "(/gpt show GPT help)\n"
    response += "====UCL====\n"
    response += "(/ucl - show UCL help)\n"

    markup = types.ReplyKeyboardMarkup()
    itemHelp = types.KeyboardButton('/help')
    itemTrUsage = types.KeyboardButton('/translate')
    itemGPT = types.KeyboardButton('/gpt')
    itemUCL = types.KeyboardButton('/ucl')
    markup.add(itemHelp, itemTrUsage, itemGPT, itemUCL)

    bot.send_message(message.chat.id, response, reply_markup=markup)

############
# /echo
@bot.message_handler(commands=['echo'])
def echo_message(message):
    validate_user(message)
    bot.send_message(message.chat.id, message.text[len('/echo'):])

############
# /kill this bot service
@bot.message_handler(commands=['kill'])
def kill_service(message):
    def kill_service_confirm(message):
        if message.text == 'y':
            bot.stop_bot()
        elif message.text == 'n':
            bot.send_message(message.chat.id, 'Cancelled')
        else:
            bot.send_message(message.chat.id, 'Invalid command')
    validate_user(message)
    # ask if him serious, if yes, run bot.stop_bot()
    bot.send_message(message.chat.id, 'This shuts down your entire bot service. May need tremendous effort to restart.')
    bot.send_message(message.chat.id, 'Are you serious? (y/n)')
    bot.register_next_step_handler(message, kill_service_confirm)

if __name__ == "__main__":
    print("I'm up and running!")
    bot.send_message(USERS[0], "I'm up and running!")
    bot.infinity_polling()
    bot.send_message(USERS[0], "I'm down!")
