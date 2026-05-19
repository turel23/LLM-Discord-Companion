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
    def calculate_retention(self, timestamp, S):
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        # Make datetime.now() aware (UTC)
        now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
        return math.e**(-(now - timestamp).total_seconds()/(60*36.716*S))
    def retrieve_relevant(self, query, top_k = 50, user_id = ""):
        relevant = self.memory.search(query, top_k = top_k, filters = {"user_id": user_id})
        
        for doc in relevant["results"]:
            if doc["metadata"].get("retention") < 0.02:
                self.memory.delete(memory_id=doc["id"])
            retention = self.calculate_retention(doc["created_at"], doc["metadata"].get("S", 1.0))
            print("DEBUG retention memory:", doc["memory"], "created at:", doc["created_at"], "retention:", retention)
            self.memory.update(memory_id=doc["id"], data=self.compressed_memory(doc["memory"], retention), metadata={"retention": retention})
        
        # Random removal based on retention
        to_remove = [doc for doc in relevant["results"] if random.random() > doc["metadata"].get("retention", 1.0)]
        for doc in to_remove:
            relevant["results"].remove(doc)
        
        # Refresh some memories (boost retention)
        for doc in relevant["results"]:
            if random.random() < 0.3:
                self.memory.update(memory_id=doc["id"], data=doc["memory"], metadata={"retention": 1.0, "S": doc["metadata"].get("S", 1.0) * 1.5}, created_at = datetime.now().isoformat())
        
        results = relevant.copy()
        past_semantic = [doc["memory"] for doc in results["results"] if doc["metadata"].get("type") == "semantic"]
        past_episodic = [doc["memory"] for doc in results["results"] if doc["metadata"].get("type") == "episodic"]
        return past_semantic, past_episodic
    #to implement comrpession of memory
    def compressed_memory(self, text, retention):
        words = text.split()
        sample_size = min(int(retention * len(words)), len(words))
        indices = sorted(random.sample(range(len(words)), sample_size))
        return " ".join(words[i] for i in indices)