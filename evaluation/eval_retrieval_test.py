def test_query(memory, user_id, query):
    print("\nQUERY:", query)
    results = memory.search(query, user_id=user_id)
    for r in results[:5]:
        print("-", r["memory"])


# Example queries
queries = [
    "Where does the user live?",
    "What is the user's occupation?",
    "What activities does the user enjoy?",
    "Is the user married?"
]