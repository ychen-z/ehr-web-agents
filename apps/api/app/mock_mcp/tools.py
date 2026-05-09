import re

from app.mock_mcp.schemas import (
    InterviewFeedbackResult,
    InterviewQuestionsResult,
    JDResult,
    ScreeningDimension,
    ScreenResumeResult,
)


class UnknownSkillError(ValueError):
    def __init__(self, skill_id: str):
        super().__init__(f"Unknown skill: {skill_id}")
        self.skill_id = skill_id


def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z+#.0-9]{2,}", text.lower())
    stop = {"the", "and", "for", "with", "that", "this", "have", "from", "their", "they", "are", "was", "were", "been", "need", "experience", "skills", "years", "role",
            "candidate", "should", "about", "will", "team", "work", "good", "strong", "able", "also", "more", "some", "very", "must", "using", "based", "such", "demonstrated"}
    return list(dict.fromkeys(w for w in words if w not in stop))


def generate_jd(input_text: str) -> dict:
    keywords = _extract_keywords(input_text)
    text_lower = input_text.lower()

    title_keywords = [w for w in keywords if w not in ("senior", "junior", "lead", "principal", "staff", "intern")]
    if any(w in text_lower for w in ("senior", "lead", "principal", "staff")):
        level = "Senior"
    elif "junior" in text_lower or "intern" in text_lower:
        level = "Junior"
    else:
        level = ""

    role_hints = [w for w in title_keywords if w in (
        "developer", "engineer", "manager", "designer", "analyst", "architect",
        "devops", "scientist", "frontend", "backend", "fullstack", "full-stack",
        "product", "data", "qa", "security", "cloud", "mobile", "ios", "android",
        "platform", "site", "reliability", "sre", "support", "administrator",
        "consultant", "director", "vp", "officer", "specialist", "coordinator",
    )]
    role = " ".join(role_hints[:2]) if role_hints else "Professional"
    job_title = f"{level} {role.title()}".strip()

    tech_keywords = [w for w in title_keywords if w in (
        "python", "java", "javascript", "typescript", "react", "angular", "vue",
        "node", "golang", "go", "rust", "c++", "c#", "ruby", "php", "scala",
        "kotlin", "swift", "aws", "azure", "gcp", "kubernetes", "docker",
        "terraform", "redis", "kafka", "postgresql", "postgres", "mysql",
        "mongodb", "elasticsearch", "graphql", "rest", "grpc", "linux",
        "ci/cd", "jenkins", "git", "snowflake", "airflow", "spark", "hadoop",
        "html", "css", "sql", "nosql", "api", "apis", "ml", "ai",
    )]

    responsibilities = [
        f"Design and implement {kw}-based solutions" for kw in tech_keywords[:2]
    ] or [
        "Design, develop, and maintain high-quality software solutions",
        "Collaborate with cross-functional teams to deliver business value",
    ]
    responsibilities += [
        "Participate in code reviews and mentor junior team members",
        "Drive technical decisions and contribute to architectural planning",
        "Write and maintain technical documentation",
    ]

    requirements = []
    if tech_keywords:
        requirements.append(f"Proven expertise in {', '.join(tech_keywords[:3])}")
    else:
        requirements.append("Proven expertise in relevant technologies and frameworks")
    requirements += [
        "Strong problem-solving and analytical skills",
        "Excellent communication and collaboration abilities",
        "Experience working in agile development environments",
        "Bachelor's degree in Computer Science or related field (or equivalent experience)",
    ]

    tech_areas = tech_keywords[:3] if tech_keywords else ["core technologies", "system design", "problem solving"]
    interview_focus = [
        f"Deep-dive into {area} knowledge and practical experience" for area in tech_areas
    ]

    selling_points = [
        f"Work with cutting-edge {', '.join(tech_keywords[:2])} stack" if len(tech_keywords) >= 2 else "Work with modern technology stack",
        "Competitive compensation and equity package",
        "Flexible remote/hybrid work environment",
        "Professional development budget and learning opportunities",
        "Collaborative and inclusive engineering culture",
    ]

    result = JDResult(
        job_title=job_title,
        responsibilities=responsibilities,
        requirements=requirements,
        interview_focus=interview_focus,
        selling_points=selling_points,
    )
    return result.model_dump()


def screen_resume(input_text: str) -> dict:
    keywords = _extract_keywords(input_text)
    text_lower = input_text.lower()

    years_match = re.search(r"(\d+)\s*(?:\+)?\s*years?", text_lower)
    years = int(years_match.group(1)) if years_match else None

    tech_keywords = [w for w in keywords if w in (
        "python", "java", "javascript", "typescript", "react", "angular", "vue",
        "node", "golang", "go", "rust", "c++", "c#", "aws", "azure", "gcp",
        "kubernetes", "docker", "terraform", "redis", "kafka", "sql", "nosql",
        "mongodb", "postgresql", "mysql", "graphql", "api", "linux", "git",
    )]
    soft_keywords = [w for w in keywords if w in (
        "leadership", "communication", "team", "mentoring", "collaboration",
        "agile", "scrum", "management", "presentation", "stakeholder",
    )]

    if years and years >= 7:
        exp_score = "Strong"
    elif years and years >= 3:
        exp_score = "Adequate"
    elif years:
        exp_score = "Limited"
    else:
        exp_score = "Moderate"

    dimensions: list[ScreeningDimension] = []
    if tech_keywords:
        dimensions.append(ScreeningDimension(
            dimension="Technical Skills",
            score="Strong" if len(tech_keywords) >= 3 else "Adequate",
            notes=f"Demonstrates proficiency in {', '.join(tech_keywords[:3])}",
        ))
    else:
        dimensions.append(ScreeningDimension(
            dimension="Technical Skills",
            score="Moderate",
            notes="Limited technology-specific evidence in resume",
        ))

    dimensions.append(ScreeningDimension(
        dimension="Experience Level",
        score=exp_score,
        notes=f"{years}+ years of professional experience" if years else "Experience level needs further assessment",
    ))

    dimensions.append(ScreeningDimension(
        dimension="Communication",
        score="Strong" if soft_keywords else "Adequate",
        notes="Evidence of collaboration and stakeholder engagement" if soft_keywords else "Communication skills need further evaluation",
    ))

    strengths: list[str] = []
    if tech_keywords:
        strengths.append(f"Strong technical background in {', '.join(tech_keywords[:2])}")
    if years and years >= 5:
        strengths.append(f"Significant industry experience ({years}+ years)")
    if soft_keywords:
        strengths.append(f"Demonstrated {soft_keywords[0]} and interpersonal skills")
    if not strengths:
        strengths.append("Relevant background aligned with role requirements")

    risks: list[str] = []
    if years is None or years < 2:
        risks.append("Limited professional experience may require additional ramp-up time")
    if len(tech_keywords) < 3:
        risks.append("Technical breadth may not fully cover role requirements")
    if not soft_keywords:
        risks.append("Soft skills and team collaboration experience not clearly demonstrated")
    if not risks:
        risks.append("No significant risks identified")

    if any(w in text_lower for w in ("reject", "not qualified", "poor fit", "decline")):
        next_step = "Decline — does not meet minimum requirements"
    elif risks and len(risks) >= 2:
        next_step = "Proceed to phone screen with targeted questions on identified risk areas"
    else:
        next_step = "Recommend for hiring manager interview"

    result = ScreenResumeResult(
        screening_dimensions=dimensions,
        strengths=strengths,
        risks=risks,
        recommended_next_step=next_step,
    )
    return result.model_dump()


def generate_interview_questions(input_text: str) -> dict:
    keywords = _extract_keywords(input_text)
    text_lower = input_text.lower()

    tech_keywords = [w for w in keywords if w in (
        "python", "java", "javascript", "typescript", "react", "angular", "vue",
        "node", "golang", "go", "rust", "aws", "azure", "kubernetes", "docker",
        "sql", "nosql", "api", "apis", "graphql", "rest", "microservices",
        "machine", "learning", "ml", "ai", "data", "cloud", "devops", "security",
        "testing", "agile", "scrum", "frontend", "backend", "fullstack",
        "mobile", "ios", "android", "database", "architecture", "performance",
    )]
    domain_keywords = [w for w in keywords if w in (
        "product", "management", "saas", "b2b", "b2c", "enterprise",
        "fintech", "healthcare", "e-commerce", "ecommerce", "marketing",
        "sales", "operations", "finance", "hr", "analytics",
    )]
    leadership_keywords = [w for w in keywords if w in (
        "lead", "senior", "manager", "director", "vp", "head", "principal",
        "staff", "leadership", "team", "mentoring", "management",
    )]

    groups: list = []

    if tech_keywords:
        groups.append({
            "competency": "Technical Depth",
            "questions": [
                f"Can you walk us through a complex project where you used {tech_keywords[0] if tech_keywords else 'your core technology'} to solve a difficult problem?",
                f"How do you evaluate trade-offs when choosing between {' and '.join(tech_keywords[:2]) if len(tech_keywords) >= 2 else 'different technologies'} for a new project?",
                "Describe a production incident you debugged and resolved. What was your troubleshooting approach?",
                "How do you stay current with evolving technology trends in your domain?",
            ],
        })

    if domain_keywords or "product" in text_lower or "manager" in text_lower:
        groups.append({
            "competency": "Domain & Product Thinking",
            "questions": [
                "How do you prioritize features when stakeholders have conflicting requests?",
                "Describe a product decision you made that was initially unpopular but proved correct.",
                "How do you measure the success of a product or feature launch?",
                "Walk us through how you would gather requirements for a complex cross-functional initiative.",
            ],
        })

    if leadership_keywords or any(w in text_lower for w in ("senior", "lead", "manager", "director")):
        groups.append({
            "competency": "Leadership & Collaboration",
            "questions": [
                "Tell us about a time you had to influence a decision without formal authority.",
                "How do you handle disagreement within your team during technical discussions?",
                "Describe your approach to mentoring and developing junior team members.",
                "How have you handled a situation where a project was at risk of missing its deadline?",
            ],
        })

    groups.append({
        "competency": "Problem Solving & Adaptability",
        "questions": [
            "Describe the most challenging technical problem you have solved.",
            "Tell us about a time you had to learn a new technology or domain quickly to deliver results.",
            "How do you approach debugging when you have limited information?",
            "Walk us through how you would design a system to handle a significant increase in scale.",
        ],
    })

    groups.append({
        "competency": "Culture & Values",
        "questions": [
            "What type of work environment helps you do your best work?",
            "Describe a situation where you received difficult feedback. How did you respond?",
            "What motivates you beyond compensation and title?",
            "How do you balance speed of delivery with code quality and long-term maintainability?",
        ],
    })

    result = InterviewQuestionsResult(question_groups=groups)
    return result.model_dump()


def summarize_interview_feedback(input_text: str) -> dict:
    text_lower = input_text.lower()

    positive_signals = re.findall(
        r"(strong|excellent|impressive|outstanding|great|solid|clear|deep|good|exceptional)\s+(\w+(?:\s+\w+){0,3})",
        text_lower,
    )
    negative_signals = re.findall(
        r"(struggled|weak|lacked|could\s+not|unable|poor|failed|unprepared|late|missing|insufficient|limited|vague|unclear|nervous)\s+(\w+(?:\s+\w+){0,3})",
        text_lower,
    )

    has_signals = bool(positive_signals or negative_signals)

    evidence: list[str] = []
    for adj, area in positive_signals:
        evidence.append(f"Positive: demonstrated {adj} {area.strip()}")
    for adj, area in negative_signals:
        evidence.append(f"Concern: {adj} {area.strip()}")
    if not evidence:
        evidence = [
            "Technical assessment completed across core competencies",
            "Behavioral and cultural fit evaluation conducted",
        ]

    strengths = [e for e in evidence if e.startswith("Positive")]
    weaknesses = [e for e in evidence if e.startswith("Concern")]

    if strengths:
        summary = f"Candidate showed {len(strengths)} notable strength(s) including {strengths[0].split(': ', 1)[1] if strengths[0].startswith('Positive:') else strengths[0]}. "
    else:
        summary = "Candidate completed the interview process. "

    if weaknesses:
        summary += f"Areas requiring attention include {weaknesses[0].split(': ', 1)[1] if weaknesses[0].startswith('Concern:') else weaknesses[0]}. "
    else:
        summary += "No major concerns were identified during the interview. "

    concerns: list[str] = []
    for adj, area in negative_signals:
        concerns.append(f"{adj.title()} {area.strip()}")
    if not concerns and any(w in text_lower for w in ("reject", "decline", "poor", "not recommend", "fail")):
        concerns.append("Overall assessment indicates candidate may not be a good fit")
    if not concerns:
        concerns = []

    positive_count = len([e for e in evidence if e.startswith("Positive")])
    negative_count = len([e for e in evidence if e.startswith("Concern")])

    if not has_signals:
        decision = "Insufficient information — collect additional structured feedback before making a decision"
    elif any(w in text_lower for w in ("reject", "decline", "not recommend", "no hire", "fail")):
        decision = "Do not advance — significant concerns outweigh strengths"
    elif negative_count > positive_count:
        decision = "Lean no — proceed with caution; address concerns with additional evaluation"
    elif positive_count > negative_count + 1:
        decision = "Strong hire — recommend advancing to offer stage"
    else:
        decision = "Hire — recommend advancing to next round with targeted follow-up on identified areas"

    result = InterviewFeedbackResult(
        feedback_summary=summary.strip(),
        evidence=evidence,
        concerns=concerns,
        decision_recommendation=decision,
    )
    return result.model_dump()


_TOOL_REGISTRY = {
    "generate_jd": generate_jd,
    "screen_resume": screen_resume,
    "generate_interview_questions": generate_interview_questions,
    "summarize_interview_feedback": summarize_interview_feedback,
}


def run_mock_tool(skill_id: str, input_text: str) -> dict:
    if skill_id not in _TOOL_REGISTRY:
        raise UnknownSkillError(skill_id)
    return _TOOL_REGISTRY[skill_id](input_text)
