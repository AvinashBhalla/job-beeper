"""Shared rules for requirement extraction and alert eligibility."""

import re

from bs4 import BeautifulSoup, Tag


ALERT_EXPERIENCE_COLUMNS = """
    CASE WHEN j.experience_min_years IS NOT NULL OR j.experience_max_years IS NOT NULL
        THEN j.experience_min_years ELSE e.experience_min_years END AS experience_min_years,
    CASE WHEN j.experience_min_years IS NOT NULL OR j.experience_max_years IS NOT NULL
        THEN j.experience_max_years ELSE e.experience_max_years END AS experience_max_years
"""


def experience_mismatch(low: float | None, high: float | None, preferences: dict) -> str | None:
    minimum = low if low is not None else high
    maximum = high if high is not None else low
    if minimum is None or maximum is None:
        return None
    candidate = preferences.get("candidate_experience_years")
    floor = preferences.get("min_experience_years")
    cap = float(preferences.get("max_experience_years", 3))
    if candidate is not None and minimum > float(candidate):
        return f"experience minimum {minimum:g} exceeds candidate {float(candidate):g} years"
    if floor is not None and high is not None and high < float(floor):
        return f"job maximum experience {high:g} is below configured minimum {float(floor):g} years"
    if maximum > cap:
        return f"experience range exceeds configured maximum of {cap:g} years"
    return None


def clean_skills(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(
        value.strip() for value in values
        if isinstance(value, str) and 0 < len(value.strip()) <= 60
        and not re.search(r"\[\[|\{\{|\bhiddenSkillsCount\b|^\s*\+\d+\s+more\s*$", value, re.I)
        and any(char.isalpha() for char in value)
    ))


_TECH_SKILL_NAMES = (
    "Apache Spark", "Spring Boot", "React Native", "Machine Learning",
    "Distributed Systems", "System Design", "Experiment Design", "Microservices",
    "TypeScript", "JavaScript", "PostgreSQL", "Kubernetes", "TensorFlow", "PyTorch",
    "Power BI", "SQL", "Python", "Java", "Scala", "Rust", "C++", "C#", ".NET",
    "Node.js", "React", "Kafka", "Docker", "Terraform", "Azure", "AWS", "GCP",
    "Spark", "Hive", "Redshift", "Linux", "GraphQL",
)
_TECH_SKILLS = re.compile(
    r"(?<![\w.])(?:" + "|".join(map(re.escape, _TECH_SKILL_NAMES)) + r")(?![\w+#])",
    re.I,
)


def listed_skills(description: str) -> list[str]:
    """Read short, delimited skill lists supplied as a labeled JD field."""
    match = re.search(
        r"(?im)^\s*(?:#{1,6}\s+|[-•]\s+)?\**(?:key skills|technical skills|required skills|skills|tech stack)"
        r"\**[ \t]*:\**[ \t]*(?P<skills>[^\r\n]{2,200})$",
        description,
    )
    if match:
        skills = clean_skills([part.strip().strip("*") for part in re.split(r"[,;|]", match["skills"])
                               if 0 < len(part.split()) <= 5])
        if skills:
            return skills
    observed = {value.casefold() for value in _TECH_SKILLS.findall(description)}
    return [name for name in _TECH_SKILL_NAMES if name.casefold() in observed][:12]


def description_to_markdown(soup: BeautifulSoup | Tag) -> str:
    """Keep the job's paragraphs, emphasis and lists in the dashboard's safe format."""
    for node in soup.select("script, style, template, iframe, form"):
        node.decompose()
    for node in soup.find_all(["strong", "b", "em", "i"]):
        marker = "**" if node.name in {"strong", "b"} else "*"
        text = node.get_text().strip()
        node.replace_with(f"{marker}{text}{marker}" if text else "")
    for node in soup.find_all("br"):
        node.replace_with("\n")
    for node in soup.find_all(["li", "p", "h1", "h2", "h3", "h4", "h5", "h6"]):
        if node.parent is None:
            continue
        value = node.get_text().strip()
        if node.name == "li":
            prefix = "1. " if node.parent.name == "ol" else "- "
            node.insert_before("\n" + prefix)
            node.insert_after("\n")
        elif node.name == "p":
            node.insert_before("\n\n")
            node.insert_after("\n\n")
        elif value:
            node.insert_before("\n\n### ")
            node.insert_after("\n\n")
    for node in soup.find_all(["ul", "ol", "div"]):
        node.insert_before("\n\n")
        node.insert_after("\n\n")
    lines = (re.sub(r"[^\S\n]+", " ", line).strip() for line in soup.get_text().splitlines())
    markdown = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    # Newlines between successive list items are enough. A blank line would
    # cause the dashboard's Markdown renderer to split the list.
    return re.sub(r"(?m)(^[-] .+|^1\. .+)\n\n(?=- |1\. )", r"\1\n", markdown)
