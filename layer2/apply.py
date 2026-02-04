from typing import List, Dict


class Mem0PruneApplier:
    """
    Applies pruning decisions back to Mem0 safely using metadata updates.
    """

    def __init__(self, memory):
        """
        memory: mem0.Memory instance
        """
        self.memory = memory

    def apply(self, pruned_memories: List[Dict]):
        """
        Update Mem0 memories with pruning metadata.
        """
        for mem in pruned_memories:
            metadata = mem.get("metadata") or {}

            metadata.update(
                {
                    "status": mem.get("status", "ACTIVE"),
                    "canonical": mem.get("canonical", False),
                }
            )

            self.memory.update(
                memory_id=mem["id"],
                metadata=metadata,
            )
