
class Thinking:
    def __init__(self, llm_client, memory):
        self.client = llm_client
        self.memory = memory
        self.messages = []
    
    def process_statement(self, author, context):
        context.append(
            {"role": "system", 
             "content":"""You form the thought process of Lumo."""}
        )
        thought = self.client.chat.completions.create(
            model = "local", 
            messages = context, 
            temperature = 0
        )
        memories = self.memory.retrieve_memories(query = thought.choices[0].message.content, top_k = 3, filters = {})

        return thought.choices[0].message.content + " memories relevant to thoughts: " + " | ".join(memories["results"])