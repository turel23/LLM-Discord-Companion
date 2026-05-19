import os
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
from mem0 import Memory
from memory import MemoryManage as MemoryManager

load_dotenv()
main_prompt = str(os.getenv("PROMPT"))

client = OpenAI(base_url="http://localhost:1234/v1", api_key="placeholder")
character = {"role": "system", "content": main_prompt + """Throughout the conversation, you will recieve memories with the time elapsed since then do NOT add your own time, e.g. no "(from X minutes ago)"."""}
messages = []
messages.append(character)

m = MemoryManager()

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
                diff = datetime.now(msg.created_at.tzinfo) - msg.created_at
                if diff.total_seconds() < 3600:
                    recency = f"{int(diff.total_seconds() // 60)} minutes ago"
                elif diff.total_seconds() < 3600 * 24:
                    recency = f"{int(diff.total_seconds() // 3600)} hours ago"
                else:
                    recency = f"{int(diff.total_seconds() // (3600 * 24))} days ago"
                if msg.author.bot:
                    # AI response
                    self.messages.append({"role": "assistant", "content": f"{msg.content} "})
                else:
                    # User message
                    author_display_name = getattr(msg.author, "display_name", msg.author.name)
                    self.messages.append({"role": "user", "name": author_display_name.replace(" ", "_"), "content": f"[{author_display_name}]: {msg.content}"})
            
            print(f"Loaded {len(past_messages)} past messages from Discord")
        except Exception as e:
            print(f"Error loading past messages: {e}")
    async def ask(self, statement = str, author = str):
        print(f"received message: {statement}")
        conversation_history = "\n".join([f"{'User' if msg['role'] == 'user' else 'Lumo'}: {msg['content']}" for msg in self.messages[-10:]])
        last_ai_message = next((msg['content'] for msg in reversed(self.messages) if msg['role'] == 'assistant'), '')
        print("DEBUG: last AI message:", last_ai_message)
        content = client.chat.completions.create(
            model = "local",
            messages=[{
                "role": "system", "content": f"""Lumo is an AI who interacts with users on the messaging app Discord. Today is {datetime.now().strftime('%A, %B %d, %Y')}. 
                Your task is to extract facts. The user is talking to Lumo.
                CONVERSATION HISTORY:
                {conversation_history}
                Format: "[username] fact" or "[fact about Lumo]"
                User says "I have a test tomorrow" and today is May 12th → Extract: "[username] has a test on May 13th"
                Extract facts with ABSOLUTE dates, not relative dates.
                Extract facts including:
                - Personal information: "[alice] likes dogs"
                - User's relationships/actions with Lumo: "[alice] created me", "[bob] told [Lumo] to help"
                - User's preferences and traits: "[carol] is learning Python"
                - Facts about Lumo
                       
                IMPORTANT: only extract around {len(statement.split()) // 6} facts or however many are necessary, and make sure they are concise and relevant.
                IMPORTANT: Extract only both messages you sent and the user sent, given the context of the conversation. Do NOT respond to the user, responses should be your internal semantic thoughts.
                OUTPUT FORMAT: Return ONLY facts in the format "[someone] fact" - one per line. 
                NO commentary, analysis, or meta-thoughts.  
                EXTRACT THIS MESSAGE:
                Lumo: {last_ai_message}
                THEN EXTRACT THIS MESSAGE:
                User: {author}
                Message: {statement}
                """}],
            temperature = 0
        )
        content_text = content.choices[0].message.content
        print(f"DEBUG extracted facts: {content_text}")
        past_semantic, past_episodic = m.retrieve_relevant(query = content_text, top_k = 50, user_id = author.replace(" ", "_"))
        # past_semantic = memory.retrieve_memories(query = content_text, type = "semantic")
        # past_episodic = memory.retrieve_memories(query = content_text, type = "episodic")
        #experiment: mix semantic and episodic vs list them separately
        context = messages.copy()
        context.append({"role": "system", "content": f"Current date and time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}"})
        if past_semantic or past_episodic:
            facts = " | ".join(past_semantic)
            context.append({"role": "system", "content": f"Your semantic memories: {facts}"})
            episodes = " | ".join(past_episodic)
            context.append({"role": "system", "content": f"Your episodic memories: {episodes}"})
        else:
            context.append({"role": "system", "content": "To your knowledge, you have no memories of the user. However, you may see that there have been past messages sent. Confused, you come to the conclusion that your memories have been wiped."})
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
        print(f"DEBUG: Adding memory with timestamp: {datetime.now().isoformat()}")
        facts = [f.strip() for f in content_text.split('\n') if f.strip()]
        m.memory.add(
            messages = [{"role": "user", "content": content_text}], 
            metadata = {"type": "semantic", "retention": 1.0, "timestamp": datetime.now().isoformat(), "S": 1.0}, 
            user_id=author.replace(" ", "_"),
            infer = True
            )
        #retention = e^-t/S, S=36.716, while t is in minutes
        return answer
    async def form_episodic_memory(self, user):
        prompt =[]
        prompt.append({"role": "system", "content": f"""Lumo is an AI who interacts with users on the messaging app Discord. You create the episodic memory of Lumo. Write in the third-person perspective.
            You will be given a past section of a conversation, 
            and your task is to create the episodic memory that will be recalled for future use. Summaries should be concise, output ONLY the memory
            Keep episodic memories to 1-3 sentences. You can describe emotions, tone, and personality traits, but don't pad it with irrelevant details.
            Dialogue marked with "role": "assistant" are the responses you gave, and "role": "user" are the messages from the user.
            Example: "[alice] and [Lumo] talked about our day and we got along well."
            Example: "[Lumo] found out that [bob] is their creator and [Lumo] is grateful for that."
            
                        
            
            Here is the conversation segment: {self.messages[-10:]}"""})
        episode = client.chat.completions.create(
            model = "local",
            messages = prompt,
            temperature = 0 #idea: change the temperature based on mood
        )
        print(f"DEBUG episodic memory output: {episode.choices[0].message.content}")
        m.memory.add(messages = [{"role": "user", "content": episode.choices[0].message.content}], metadata = {"type": "episodic", "retention": 1.0, "S": 1.0,"timestamp": datetime.now().isoformat()}, user_id = user.replace(" ", "_"), infer = False)