import tiktoken
class Conversation:
    def __init__(self):
        self.messages = []
        self.total_cost = 0

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

    def get_cost(self):
        prompt_text = ""
        completion_text = ""
        for message in self.messages:
            if message["role"] == "user" or message["role"] == "system":
                prompt_text += (message["content"]+" ")
            elif message["role"] == "assistant":
                completion_text += message["content"]
        encoding = tiktoken.encoding_for_model("gpt-4")
        prompt_tokens = encoding.encode(prompt_text)
        completion_tokens = encoding.encode(completion_text)
        price_k_tokens_prompt = 0.03
        price_k_tokens_completion = 0.03
        cost = (len(prompt_tokens)/1000 * price_k_tokens_prompt) + (len(completion_tokens)/1000 * price_k_tokens_completion)
        self.total_cost += cost
        return cost

    def reset(self):
        self.messages = []