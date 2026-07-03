BUILTIN_SKILLS = [
    {
        "skill_id": "generate_jd",
        "name": "JD Generation",
        "description": "Generate professional job descriptions from role requirements and qualifications.",
        "category": "recruitment",
        "prompt_template": None,
        "mock_tool_name": "generate_jd",
        "checkpoints": None,
    },
    {
        "skill_id": "screen_resume",
        "name": "Resume Screening",
        "description": "Screen and evaluate candidate resumes against job requirements.",
        "category": "recruitment",
        "prompt_template": None,
        "mock_tool_name": "screen_resume",
        "checkpoints": [
            {
                "after_tool": "screen_resume",
                "prompt": "简历筛选完成，请确认下一步操作：",
                "options": [
                    {"label": "推进到面试", "value": "proceed_interview"},
                    {"label": "拒绝候选人", "value": "reject"},
                    {"label": "需要更多信息", "value": "need_more_info"},
                ],
            }
        ],
    },
    {
        "skill_id": "generate_interview_questions",
        "name": "Interview Questions",
        "description": "Generate tailored interview questions based on job requirements and candidate profile.",
        "category": "recruitment",
        "prompt_template": None,
        "mock_tool_name": "generate_interview_questions",
        "checkpoints": None,
    },
    {
        "skill_id": "summarize_interview_feedback",
        "name": "Interview Feedback Summary",
        "description": "Summarize and structure interview feedback from multiple interviewers.",
        "category": "recruitment",
        "prompt_template": None,
        "mock_tool_name": "summarize_interview_feedback",
        "checkpoints": [
            {
                "after_tool": "summarize_interview_feedback",
                "prompt": "面试反馈已汇总，请确认录用决策：",
                "options": [
                    {"label": "发放 Offer", "value": "send_offer"},
                    {"label": "安排下一轮面试", "value": "next_round"},
                    {"label": "拒绝候选人", "value": "reject"},
                    {"label": "暂时搁置", "value": "hold"},
                ],
            }
        ],
    },
    {
        "skill_id": "generate_html",
        "name": "HTML Page Generator",
        "description": "Generate a complete, self-contained HTML page with inline CSS and JavaScript from natural language requirements.",
        "category": "development",
        "prompt_template": None,
        "mock_tool_name": "generate_html",
        "checkpoints": None,
    },
]
