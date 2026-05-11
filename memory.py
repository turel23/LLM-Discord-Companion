import chromadb
from datetime import datetime
class Memory:
    def __init__(self):
        self.client = chromadb.PersistentClient(path = "./memories")
        self.semantic = self.client.get_or_create_collection(name = "semantic_memories")
        self.episodic = self.client.get_or_create_collection(name = "episodic_memories")
    def save_semantic_memory(self, memory):
        memory_id = f"memory_{datetime.now().timestamp()}"
        self.semantic.add(
            documents = [memory],
            ids = [memory_id],
            metadatas = [{"timestamp": str(datatime.now())}]
        )
        print("Saved semantic memory: ", memory)
    def save_episodic_memory(self, memory):
        memory_id = f"memory_{datetime.now().timestamp()}"
        self.episodic.add(
            documents = [memory],
            ids = [memory_id],
            metadatas = [{"timestamp": str(datatime.now())}]
        )
        print("Saved episodic memory: ", memory)
    def retrieve_memories(self, query = query, n = 10, type = type):
        if type == "semantic":
            results = self.semantic.query(
                query_texts = [query],
                n_results = n
            )
        else:
            results = self.episodic.query(
                query_texts = [query],
                n_results = n
            )
        return results['documents'] if result["documents"] else []