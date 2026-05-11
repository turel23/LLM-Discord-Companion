from openai import OpenAI
client = OpenAI(base_url="http://localhost:1234/v1", api_key="placeholder")
messages = [{"role": "system", "content": "you are an assistant for a discord bot, you will be given messages from users and you should respond to them in a helpful and concise manner. If the user asks you to do something that is not possible, you should politely decline."}]

class llm:
    def __init__(self):
        self.client = client
        self.messages = messages
    async def ask(self, question, author):
        print(f"received message: {question}")
        self.messages.append({"role": "user", "name": author.replace(" ", "_"), "content": f"[{author}]: {question}"})
        response = self.client.chat.completions.create(model="local", messages=self.messages, temperature=0)
        answer = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": answer})
        print(f"DEBUG output: {answer} ")
        return answer