from dotenv import load_dotenv
from .graph import build_graph

load_dotenv()

def run_agent(question: str):
    graph = build_graph()
    
    result = graph.invoke({
        "question": question,
        "messages": []
    })
    
    print("\n── RESULT ──────────────────────────")
    print("Question :", result["question"])
    print("Query    :", result["generated_query"])
    print("Valid    :", result["is_valid"])
    print("Answer   :", result["final_answer"])

if __name__ == "__main__":
    run_agent("What are the top 5 product categories by number of orders?")