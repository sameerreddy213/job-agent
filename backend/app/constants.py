"""Shared rule constants for filtering and scoring (Phase 2 rule engine).

These deterministic rules stand in for an LLM in the MVP. They live behind the
scoring/filter modules so an AI provider can later replace the logic without
changing the pipeline or API.
"""
import re

# Target locations (primary cities + remote/hybrid in India)
TARGET_CITIES = {
    "hyderabad", "bangalore", "bengaluru", "pune", "chennai", "noida", "gurugram",
    "gurgaon",
}
REMOTE_INDIA_HINTS = {"remote", "india", "hybrid", "anywhere in india"}

# Role acceptance / rejection (title-level)
ACCEPT_ROLE_KEYWORDS = [
    "software engineer", "sde", "sde-1", "sde 1", "sde i",
    "associate software engineer", "graduate engineer trainee",
    "frontend developer", "front end developer", "backend developer",
    "back end developer", "full stack developer", "fullstack developer",
    "mern", "react developer", "node.js developer", "nodejs developer",
    "java developer", "ai engineer",
]
REJECT_TITLE_KEYWORDS = [
    "senior", "sr.", "lead", "principal", "architect", "manager",
    "staff", "head of", "director", "vp ",
]

# Fresher / experience signals
FRESHER_KEYWORDS = [
    "fresher", "freshers", "entry level", "entry-level", "graduate",
    "0-1 year", "0 to 1 year", "0-2 year", "no experience", "trainee",
]
# Patterns like "2+ years", "3-5 years", "minimum 2 years", "2 yrs"
EXPERIENCE_REQ_REGEX = re.compile(
    r"(\d+)\s*\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)", re.IGNORECASE
)
# Max acceptable required years for a fresher role
MAX_FRESHER_YEARS = 1

# Default candidate skills used when no resume skills are detected yet.
# (Skill detection from resumes is a later AI phase.)
DEFAULT_SKILLS = [
    "javascript", "typescript", "react", "node", "express", "mongodb",
    "html", "css", "java", "python", "sql", "rest", "git", "docker",
    "spring", "redux", "next.js", "postgresql",
]

# Map title keywords -> resume category (best-fit resume selection)
ROLE_TO_CATEGORY = [
    ("mern", "MERN_Stack"),
    ("full stack", "Full_Stack"),
    ("fullstack", "Full_Stack"),
    ("react", "React_Developer"),
    ("node", "Node_js_Developer"),
    ("frontend", "Frontend"),
    ("front end", "Frontend"),
    ("backend", "Backend_Developer"),
    ("back end", "Backend_Developer"),
    ("java", "Java_Developer"),
    ("ai engineer", "AI_Data_Platform_Engineer"),
    ("associate software engineer", "Associate_Software_Engineer"),
    ("graduate engineer trainee", "Graduate_Engineer_Trainee"),
    ("sde-1", "SDE_1"),
    ("sde 1", "SDE_1"),
    ("sde", "SDE"),
    ("software engineer", "Software_Engineer"),
]

# Scoring weights (sum = 100)
WEIGHT_FRESHERS = 40
WEIGHT_SKILLS = 30
WEIGHT_LOCATION = 10
WEIGHT_ROLE = 20

# Classification thresholds
THRESHOLD_AUTO_APPROVE = 90
THRESHOLD_REVIEW = 70

# The 13 fixed resume role categories.
ALLOWED_CATEGORIES = {
    "SDE", "SDE_1", "Software_Engineer", "Associate_Software_Engineer",
    "Graduate_Engineer_Trainee", "Frontend", "Backend_Developer",
    "Full_Stack", "MERN_Stack", "React_Developer", "Node_js_Developer",
    "Java_Developer", "AI_Data_Platform_Engineer",
}

# Classifications / statuses
CLASS_AUTO = "AUTO_APPROVE_ELIGIBLE"
CLASS_REVIEW = "REVIEW_QUEUE"
CLASS_REJECT = "REJECT"
STATUS_REJECTED_FILTER = "REJECTED_FILTER"
