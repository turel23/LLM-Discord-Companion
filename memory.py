from __future__ import annotations

import math
import os
import random
from datetime import datetime, timezone
from typing import Any


class MemoryManage:
    def __init__(self):
        self._graphiti = None
        self._episode_type = None
        self.memory = self

    def _load_graphiti(self):
        if self._graphiti is None:
            try:
                from graphiti_core import Graphiti
                from graphiti_core.nodes import EpisodeType
            except ImportError as exc:
                raise RuntimeError(
                    "graphiti-core is required for memory access. Install graphiti-core and run a local Graphiti backend."
                ) from exc

            uri = os.getenv("GRAPHITI_URI", "bolt://localhost:7687")
            user = os.getenv("GRAPHITI_USER", "neo4j")
            password = os.getenv("GRAPHITI_PASSWORD", "password")
            self._graphiti = Graphiti(uri, user, password)
            self._episode_type = EpisodeType

        return self._graphiti

    def _coerce_episode_type(self, source: Any):
        episode_type = self._episode_type
        if episode_type is None:
            self._load_graphiti()
            episode_type = self._episode_type

        if isinstance(source, str):
            return episode_type.from_str(source)
        return source

    @staticmethod
    def _as_iso(timestamp: Any):
        if timestamp is None:
            return None
        if isinstance(timestamp, str):
            return timestamp
        if hasattr(timestamp, "isoformat"):
            return timestamp.isoformat()
        return str(timestamp)

    @staticmethod
    def _doc_from_fact(fact: Any):
        if isinstance(fact, dict):
            fact_text = fact.get("fact") or fact.get("content") or fact.get("memory") or str(fact)
            created_at = fact.get("created_at") or fact.get("valid_at")
            uuid = fact.get("uuid")
            group_id = fact.get("group_id")
            metadata = dict(fact.get("metadata") or {})
        else:
            fact_text = getattr(fact, "fact", None) or getattr(fact, "content", None) or str(fact)
            created_at = getattr(fact, "created_at", None)
            uuid = getattr(fact, "uuid", None)
            group_id = getattr(fact, "group_id", None)
            metadata = dict(getattr(fact, "metadata", None) or {})

        return {
            "id": uuid,
            "memory": fact_text,
            "created_at": MemoryManage._as_iso(created_at),
            "group_id": group_id,
            "metadata": {"type": "semantic", "S": metadata.get("S", 1.0), **metadata},
        }

    @staticmethod
    def _doc_from_episode(episode: Any):
        content = getattr(episode, "content", None)
        if content is None and isinstance(episode, dict):
            content = episode.get("content")

        created_at = getattr(episode, "created_at", None)
        if created_at is None and isinstance(episode, dict):
            created_at = episode.get("created_at")

        uuid = getattr(episode, "uuid", None)
        if uuid is None and isinstance(episode, dict):
            uuid = episode.get("uuid")
        group_id = getattr(episode, "group_id", None)
        if group_id is None and isinstance(episode, dict):
            group_id = episode.get("group_id")

        metadata = getattr(episode, "episode_metadata", None)
        if metadata is None and isinstance(episode, dict):
            metadata = episode.get("episode_metadata") or episode.get("metadata")

        return {
            "id": uuid,
            "memory": content or "",
            "created_at": MemoryManage._as_iso(created_at),
            "group_id": group_id,
            "metadata": {"type": "episodic", "S": (metadata or {}).get("S", 1.0), **(metadata or {})},
        }

    async def add_memory(
        self,
        name: str,
        episode_body: str,
        group_id: str = "global",
        source: str = "text",
        source_description: str = "",
        reference_time: datetime | None = None,
        uuid: str | None = None,
        update_communities: bool = False,
        **kwargs: Any,
    ):
        graphiti = self._load_graphiti()
        episode_type = self._coerce_episode_type(source)
        reference_time = reference_time or datetime.now(timezone.utc)
        return await graphiti.add_episode(
            name=name,
            episode_body=episode_body,
            source_description=source_description,
            reference_time=reference_time,
            source=episode_type,
            group_id=group_id,
            uuid=uuid,
            update_communities=update_communities,
            **kwargs,
        )

    async def retrieve_relevant(self, query: str, top_k: int, user_id: str = "global"):
        graphiti = self._load_graphiti()
        group_id = user_id or "global"

        try:
            semantic_results = await graphiti.search(
                query=query,
                group_ids=[group_id],
                num_results=top_k,
            )
        except TypeError:
            semantic_results = await graphiti.search(
                query=query,
                group_ids=[group_id],
                limit=top_k,
            )

        try:
            episodic_results = await graphiti.retrieve_episodes(
                reference_time=datetime.now(timezone.utc),
                last_n=top_k,
                group_ids=[group_id],
            )
        except TypeError:
            episodic_results = []

        def retention_for_doc(doc: dict[str, Any]) -> float:
            created_at = doc.get("created_at")
            s_value = float(doc.get("metadata", {}).get("S", 1.0) or 1.0)
            return self.calculate_retention(created_at, s_value)

        filtered_semantic_docs = []
        filtered_episodic_docs = []
        accessed_docs = []

        for result in semantic_results or []:
            doc = self._doc_from_fact(result)
            retention = retention_for_doc(doc)
            if retention < 0.02:
                continue
            doc["metadata"]["retention"] = retention
            filtered_semantic_docs.append(doc)
            accessed_docs.append(doc)

        for result in episodic_results or []:
            doc = self._doc_from_episode(result)
            retention = retention_for_doc(doc)
            if retention < 0.02:
                continue
            doc["metadata"]["retention"] = retention
            filtered_episodic_docs.append(doc)
            accessed_docs.append(doc)

        past_semantic = [doc["memory"] for doc in filtered_semantic_docs if doc["memory"]]
        past_episodic = [doc["memory"] for doc in filtered_episodic_docs if doc["memory"]]
        return past_semantic, past_episodic, accessed_docs

    async def list_memories(self, user_id: str = "global", limit: int = 50):
        graphiti = self._load_graphiti()
        episodes = await graphiti.retrieve_episodes(
            reference_time=datetime.now(timezone.utc),
            last_n=limit,
            group_ids=[user_id or "global"],
        )
        return [self._doc_from_episode(episode) for episode in episodes]

    async def update_accessed_memories(self, docs):
        graphiti = self._load_graphiti()

        for doc in docs:
            try:
                retention = self.calculate_retention(doc.get("created_at"), doc.get("metadata", {}).get("S", 1.0))
                uuid = doc.get("id")
                group_id = doc.get("group_id") or doc.get("metadata", {}).get("group_id") or "global"

                if not uuid:
                    continue

                if retention < 0.5:
                    compressed = self.compressed_memory(doc.get("memory", ""), retention)
                    await graphiti.remove_episode(uuid)
                    if compressed:
                        source = "message" if doc.get("metadata", {}).get("type") == "episodic" else "text"
                        await self.add_memory(
                            name=doc.get("memory", "")[:80] or "Compressed memory",
                            episode_body=compressed,
                            source=source,
                            source_description="Compressed episodic memory after retrieval",
                            group_id=group_id,
                            reference_time=datetime.now(timezone.utc),
                        )
            except Exception as e:
                print(f"Error updating memory {doc.get('id')}: {e}")

    def calculate_retention(self, timestamp, S):
        if timestamp is None:
            return 1.0
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
        return math.e ** (-(now - timestamp).total_seconds() / (60 * 86.56 * S))

    def compressed_memory(self, text, retention):
        words = text.split()
        sample_size = min(int(retention * len(words)), len(words))
        if sample_size <= 0:
            return ""
        indices = sorted(random.sample(range(len(words)), sample_size))
        return " ".join(words[i] for i in indices)