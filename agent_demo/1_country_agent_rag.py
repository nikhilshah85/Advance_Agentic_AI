import json
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI

load_dotenv(override=True);

# ---------------------------------
# Load JSON
# ---------------------------------

with open("countries.json", "r", encoding="utf-8") as f:
    countries = json.load(f)

documents = []

for item in countries:

    text = f"""
    Country: {item['country']}
    Capital: {item['capital']}
    Currency: {item['currency']}
    Timezone: {item['timezone']}
    Population: {item['population']}

    Places:
    {', '.join(item['places_to_visit'])}

    Slangs:
    {', '.join(item['common_slangs'])}
    """

    documents.append(
        Document(
            page_content=text,
            metadata={"country": item["country"]}
        )
    )

# ---------------------------------
# Embeddings
# ---------------------------------

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

# ---------------------------------
# Vector DB
# ---------------------------------

vectorstore = Chroma.from_documents(
    documents,
    embeddings,
    persist_directory="./country_db"
)

retriever = vectorstore.as_retriever(
    search_kwargs={"k": 2}
)

# ---------------------------------
# LLM
# ---------------------------------

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)

# ---------------------------------
# Agent Loop
# ---------------------------------

print("\n🌍 Country Expert Agent")
print("Type exit to quit\n")

while True:

    question = input("You: ")

    if question.lower() == "exit":
        break

    docs = retriever.invoke(question)

    context = "\n".join(
        doc.page_content
        for doc in docs
    )

    prompt = f"""
You are a Country Expert AI.

Use ONLY the supplied context.

Context:
{context}

Question:
{question}

Answer:
"""

    response = llm.invoke(prompt)

    print("\nAgent:")
    print(response.content)
    print()