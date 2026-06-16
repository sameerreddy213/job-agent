"""Rule-based skill extraction and category skill-profiles.

A curated dictionary maps a canonical skill to its surface aliases. Extraction
is exact alias matching with non-alphanumeric boundaries (handles tokens like
c++, c#, node.js, .net, ci/cd). No LLM.
"""
import re

# canonical -> aliases (all lowercase). The canonical form is what we store.
SKILL_ALIASES: dict[str, list[str]] = {
    # languages
    "javascript": ["javascript", "js", "es6", "ecmascript"],
    "typescript": ["typescript", "ts"],
    "python": ["python"],
    "java": ["java"],
    "c++": ["c++", "cpp"],
    "c#": ["c#", "csharp"],
    "golang": ["golang", "go"],
    "ruby": ["ruby"],
    "php": ["php"],
    "kotlin": ["kotlin"],
    "swift": ["swift"],
    "sql": ["sql"],
    # frontend
    "react": ["react", "react.js", "reactjs"],
    "angular": ["angular", "angularjs"],
    "vue": ["vue", "vue.js", "vuejs"],
    "next.js": ["next.js", "nextjs"],
    "redux": ["redux"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "tailwind": ["tailwind", "tailwindcss"],
    "sass": ["sass", "scss"],
    "bootstrap": ["bootstrap"],
    # backend / frameworks
    "node.js": ["node.js", "nodejs", "node js", "node"],
    "express": ["express", "express.js", "expressjs"],
    "spring": ["spring"],
    "spring boot": ["spring boot", "springboot"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    ".net": [".net", "dotnet", "asp.net"],
    "rails": ["rails", "ruby on rails"],
    # databases
    "mongodb": ["mongodb", "mongo"],
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "redis": ["redis"],
    "sqlite": ["sqlite"],
    "oracle": ["oracle db", "oracle database"],
    # devops / cloud / tooling
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure"],
    "gcp": ["gcp", "google cloud"],
    "ci/cd": ["ci/cd", "cicd"],
    "git": ["git"],
    "linux": ["linux"],
    "jenkins": ["jenkins"],
    # data / ai
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "machine learning": ["machine learning", "ml"],
    "nlp": ["nlp", "natural language processing"],
    "data analysis": ["data analysis", "data analytics"],
    # testing
    "jest": ["jest"],
    "pytest": ["pytest"],
    "junit": ["junit"],
    "selenium": ["selenium"],
    # concepts
    "rest": ["rest", "rest api", "restful"],
    "graphql": ["graphql"],
    "microservices": ["microservices", "microservice"],
    "oop": ["oop", "object oriented", "object-oriented"],
    "data structures": ["data structures"],
    "algorithms": ["algorithms"],
    "agile": ["agile", "scrum"],
}

# Precompile boundary-aware patterns per alias.
# Plain alphanumeric aliases use \b (so "typescript." still matches). Aliases
# containing special chars (c++, c#, node.js, .net, ci/cd) use a custom boundary
# that treats +, #, . as part of the token.
_ALNUM = re.compile(r"^[a-z0-9 ]+$")
_BOUNDARY_BEFORE = r"(?<![a-z0-9+#.])"
_BOUNDARY_AFTER = r"(?![a-z0-9+#.])"
_COMPILED: list[tuple[str, re.Pattern]] = []
for _canon, _aliases in SKILL_ALIASES.items():
    for _alias in _aliases:
        if _ALNUM.match(_alias):
            # (?<!\.) stops short aliases like "js"/"ts" matching inside
            # ".js" suffixes (e.g. node.js) while still matching standalone.
            _pat = re.compile(r"(?<!\.)\b" + re.escape(_alias) + r"\b")
        else:
            _pat = re.compile(_BOUNDARY_BEFORE + re.escape(_alias) + _BOUNDARY_AFTER)
        _COMPILED.append((_canon, _pat))


def extract_skills(text: str | None) -> list[str]:
    """Return the sorted set of canonical skills found in the text."""
    if not text:
        return []
    lowered = text.lower()
    found: set[str] = set()
    for canon, pattern in _COMPILED:
        if pattern.search(lowered):
            found.add(canon)
    return sorted(found)


# Category -> signature skills (used for categorization and role hints).
CATEGORY_PROFILES: dict[str, set[str]] = {
    "MERN_Stack": {"mongodb", "express", "react", "node.js", "javascript"},
    "Full_Stack": {"react", "node.js", "sql", "rest", "javascript", "express"},
    "Frontend": {"react", "html", "css", "javascript", "typescript", "redux"},
    "React_Developer": {"react", "redux", "javascript", "typescript", "next.js"},
    "Node_js_Developer": {"node.js", "express", "javascript", "mongodb", "rest"},
    "Backend_Developer": {"node.js", "express", "sql", "rest", "django", "spring"},
    "Java_Developer": {"java", "spring", "spring boot", "sql", "rest"},
    "AI_Data_Platform_Engineer": {
        "python", "machine learning", "pandas", "numpy", "sql", "tensorflow", "pytorch",
    },
    "Software_Engineer": {"data structures", "algorithms", "oop", "git", "sql"},
    "SDE": {"data structures", "algorithms", "oop", "git"},
    "SDE_1": {"data structures", "algorithms", "oop", "git"},
    "Associate_Software_Engineer": {"data structures", "algorithms", "oop", "git"},
    "Graduate_Engineer_Trainee": {"data structures", "algorithms", "oop"},
}
