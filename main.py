import os
from dotenv import load_dotenv
import telebot
from telebot import types
import requests
import urllib
import openai
from Conversation import Conversation


load_dotenv()
API_KEY = os.getenv('API_KEY')
DEEPL_KEY = os.getenv('DEEPL_KEY')
GOOGLE_SEARCH_KEY = os.getenv('GOOGLE_SEARCH_KEY')
GPT_KEY = os.getenv('GPT_KEY')
openai.api_key = GPT_KEY[7:]
USERS = [int(x) for x in os.getenv('USERS').split(',')]
bot = telebot.TeleBot(API_KEY)

def validate_user(message):
    print(message.chat.id)
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

def gpt(prompt, engine='text-davinci-003', temperature=0.1, stop=None, max_tokens=200):
    if stop is None:
        stop = ['\n\n']
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'{GPT_KEY}'
    }
    payload = {
      "model":engine,
      "prompt":prompt,
      "temperature":temperature,
      "max_tokens":max_tokens,
      "top_p":1,
      "frequency_penalty":0,
      "presence_penalty":0,
      "stop":stop
    }
    print(payload)
    response = requests.post('https://api.openai.com/v1/completions', json=payload, headers=headers)
    print(response.json())
    return response.json()['choices'][0]['text'], response.json()['usage']['total_tokens']
############
# translate
@bot.message_handler(commands=['tocn', 'toch'])
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
    help_message = "Usage: /[command] [prompt] -t [temperature] -s [stop tokens] -m [max tokens]\n\n"
    help_message += "/davinci [prompt]: Get a completion from text-davinci-002\n"
    help_message += "/curie [prompt]: Get a completion from text-curie-001\n"
    help_message += "/babbage [prompt]: Get a completion from text-babbage-001\n\n"
    help_message += "=== optional flags ===\n"
    help_message += "-t [temperature]: Set the temperature (0~1, default to 0.1)\n"
    help_message += "-s [stop]: Set the stop token, seperated by comma (default to [\"\\n\\n\\n\\n\"])\n"
    help_message += "-m [max_tokens]: Set the max tokens (default to 490)\n\n"
    help_message += "=== example ===\n"
    help_message += "/davinci What is the meaning of life? -m 100 -s [\"Hello world!\",\'\\n\']\n"
    # /davinci What is the meaning of life -t 0.5 -m 100 -s ["Hello world!","\n"] ?
    help_message += "--Calls Davinci-002 with temperature 0.5 and max tokens 100\n"
    help_message += "--and with stop token \"Hello world!\" and line break"
    bot.send_message(message.chat.id, help_message)

def parse_request(message: str) -> dict:
    request = {}
    rest = message[:]

    if ' -t ' in message:
        try:
            request['temperature'] = float(message.split(' -t ')[1].split(' ')[0])
            # remove temperature flag and its argument from rest
            rest = rest.split(' -t ')[0]
        except Exception as e:
            raise Exception('Invalid temperature: '+str(e))

    if ' -s ' in message:
        try:
            after_s_flag = message.split(' -s ')[1]
            if after_s_flag[0] != '[':
                stack = []
                s_result = []
                for i in after_s_flag:
                    if i == '"' and i in stack:
                        s_result.append(''.join(stack[1:]))
                        request['stop'] = s_result
                        break
                    else:
                        stack.append(i)
            else:
                inside_sq_bracket = after_s_flag[1:].split(']')[0]
                elements = [x[1:-1] for x in inside_sq_bracket.split('",')]
                request['stop'] = elements
            rest = rest.split(' -s ')[0]
        except Exception as e:
            raise Exception('Invalid stop token: '+str(e))

    if ' -m ' in message:
        try:
            request['max_tokens'] = int(message.split(' -m ')[1].split(' ')[0])
            rest = rest.split(' -m ')[0]
        except Exception as e:
            raise Exception('Invalid max tokens: '+str(e))

    request['prompt'] = rest
    return request

def gpt_request(message: str, engine: str) -> tuple[str, int]:
    request = parse_request(message)
    if 'temperature' not in request:
        request['temperature'] = 0.1
    if 'max_tokens' not in request:
        request['max_tokens'] = 200
    if 'stop' not in request:
        request['stop'] = ['\n\n\n\n']
    return gpt(request['prompt'], engine, request['temperature'], request['stop'], request['max_tokens'])

@bot.message_handler(commands=['davinci'])
def davinci(message):
    validate_user(message)
    try:
        response, prompt_length = gpt_request(message.text[len('/davinci'):], 'text-davinci-003')
        bot.reply_to(message, response)
        cost = (prompt_length/1000)*0.02
        bot.send_message(message.chat.id, 'Estimate Cost: $'+str(cost))
    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))

@bot.message_handler(commands=['curie'])
def curie(message):
    validate_user(message)
    try:
        response, prompt_length = gpt_request(message.text[len('/curie'):], 'text-curie-001')
        bot.reply_to(message, response)
        cost = (prompt_length/1000)*0.0002
        bot.send_message(message.chat.id, 'Estimate Cost: $'+str(cost))
    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))

@bot.message_handler(commands=['babbage'])
def babbage(message):
    validate_user(message)
    try:
        response, prompt_length = gpt_request(message.text[len('/babbage'):], 'text-babbage-001')
        bot.reply_to(message, response)
        cost = (prompt_length/1000)*0.0005
        bot.send_message(message.chat.id, 'Estimate Cost: $'+str(cost))
    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))

############
# GPT-3 applications

@bot.message_handler(commands=['philo'])
def philosopher(message):
    validate_user(message)
    try:
        prompt = f"""Below is a paragraph generated by a philosopher, which sees the human world from the outside, without the prejudices of human experience. Fully neutral and objective, the philosopher sees the world as is. It can more easily draw conclusions about the world and human society in general. 
The topic provided by the human is "{message.text[len('/philo'):]}" to which the philosopher responds with deep thought

Hmmm, interesting topic. Here is my response after a long time of thinking:

Let's think step by step."""
        response, total_tokens = gpt(prompt, 'text-davinci-003', 0.5, ['\n\n\n\n'], 400)
        # split response into paragraphs and send each paragraph separately
        for paragraph in response.split('\n\n'):
            bot.send_message(message.chat.id, paragraph)
        cost = (total_tokens/1000)*0.06
        bot.send_message(message.chat.id, 'Estimate Cost: $'+str(cost))
    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))

therapy_conversation = None

@bot.message_handler(commands=['thera'])
def therapist(message):
    global therapy_conversation # set global because we want to keep the conversation state

    # if user provided only the command
    if message.text == '/thera':
        bot.send_message(message.chat.id, 'Hi there, I am the therapist. I can help you with your problems. Just send me a message and I will help you.')
        return

    # else
    validate_user(message)
    try:
        if message.text=='/thera end':
            therapy_conversation = None
            bot.send_message(message.chat.id, 'Thanks for talking to me. I hope I helped you. If you want to talk to me again, just type /thera. ')
            bot.send_message(message.chat.id, '😊')
            return

        if therapy_conversation is None: # if conversation is not started
            bot.send_message(message.chat.id, 'Thanks for the message 😊! Please bear with me while I am typing 👩‍💻.')
            bot.send_message(message.chat.id,
                             'I will continue to talk to you, if you say anything after /thera. Simply type "/thera end" to end our conversation anytime')
            therapy_conversation = Conversation()
            # read client profile from thera_profile.txt
            with open('thera_profile.txt', 'r') as f:
                therapist_profile = f.read()

            first_few_message = [
                {"role": "system", "content": "You are a therapist who is also a mental health professional and has a vast knowledge of mental processes to her client. You are helpful, creative, clever, and very friendly. You are good at building rapport, providing feedbacks, offering guidance, and offering support."},
                {"role": "user", "content": f"Here is some basic information about myself: {therapist_profile}"},
                {"role": "assistant", "content": "Thanks for sharing your problems with me! How can I help you with today?"}
            ]

            therapy_conversation.add_messages(first_few_message)
        # END IF

        # grab current conversation and add new message
        therapy_conversation.add_message(role='user', message=message.text[len('/thera'):])
        raw_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=therapy_conversation.messages
        )
        response = raw_response.choices[0].message

        therapy_conversation.add_message(role=response.role, message=response.content)

        pure_response = response.content
        # send response paragraph by paragraph
        for paragraph in pure_response.split('\n\n'):
            if paragraph:
                try:
                    bot.send_message(message.chat.id, paragraph)
                except Exception as e:
                    bot.send_message(message.chat.id, 'Hmm, '+str(e))

        cost = raw_response.usage.total_tokens/1000*0.002
        bot.send_message(message.chat.id, 'Cost: $'+format(cost, '.5f'))


    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))

@bot.message_handler(commands=['reply'])
def flirt(message):
    validate_user(message)
    try:
        prompt = f"""This is a teen's conversation on a dating app.
They use a lot of Internet slang.
They are really smart, they understand each other well.
They have a good vibe with each other.
They are skilled in social interactions and can easily attract the attention of others.
They are very charming and can easily make friends. 
They are also very good at flirting in a polite way.

Tinder conversation:
Girl: {message.text[len('/reply'):]}
Boy:"""
        response, total_tokens = gpt(prompt, 'text-davinci-003', 0.5, ['\n\n\n\n', 'Girl:'], 400)
        # split response into paragraphs and send each paragraph separately
        bot.send_message(message.chat.id, response)
        cost = (total_tokens/1000)*0.06
        bot.send_message(message.chat.id, 'Estimate Cost: $'+str(cost))
    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))


@bot.message_handler(commands=['gptapp'])
def gpt_app_help(message):
    validate_user(message)
    help_message = "/philo [question] - Ask a philosopher\n"
    help_message += "/thera [question] - Ask a therapist\n"
    bot.send_message(message.chat.id, help_message)



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
        bot.send_message(message.chat.id, response['items'][0]['link'])
    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))
############
# /start /help
@bot.message_handler(commands=['start', 'help'])
def greet(message):
    validate_user(message)

    response = "Hi there, try these commands:\n"
    response += "/help - show this message\n"
    response += "====Translate====\n"
    response += "(/translate - show translate help and usage)\n"
    response += "====GPT-3====\n"
    response += "(/gpt show GPT help)\n"
    response += "(/gptapp show GPT-app help)\n"
    response += "====UCL====\n"
    response += "(/ucl - show UCL help)\n"
    response += "====Other====\n"
    response += "/hide - hide keyboard markup\n"

    markup = types.ReplyKeyboardMarkup()
    itemHelp = types.KeyboardButton('/help')
    itemTrUsage = types.KeyboardButton('/translate')
    itemGPT = types.KeyboardButton('/gpt')
    itemGPTApp = types.KeyboardButton('/gptapp')
    itemUCL = types.KeyboardButton('/ucl')
    itemHide = types.KeyboardButton('/hide')
    markup.add(itemHelp, itemTrUsage, itemGPT, itemGPTApp, itemUCL, itemHide)

    bot.send_message(message.chat.id, response, reply_markup=markup)

# /hide
@bot.message_handler(commands=['hide'])
def hide_keys(message):
    validate_user(message)
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, 'Sure!', reply_markup=markup)

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
    def kill_service_confirm(message_):
        if message_.text == 'y':
            bot.stop_bot()
        elif message_.text == 'n':
            bot.send_message(message_.chat.id, 'Cancelled')
        else:
            bot.send_message(message_.chat.id, 'Invalid command')
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
