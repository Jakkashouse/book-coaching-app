"""프롬프트 템플릿 모듈"""
from prompts.templates import (
    TITLE_FORMULAS,
    WRITING_TONES,
    get_title_generation_prompt,
    get_toc_generation_prompt,
    get_draft_generation_prompt,
    get_feedback_prompt,
    get_refine_prompt,
    get_storytelling_prompt,
    get_proposal_generation_prompt,
    get_landing_page_prompt,
)

__all__ = [
    "TITLE_FORMULAS",
    "WRITING_TONES",
    "get_title_generation_prompt",
    "get_toc_generation_prompt",
    "get_draft_generation_prompt",
    "get_feedback_prompt",
    "get_refine_prompt",
    "get_storytelling_prompt",
    "get_proposal_generation_prompt",
    "get_landing_page_prompt",
]
