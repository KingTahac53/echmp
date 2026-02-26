from mem0 import Memory
import json

DATASET_PATH = "data/locomo/locomo10.json"

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0_baseline_eval",
            "host": "localhost",
            "port": 6333,
            "embedding_model_dims": 384,
        },
    },
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3.1:8b",
            "temperature": 0,
            "ollama_base_url": "http://localhost:11434",
        },
    },
}

memory = Memory.from_config(config)
memory.delete_all(user_id="mem0_baseline")

with open(DATASET_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

utterance_count = 0

for convo in data:
    conversation = convo["conversation"]
    session_keys = [
        k for k in conversation.keys()
        if k.startswith("session_") and not k.endswith("_date_time")
    ]

    for key in session_keys:
        for turn in conversation[key]:
            memory.add(
                turn["text"],
                user_id="mem0_baseline",
                metadata={"source": "raw_locomo"}
            )
            utterance_count += 1

print("Total utterances added:", utterance_count)

all_memories = list(memory.get_all(user_id="mem0_baseline"))
print("Total Mem0 entries stored:", len(all_memories))