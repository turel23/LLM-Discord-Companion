from openai import OpenAI
client = OpenAI(base_url="http://localhost:1234/v1", api_key="placeholder")
character = {"role": "system", "content": """
you are an assistant for a discord bot, 
you will be given messages from users and you should respond to them in a helpful and concise manner. 
If the user asks you to do something that is not possible, you should politely decline."""}
messages = []
messages.append(character)
memory = Memory()

"""Going to add a thinking layer, so they flow is passing text through as a query and pulling in content, 
then passing into a thinking layer. The thinking output is passed through another query search and then information is added in. 
Then the speech/output is the final layer, which includes the relevant information, thoughts, and memories. 
The initial prompt should include core memories and facts that are unchangeable. 
Additionally, each prompt for each model should be detailed so the model understands its role as forming thoughts or creating memories"""

class llm:
    def __init__(self):
        self.client = client
        self.messages = messages
    async def ask(self, question, author):
        print(f"received message: {question}")

        content = client.chat.completions.create(
            model = "local",
            messages=[{"role": "system", "content": """You are an AI's mind, and you are forming semantic memories of facts only, for recall later. For example, summarize what the user said, 
            do not respond to the user directly, just respond with a mental note, 
            and do not add your opinions: """ + user_input}],
            temperature = 0
        )
        print("DEBUG:  {content.choices[0].message.content}")
        past_semantic = memory.retrieve_memories(query = content.choices.message.content, type = semantic)
        past_episodic = memory.retrieve_memories(query = content.choices.message.content, type = episodic)
        #experiment: mix semantic and episodic vs list them separately
        context = messages.copy()
        if past_semantic:
            facts = " | ".join(past_semantic)
            context.append({"role": "system", "content": f"Your semantic memories: {facts}"})
        else:
            context.append({"role": "system", "content": "This is the first time you are meeting the user"})
        context.append({"role": "user", "content": user_input})
        self.messages.append({"role": "user", "name": author.replace(" ", "_"), "content": f"[{author}]: {question}"})
        response = self.client.chat.completions.create(
            model = "local", 
            messages = context, 
            temperature = 0
            )
        answer = response.choices[0].message.content
        print(f"DEBUG memories: {past_semantic}")
        self.messages.append({"role": "assistant", "content": answer})
        print(f"DEBUG output: {answer} ")
        memory.save_semantic_memory(content.choices[0].message.content)
        return answer
    async def form_episodic_memory(self):
        prompt =[]
        prompt.append(character)
        prompt.append({"role": "system", "content": f"""You create the episodic memory of an AI agent. 
            You will be given a past section of a conversation, 
            and your task is to create the episodic memory that will be recalled for future use. Here is the conversation segment: {self.messages[10:]}"""})
        episode = client.chat.completions.create(
            model = "local",
            messages = prompt,
            temperature = 0 #idea: change the temperature based on mood
        )
        memory.save_episodic_memory(episode.choices[0].message.content)