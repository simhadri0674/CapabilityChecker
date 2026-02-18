import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_community.graphs import Neo4jGraph
from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_groq import ChatGroq




load_dotenv()

# Create graph connection
graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
)

print("✅ Connected to Neo4j Aura")
print("Schema:")
#print(graph.schema)

llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY")
    
)
strict_prompt = PromptTemplate(
    input_variables=["schema", "question"],
    template="""
You are an expert Neo4j Cypher generator.

Graph schema:
{schema}

Rules:
- Use property `id`
- Use exact matching:
  WHERE toLower(n.id) CONTAINS toLower("value")
- Return:
  OPTIONAL MATCH (n)-[r]-(related)
  RETURN n, r, related
- Start directly with MATCH
- Return only raw Cypher

Question:
{question}
"""
)


fallback_prompt = PromptTemplate(
    input_variables=["schema", "question"],
    template="""
You are an expert Neo4j Cypher generator.

Graph schema:
{schema}

Rules:
- Try matching using:
  id OR name
- Use:
  WHERE toLower(n.id) CONTAINS toLower("value")
     OR toLower(n.name) CONTAINS toLower("value")
- Return:
  OPTIONAL MATCH (n)-[r]-(related)
  RETURN n, r, related
- Start with MATCH
- Return only raw Cypher

Question:
{question}
"""
)




strict_chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    cypher_prompt=strict_prompt,
    verbose=True,
    validate_cypher=True,
    return_intermediate_steps=True,
    allow_dangerous_requests=True
)

fallback_chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    cypher_prompt=fallback_prompt,
    verbose=True,
    validate_cypher=True,
    return_intermediate_steps=True,
    allow_dangerous_requests=True
)


print(" Graph Chatbot Started")
print("Type 'exit' to quit.\n")

while True:
    user_question = input("💬 You: ")

    if user_question.lower() in[ "exit", "quit"]:
        print("👋 Exiting chatbot...")
        break

    try:
        # 1️⃣ Try strict first
        response = strict_chain.invoke({"query": user_question})

        if not response["intermediate_steps"][1]["context"]:
            print("⚠ No result with strict search. Trying fallback...\n")

            # 2️⃣ Try fallback
            response = fallback_chain.invoke({"query": user_question})

        print("\n--- Generated Cypher ---")
        print(response["intermediate_steps"][0])

        print("\n--- Neo4j Result ---")
        print(response["intermediate_steps"][1])

        print("\n--- Final Answer ---")
        print(response["result"])
        print("\n" + "-"*50 + "\n")

    except Exception as e:
        print("❌ Error:", e)
        print("\n" + "-"*50 + "\n")