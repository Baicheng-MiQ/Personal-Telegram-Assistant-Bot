import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv('API_KEY')

import telebot
bot = telebot.TeleBot(API_KEY)

@bot.message_handler(commands=['start', 'help'])
def greet(message):
    bot.send_message(message.chat.id, 'Hello!')

@bot.message_handler(func=lambda message: True)
def echo_message(message):
    bot.reply_to(message, message.text)

if __name__ == "__main__":
    print("I'm up and running!")
    bot.polling(none_stop=True)
