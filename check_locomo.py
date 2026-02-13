import json

with open("data/locomo/locomo10.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(type(data))
print(len(data))

# Print keys of first object
print(data[0].keys())

first = data[0]

# If conversations are nested
for key, value in first.items():
    print(key, "→", type(value))

# If there is a messages list inside:
if "messages" in first:
    print(first["messages"][0])
first = data[0]

# If conversations are nested
for key, value in first.items():
    print(key, "→", type(value))

# If there is a messages list inside:
if "messages" in first:
    print(first["messages"][0])

first = data[0]

conv = first["conversation"]

print(type(conv))
print(conv.keys())

for key, value in conv.items():
    print(key, "→", type(value))

# Try to find messages inside
for key in conv.keys():
    if isinstance(conv[key], list):
        print("List key:", key)
        print("First element:", conv[key][0])
        break
