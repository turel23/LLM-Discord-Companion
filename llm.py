from openai import OpenAI
client = OpenAI(base_url="http://localhost:1234/v1", api_key="placeholder")
messages = [{"role": "system", "content": "you are an assistant for a discord bot, you will be given messages from users and you should respond to them in a helpful and concise manner. If the user asks you to do something that is not possible, you should politely decline."}]
memory = Memory()

class llm:
    def __init__(self):
        self.client = client
        self.messages = messages
    async def ask(self, question, author):
        print(f"received message: {question}")
        content = client.chat.completions.create(
            model = "local",
            messages=[{"role": "system", "content": """Summarize what the user said, 
            do not respond to the user directly, just respond witha mental note, 
            and do not add your opinions: """ + user_input}],
            temperature = 0
        )
        print("DEBUG:  {content.choices[0].message.content}")
        past_memories = memory.retrieve_memories(content.choices[0].message.content)
        context = messages.copy()
        if past_memories:
            facts = " | ".join(past_memories)
            context.append({"role": "system", "content": f"Relevant past memories: {facts}"})
        else:
            context.append({"role": "system", "content": "This is the first time you are meeting the user"})
        context.append({"role": "user", "content": user_input})
        self.messages.append({"role": "user", "name": author.replace(" ", "_"), "content": f"[{author}]: {question}"})
        response = self.client.chat.completions.create(
            model="local", 
            messages=context, 
            temperature=0
            )
        answer = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": answer})
        print(f"DEBUG output: {answer} ")
        return answer