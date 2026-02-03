def fact_to_sentence(subject: str, relation: str, obj: str) -> str:
    if relation == "WorksAs":
        return f"{subject} works as a {obj}."
    if relation == "Location":
        return f"{subject} lives in {obj}."
    return f"{subject} has relation {relation} with {obj}."
