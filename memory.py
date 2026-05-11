import chromadb
from datetime import datetime
class Memory:
    def __init__(self):
        self.client = chromadb.PersistentClient(path = "./memories")
        self.collection = self.client.get_or_create_collection(name = "memories")
    def save_memory(self, memory):
        memory_id = f"memory_{datetime.now().timestamp()}"
        self.collection.add(
            documents = [memory],
            ids = [memory_id],
            metadatas = [{"timestamp": str(datatime.now())}]
        )
        print("Saved memory: ", memory)
    def retrieve_memories(self, query, n=10):
        results = self.collection.query(
            query_texts = [query],
            n_results = n
        )
        return results['documents'][0] if result["documents"] else []