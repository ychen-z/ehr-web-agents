from app.mock_mcp.tools import (
    UnknownSkillError,
    run_mock_tool,
    generate_jd,
    screen_resume,
    generate_interview_questions,
    summarize_interview_feedback,
)


def test_generate_jd_returns_expected_fields():
    result = generate_jd("Senior Backend Engineer with Python and AWS experience")

    assert isinstance(result, dict)
    assert "job_title" in result
    assert "responsibilities" in result
    assert "requirements" in result
    assert "interview_focus" in result
    assert "selling_points" in result

    assert isinstance(result["job_title"], str) and len(result["job_title"]) > 0
    assert isinstance(result["responsibilities"], list) and len(result["responsibilities"]) > 0
    assert isinstance(result["requirements"], list) and len(result["requirements"]) > 0
    assert isinstance(result["interview_focus"], list) and len(result["interview_focus"]) > 0
    assert isinstance(result["selling_points"], list) and len(result["selling_points"]) > 0


def test_generate_jd_derives_title_from_input():
    result = generate_jd("We need a Senior Frontend Developer with React skills")
    assert "Frontend" in result["job_title"] or "Senior" in result["job_title"]


def test_generate_jd_derives_keywords_from_input():
    result = generate_jd("Need a DevOps engineer with Kubernetes and Docker for cloud infrastructure")
    tech_combined = " ".join(result["requirements"] + result["responsibilities"]).lower()
    assert "kubernetes" in tech_combined or "docker" in tech_combined or "cloud" in tech_combined


def test_generate_jd_is_deterministic():
    input_text = "Senior Backend Engineer with Python and AWS experience"
    result1 = generate_jd(input_text)
    result2 = generate_jd(input_text)
    assert result1 == result2


def test_screen_resume_returns_expected_fields():
    result = screen_resume("5 years of Python experience, led a team of 3 engineers, built scalable APIs")

    assert isinstance(result, dict)
    assert "screening_dimensions" in result
    assert "strengths" in result
    assert "risks" in result
    assert "recommended_next_step" in result

    assert isinstance(result["screening_dimensions"], list) and len(result["screening_dimensions"]) > 0
    assert isinstance(result["strengths"], list) and len(result["strengths"]) > 0
    assert isinstance(result["risks"], list) and len(result["risks"]) > 0
    assert isinstance(result["recommended_next_step"], str) and len(result["recommended_next_step"]) > 0


def test_screen_resume_extracts_experience_years():
    result = screen_resume("I have 8 years of experience in DevOps and 5 years managing cloud infrastructure")
    dim_text = " ".join(str(d) for d in result["screening_dimensions"]).lower()
    assert "8" in dim_text or "devops" in dim_text or "cloud" in dim_text


def test_generate_interview_questions_returns_expected_fields():
    result = generate_interview_questions("Senior Product Manager with experience in B2B SaaS and data-driven decision making")

    assert isinstance(result, dict)
    assert "question_groups" in result
    assert isinstance(result["question_groups"], list) and len(result["question_groups"]) > 0

    for group in result["question_groups"]:
        assert "competency" in group
        assert "questions" in group
        assert isinstance(group["competency"], str) and len(group["competency"]) > 0
        assert isinstance(group["questions"], list) and len(group["questions"]) > 0
        for q in group["questions"]:
            assert isinstance(q, str) and len(q) > 0


def test_generate_interview_questions_derives_competency_from_input():
    result = generate_interview_questions("Frontend engineer with deep React and TypeScript knowledge")
    competencies = [g["competency"].lower() for g in result["question_groups"]]
    match = any("react" in c or "frontend" in c or "technical" in c for c in competencies)
    assert match


def test_summarize_interview_feedback_returns_expected_fields():
    result = summarize_interview_feedback(
        "Candidate demonstrated strong system design skills but struggled with basic SQL. Good cultural fit."
    )

    assert isinstance(result, dict)
    assert "feedback_summary" in result
    assert "evidence" in result
    assert "concerns" in result
    assert "decision_recommendation" in result

    assert isinstance(result["feedback_summary"], str) and len(result["feedback_summary"]) > 0
    assert isinstance(result["evidence"], list) and len(result["evidence"]) > 0
    assert isinstance(result["concerns"], list)
    assert isinstance(result["decision_recommendation"], str) and len(result["decision_recommendation"]) > 0


def test_summarize_interview_feedback_detects_concerns_from_negative_input():
    result = summarize_interview_feedback(
        "Candidate was late, unprepared, and could not answer basic architecture questions."
    )
    assert len(result["concerns"]) > 0
    concerns_text = " ".join(result["concerns"]).lower()
    assert any(word in concerns_text for word in ["late", "unprepared", "could not", "basic"])


def test_summarize_interview_feedback_insufficient_info_for_no_evidence():
    result = summarize_interview_feedback("The interview was completed today.")
    assert "Insufficient information" in result["decision_recommendation"]


def test_run_mock_tool_dispatches_generate_jd():
    result = run_mock_tool("generate_jd", "Senior Python Developer")
    assert "job_title" in result
    assert "responsibilities" in result


def test_run_mock_tool_dispatches_screen_resume():
    result = run_mock_tool("screen_resume", "5 years React experience")
    assert "screening_dimensions" in result
    assert "strengths" in result


def test_run_mock_tool_dispatches_generate_interview_questions():
    result = run_mock_tool("generate_interview_questions", "Product Manager")
    assert "question_groups" in result


def test_run_mock_tool_dispatches_summarize_interview_feedback():
    result = run_mock_tool("summarize_interview_feedback", "Good technical skills.")
    assert "feedback_summary" in result


def test_run_mock_tool_raises_for_unknown_skill():
    try:
        run_mock_tool("nonexistent_skill", "some input")
        assert False, "Expected UnknownSkillError but no exception was raised"
    except UnknownSkillError as e:
        assert e.skill_id == "nonexistent_skill"
        assert "Unknown skill" in str(e)
