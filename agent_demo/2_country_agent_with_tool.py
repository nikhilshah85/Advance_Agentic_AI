import json
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
# python -m pip install duckduckgo-search
from duckduckgo_search import DDGS

# =====================================================
# Load Environment
# =====================================================

load_dotenv(override=True);

# =====================================================
# Load Country Data
# =====================================================

with open("countries.json", "r", encoding="utf-8") as f:
    countries = json.load(f)

documents = []

for item in countries:

    places = item.get(
        "places",
        item.get("places_to_visit", [])
    )

    slangs = item.get(
        "slangs",
        item.get("common_slangs", [])
    )

    text = f"""
Country: {item.get('country')}

Capital: {item.get('capital')}

Currency: {item.get('currency')}

Timezone: {item.get('timezone')}

Population: {item.get('population')}

Places To Visit:
{", ".join(places)}

Common Slangs:
{", ".join(slangs)}
"""

    documents.append(
        Document(
            page_content=text,
            metadata={
                "country": item.get("country")
            }
        )
    )

# =====================================================
# Embeddings + Vector DB
# =====================================================

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

vectorstore = Chroma.from_documents(
    documents=documents,
    embedding=embeddings,
    persist_directory="./country_db"
)

# =====================================================
# LLM
# =====================================================

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)

# =====================================================
# Country List
# =====================================================

COUNTRIES = [
    "india",
    "united states",
    "usa",
    "united kingdom",
    "uk",
    "japan",
    "germany",
    "australia",
    "canada",
    "brazil"
]

# =====================================================
# Web Search Tool
# =====================================================

def web_search(query):

    results_text = []

    try:

        with DDGS() as ddgs:

            results = ddgs.text(
                query,
                max_results=5
            )

            for r in results:

                title = r.get("title", "")
                body = r.get("body", "")

                results_text.append(
                    f"Title: {title}\n"
                    f"Content: {body}"
                )

    except Exception as e:

        return f"Search Error: {e}"

    return "\n\n".join(results_text)

# =====================================================
# Country Detection
# =====================================================

def contains_country(question):

    q = question.lower()

    for country in COUNTRIES:

        if country in q:
            return True

    return False

# =====================================================
# Search Vector DB
# =====================================================

def search_country_db(question):

    docs = vectorstore.similarity_search(
        question,
        k=3
    )

    context = "\n\n".join(
        doc.page_content
        for doc in docs
    )

    return context

# =====================================================
# Check if Context Answers Question
# =====================================================

def can_answer_from_context(question, context):

    prompt = f"""
You are a routing assistant.

Question:
{question}

Context:
{context}

Can the question be answered accurately using ONLY the context?

Respond with exactly:

YES

or

NO
"""

    response = llm.invoke(prompt)

    decision = response.content.strip().upper()

    return decision.startswith("YES")

# =====================================================
# Generate Final Answer
# =====================================================

def generate_answer(question, context, source):

    prompt = f"""
You are a Country Expert AI Agent.

Source:
{source}

Context:
{context}

Question:
{question}

Instructions:
- Answer only from supplied context.
- If answer is unavailable say so.
- Use bullet points when useful.
- Keep answer concise.

Answer:
"""

    response = llm.invoke(prompt)

    return response.content

# =====================================================
# Agent
# =====================================================

def agent(question):

    source = None

    # Step 1
    if contains_country(question):

        context = search_country_db(question)

        if can_answer_from_context(
            question,
            context
        ):

            source = "COUNTRY_DB"

            answer = generate_answer(
                question,
                context,
                source
            )

            return answer, source

    # Step 2
    context = web_search(question)

    source = "WEB_SEARCH"

    answer = generate_answer(
        question,
        context,
        source
    )

    return answer, source

# =====================================================
# Chat Loop
# =====================================================

print("=" * 60)
print("🌍 COUNTRY EXPERT AGENT")
print("=" * 60)

print("\nType exit to quit\n")

while True:

    question = input("You: ")

    if question.lower() in [
        "exit",
        "quit",
        "bye"
    ]:
        break

    answer, source = agent(question)

    print("\nSource:", source)
    print("\nAgent:")
    print(answer)
    print("\n" + "-" * 60)

