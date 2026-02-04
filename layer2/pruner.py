from typing import List, Dict
from datetime import datetime


class MemoryPruner:
    """
    Selects canonical memories and soft-prunes redundant ones.
    """

    def select_canonical(self, group: List[Dict]) -> Dict:
        """
        Select the best representative memory from a semantic group.
        """

        def sort_key(m):
            created = m.get("created_at")
            try:
                created_ts = datetime.fromisoformat(created)
            except Exception:
                created_ts = datetime.min

            return (
                created_ts,  # newest preferred
                -len(m.get("memory", "")),  # shorter preferred
            )

        return sorted(group, key=sort_key, reverse=True)[0]

    def prune_groups(self, groups: List[List[Dict]]) -> List[Dict]:
        """
        Mark non-canonical memories as PRUNED.
        Returns a flat list of updated memories.
        """
        updated_memories = []

        for group in groups:
            canonical = self.select_canonical(group)

            for mem in group:
                mem_copy = mem.copy()

                if mem["id"] == canonical["id"]:
                    mem_copy["status"] = "ACTIVE"
                    mem_copy["canonical"] = True
                else:
                    mem_copy["status"] = "PRUNED"
                    mem_copy["canonical"] = False

                updated_memories.append(mem_copy)

        return updated_memories
