import random

from memory import MemoryManage as m

class Sleep:
    @staticmethod
    async def pull_memories(group_id: str = "global", limit: int = 50):
        memories = await m.list_memories(user_id=group_id, limit=limit)

        selected_memories = []

        for mem in memories:
            retention = mem.get("metadata", {}).get("retention", 1.0)
            retention = max(0.0, min(float(retention), 1.0))
            if random.random() < retention:
                selected_memories.append(mem)

        return selected_memories

    @staticmethod
    async def sleep_cycle(memories, group_id: str = "global"):
        reflections = []
        for mem in memories:
            results = await m.retrieve_relevant(query=mem["memory"], top_k=3, user_id=group_id)
            reflections.append({"memory": mem, "related": results})

        return reflections


