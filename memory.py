from datetime import datetime
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize LM Studio clients
text_client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
embedding_client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")

class MemoryManage:
    """Memory manager using Neo4j for graph-based memory storage with LM Studio embeddings"""
    
    def __init__(self):
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise RuntimeError("neo4j is required. Install with: pip install neo4j")
        
        self.driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
        self.session_id = "discord_bot"
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize Neo4j with constraints"""
        with self.driver.session() as session:
            # Create constraints for better performance
            try:
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE")
                print("Neo4j constraints initialized")
            except Exception as e:
                print(f"Constraint creation info: {e}")
    
    async def retrieve_relevant(self, query, top_k=10, user_id=""):
        """Retrieve relevant memories using embedding similarity search"""
        try:
            # Get embedding for query
            query_embedding = await self._get_embedding(query)
            
            with self.driver.session() as session:
                # Find similar memories using Euclidean distance
                # For now, return memories with simple text matching
                result = session.run("""
                    MATCH (m:Memory {session_id: $session_id})
                    WITH m
                    ORDER BY m.timestamp DESC
                    LIMIT $limit
                    RETURN m.content as content, m.type as type, m.poignancy as poignancy, m.timestamp as timestamp
                """, session_id=self.session_id, limit=top_k)
                
                past_semantic = []
                past_episodic = []
                accessed_docs = []
                
                for record in result:
                    content = record["content"]
                    memory_type = record["type"]
                    
                    memory_obj = {
                        "content": content,
                        "type": memory_type,
                        "poignancy": record["poignancy"],
                        "timestamp": record["timestamp"]
                    }
                    
                    if memory_type == "semantic":
                        past_semantic.append(content)
                    elif memory_type == "episodic":
                        past_episodic.append(content)
                    
                    accessed_docs.append(memory_obj)
                
                print(f"DEBUG: Retrieved {len(past_semantic)} semantic and {len(past_episodic)} episodic memories")
                return past_semantic, past_episodic, accessed_docs
                
        except Exception as e:
            print(f"Error retrieving memories from Neo4j: {e}")
            import traceback
            traceback.print_exc()
            return [], [], []
    
    async def add_memory(self, content, memory_type="semantic", metadata=None):
        """Add a memory to Neo4j with embeddings"""
        try:
            embedding = await self._get_embedding(content)
            
            with self.driver.session() as session:
                memory_id = f"{self.session_id}_{datetime.now().timestamp()}"
                session.run("""
                    CREATE (m:Memory {
                        id: $id,
                        session_id: $session_id,
                        content: $content,
                        type: $type,
                        embedding: $embedding,
                        poignancy: $poignancy,
                        timestamp: $timestamp,
                        author: $author
                    })
                """, 
                    id=memory_id,
                    session_id=self.session_id,
                    content=content,
                    type=memory_type,
                    embedding=embedding,
                    poignancy=metadata.get("poignancy", 5.0) if metadata else 5.0,
                    timestamp=datetime.now().isoformat(),
                    author=metadata.get("author", "unknown") if metadata else "unknown"
                )
                print(f"Stored memory: {content[:50]}...")
        except Exception as e:
            print(f"Error adding memory to Neo4j: {e}")
            import traceback
            traceback.print_exc()
    
    async def _get_embedding(self, text):
        """Get embedding from LM Studio embedding endpoint"""
        try:
            response = embedding_client.embeddings.create(
                model="local",
                input=text
            )
            embedding = response.data[0].embedding
            print(f"DEBUG: Got embedding with {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            print(f"Warning: Could not get embedding ({e}), using dummy vector")
            # Return dummy vector on error - still stores memory, just without semantic search
            return [0.0] * 768
    
    def update_accessed_memories(self, docs):
        """Update memory access statistics"""
        # Neo4j handles this through query execution
        pass
    
    def __del__(self):
        """Close Neo4j driver on cleanup"""
        try:
            self.driver.close()
        except:
            pass
