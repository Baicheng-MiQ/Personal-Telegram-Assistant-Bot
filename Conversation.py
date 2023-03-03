class Conversation:
    def __init__(self):
        self.messages = []

    def add_message(self, role, message):
        if role not in ["user", "assistant", "system"]:
            raise ValueError("Role must be user, assistant or system")
        self.messages.append(
            {
                "role": role,
                "content": message
            }
        )

    def add_messages(self, messages):
        for message in messages:
            if message["role"] not in ["user", "assistant", "system"]:
                raise ValueError("Role must be user, assistant or system")
            if "content" not in message:
                raise ValueError("Message must have a content")
        self.messages += messages

    def reset(self):
        self.messages = []