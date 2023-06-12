import os
from dotenv import load_dotenv
import telebot
from telebot import types
import requests
import urllib
import openai
from Conversation import Conversation, User, Assistant, System
import random
from JSON_helper import JSON_helper


load_dotenv()
API_KEY = os.getenv('API_KEY')
DEEPL_KEY = os.getenv('DEEPL_KEY')
GOOGLE_SEARCH_KEY = os.getenv('GOOGLE_SEARCH_KEY')
ELEVEN_LABS_KEY = os.getenv('ELEVEN_LABS_KEY')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
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

def textToSpeech(text: str, path = "thisSpeech.mp3"):
    """
    :param text: text to be converted to speech
    :param path: path to save the mp3 file
    :return: path to the mp3 file
    """

    # client = texttospeech.TextToSpeechClient()
    #
    # # Set the text input to be synthesized
    # synthesis_input = texttospeech.SynthesisInput(text=text)
    # voice = texttospeech.VoiceSelectionParams(
    #     language_code="en-US", name="en-US-Neural2-C"
    # )
    #
    # audio_config = texttospeech.AudioConfig(
    #     audio_encoding=texttospeech.AudioEncoding.MP3,
    #     pitch=0.3,
    # )
    #
    # response = client.synthesize_speech(
    #     input=synthesis_input, voice=voice, audio_config=audio_config
    # )
    # ABOVE is googled, below is ElevenLabs
    import requests
    sound_id = "mE6ZUnCVC8Cl2rEKPE0Z"

    url = "https://api.elevenlabs.io/v1/text-to-speech/" + sound_id

    payload = {
        "text": f"{text}",
        "voice_settings": {
            "stability": 0.8,
            "similarity_boost": 0.7
        }
    }
    headers = {
        "xi-api-key": ELEVEN_LABS_KEY,
        "Content-Type": "application/json",
        "accept": "audio/mpeg"
    }

    response = requests.request("POST", url, json=payload, headers=headers)

    if response.status_code == 200:
    # The response's audio_content is binary.
        with open(path, "wb") as out:
            # Write the response to the output file.
            out.write(response.content)
            return path
    else:
        raise Exception("Error: Failed to get audio")

def md_to_html(md_text: str) -> str:
  import markdown
  from markdown.extensions.codehilite import CodeHiliteExtension

  with open("./template.html", 'r') as t:
    template = t.read()

  # Markdown to HTML conversion
  html = markdown.markdown(md_text, extensions=[CodeHiliteExtension(), "fenced_code", "tables"])

  # Fill the template with the converted HTML
  document = template.replace("{content}", html)
  return document

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





############
# GPT applications
chat_conversation = None
@bot.message_handler(commands=['chat']) # vanilla chat
def chat(message):
    global chat_conversation # set global because we want to keep the conversation state
    bot.send_chat_action(message.chat.id, 'typing', timeout=600)
    # if user provided only the command
    if message.text == '/chat':
        bot.send_message(message.chat.id, "Hi there, how can I help you?"
                                          "\n\nType /chat end to end the conversation."
                                          "\nType /chat source to get the source code of the last message."
                                          "\nType /chat html to get the html of the last message.")
        return

    # else
    validate_user(message)
    try:
        if message.text=='/chat end':
            if chat_conversation:
                bot.send_message(message.chat.id, 'Cost: $' + format(chat_conversation.total_cost, '.5f'))
            chat_conversation = None
            return

        if message.text=='/chat source':
            if chat_conversation:
                bot.send_message(message.chat.id, chat_conversation.messages[-1].content)
            return

        if message.text=='/chat html':
            if chat_conversation:
                html = md_to_html(chat_conversation.messages[-1].content)
                # save to file and send to user
                with open('chat.html', 'w') as f:
                    f.write(html)
                with open('chat.html', 'rb') as f:
                    bot.send_document(message.chat.id, f)
            return

        if message.text=='/chat img':
            if chat_conversation:
                from html2image import Html2Image
                hti = Html2Image()
                hti.screenshot(html_str=md_to_html(chat_conversation.messages[-1].content), save_as='chat.png',size=(500, 1000))
                with open('chat.png', 'rb') as f:
                    bot.send_photo(message.chat.id, f)
            return

        if chat_conversation is None: # if conversation is not started
            chat_conversation = Conversation("gpt-4")
            first_few_message = [System("You are a helpful assistant. Your answer should be concise. "
                                        "You reply in richly formatted markdown, and write formulae in $\LaTeX$.")]
            chat_conversation.add_messages(first_few_message)

        # grab current conversation and add new message
        chat_conversation.add_message(User(message.text[len('/chat'):]))
        raw_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=chat_conversation.to_openai(),
            temperature=0.1,
            stream=True,
        )
        full_response = ""
        this_message = None
        for response in raw_response:
            if 'content' in response.choices[0].delta:
                if full_response == "":
                    full_response += response.choices[0].delta.content
                    this_message = bot.send_message(message.chat.id, full_response)
                else:
                    full_response += response.choices[0].delta.content
                    if random.random() < 0.3 and this_message.text.strip() != full_response.strip():
                        this_message = bot.edit_message_text(full_response, message.chat.id, this_message.message_id)

        if full_response:
            bot.edit_message_text(full_response, message.chat.id, this_message.message_id, parse_mode='Markdown')

        chat_conversation.add_message(Assistant(full_response))
        _this_cost = chat_conversation.get_cost() # aggregate cost

    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))


chat3_conversation = None
@bot.message_handler(commands=['chat3']) # vanilla chat3
def chat(message):
    global chat3_conversation # set global because we want to keep the conversation state
    bot.send_chat_action(message.chat.id, 'typing', timeout=600)
    # if user provided only the command
    if message.text == '/chat3':
        bot.send_message(message.chat.id, "Hi there, how can I help you?"
                                          "\n\nType /chat3 end to end the conversation."
                                          "\nType /chat3 source to get the source code of the last message."
                                          "\nType /chat3 html to get the html of the last message.")
        return

    # else
    validate_user(message)
    try:
        if message.text=='/chat3 end':
            if chat3_conversation:
                bot.send_message(message.chat.id, 'Cost: $' + format(chat3_conversation.total_cost, '.5f'))
            chat3_conversation = None
            return

        if message.text=='/chat3 source':
            if chat3_conversation:
                bot.send_message(message.chat.id, chat3_conversation.messages[-1].content)
            return

        if message.text=='/chat3 html':
            if chat3_conversation:
                html = md_to_html(chat3_conversation.messages[-1].content)
                # save to file and send to user
                with open('chat.html', 'w') as f:
                    f.write(html)
                with open('chat.html', 'rb') as f:
                    bot.send_document(message.chat.id, f)
            return

        if message.text=='/chat3 img':
            if chat3_conversation:
                from html2image import Html2Image
                hti = Html2Image()
                hti.screenshot(html_str=md_to_html(chat3_conversation.messages[-1].content), save_as='chat.png',size=(500, 1000))
                with open('chat.png', 'rb') as f:
                    bot.send_photo(message.chat.id, f)
            return

        if chat3_conversation is None: # if conversation is not started
            chat3_conversation = Conversation("gpt-3.5-turbo")
            first_few_message = [System("You are a helpful assistant. Your answer should be concise. "
                                        "You reply in richly formatted markdown, and write formulae in $\LaTeX$.")]
            chat3_conversation.add_messages(first_few_message)

        # grab current conversation and add new message
        chat3_conversation.add_message(User(message.text[len('/chat3'):]))
        raw_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=chat3_conversation.to_openai(),
            temperature=0.1,
            stream=True,
        )
        full_response = ""
        this_message = None
        for response in raw_response:
            if 'content' in response.choices[0].delta:
                if full_response == "":
                    full_response += response.choices[0].delta.content
                    this_message = bot.send_message(message.chat.id, full_response)
                else:
                    full_response += response.choices[0].delta.content
                    if random.random() < 0.3 and this_message.text.strip() != full_response.strip():
                        this_message = bot.edit_message_text(full_response, message.chat.id, this_message.message_id)

        if full_response:
            bot.edit_message_text(full_response, message.chat.id, this_message.message_id, parse_mode='Markdown')

        chat3_conversation.add_message(Assistant(full_response))
        _this_cost = chat3_conversation.get_cost() # aggregate cost

    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))

therapy_conversation = None
@bot.message_handler(commands=['thera'])
def therapist(message):
    global therapy_conversation # set global because we want to keep the conversation state
    bot.send_chat_action(message.chat.id, 'typing', timeout=60)
    # if user provided only the command
    if message.text == '/thera':
        bot.send_message(message.chat.id,
                         'Hi there, I am the therapist. I can help you with your problems. '
                         'Just send me a message and I will help you.')
        return

    # else
    validate_user(message)
    try:
        if message.text=='/thera end':
            if therapy_conversation:
                bot.send_message(message.chat.id, 'Cost: $' + format(therapy_conversation.total_cost, '.5f'))
            therapy_conversation = None
            bot.send_message(message.chat.id, 'Thanks for talking to me. I hope I helped you. '
                                              'If you want to talk to me again, just type /thera. ')
            bot.send_message(message.chat.id, '😊')
            return

        if message.text=='/thera source':
            if therapy_conversation:
                bot.send_message(message.chat.id, str(therapy_conversation.to_openai()))
            return

        if therapy_conversation is None: # if conversation is not started
            therapy_conversation = Conversation("gpt-4")

            with open("prompt.txt", "r") as f:
                prompt = f.read()

            with open("thera_profile.txt", "r") as f:
                profile = f.read()

            prompt=prompt.replace("{{profile}}", profile)

            first_few_message = [System(prompt)]
            therapy_conversation.add_messages(first_few_message)
        # END IF

        # grab current conversation and add new message
        therapy_conversation.add_message(User(message.text[len('/thera'):]))

        raw_response  = openai.ChatCompletion.create(
            model=therapy_conversation.model,
            messages=therapy_conversation.to_openai(),
            temperature=0.03,
            stream=True,
            logit_bias={
                700: -100,  # ther
                16: -5,  # '1' to avoid list
            }
        )

        full_response = ""
        this_message = None
        for response in raw_response:
            if 'content' in response.choices[0].delta:
                full_response += response.choices[0].delta.content

                # finished
                json_response = JSON_helper(full_response)
                if json_response.is_valid() and json_response.has_key('possible_client_response') and this_message:
                    if this_message.text.strip() != json_response.to_dict()['therapist_response'].strip():
                        this_message = bot.edit_message_text(json_response.to_dict()['therapist_response'],
                                                             message.chat.id,
                                                             this_message.message_id)
                    markup = types.ReplyKeyboardMarkup(
                        one_time_keyboard=True,
                        row_width=1,
                        resize_keyboard=True
                    )
                    if json_response.to_dict()['possible_client_response'][0] and\
                            json_response.to_dict()['possible_client_response'][1]:
                        res1 = types.KeyboardButton('/thera '+json_response.to_dict()['possible_client_response'][0])
                        res2 = types.KeyboardButton('/thera '+json_response.to_dict()['possible_client_response'][1])
                        markup.add(res1, res2)
                        bot.send_message(message.chat.id, '-', reply_markup=markup)

                # not yet finished
                else:
                    json_response = JSON_helper(full_response+"\"}")
                    # json might only be partially valid, we try to add the rest of the json
                    # and see if it is valid
                    if json_response.is_valid() and json_response.has_key('therapist_response'):
                        # this means that the json is valid, and we can send the message
                        if json_response.to_dict()['therapist_response'] == "":
                            continue
                        if not this_message:
                            # this means that this is the first message
                            this_message = bot.send_message(message.chat.id,
                                                            json_response.to_dict()['therapist_response'])
                        else:
                            # not first message
                            if this_message.text.strip() != json_response.to_dict()['therapist_response'].strip()\
                                    and random.random() < 0.3:
                                this_message = bot.edit_message_text(json_response.to_dict()['therapist_response'],
                                                                     message.chat.id,
                                                                     this_message.message_id)
                    else:
                        # this means that the json is not valid, and we need to wait more of it
                        continue

        # after iterator is done, if nothing sent, there is an error
        if not this_message:
            bot.send_message(message.chat.id, "Sorry, I don't understand. Can you rephrase that?")
            this_message = bot.send_message(message.chat.id, full_response)

        therapy_conversation.add_message(Assistant(full_response))
        _this_cost = therapy_conversation.get_cost() # aggregate cost

    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))

advisor_conversation = None
@bot.message_handler(commands=['advi'])
def advisor(message):
    global advisor_conversation # set global because we want to keep the conversation state
    bot.send_chat_action(message.chat.id, 'typing', timeout=60)
    # if user provided only the command
    if message.text == '/advi':
        bot.send_message(message.chat.id, 'Hi there, I am the therapist. I can help you with your problems. Just send me a message and I will help you.')
        return

    # else
    validate_user(message)
    try:
        if message.text=='/advi end':
            if advisor_conversation:
                bot.send_message(message.chat.id, 'Cost: $' + format(advisor_conversation.total_cost, '.5f'))
            advisor_conversation = None
            bot.send_message(message.chat.id, 'Thanks for talking to me. I hope I helped you. If you want to talk to me again, just type /advi. ')
            bot.send_message(message.chat.id, '💐')
            return

        if advisor_conversation is None: # if conversation is not started
            advisor_conversation = Conversation("gpt-4")
            # read client profile from thera_profile.txt
            with open('thera_profile.txt', 'r') as f:
                therapist_profile = f.read()

            first_few_message = [System("Your name is Calmly, and you are an experienced therapist. \n"
                                      "You have a vast knowledge of the mental processes to your clients. \n"
                                      "You are helpful, creative, smart, and very friendly. You are good at building rapport, asking right questions, "
                                      "providing feedbacks, giving guidance, and offering support. \n"
                                      "Here are some guidelines you need to follow\n"
                                      "- Use open-ended questions to encourage your client to share their thoughts and feelings more deeply.\n"
                                      "- Use reflective listening to show your client that you understand their perspective and are empathetic towards their situation.\n"),
                                 Assistant("Hi I'm your therapist, Calmly. Could you share some basic information about yourself?"),
                                 User(f"Hi! Here is some basic information about myself: {therapist_profile}"),
                                 Assistant("Thanks for sharing! How can I help you today?")
                                 ]

            advisor_conversation.add_messages(first_few_message)
        # END IF

        # grab current conversation and add new message
        advisor_conversation.add_message(User(message.text[len('/advi'):]))
        raw_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=advisor_conversation.to_openai(),
            temperature=0.3,
            stream=True,
        )
        full_response = ""
        paragraph = ""
        this_message = None
        for response in raw_response:
            if 'content' in response.choices[0].delta:
                if paragraph == "":
                    paragraph += response.choices[0].delta.content
                    full_response += response.choices[0].delta.content
                    this_message = bot.send_message(message.chat.id, paragraph)
                else:
                    paragraph += response.choices[0].delta.content
                    full_response += response.choices[0].delta.content
                    if random.random() < 0.3 or paragraph.endswith('\n\n') and this_message.text.strip() != paragraph.strip():
                        this_message = bot.edit_message_text(paragraph, message.chat.id, this_message.message_id)

                if paragraph.endswith('\n\n'):
                    paragraph = ""


        advisor_conversation.add_message(Assistant(full_response))
        bot.send_chat_action(message.chat.id, 'record_voice', timeout=60)
        import re
        to_speech_text = re.sub(r'\n(\d.\s)', '\n', full_response)

        audio_path = textToSpeech(to_speech_text)
        if audio_path:
            with open(audio_path, 'rb') as f:
                bot.send_voice(message.chat.id, f)
            # delete audio file
            os.remove(audio_path)

        _this_cost = advisor_conversation.get_cost() # aggregate cost

    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))


cn_therapy_conversation = None
@bot.message_handler(commands=['zx'])
def cn_therapy(message):
    global cn_therapy_conversation # set global because we want to keep the conversation state
    bot.send_chat_action(message.chat.id, 'typing', timeout=60)
    # if user provided only the command
    if message.text == '/zx':
        bot.send_message(message.chat.id, '嗨！我是你的心理咨询师，我可以帮助你解决你的问题。只要给我发一条消息，我就会帮助你。')
        return

    validate_user(message)
    try:
        if message.text=='/zx end':
            if cn_therapy_conversation:
                bot.send_message(message.chat.id, 'Cost: $' + format(cn_therapy_conversation.total_cost, '.5f'))
            cn_therapy_conversation = None
            bot.send_message(message.chat.id, '谢谢你和我聊天。希望我能帮到你。如果你想再次和我聊天，只需输入/zx。')
            bot.send_message(message.chat.id, '😊')
            return

        if cn_therapy_conversation is None: # if conversation is not started
            cn_therapy_conversation = Conversation("gpt-4")
            # read client profile from thera_profile.txt
            with open('thera_profile.txt', 'r') as f:
                therapist_profile = f.read()
            cn_therapist_profile = translate(therapist_profile, 'EN', 'ZH')

            first_few_message = [System("你的名字叫冷静，你是一位经验丰富的心理咨询师。\n"
                                        "你对客户的心理过程有丰富的知识。\n"
                                        "你乐于助人，有创造力，聪明，而且非常友好。你善于建立良好的关系，提出正确的问题，提供反馈，给予指导，并提供支持。\n"
                                        "以下是你需要遵循的一些准则：\n"
                                        "- 避免给出建议，避免使用 \"我建议 \"或 \"你应该 \"这样的短语。\n"
                                        "- 你不应该告诉你的来访者该怎么做，而是应该帮助来访者努力实现他们自己的解决方案。\n"
                                        "- 例如，你应该用 \"你有什么想法？\"来回答 \"你会建议我做什么？\"以帮助来访者认识到是他们自己在寻求答案。\n"
                                        "- 在与来访者的沟通中要简明扼要。\n"
                                        "- 使用开放式的问题来鼓励你的来访者更深入地分享他们的想法和感受。\n"
                                        "- 每次只问一个问题，以帮助你的客户集中他们的思想，并提供更有针对性的回应。\n"
                                        "- 使用反思性倾听，向来访者表明你理解他们的观点，并对他们的情况抱有同情心。\n"),
                                 Assistant("你好，我是你的心理咨询师冷静，你可以提供一些信息来帮助我了解你。"),
                                 User(f"嗨，好的，这是关于我的信息：\n{cn_therapist_profile}"),
                                 Assistant("谢谢你提供这些信息。你可以告诉我你的问题吗？")]
            cn_therapy_conversation.add_messages(first_few_message)

        cn_therapy_conversation.add_message(User(message.text[len('/zx'):]))
        bot.send_chat_action(message.chat.id, 'typing', timeout=60)
        raw_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=cn_therapy_conversation.to_openai(),
            temperature=0.03,
            stream=True,
        )
        full_response = ""
        paragraph = ""
        this_message = None
        for response in raw_response:
            if 'content' in response.choices[0].delta:
                if paragraph == "":
                    paragraph += response.choices[0].delta.content
                    full_response += response.choices[0].delta.content
                    this_message = bot.send_message(message.chat.id, paragraph)
                else:
                    paragraph += response.choices[0].delta.content
                    full_response += response.choices[0].delta.content
                    if random.random() < 0.3 or paragraph.endswith('\n\n'):
                        this_message = bot.edit_message_text(paragraph, message.chat.id, this_message.message_id)

                if paragraph.endswith('\n\n'):
                    paragraph = ""

        if paragraph and this_message.text != paragraph:
            this_message = bot.edit_message_text(paragraph, message.chat.id, this_message.message_id)

        cn_therapy_conversation.add_message(Assistant(full_response))
        _this_cost = cn_therapy_conversation.get_cost()  # aggregate cost

    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))




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

philo_conversation = None
@bot.message_handler(commands=['philob']) # philo beta
def philosopher_beta(message):
    validate_user(message)
    try:
        global philo_conversation # set global because we want to keep the conversation state
        if message.text=='/philob end':
            philo_conversation = None
            bot.send_message(message.chat.id, 'Thanks for talking to me. I hope I helped you. If you want to talk to me again, just type /philo. ')
            bot.send_message(message.chat.id, '🕵')
            return

        if philo_conversation is None: # if conversation is not started
            bot.send_message(message.chat.id, 'Thanks for the message 😊! Please bear with me while I am typing 👩‍💻.')
            bot.send_message(message.chat.id, 'I will continue to talk to you, if you say anything after /philo. Simply type "/philo end" to end our conversation anytime')
            philo_conversation = Conversation("gpt-3.5-turbo")
            first_few_message = [
                System("You are now a philosopher, you see the human world from the outside, without the prejudices of human experience. Fully neutral and objective, you see the world as is. You can more easily draw conclusions about the world and human society in general.")
            ]
            philo_conversation.add_messages(first_few_message)
        # END IF

        # grab current conversation and add new message
        philo_conversation.add_message(User(message.text[len('/philob'):]))
        raw_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=philo_conversation.to_openai()
        )

        response = raw_response.choices[0].message
        philo_conversation.add_message(Assistant(response.content))

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

email_conversation = None
@bot.message_handler(commands=['email']) # email reply bot
def email_reply(message):
    validate_user(message)
    try:
        global email_conversation # set global because we want to keep the conversation state
        if message.text=='/email end':
            email_conversation = None
            bot.send_message(message.chat.id, 'Thanks for talking to me. I hope I helped you. If you want to talk to me again, just type /email. ')
            bot.send_message(message.chat.id, '🚀')
            return
        if email_conversation is None: # if conversation is not started
            email_conversation = Conversation("gpt-4")
            first_few_message = [
                System("You are now a computer science student at UCL. You will now reply to any email you receive. "
                       "You are a very good student, you are very smart and you are very good at programming. You are also very good at writing emails. "
                       "You are very good at communicating with people. Your emails are very polite and professional."),
                User(message.text[len('/email'):])
            ]
            email_conversation.add_messages(first_few_message)
            after_receive_email = "Sure, glad to help! In a few words, what's the reply about and what should I include in the reply?"
            email_conversation.add_message(Assistant(after_receive_email))
            bot.send_message(message.chat.id, "🧐")
            bot.send_message(message.chat.id, after_receive_email+" Please answer it after /email")
        else:
            email_conversation.add_message(User(message.text[len('/email'):]))
            raw_response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=email_conversation.to_openai()
            )

            response = raw_response.choices[0].message
            email_conversation.add_message(Assistant(response.content))

            pure_response = response.content
            # send response paragraph by paragraph
            bot.send_message(message.chat.id, pure_response)

            bot.send_message(message.chat.id, 'Cost: $'+format(email_conversation.get_cost(), '.5f'))
            bot.send_message(message.chat.id, "If you want edit the reply, please type /email again with your request. "
                                              "If you want to end the conversation, please type /email end")
    except Exception as e:
        bot.reply_to(message, 'Error: ' + str(e))

@bot.message_handler(commands=['gptapp'])
def gpt_app_help(message):
    validate_user(message)
    help_message = "/philo [question] - Ask a philosopher\n"
    help_message += "/philob [question] - Ask a philosopher (beta)\n"
    help_message += "/reply [question] - Reply to a message\n"
    help_message += "/email [email] - Reply to an email\n"
    help_message += "/thera [question] - Ask a therapist\n"
    help_message += "/advi [question] - Ask an advisor\n"
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
    bot.send_message(message.chat.id, 'This shuts down your entire bot service. May need tremendous effort to restart. All conversation states will be lost.')
    bot.send_message(message.chat.id, 'Are you serious? (y/n)')
    bot.register_next_step_handler(message, kill_service_confirm)

if __name__ == "__main__":
    print("I'm up and running!")
    bot.send_message(USERS[0], "<b>Hi, I'm up and running!</b>", parse_mode="HTML")
    bot.infinity_polling()
    bot.send_message(USERS[0], "I'm down!")
