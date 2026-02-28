import os
import sys
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_neo4j import Neo4jGraph

from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.runnables import RunnablePassthrough
# from langchain.chains.retrieval_qa.base import RetrievalQA

# from langchain.prompts import PromptTemplate

# from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain


# =====================================================
# 1️⃣ LOAD ENV VARIABLES
# =====================================================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not all([GROQ_API_KEY, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
    print("❌ Missing environment variables. Check your .env file.")
    sys.exit(1)


# =====================================================
# 2️⃣ INITIALIZE LLM
# =====================================================
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0
)


# =====================================================
# 3️⃣ CONNECT TO NEO4J
# =====================================================
graph = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD
)

print("✅ Connected to Neo4j")


# =====================================================
# 4️⃣ OPTIONAL: CLEAR DATABASE (FOR TESTING)
# =====================================================
def clear_database():
    graph.query("MATCH (n) DETACH DELETE n")
    print("🧹 Database cleared")

# Uncomment if you want clean DB each run
# clear_database()


# =====================================================
# 5️⃣ LOAD AND SPLIT TEXT
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
# 6️⃣ TEXT → GRAPH TRANSFORMATION
# =====================================================
def extract_graph_documents(documents):
    transformer = LLMGraphTransformer(
            llm=llm,
            allowed_nodes=["Person", "Organization", "Location", "Concept", "Event", "Object"],
            allowed_relationships=[
                "RELATED_TO",
                "PART_OF",
                "PARTICIPATED_IN",
                "LOCATED_AT",
                "BORN_IN",
                "FOUNDED",
                "MEMBER_OF",
                "OWNED_BY"
            ],
            strict_mode=True
        )


    print("🔄 Extracting graph structure...")
    graph_docs = transformer.convert_to_graph_documents(documents)

    if not graph_docs:
        print("⚠️ No graph data extracted")
    else:
        print(f"✅ Extracted {len(graph_docs)} graph documents")

    return graph_docs


# =====================================================
# 7️⃣ INSERT INTO NEO4J
# =====================================================
def insert_graph(graph_docs):
    if not graph_docs:
        print("❌ Nothing to insert")
        return

    for doc in graph_docs:
        for node in doc.nodes:
            node.type = node.type.replace(" ", "_")
        for rel in doc.relationships:
            rel.type = rel.type.replace(" ", "_")

    graph.add_graph_documents(graph_docs)

    graph.refresh_schema()

    print("✅ Data inserted successfully")
    # print("📊 Labels:", graph.query("CALL db.labels()"))
    # print("📊 Relationship Types:", graph.query("CALL db.relationshipTypes()"))
    print("📊 Types:", graph.query("CALL db.schema.visualization()"))

# =====================================================
# 8️⃣ CREATE GRAPH QA CHAIN
# =====================================================
from langchain_core.prompts import PromptTemplate

def graph_query_answer(query, graph, llm):

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
# 9 CREATE VECTOR STORE (RAG)
# =====================================================
def create_vector_store(documents):

    print("🔎 Creating Vector Store...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vector_store = FAISS.from_documents(documents, embeddings)

    print("✅ Vector store ready")

    return vector_store
# =====================================================
#  HYBRID GRAPH + RAG QA
# =====================================================
def hybrid_answer(query, qa_chain, retriever, llm):
    """
    Hybrid Graph + RAG answering logic.

    Priority:
    1. Use Graph if valid result found
    2. Fallback to RAG if graph empty
    3. Return clean structured answer
    """

    print("\n===============================")
    print("🔍 USER QUERY:", query)
    print("===============================\n")

    # ===============================
    # 1️⃣ GRAPH QUERY SECTION
    # ===============================
    try:
        # print("🚀 Step 1: Querying Neo4j Graph...")

        # graph_result = qa_chain.invoke({"query": query})

        # print("📦 Raw Graph Result:", graph_result)

        print("\n🔎 Trying GRAPH first...")

        graph_answer = graph_query_answer(query, graph, llm)

        # Check meaningful result
        if graph_answer and graph_answer.lower() not in [
            "i don't know the answer.",
            "no data found",
            "none",
            ""
        ]:

            print("✅ Valid data found in GRAPH")
            print("🧠 Step 2: Sending Graph data to LLM for structured formatting...\n")

            graph_prompt = f"""
You are an intelligent Graph Database assistant.

Use ONLY the below Graph Query Result to answer the question.
Do NOT use external knowledge.

Graph Query Result:
{graph_answer}

Question:
{query}

Instructions:
1. Explain in structured format.
2. Show reasoning clearly.
3. If data contains relationships, explain them.
4. Do not assume missing information.
"""

            graph_response = llm.invoke(graph_prompt)

            print("📤 Final Answer Source: GRAPH\n")
            return graph_response.content

        else:
            print("⚠ Graph returned empty or insufficient data.")

    except Exception as e:
        print("❌ Graph Error:", e)

    # ===============================
    # 2️⃣ RAG FALLBACK SECTION
    # ===============================
    try:
        print("\n🚀 Step 3: Falling back to Vector RAG Retrieval...")

        rag_docs = retriever.invoke(query)

        if rag_docs:
            print(f"📚 Retrieved {len(rag_docs)} documents from FAISS\n")

            for i, doc in enumerate(rag_docs, 1):
                print(f"🔹 Document {i} Preview:\n{doc.page_content[:300]}...\n")

            rag_context = "\n".join([doc.page_content for doc in rag_docs])

            print("🧠 Step 4: Sending RAG context to LLM...\n")

            rag_prompt = f"""
You are an intelligent assistant.

Use ONLY the below context to answer the question.

Context:
{rag_context}

Question:
{query}

Instructions:
1. Provide clear structured explanation.
2. Do not add external knowledge.
3. If context insufficient, say so clearly.
"""

            rag_response = llm.invoke(rag_prompt)

            print("📤 Final Answer Source: RAG\n")
            return rag_response.content

        else:
            print("⚠ No documents retrieved from FAISS.")

    except Exception as e:
        print("❌ RAG Error:", e)

    # ===============================
    # 3️⃣ NO DATA FOUND
    # ===============================
    return "❌ No relevant data found in Graph or RAG."

# =====================================================
# =====================================================
def main():

    # Load docs
    docs = load_and_split("data.txt")

    # Create Vector Store
    vector_store = create_vector_store(docs)
    retriever = vector_store.as_retriever()

    # Extract Graph
    graph_docs = extract_graph_documents(docs)
    insert_graph(graph_docs)

    # Create Graph QA
    # qa_chain = graph_query_answer(query, graph, llm)

    print("\n🚀 Hybrid GraphRAG System Ready!")
    print("Type 'exit' to quit.\n")

    while True:
        query = input("Ask a question: ")

        if query.lower() == "exit":
            break

        try:
            answer = hybrid_answer(query, graph, retriever, llm)

            print("\n🤖 Final Answer:")
            print(answer)

        except Exception as e:
            print("❌ Error:", e)


if __name__ == "__main__":
    main()
