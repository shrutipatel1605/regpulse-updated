"""Constants for RBI metadata extraction.

RBI department abbreviations, team taxonomy keywords, and date format patterns.
Standalone scraper module — NEVER imports from backend/app/.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# RBI Department abbreviations → full names
# Source: RBI department reference numbers in circulars (e.g. DOR.MRG.REC.No.xxx)
# ---------------------------------------------------------------------------

RBI_DEPARTMENTS: dict[str, str] = {
    # Department of Regulation
    "DOR": "Department of Regulation",
    "DBOD": "Department of Banking Operations and Development",
    "DBR": "Department of Banking Regulation",
    # Department of Supervision
    "DOS": "Department of Supervision",
    "DBS": "Department of Banking Supervision",
    # Financial Markets
    "FMRD": "Financial Markets Regulation Department",
    "FMD": "Financial Markets Department",
    "IDMD": "Internal Debt Management Department",
    # Payment Systems
    "DPSS": "Department of Payment and Settlement Systems",
    "PSS": "Payment and Settlement Systems",
    # Currency / Cash
    "DCM": "Department of Currency Management",
    # External Investment / Trade
    "FED": "Foreign Exchange Department",
    "FEAD": "Foreign Exchange Adjudication Department",
    # Consumer Protection
    "CEPD": "Consumer Education and Protection Department",
    # Risk / NPAs
    "DNBS": "Department of Non-Banking Supervision",
    "DNBR": "Department of Non-Banking Regulation",
    # IT / Cyber
    "DoIT": "Department of Information Technology",
    "DSIM": "Department of Statistics and Information Management",
    # Financial Inclusion
    "FIDD": "Financial Inclusion and Development Department",
    "RPCD": "Rural Planning and Credit Department",
    # Monetary Policy
    "MPD": "Monetary Policy Department",
    # Government Accounts
    "DGBA": "Department of Government and Bank Accounts",
    # Cooperative Banks
    "DCBR": "Department of Co-operative Bank Regulation",
    "UBD": "Urban Banks Department",
    # Financial Stability
    "FSDD": "Financial Stability Development Department",
    "FSU": "Financial Stability Unit",
    # Human Resources
    "HRMD": "Human Resources Management Department",
    # Legal
    "LAD": "Legal Advisory Department",
    # Communication
    "DoC": "Department of Communication",
    # Customer Service
    "CSITE": "Customer Service and Information Technology Department",
    # Credit Information
    "CICRA": "Credit Information Companies Regulation Authority",
    # Economic Research
    "DEPR": "Department of Economic and Policy Research",
    # Secretary's Department
    "SecDept": "Secretary's Department",
    # Corporate Strategy
    "CSBD": "Corporate Strategy and Budget Department",
}

# ---------------------------------------------------------------------------
# Team taxonomy — keyword-based classification
# Each team maps to a set of keywords found in RBI circular text
# ---------------------------------------------------------------------------

TEAM_KEYWORDS: dict[str, list[str]] = {
    "Compliance": [
        "compliance",
        "kyc",
        "know your customer",
        "aml",
        "anti-money laundering",
        "cft",
        "combating the financing of terrorism",
        "regulatory",
        "regulation",
        "master direction",
        "guidelines",
        "circular",
        "reporting",
        "disclosure",
        "filing",
        "statutory",
        "prudential norms",
        "fit and proper",
        "fit & proper",
        "returns",
        "supervisory",
    ],
    "Risk Management": [
        "risk",
        "risk management",
        "npa",
        "non-performing",
        "provisioning",
        "capital adequacy",
        "crar",
        "basel",
        "stress test",
        "icaap",
        "credit risk",
        "market risk",
        "operational risk",
        "liquidity risk",
        "exposure",
        "concentration risk",
        "risk weight",
        "slr",
        "crr",
        "large exposure",
        "irrbb",
    ],
    "Operations": [
        "operations",
        "branch",
        "account opening",
        "deposit",
        "lending",
        "loan",
        "interest rate",
        "base rate",
        "mclr",
        "repo rate",
        "rtgs",
        "neft",
        "upi",
        "payment",
        "settlement",
        "cheque",
        "demand draft",
        "clearing",
        "remittance",
        "cash reserve",
        "priority sector",
        "psl",
        "gold loan",
        "housing loan",
        "education loan",
        "vehicle loan",
        "msme",
        "nbfc",
    ],
    "Legal": [
        "legal",
        "act",
        "statute",
        "tribunal",
        "adjudication",
        "penalty",
        "enforcement",
        "prosecution",
        "sarfaesi",
        "drt",
        "nclt",
        "ombudsman",
        "arbitration",
        "dispute",
        "banking regulation act",
        "rbi act",
        "fema",
        "pmla",
        "insolvency",
        "bankruptcy",
        "wilful defaulter",
        "fraud",
    ],
    "IT Security": [
        "cyber",
        "it security",
        "information security",
        "data protection",
        "digital",
        "technology",
        "outsourcing",
        "cloud",
        "data privacy",
        "phishing",
        "ransomware",
        "incident reporting",
        "it governance",
        "business continuity",
        "disaster recovery",
        "bcp",
        "drp",
        "ciso",
        "soc",
        "penetration test",
        "vulnerability",
        "api security",
        "two-factor",
        "2fa",
        "otp",
    ],
    "Finance": [
        "finance",
        "capital",
        "profit",
        "dividend",
        "balance sheet",
        "audit",
        "accounting",
        "ind as",
        "ifrs",
        "gaap",
        "tax",
        "gst",
        "tds",
        "valuation",
        "investment",
        "treasury",
        "government securities",
        "g-sec",
        "t-bill",
        "bond",
        "forex",
        "foreign exchange",
        "ecb",
        "fdi",
        "fpi",
    ],
}

# ---------------------------------------------------------------------------
# Supersession keywords — phrases indicating this circular replaces another
# ---------------------------------------------------------------------------

SUPERSESSION_PATTERNS: list[str] = [
    r"(?:supersed|replac|rescind|repeal|cancel|withdraw|revok)(?:es?|ed|ing)",
    r"(?:in\s+)?(?:supersession|replacement|lieu)\s+of",
    r"(?:stands?\s+)?(?:superseded|replaced|rescinded|repealed|cancelled|withdrawn|revoked)",
    r"ceases?\s+to\s+(?:be\s+)?(?:effective|operative|applicable|valid)",
    r"no\s+longer\s+(?:effective|operative|applicable|valid)",
]

# ---------------------------------------------------------------------------
# Action deadline trigger phrases
# ---------------------------------------------------------------------------

ACTION_DEADLINE_TRIGGERS: list[str] = [
    r"last\s+date",
    r"on\s+or\s+before",
    r"submit\s+by",
    r"implement\s+by",
    r"comply\s+(?:by|before|within)",
    r"(?:effective|applicable|operative)\s+from",
    r"not\s+later\s+than",
    r"shall\s+(?:be\s+)?(?:completed?|implemented|submitted|filed|furnished)\s+(?:by|before|within)",
    r"within\s+a\s+period\s+of",
    r"time\s*(?:limit|frame|line)",
    r"deadline",
]
