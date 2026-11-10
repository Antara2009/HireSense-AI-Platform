import re

SKILL_ALIASES = {
    "machine learning": ["ml", "machine-learning"],
    "javascript": ["js"],
    "scikit-learn": ["sklearn"],
    "data analysis": ["data analytics", "data analyzing"],
    "communication": ["communication skills"],
    "problem solving": ["problem-solving"],
    "rest api": ["restful api", "apis"],
    "power bi": ["powerbi"],
    "artificial intelligence": ["ai"],
    "c++": ["cpp"],
    "c#": ["c sharp"],
    "node.js": ["nodejs"],
}

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#.\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def split_skills(required_skills):
    return [s.strip().lower() for s in re.split(r"[,;\n|]", required_skills) if s.strip()]

def contains_skill(text, skill):
    text_n = f" {normalize(text)} "
    candidates = [skill] + SKILL_ALIASES.get(skill, [])
    for alias in candidates:
        alias_n = normalize(alias)
        if alias_n and re.search(r"(?<![a-z0-9])" + re.escape(alias_n) + r"(?![a-z0-9])", text_n):
            return True
    return False

def analyze_resume(resume_text, required_skills, job_description=""):
    required = split_skills(required_skills)
    if not required:
        required = ["communication", "problem solving"]
    matched, missing = [], []
    for skill in required:
        (matched if contains_skill(resume_text, skill) else missing).append(skill)
    # Transparent skill coverage score; the job description provides context, not hidden scoring.
    score = round((len(matched) / len(required)) * 100) if required else 0
    words = len(re.findall(r"\b[a-zA-Z]+\b", resume_text))
    return {
        "score": max(0, min(100, score)),
        "matched_skills": matched,
        "missing_skills": missing,
        "total_skills": len(required),
        "resume_words": words,
        "summary": "Your resume covers most of the listed requirements." if score >= 70 else
                   "Your resume has some matching skills. Review the missing skills below." if score >= 40 else
                   "There is an opportunity to strengthen your profile for this role."
    }
