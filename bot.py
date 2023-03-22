import re
import os
import irc.bot
import openai
import logging
import socket

IRC_SERVER = os.environ.get('IRC_SERVER', 'localhost')
IRC_PORT = int(os.environ.get('IRC_PORT', 6667))
IRC_NICKNAME = os.environ.get('IRC_NICKNAME', 'ChatGPT')
IRC_REALNAME = os.environ.get('IRC_REALNAME', 'OpenAI-Assistant')
IRC_CHANNELS = os.environ.get('IRC_CHANNELS', '#ChatGPT,#wakka')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'sk-xxx')

openai.api_key = OPENAI_API_KEY

class MyBot(irc.bot.SingleServerIRCBot):
    def __init__(self):
        server = irc.bot.ServerSpec(IRC_SERVER, IRC_PORT)
        super().__init__([server], IRC_NICKNAME, IRC_REALNAME)

    def on_welcome(self, connection, event):
        for channel in IRC_CHANNELS.split(","):
            connection.join(channel)

    def on_privmsg(self, connection, event):
        message = event.arguments[0]
        if message.startswith('!') or message.startswith('.'):
            return  # Ignore message
        print("Received private message")
        message = event.arguments[0]
        generate_and_relay_responses(message, connection, event)

    def on_pubmsg(self, connection, event):
        message = event.arguments[0]
        if message.startswith('!') or message.startswith('.'):
            return  # Ignore message
        print("Received message in channel")
        message = event.arguments[0]
        if IRC_NICKNAME in message:
            generate_and_relay_response(message, connection, event)

def on_ctcp(self, connection, event):
    ctcp_type = event.arguments[0]
    if ctcp_type == "ERRMSG":
        connection.ctcp_reply(event.source.nick, "ERRMSG")
    elif ctcp_type == "VERSION":
        connection.ctcp_reply(event.source.nick, "VERSION " + self.get_version())
    elif ctcp_type == "PING":
        connection.ctcp_reply(event.source.nick, "PONG " + event.arguments[1])
    elif ctcp_type == "SOURCE":
        connection.ctcp_reply(event.source.nick, "SOURCE https://github.com/Strykar/chatgpt-irc-bot")
    elif ctcp_type == "DCC":
        dcc_args = event.arguments[1].split(" ")
        dcc_type = dcc_args[0]
        if dcc_type == "CHAT":
            if len(dcc_args) == 2:
                dcc_info = dcc_args[1].split()
                dcc_ip = dcc_info[0]
                dcc_port = int(dcc_info[1])
                dcc_size = int(dcc_info[2])
                # handle the DCC CHAT connection here
            else:
                print("Not enough arguments for DCC CHAT")
    else:
        print(f"Received unknown CTCP message: {ctcp_type}")

def generate(prompt):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.7,
    )
    return response.choices[0].text

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def send_message(message: str, connection: irc.client.ServerConnection, recipient: str, max_message_length: int = 400) -> bool:
    # Validate inputs
    if not isinstance(message, str):
        logger.error(f"Invalid input type for message: {type(message)}")
        return False
    if not isinstance(connection, irc.client.ServerConnection):
        logger.error(f"Invalid input type for connection: {type(connection)}")
        return False
    if not isinstance(recipient, str):
        logger.error(f"Invalid input type for recipient: {type(recipient)}")
        return False
    if len(message) > max_message_length:
        logger.warning(f"Message length exceeds max message length of {max_message_length}")
    
    # Clean message
    message = re.sub(r'<.*?>', '', message) # Remove any HTML tags
    message = re.sub(r'[\r\n]', '', message) # Remove carriage returns and newlines
    chunks = [chunk.strip() for chunk in re.split(r'(?<=[.?!])\s+', message)]
    
    # Send message chunks
    for chunk in chunks:
        if len(chunk) > max_message_length:
            logger.warning(f"Message chunk length exceeds max message length of {max_message_length}")
            continue
        connection.privmsg(recipient, chunk)
        logger.debug(f"Sent message chunk: {chunk}")
    return True

def generate_and_relay_response(message, connection, event):
    prompt = f"{message}\nAI:"
    response = generate(prompt)
    send_message(response, connection, event.target)

def generate_and_relay_responses(message, connection, event):
    nick = event.source.nick
    message = re.sub(r'<.*?>', '', message) # Remove any HTML tags
    message = re.sub(r'[\r\n]', '', message) # Remove carriage returns and newlines
    chunks = [chunk.strip() for chunk in re.split(r'(?<=[.?!])\s+', message)]
    prompt = f"{message}\nAI:"
    response = generate(prompt)
    clean_nick = re.sub(r'[^\x00-\x7F]+', ' ', nick)  # Replace non-ASCII characters with spaces
    clean_nick = re.sub(r'[\r\n]+', ' ', clean_nick)  # Replace carriage returns and newlines with spaces
    send_message(response, connection, clean_nick)

if __name__ == '__main__':
    bot = MyBot()
    bot.start()
