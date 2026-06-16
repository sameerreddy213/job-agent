"""Phase 5A — Resume Intelligence Layer validation.

Unit tests run without a server. API tests use the running-stack fixtures.
"""
from app.intelligence.categorize import categorize_resume
from app.intelligence.matching import ResumeProfile, recommend_resume
from app.intelligence.skills import extract_skills


# --------------------------- unit (no server) --------------------------- #
def test_extract_skills_basic():
    skills = extract_skills("React, Node.js, Express, MongoDB and TypeScript. REST APIs.")
    assert {"react", "node.js", "express", "mongodb", "typescript", "rest"} <= set(skills)


def test_extract_skills_no_false_js_in_nodejs():
    # 'js' must not be matched inside 'node.js'
    assert "javascript" not in extract_skills("node.js")
    assert "javascript" in extract_skills("strong JS fundamentals")


def test_extract_skills_special_tokens():
    skills = set(extract_skills("C++, C#, Go, .NET, CI/CD"))
    assert {"c++", "c#", "golang", ".net", "ci/cd"} <= skills


def test_categorize_mern():
    cat, conf = categorize_resume("React, Redux, Node.js, Express, MongoDB, JavaScript")
    assert cat == "MERN_Stack"
    assert conf > 0


def test_recommend_selects_best_resume():
    resumes = [
        ResumeProfile("MERN_Stack", {"javascript", "react", "node.js", "express", "mongodb"}),
        ResumeProfile("Java_Developer", {"java", "spring", "sql", "rest"}),
    ]
    rec = recommend_resume("MERN Stack Developer", "React, Node.js, Express, MongoDB", resumes)
    assert rec.selected_category == "MERN_Stack"
    assert rec.match_score >= 75
    assert "react" in rec.matched_skills
    assert rec.confidence > 0


def test_recommend_no_resumes():
    rec = recommend_resume("Java Developer", "Spring, SQL", [])
    assert rec.match_score == 0
    assert rec.confidence == 0


# --------------------------- API (running stack) --------------------------- #
def test_rematch_and_override(client, auth):
    jobs = client.get("/queue", headers=auth, params={"limit": 1}).json()
    if not jobs:
        return  # nothing scored yet; skip gracefully
    job_id = jobs[0]["id"]

    rematch = client.post(f"/jobs/{job_id}/rematch", headers=auth)
    assert rematch.status_code == 200
    assert "score" in rematch.json()

    override = client.post(f"/jobs/{job_id}/resume", headers=auth, json={"category": "SDE"})
    assert override.status_code == 200
    score = override.json()["score"]
    assert score["matched_resume_category"] == "SDE"
    assert score["resume_override"] is True


def test_override_rejects_unknown_category(client, auth):
    jobs = client.get("/queue", headers=auth, params={"limit": 1}).json()
    if not jobs:
        return
    bad = client.post(f"/jobs/{jobs[0]['id']}/resume", headers=auth, json={"category": "NOPE"})
    assert bad.status_code == 400
