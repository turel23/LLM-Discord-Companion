from mem0 import Memory
import math
from datetime import datetime
import random

config = {
    "llm": {"provider": "lmstudio"},
    "embedder": {
        "provider": "lmstudio",
        "config": {"embedding_dims": 384},   # match your LM Studio model
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0_local",
            "embedding_model_dims": 384,     # MUST match embedder
            "path": "./mem_db",       # NEW path so old 1536 collection doesn't conflict
        },
    },
}
memory = Memory.from_config(config)
class MemoryManage:
    def __init__(self):
        self.memory = memory
    def calculate_retention(self, created_at):
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('+00:00', ''))
        return math.e**(-(datetime.now()-created_at).total_seconds()/(60*36.716))
    def retrieve_relevant(self, query, top_k = 50, user_id = ""):
        relevant = self.memory.search(query, top_k = top_k, filters = {"user_id": user_id})
        
        for doc in relevant["results"]:
            retention = self.calculate_retention(doc["created_at"])
            self.memory.update(memory_id=doc["id"], data=self.compressed_memory(doc["memory"], retention), metadata={"retention": retention})
        
        # Random removal based on retention
        to_remove = [doc for doc in relevant["results"] if random.random() > doc["metadata"].get("retention", 1.0)]
        for doc in to_remove:
            relevant["results"].remove(doc)
        
        # Refresh some memories (boost retention)
        for doc in relevant["results"]:
            if random.random() < 0.3:
                self.memory.update(memory_id=doc["id"], data=doc["memory"], metadata={"retention": 1.0})
        
        past_semantic = [doc["memory"] for doc in relevant["results"] if doc["metadata"].get("type") == "semantic"]
        past_episodic = [doc["memory"] for doc in relevant["results"] if doc["metadata"].get("type") == "episodic"]
        return past_semantic, past_episodic
    #to implement comrpession of memory
    def compressed_memory(self, text, retention):
        if retention < 0.05:
            return "I forgot what the user said"
        words = text.split()
        sample_size = min(int(retention * len(words)), len(words))
        indices = sorted(random.sample(range(len(words)), sample_size))
        return "...".join(words[i] for i in indices)