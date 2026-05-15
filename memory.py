from mem0.memory import Memory
import math
from datetime import datetime
import random
from rake_nltk import Rake

memory = Memory()
class MemoryManage:
    def __init__(self):
        self.memory = memory
    def calculate_retention(self, timestamp):
        return math.e**(-(datetime.now()-timestamp.fromisoformat()).total_seconds()/(60*36.716))
    def retrieve_relevant(self, query, top_k = int):
        relevant = self.memory.query(query = query, top_k = top_k)
        relevant.metadata["retention"] = self.calculate_retention(relevant.metadata["retention"])        
        relevant.metadata["m"]
        for doc in relevant:
            if random.random() > doc.metadata["retention"]:
                relevant.remove(doc)
        if random.random() < 0.3:
            relevant.metadata["retention"] = 1.0
            relevant.metadata["timestamp"] = datetime.now().isoformat()
        past_semantic = [doc for doc in relevant if doc.metadata.get("type") == "semantic"]
        past_episodic = [doc for doc in relevant if doc.metadata.get("type") == "episodic"]
        return past_semantic, past_episodic
    #to implement comrpession of memory
    def compressed_memory(self, text, retention):
        if retention < 0.05:
            return "I forgot what the user said"
        phrases = random.sample(range(1, len(text.split())), int(retention * len(text.split()))).sort()
        words = [text.split()[i] for i in phrases]
        return "...".join(words)