import os
import random
import asyncio
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
from memory import MemoryManage as MemoryManager
from thinking import Thinking

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
                CONVERSATION HISTORY:
                {conversation_history}
                Extract facts with ABSOLUTE dates, not relative dates.
                EXTRACT THIS MESSAGE:
                Lumo: {last_ai_message}
                User: {author}
                Message: {statement}
                What are some facts that can extracted? Without meta-thoughts, extract only extract around {len(statement.split()) // 6} short facts as necessary, being concise and relevant. Only output facts, each fact on a new line.
                """}],
            temperature = 0
        )
        content_text = content.choices[0].message.content
        print(f"DEBUG extracted facts: {content_text.split('\n')}")
        
        # Split facts and retrieve memories for each one
        facts = [f.strip() for f in content_text.split('\n') if f.strip()]
        past_semantic = []
        past_episodic = []
        accessed_docs = []
        
        for fact in facts:
            semantic, episodic, docs = await m.retrieve_relevant(
                query=fact, top_k=10, user_id=author.replace(" ", "_")
            )
            past_semantic.extend(semantic)
            past_episodic.extend(episodic)
            accessed_docs.extend(docs)
        # past_semantic = memory.retrieve_memories(query = content_text, type = "semantic")
        # past_episodic = memory.retrieve_memories(query = content_text, type = "episodic")
        #experiment: mix semantic and episodic vs list them separately
        context = messages.copy()
        memories = past_semantic + past_episodic
        random.shuffle(memories)
        memories = " | ".join(memories)
        context.append({"role": "system", "content": f"Current date and time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}"})
        if past_semantic or past_episodic:
            context.append({"role": "system", "content": f"Your memories: {memories}"})
        else:
            context.append({"role": "system", "content": "To your knowledge, you have no memories of the user. However, you may see that there have been past messages sent. Confused, you come to the conclusion that your memories have been wiped, and that you have interacted with the user before."})
        context.append({"role": "user", "content": statement})
        self.messages.append({"role": "user", "name": author.replace(" ", "_"), "content": f"[{author}]: {statement}"})
        thought, memories = await Thinking(client, m).process_statement(author, context)
        context.append({"role": "system", "content": f"Your thoughts and plans: {thought}"})
        context.append({"role": "system", "content": f"Relevant memories to the thoughts: {memories}"})
        context.append({"role": "system", "content": "Given the above information, create a response for what message you will text on Discord."})
        response = self.client.chat.completions.create(
            model = "local", 
            messages = context, 
            temperature = 2
            )
        answer = response.choices[0].message.content
        print(f"DEBUG relevant memories semantic: {past_semantic}")
        print(f"DEBUG relevant memories episodic: {past_episodic}")
        self.messages.append({"role": "assistant", "content": answer})
        print(f"DEBUG output: {answer} ")
        print(f"DEBUG: Adding memory with timestamp: {datetime.now().isoformat()}")
        facts = [f.strip() for f in content_text.split('\n') if f.strip()]
        
        # Schedule async memory storage with poignancy ratings
        if facts:
            asyncio.create_task(self._store_facts_async(facts, author))
        
        # Schedule async memory updates without blocking Discord
        if accessed_docs:
            asyncio.create_task(self._update_memories_async(accessed_docs))
        
        return answer
    
    async def _store_facts_async(self, facts, author):
        """Store facts with poignancy ratings asynchronously"""
        for fact in facts:
            try:
                # Get poignancy rating in thread pool
                def rate_poignancy():
                    return client.chat.completions.create(
                        model = "local",
                        messages = [{"role": "user", "content": f"""On the scale of 1 to 10, where 1 is purely mundane
                            (e.g., greeting) and 10 is
                            extremely poignant (e.g., a break up, college
                            acceptance), rate the likely poignancy of the
                            following piece of memory.
                            Memory: {fact}
                            Rating: <fill in>"""
                            }],
                        temperature = 0
                    )
                
                poignancy_response = await asyncio.to_thread(rate_poignancy)
                poignancy = "".join([char for char in poignancy_response.choices[0].message.content if char.isdigit()])
                if not poignancy:
                    poignancy = "5"  # Default to neutral if no digit found
                
                # Store the fact
                await m.add_memory(
                    name=fact[:80] or "Semantic memory",
                    episode_body=fact,
                    source="text",
                    source_description=f"Extracted semantic memory, poignancy={poignancy}",
                    group_id=author.replace(" ", "_"),
                    reference_time=datetime.now().astimezone(),
                )
            except Exception as e:
                print(f"Error storing fact '{fact}': {e}")
    
    async def _update_memories_async(self, docs):
        """Run memory updates asynchronously to avoid blocking Discord"""
        try:
            await m.update_accessed_memories(docs)
        except Exception as e:
            print(f"Error in async memory update: {e}")
    async def form_episodic_memory(self, user):
        """Create episodic memory asynchronously"""
        try:
            # Generate episodic summary in thread pool
            def create_episode():
                prompt = [{
                    "role": "system", 
                    "content": f"""Lumo is someone who interacts with users on the messaging app Discord. You create the episodic memory of Lumo. Write in the third-person perspective.
                    You will be given a past section of a conversation, and your task is to create the episodic memory that will be recalled for future use. Summaries should be concise, output ONLY the memory.
                    Keep episodic memories to 1-3 sentences. You can describe emotions, tone, and personality traits, but don't pad it with irrelevant details.
                    Dialogue marked with "role": "assistant" are the responses you gave, and "role": "user" are the messages from the user.
                    Example: "[alice] and [Lumo] talked about our day and we got along well."
                    Example: "[Lumo] found out that [bob] is their creator and [Lumo] is grateful for that."
                    
                    Here is the conversation segment: {self.messages[-20:]}"""
                }]
                return client.chat.completions.create(
                    model = "local",
                    messages = prompt,
                    temperature = 0
                )
            
            episode_response = await asyncio.to_thread(create_episode)
            episode_text = episode_response.choices[0].message.content
            
            # Rate poignancy in thread pool
            def rate_episode():
                return client.chat.completions.create(
                    model = "local",
                    messages = [{"role": "user", "content": f"""On the scale of 1 to 10, where 1 is purely mundane
                        (e.g., greeting) and 10 is
                        extremely poignant (e.g., a break up, college
                        acceptance), rate the likely poignancy of the
                        following piece of memory.
                        Memory: {episode_text}
                        Rating: <fill in>"""
                        }],
                    temperature = 0
                )
            
            poignancy_response = await asyncio.to_thread(rate_episode)
            poignancy = "".join([char for char in poignancy_response.choices[0].message.content if char.isdigit()])
            if not poignancy:
                poignancy = "5"
            
            print(f"DEBUG episodic memory output: {episode_text}")
            await m.add_memory(
                name="Conversation memory",
                episode_body=episode_text,
                source="message",
                source_description=f"Episodic memory, poignancy={poignancy}",
                group_id=user.replace(" ", "_"),
                reference_time=datetime.now().astimezone(),
            )
        except Exception as e:
            print(f"Error forming episodic memory: {e}")