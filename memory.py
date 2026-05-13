import chromadb
from datetime import datetime
class Memory:
    def __init__(self):
        self.client = chromadb.PersistentClient(path = "./memories")
        self.semantic = self.client.get_or_create_collection(name = "semantic_memories")
        self.episodic = self.client.get_or_create_collection(name = "episodic_memories")
    
    def save_semantic_memory(self, memory, user = "", topic = ""):
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
    def save_episodic_memory(self, memory, topic = ""):
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
    def retrieve_memories(self, query = "", n = 20, threshold = 0):
        query_list = [query] if isinstance(query, str) else query
        semantic_results = self.semantic.query(
            query_texts = query_list,
            n_results = n
        )
        episodic_results = self.episodic.query(
            query_texts = query_list,
            n_results = n
        )
        semantic_recency_list = self.format_recency(semantic_results['documents'][0], semantic_results['metadatas'][0]) if semantic_results["documents"] else []
        episodic_recency_list = self.format_recency(episodic_results['documents'][0], episodic_results['metadatas'][0]) if episodic_results["documents"] else []
        return semantic_recency_list, episodic_recency_list
    def format_recency(self, docs, metadatas):
        recency_list = []
        for doc, metadata in zip(docs, metadatas):
            timestamp = datetime.fromisoformat(metadata['timestamp'])
            diff = datetime.now() - timestamp
            if diff.total_seconds() < 60 * 60:
                recency = f"{diff.total_seconds() // 60} minutes ago"
            elif diff.total_seconds() < 60 * 60 * 24:
                recency = f"{diff.total_seconds() // (60 * 60)} hours ago"
            elif diff.total_seconds() < 60 * 60 * 24 * 7:
                recency = f"{diff.total_seconds() // (60 * 60 * 24)} days ago"
            else:
                recency = f"{diff.total_seconds() // (60 * 60 * 24 * 7)} weeks ago"
            recency_list.append(f"{doc} (from {recency})")
        return recency_list