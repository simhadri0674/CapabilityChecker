# =====================================================
# IMPORTS
# =====================================================
import os
import sys
import json
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_community.graphs import Neo4jGraph
from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_groq import ChatGroq

# =====================================================
# LOAD ENV
# =====================================================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not all([GROQ_API_KEY, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
    print("❌ Missing environment variables.")
    sys.exit(1)

# =====================================================
# INITIALIZE LLM
# =====================================================
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0
)

# =====================================================
# CONNECT TO NEO4J
# =====================================================
graph = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD
)

print("✅ Connected to Neo4j")

# =====================================================
# LOAD & SPLIT TEXT
# =====================================================
def load_and_split(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    return splitter.create_documents([text])

# =====================================================
# TEXT → GRAPH
# =====================================================
def extract_graph_documents(documents):
    transformer = LLMGraphTransformer(llm=llm)
    return transformer.convert_to_graph_documents(documents)

def insert_graph(graph_docs):
    if graph_docs:
        graph.add_graph_documents(graph_docs)
        graph.refresh_schema()
        print("✅ Graph data inserted")

# =====================================================
# GRAPH QUERY (GRAPH FIRST)
# =====================================================
def graph_query_answer(query):

    schema = graph.get_schema

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
    try:
        # 1️⃣ Try strict first
        response = strict_chain.invoke({"query": query})

        if not response["intermediate_steps"][1]["context"]:
            print("⚠ No result with strict search. Trying fallback...\n")

            # 2️⃣ Try fallback
            response = fallback_chain.invoke({"query": query})

        print("\n--- Generated Cypher ---")
        print(response["intermediate_steps"][0])

        print("\n--- Neo4j Result ---")
        print(response["intermediate_steps"][1])

        print("\n--- Final Answer ---")
        result = response["result"]
        return result if result else "❌ No relevant data found."
        

    except Exception as e:
        print("❌ Error:", e)
        print("\n" + "-"*50 + "\n")



# =====================================================
# RAG
# =====================================================
def create_vector_store(documents):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    return FAISS.from_documents(documents, embeddings)

def rag_answer(query, retriever):

    docs = retriever.invoke(query)

    if not docs:
        return None

    context = "\n".join([doc.page_content for doc in docs])

    rag_prompt = f"""
You are an intelligent assistant.

Use ONLY the below context to answer the question.

Context:
{context}

Question:
{query}

Instructions:
1. Provide clear structured explanation.
2. Do not add external knowledge.
3. If context insufficient, say so clearly.
"""

    return llm.invoke(rag_prompt).content

# =====================================================
# STORE NEW KNOWLEDGE FROM CONVERSATION
# =====================================================
def extract_and_store_from_conversation(history):

    extraction_prompt = f"""
Extract structured knowledge from this conversation.

Return JSON list:
[
  {{
    "source": "...",
    "relationship": "...",
    "target": "..."
  }}
]

Conversation:
{history}

Return ONLY JSON.
"""

    response = llm.invoke(extraction_prompt).content

    try:
        data = json.loads(response)

        for item in data:
            graph.query(f"""
MERGE (a:Entity {{name: "{item['source']}"}})
MERGE (b:Entity {{name: "{item['target']}"}})
MERGE (a)-[:{item['relationship']}]->(b)
""")

        print("🧠 New knowledge stored in graph")

    except:
        pass

# =====================================================
# HYBRID LOGIC (GRAPH → RAG)
# =====================================================
def hybrid_answer(query, retriever, conversation_history):

    print("\n🔎 Trying GRAPH first...")
    graph_answer = graph_query_answer(query)

    if graph_answer:
        print("✅ Answer from GRAPH")
        return graph_answer

    print("⚠ Graph empty → Falling back to RAG")
    rag_result = rag_answer(query, retriever)

    if rag_result:
        return rag_result

    return "❌ No relevant data found."

# =====================================================
# MAIN
# =====================================================
def main():

    docs = load_and_split("data.txt")

    vector_store = create_vector_store(docs)
    retriever = vector_store.as_retriever()

    graph_docs = extract_graph_documents(docs)
    insert_graph(graph_docs)

    conversation_history = ""

    print("\n🚀 Hybrid GraphRAG Ready")
    print("Type 'exit or quit' to quit\n")

    while True:
        query = input("Ask: ")

        if query.lower() == "exit" or query.lower() == "quit":
            break

        conversation_history += f"\nUser: {query}"

        answer = hybrid_answer(query, retriever, conversation_history)

        print("\n🤖", answer)

        conversation_history += f"\nAssistant: {answer}"

        # 🔥 Store learned data into graph
        extract_and_store_from_conversation(conversation_history)

if __name__ == "__main__":
    main()
