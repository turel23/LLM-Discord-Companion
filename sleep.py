import random

from memory import MemoryManage as m

class Sleep:
    @staticmethod
    def pull_memories():
        memories = m.memory.get_all(filters={})
        if isinstance(memories, dict):
            memories = memories.get("results", [])

        selected_memories = []

        for mem in memories:
            retention = mem.get("metadata", {}).get("retention", 1.0)
            retention = max(0.0, min(float(retention), 1.0))
            if random.random() < retention:
                selected_memories.append(mem)

        return selected_memories
    def sleep_cycle():
        
