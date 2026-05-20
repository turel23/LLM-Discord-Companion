from mem0 import Memory
import math
from datetime import datetime
import random

config = {
    "llm": {
        "provider": "lmstudio",
        "config": {
            "lmstudio_base_url": "http://localhost:1234/v1",
            "lmstudio_response_format": {
                "type": "json_schema",
                "json_schema": {
                    "type": "object",
                    "schema": {}
                }
            },
        }
        },
    "embedder": {
        "provider": "lmstudio",
        "config": {"embedding_dims": 768},
        "compression_type": "binary",
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0_local",
            "embedding_model_dims": 768,    
            "path": "./mem_db",
        },
    },
}
memory = Memory.from_config(config)
class MemoryManage:
    def __init__(self):
        self.memory = memory
    def calculate_retention(self, timestamp, S):
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        # Make datetime.now() aware (UTC)
        now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
        return math.e**(-(now - timestamp).total_seconds()/(60*86.56*S))
    def retrieve_relevant(self, query, top_k: int, user_id = ""):
        relevant = self.memory.search(query, limit = top_k, filters = {"user_id": "global"})
        
        print(f"DEBUG mem0 raw search results for query '{query}':")
        for i, doc in enumerate(relevant["results"][:5]):  # Show first 5
            print(f"  {i}: {doc['memory'][:50]}... (retention calc: {self.calculate_retention(doc['created_at'], doc['metadata'].get('S', 1.0)):.3f})")
        
        # Filter by retention threshold and collect accessible memories
        filtered_results = []
        accessed_docs = []
        for doc in relevant["results"]:
            retention = self.calculate_retention(doc["created_at"], doc["metadata"].get("S", 1.0))
            if retention < 0.02:
                self.memory.delete(memory_id=doc["id"])
                continue

            filtered_results.append(doc)
            accessed_docs.append(doc)  # Return full doc for async update
        
        # Return filtered memories by type, plus docs for async update
        past_semantic = [doc["memory"] for doc in filtered_results if doc["metadata"].get("type") == "semantic"]
        past_episodic = [doc["memory"] for doc in filtered_results if doc["metadata"].get("type") == "episodic"]
        return past_semantic, past_episodic, accessed_docs
    
    def update_accessed_memories(self, docs):
        """Update memories that were accessed during retrieval (compress, boost retention, etc)"""
        for doc in docs:
            try:
                current_s = doc["metadata"].get("S", 1.0)
                retention = self.calculate_retention(doc["created_at"], current_s)
                
                # Compress if retention is low, boost if high
                if retention < 0.5:
                    # Compress low-retention memories
                    compressed = self.compressed_memory(doc["memory"], retention)
                    self.memory.update(
                        memory_id=doc["id"],
                        data=compressed,
                        metadata={"S": current_s, "retention": retention}
                    )
                else:
                    # Boost retention for frequently accessed memories
                    self.memory.update(
                        memory_id=doc["id"],
                        data=doc["memory"],
                        metadata={"S": current_s * 1.2, "retention": 1.0}
                    )
            except Exception as e:
                print(f"Error updating memory {doc.get('id')}: {e}")
    #to implement comrpession of memory
    def compressed_memory(self, text, retention):
        words = text.split()
        sample_size = min(int(retention * len(words)), len(words))
        indices = sorted(random.sample(range(len(words)), sample_size))
        return " ".join(words[i] for i in indices)