import chromadb
from datetime import datetime
class Memory:
    def __init__(self):
        self.client = chromadb.PersistentClient(path = "./memories")
        self.semantic = self.client.get_or_create_collection(name = "semantic_memories")
        self.episodic = self.client.get_or_create_collection(name = "episodic_memories")
    def save_semantic_memory(self, memory, user = str, topic = str):
        lines = memory.split("\n")
        for line in lines:
            if line.strip():  # Skip empty lines
                memory_id = f"memory_{datetime.now().timestamp()}"
                self.semantic.add(
                    documents = [line],
                    ids = [memory_id],
                    metadatas = [{"timestamp": str(datetime.now()), "user": user, "topic": topic}]
                )
                print("Saved semantic memory: ", line)
    def save_episodic_memory(self, memory, topic = str):
        memory_id = f"memory_{datetime.now().timestamp()}"
        self.episodic.add(
            documents = [memory],
            ids = [memory_id],
            metadatas = [{"timestamp": str(datetime.now()), "topic": topic}]
        )
        print("Saved episodic memory: ", memory)
    # def retrieve_memories(self, query, n = 10, type = "semantic"):
    #     # Convert string to list if needed
    #     query_list = [query] if isinstance(query, str) else query
        
    #     if type == "semantic":
    #         results = self.semantic.query(
    #             query_texts = query_list,
    #             n_results = n
    #         )
    #     else:
    #         results = self.episodic.query(
    #             query_texts = query_list,
    #             n_results = n
    #         )
    #     return results['documents'][0] if results["documents"] else []
    def retrieve_memories(self, query = str):
        query_list = [query] if isinstance(query, str) else query
        semantic_results = self.semantic.query(
            query_texts = query_list,
            n_results = 10
        )
        episodic_results = self.episodic.query(
            query_texts = query_list,
            n_results = 10
        )
        return semantic_results['documents'][0] if semantic_results["documents"] else [], episodic_results['documents'][0] if episodic_results["documents"] else []