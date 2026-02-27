from mem0 import Memory
import json
import time

# ---------------- CONFIG ----------------

DATASET_PATH = "data/locomo/locomo10.json"

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0_baseline_eval_safe",
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

# ---------------- LOAD DATA ----------------

with open(DATASET_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# 🔥 IMPORTANT: Only 1 conversation
data = data[:1]

utterance_count = 0

for convo in data:
    conversation = convo["conversation"]

    session_keys = [
        k for k in conversation.keys()
        if k.startswith("session_") and not k.endswith("_date_time")
    ]

    for key in session_keys:
        for turn in conversation[key]:
            try:
                memory.add(
                    turn["text"],
                    user_id="mem0_baseline",
                    metadata={"source": "raw_locomo"},
                )
                utterance_count += 1

                # 🔥 Small delay to avoid LLM overload
                time.sleep(0.1)

            except Exception as e:
                print("Error adding memory:", e)

print("\n--- BASELINE RESULTS ---")
print("Utterances attempted:", utterance_count)

all_memories = list(memory.get_all(user_id="mem0_baseline"))
print("Mem0 entries stored:", len(all_memories))