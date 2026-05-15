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
        for doc in relevant:
            if random.random() > doc.metadata["retention"]:
                relevant.remove(doc)
        if random.random() < 0.3:
            relevant.metadata["retention"] = 1.0
        past_semantic = [doc for doc in relevant if doc.metadata.get("type") == "semantic"]
        past_episodic = [doc for doc in relevant if doc.metadata.get("type") == "episodic"]
        return past_semantic, past_episodic
    def extract_keywords(self, text):
        rake = Rake()
        rake.extract_keywords_from_text(text)
        return rake.get_ranked_phrases()