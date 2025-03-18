from typing import List, Dict, Optional

class BaseMemory:
    """
    Abstract base for memory.
    Concrete classes can store conversation in a list, DB, or vector store.
    """
    def get_context(self) -> str:
        raise NotImplementedError

    def save_interaction(self, user_input: str, agent_output: str) -> None:
        raise NotImplementedError


class InMemoryMemory(BaseMemory):
    """
    Stores entire conversation in a Python list.
    Good for small scale or demos.
    For large usage, consider a DB or vector-based memory.
    """
    def __init__(self):
        self.history = []

    def get_context(self) -> str:
        return "\n".join(self.history)

    def save_interaction(self, user_input: str, agent_output: str) -> None:
        self.history.append(f"User: {user_input}")
        self.history.append(f"Agent: {agent_output}")


class VectorMemory(BaseMemory):
    """
    Vector-based memory implementation.
    Uses embeddings to store and retrieve relevant conversation parts.

    This is a placeholder - in a real implementation, you would
    integrate with a vector DB or embedding system.
    """
    def __init__(self, embedding_provider=None):
        self.history = []
        self.embedding_provider = embedding_provider
        self.vector_store = {}

    def get_context(self, query=None, max_results=5) -> str:
        """
        Retrieve relevant context based on semantic similarity.
        If query is None, return recent history.
        """
        if query is None or not self.vector_store:
            recent = self.history[-10:] if len(self.history) > 10 else self.history
            return "\n".join(recent)

        # In a real implementation, this would:
        # 1. Generate embedding for the query
        # 2. Perform similarity search against vector_store
        # 3. Return the most relevant context

        return "Relevant context would be retrieved here based on query embeddings"

    def save_interaction(self, user_input: str, agent_output: str) -> None:
        """
        Save interaction and update vector embeddings.
        """
        user_entry = f"User: {user_input}"
        agent_entry = f"Agent: {agent_output}"

        self.history.append(user_entry)
        self.history.append(agent_entry)

        # In a real implementation:
        # 1. Generate embeddings for these entries
        # 2. Store them in the vector database with their text
