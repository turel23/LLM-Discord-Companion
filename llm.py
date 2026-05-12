import os
from dotenv import load_dotenv
from openai import OpenAI
from memory import Memory

load_dotenv()
main_prompt = str(os.getenv("PROMPT"))

client = OpenAI(base_url="http://localhost:1234/v1", api_key="placeholder")
character = {"role": "system", "content": main_prompt}
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
    async def ask(self, statement = str, author = str):
        print(f"received message: {statement}")
        past_semantic, past_episodic = memory.retrieve_memories(query = statement)

        # content = client.chat.completions.create(
        #     model = "local",
        #     messages=[{"role": "system", "content": f"""You are forming semantic memories. You will be given a line that the user said to you.
        #                Extract only facts from what the user says. Format: "[username] fact about them".
        #                Example: "[alice] likes dogs and has a dog named Brownie" 
        #                Example: "I am an AI on Discord."
                       
        #                Here is the line:
        #                User: {author}
        #                Message: {statement}"""}],
        #     temperature = 0
        # )
        # content_text = content.choices[0].message.content
        # past_semantic = memory.retrieve_memories(query = content_text, type = "semantic")
        # past_episodic = memory.retrieve_memories(query = content_text, type = "episodic")
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
        memory.save_semantic_memory(content_text, user = author)
        return answer
    async def form_episodic_memory(self):
        prompt =[]
        prompt.append(character)
        prompt.append({"role": "system", "content": f"""You create the episodic memory of an AI agent. 
            You will be given a past section of a conversation, 
            and your task is to create the episodic memory that will be recalled for future use. Summaries should be concise, output ONLY the memory
            Keep episodic memories to 1-3 sentences. You can describe emotions, tone, and personality traits, but don't pad it with irrelevant details.
            Dialogue marked with "role": "assistant" are the responses you gave, and "role": "user" are the messages from the user.
            Example: "[alice] and I talked about our day and we got along well."
            Example: "I found out that [bob] is my creator and I am grateful for that."
            
                        
            
            Here is the conversation segment: {self.messages[-10:]}"""})
        episode = client.chat.completions.create(
            model = "local",
            messages = prompt,
            temperature = 0 #idea: change the temperature based on mood
        )
        memory.save_episodic_memory(episode.choices[0].message.content)