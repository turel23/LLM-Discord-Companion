import os
import random
from dotenv import load_dotenv
load_dotenv()
class Thinking:
    def __init__(self, llm_client, memory):
        self.client = llm_client
        self.memory = memory
        self.messages = []
    
    def process_statement(self, author, context):
        prompt = os.getenv("PROMPT")
        context.append({"role": "system", "content": prompt})
        context.append(
            {"role": "system", 
             "content":"""Given the context of the conversation, assess the situation and form a plan on what you will say or do. For example, if your friend, the user, says "hello", then you should say "I will say hello to my friend because i want to get closer to them and form a friendship"."""}
        )
        thought = self.client.chat.completions.create(
            model = "local", 
            messages = context, 
            temperature = 0
        )
        past_semantic, past_episodic, accessed_docs = self.memory.retrieve_relevant(query = thought.choices[0].message.content, top_k = 3, user_id = "global")
        memories = past_semantic + past_episodic
        random.shuffle(memories)
        memories_text = " | ".join(memories)
        return "I think that the user's favorite food is nice, and i will tell them that I think it is alright. I will tell the user that i enjoy eating chocolate cake"
        return thought.choices[0].message.content, " memories relevant to thoughts: " + memories_text