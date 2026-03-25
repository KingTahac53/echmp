# 🧠 ECHMP Evaluation Queries (Neo4j)

This document contains Cypher queries used to evaluate the **ECHMP system** on the **LoCoMo dataset**.  
All queries operate on structured conversational memory stored in Neo4j.

---

## 📌 Overview

- Queries are designed to retrieve **structured user memory**
- Only **ACTIVE facts** are considered to ensure consistency
- ECHMP removes redundant and outdated facts via **pruning**
- Demonstrates **deterministic retrieval** compared to Mem0

---

## 🔍 Evaluation Queries

### 1. Occupation Retrieval

**Question:** What is the user's occupation?

```cypher
MATCH (u:Entity {name:"User"})
-[:HAS_FACT]->(f:Fact {relation:"Occupation", status:"ACTIVE"})
-[:TARGET]->(o:Entity)
RETURN o.name
```

---

### 2. Location Retrieval

**Question:** Where did the user move from?

```cypher
MATCH (u:Entity {name:"User"})
-[:HAS_FACT]->(f:Fact {relation:"Location", status:"ACTIVE"})
-[:TARGET]->(o:Entity)
RETURN o.name
```

---

### 3. Activity Retrieval

**Step 1: Check available facts**

```cypher
MATCH (f:Fact {relation:"Activity"})
RETURN f.status, count(*)
```

**Step 2: Final Query**

```cypher
MATCH (u:Entity {name:"User"})
-[:HAS_FACT]->(f:Fact {relation:"Activity", status:"ACTIVE"})
-[:TARGET]->(o:Entity)
RETURN DISTINCT o.name LIMIT 10
```

---

### 4. Family Status

```cypher
MATCH (u:Entity {name:"User"})
-[:HAS_FACT]->(f:Fact {relation:"FamilyStatus", status:"ACTIVE"})
-[:TARGET]->(o:Entity)
RETURN DISTINCT o.name
```

---

### 5. Identity

```cypher
MATCH (u:Entity {name:"User"})
-[:HAS_FACT]->(f:Fact {relation:"Identity", status:"ACTIVE"})
-[:TARGET]->(o:Entity)
RETURN o.name
```

---

### 6. Life Goals

```cypher
MATCH (u:Entity {name:"User"})
-[:HAS_FACT]->(f:Fact {relation:"LifeGoal", status:"ACTIVE"})
-[:TARGET]->(o:Entity)
RETURN o.name
```

---

### 🛠 Debug Query (Optional)

```cypher
MATCH (u:Entity)
-[:HAS_FACT]->(f:Fact {relation:"Activity", status:"ACTIVE"})
-[:TARGET]->(o:Entity)
RETURN u.name, o.name LIMIT 20
```

---

## 📸 Evaluation Outputs

Store all query result screenshots in the following directory:

```
evaluation/echmp_results/
```

### 📂 Naming Convention

```
occupation.png
activity.png
family_status.png
identity.png
life_goal.png
location.png
```

---

## ⚠️ Best Practices

- ❌ Do NOT dump screenshots in the root directory
- ✅ Always organize outputs under `evaluation/echmp_results/`

---

## 📊 Evaluation

- Mem0 baseline results: `evaluation/Mem0_Analysis.ipynb`
- ECHMP query evaluation: `evaluation/echmp_queries.md`
- Sample outputs: `evaluation/echmp_results/`
