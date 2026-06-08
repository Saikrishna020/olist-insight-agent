from dotenv import load_dotenv

from .config import DEFAULT_DB_PATH, get_bundled_db_path
from .graph import build_graph

load_dotenv()


COMMERCE_HINTS = (
    "order",
    "orders",
    "customer",
    "customers",
    "product",
    "products",
    "payment",
    "payments",
    "review",
    "reviews",
    "seller",
    "sellers",
    "delivery",
    "shipping",
    "category",
    "categories",
    "revenue",
    "sales",
    "refund",
    "stock",
    "inventory",
    "lead",
    "leads",
)

OFFTOPIC_HINTS = (
    "movie",
    "movies",
    "film",
    "films",
    "director",
    "directors",
    "actor",
    "actors",
    "actress",
    "actresses",
    "cinema",
)


def _is_supported_question(question: str) -> bool:
    lowered = question.lower()
    if any(word in lowered for word in OFFTOPIC_HINTS) and not any(
        word in lowered for word in COMMERCE_HINTS
    ):
        return False
    return True


def invoke_agent(question: str, mode: str = "single") -> dict:
    default_path = get_bundled_db_path() or DEFAULT_DB_PATH
    active_db_path = str(default_path)

    if not _is_supported_question(question):
        return {
            "question": question,
            "mode": mode,
            "db_path": active_db_path,
            "is_valid": False,
            "generated_query": "",
            "raw_results": [],
            "analysis_runs": [],
            "analysis_summary": "",
            "final_answer": (
                "This dataset is the bundled Olist sample, so it cannot answer movie or "
                "director questions. Ask about orders, products, customers, payments, "
                "reviews, sellers, deliveries, or leads instead."
            ),
        }

    graph = build_graph()
    try:
        return graph.invoke(
            {
                "question": question,
                "messages": [],
                "mode": mode,
                "db_path": active_db_path,
            }
        )
    except Exception as exc:
        return {
            "question": question,
            "mode": mode,
            "db_path": active_db_path,
            "is_valid": False,
            "generated_query": "",
            "raw_results": [],
            "analysis_runs": [],
            "analysis_summary": "",
            "final_answer": (
                "The agent could not complete this request because the model endpoint was "
                f"unreachable in the current environment: {exc}. Check the token, network, "
                "and model service before trying again."
            ),
            "execution_error": str(exc),
        }


def run_agent(question: str, mode: str = "single"):
    result = invoke_agent(question, mode)

    print("\n--- RESULT --------------------------------------------------")
    print("Question :", result.get("question"))
    print("Query    :", result.get("generated_query"))
    print("Valid    :", result.get("is_valid"))
    print("Answer   :", result.get("final_answer"))

    if result.get("analysis_summary"):
        print("Analysis :", result.get("analysis_summary"))


if __name__ == "__main__":
    run_agent("What are the top 5 product categories by number of orders?")
