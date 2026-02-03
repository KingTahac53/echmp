from mem0 import Memory
from layer1.schemas import fact_to_sentence


class Layer1Mem0Adapter:
    def __init__(self, neo4j_driver, mem0_config: dict):
        self.driver = neo4j_driver
        self.memory = Memory.from_config(mem0_config)

    def fetch_active_facts(self):
        query = """
        MATCH (s:Entity)-[r {status:"ACTIVE"}]->(o:Entity)
        RETURN s.name AS subject,
               type(r) AS relation,
               o.name AS object,
               r.timestamp AS timestamp
        """
        with self.driver.session() as session:
            return list(session.run(query))

    def sync_to_mem0(self, user_id: str):
        facts = self.fetch_active_facts()

        for f in facts:
            sentence = fact_to_sentence(f["subject"], f["relation"], f["object"])

            self.memory.add(
                sentence,
                user_id=user_id,
                metadata={
                    "relation": f["relation"],
                    "timestamp": f["timestamp"],
                    "source": "layer1",
                },
            )
