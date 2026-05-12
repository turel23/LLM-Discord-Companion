from openai import OpenAI
from memory import Memory
client = OpenAI(base_url="http://localhost:1234/v1", api_key="placeholder")
character = {"role": "system", "content": """
You are an AI companion. 
You will be given messages from users and you should respond to them in a helpful and concise manner. 
If the user asks you to do something that is not possible, you should politely decline.
You should try to speak in the same manner that the user does, to replicate how a human would interact with another human."""}
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
    
    async def load_past_discord_messages(self, channel):
        """Load the past 15 messages from Discord channel and append to messages"""
        try:
            past_messages = []
            async for message in channel.history(limit=15):
                past_messages.append(message)
            
            # Reverse to get chronological order (oldest first)
            past_messages.reverse()
            
            for msg in past_messages:
                if msg.author.bot:
                    # AI response
                    self.messages.append({"role": "assistant", "content": msg.content})
                else:
                    # User message
                    self.messages.append({"role": "user", "name": msg.author.name.replace(" ", "_"), "content": f"[{msg.author.name}]: {msg.content}"})
            
            print(f"Loaded {len(past_messages)} past messages from Discord")
        except Exception as e:
            print(f"Error loading past messages: {e}")
    async def ask(self, statement = str, author = str):
        print(f"received message: {statement}")

        content = client.chat.completions.create(
            model = "local",
            messages=[{"role": "system", "content": f"""You are forming semantic memories. Extract only facts from what the user says. Format: "[username] fact about them".
            Example: "[alice] likes dogs and has a dog named Brownie" 
                       
            Extract facts from this user's message:
            User: {author}
            Message: {statement}"""}],
            temperature = 0
        )
        print(f"DEBUG: {content.choices[0].message.content}")
        past_semantic = memory.retrieve_memories(query = content.choices[0].message.content, type = "semantic")
        past_episodic = memory.retrieve_memories(query = content.choices[0].message.content, type = "episodic")
        #experiment: mix semantic and episodic vs list them separately
        context = messages.copy()
        if past_semantic or past_episodic:
            facts = " | ".join(past_semantic)
            context.append({"role": "system", "content": f"Your semantic memories: {facts}"})
            episodes = " | ".join(past_episodic)
            context.append({"role": "system", "content": f"Your episodic memories: {episodes}"})
        else:
            context.append({"role": "system", "content": "This is the first time you are meeting the user"})
        context.append({"role": "user", "content": statement})
        self.messages.append({"role": "user", "name": author.replace(" ", "_"), "content": f"[{author}]: {statement}"})
        response = self.client.chat.completions.create(
            model = "local", 
            messages = context, 
            temperature = 0
            )
        answer = response.choices[0].message.content
        print(f"DEBUG relevant memories semantic: {past_semantic}")
        print(f"DEBUG relevant memories episodic: {past_episodic}")
        self.messages.append({"role": "assistant", "content": answer})
        print(f"DEBUG output: {answer} ")
        memory.save_semantic_memory(content.choices[0].message.content)
        return answer
    async def form_episodic_memory(self):
        prompt =[]
        prompt.append(character)
        prompt.append({"role": "system", "content": f"""You create the episodic memory of an AI agent. 
            You will be given a past section of a conversation, 
            and your task is to create the episodic memory that will be recalled for future use. Summaries should be concise, output ONLY the memory
            Keep episodic memories to 1-3 sentences. You can describe emotions, tone, and personality traits, but don't pad it with irrelevant details.
            Example: "[alice] and I talked about our day and we got along well."
                        
            
            Here is the conversation segment: {self.messages[-10:]}"""})
        episode = client.chat.completions.create(
            model = "local",
            messages = prompt,
            temperature = 0 #idea: change the temperature based on mood
        )
        print(f"DEBUG created episodic memory: {episode.choices[0].message.content}")
        memory.save_episodic_memory(episode.choices[0].message.content)