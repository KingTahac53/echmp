import yaml
from mem0 import Memory

with open("mem0_config.yaml", "r") as f:
    config = yaml.safe_load(f)

memory = Memory.from_config(config)

memory.add(
    [
        {"role": "user", "content": "I live in Seattle"},
        {"role": "assistant", "content": "Got it"},
    ],
    user_id="test_user",
)

results = memory.search("Where do I live?", user_id="test_user")

print(results)
