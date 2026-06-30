"""
JD Intelligence Module
Derived from careful reading of the actual Redrob job description.
These are NOT generic - they map directly to what the JD says and means.
"""

# ── MUST-HAVE skills (JD says "absolutely need") ─────────────────────────────
# "Production experience with embeddings-based retrieval systems"
# "Production experience with vector databases or hybrid search"
MUST_HAVE_SKILLS = {
    "embedding", "embeddings", "sentence transformer", "sentence-transformer",
    "sentence transformers", "bge", "e5 model", "faiss", "pinecone",
    "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch",
    "vector database", "vector db", "vector search", "hybrid search",
    "dense retrieval", "bi-encoder", "cross-encoder",
}

# ── STRONG POSITIVE skills (JD "would like", high signal) ────────────────────
STRONG_POSITIVE_SKILLS = {
    "retrieval", "ranking", "recommendation", "recommendation system",
    "learning to rank", "ltr", "xgboost", "lightgbm", "lambdamart",
    "ndcg", "mrr", "map", "information retrieval", "semantic search",
    "rag", "retrieval augmented", "reranking", "re-ranking", "reranker",
    "nlp", "natural language processing", "text embedding",
    "hugging face", "huggingface", "transformers", "bert", "roberta",
    "llm fine-tuning", "fine-tuning", "lora", "qlora", "peft",
    "pytorch", "tensorflow", "scikit-learn", "sklearn",
    "a/b testing", "offline evaluation", "online evaluation",
    "search engine", "bm25", "tfidf", "tf-idf",
}

# ── SOFT POSITIVE (supporting signals) ───────────────────────────────────────
SOFT_POSITIVE_SKILLS = {
    "python", "machine learning", "deep learning", "ml", "ai",
    "data science", "mlops", "ml ops", "mlflow", "wandb", "weights & biases",
    "feature engineering", "model deployment", "inference", "serving",
    "docker", "kubernetes", "spark", "kafka",
    "llm", "gpt", "claude", "gemini",
}

# ── DISQUALIFIER companies (entire career = explicit JD disqualifier) ─────────
# JD: "People who have only worked at consulting firms in their entire career"
CONSULTING_COMPANIES = {
    "tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini",
    "hcl", "tech mahindra", "mphasis", "ltimindtree", "hexaware",
    "birlasoft", "niit technologies", "mastech", "syntel",
    "persistent systems", "kpit", "zensar", "cyient",
    # Also pure IT services (not product)
    "mindtree", "l&t infotech", "happiest minds",
}

# ── DISQUALIFIER titles (clearly wrong domain) ───────────────────────────────
BAD_TITLE_TOKENS = {
    "marketing", "accountant", "hr manager", "civil engineer",
    "mechanical engineer", "graphic designer", "customer support",
    "operations manager", "business analyst", "finance", "legal",
    "content writer", "seo", "sales", "recruitment", "talent acquisition",
}

# ── PRODUCT INDUSTRIES (JD strongly prefers product companies) ────────────────
PRODUCT_INDUSTRIES = {
    "food delivery", "fintech", "e-commerce", "ecommerce", "saas",
    "ai/ml", "healthtech", "edtech", "transportation", "media",
    "telecom", "gaming", "internet", "consumer electronics",
    "retail tech", "proptech", "legaltech", "insurtech",
    "travel tech", "logistics tech",
}

# ── PREFERRED LOCATIONS (JD: Pune/Noida preferred, Hyd/Mumbai/Delhi acceptable)
TIER_1_LOCATIONS = {"noida", "pune", "gurgaon", "gurugram", "delhi", "new delhi"}
TIER_2_LOCATIONS = {"hyderabad", "bangalore", "bengaluru", "mumbai", "chennai"}

# ── IDEAL EXPERIENCE RANGE ────────────────────────────────────────────────────
# JD: "5-9 years... we'll consider outside the band if other signals are strong"
YOE_IDEAL_MIN = 4
YOE_IDEAL_MAX = 10
YOE_STRETCH_MIN = 3
YOE_STRETCH_MAX = 13

# ── NOTICE PERIOD THRESHOLDS ─────────────────────────────────────────────────
# JD: "sub-30-day notice... can buy out up to 30 days... 30+ bar gets higher"
NOTICE_IDEAL = 30
NOTICE_ACCEPTABLE = 60
NOTICE_PENALISED = 90  # above this, heavy penalty

# ── JOB-HOPPING THRESHOLD ────────────────────────────────────────────────────
# JD: "switching companies every 1.5 years = title-chaser"
TENURE_MIN_MONTHS = 18

# ── REFERENCE DATE ────────────────────────────────────────────────────────────
from datetime import date
REFERENCE_DATE = date(2026, 6, 26)
