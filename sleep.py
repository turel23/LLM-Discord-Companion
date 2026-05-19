import random

from memory import MemoryManage as m
from llm import llm

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
    def sleep_cycle(memories):
        for mem in memories:
            results = m.memory.search(query = mem["memory"], limit = 3, filters = {})
            results["results"].join(" | ")
            output_sem = llm.chat.completions.create() #create a semantic memory
            output_episodic = llm.chat.completions.create() #create an episodic memory
            m.memory.add(output_sem)
            m.memory.add(output_episodic)


