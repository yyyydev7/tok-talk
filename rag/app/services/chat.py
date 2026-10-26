"""General question answering that does not depend on the KOSHA/FAISS index."""

import os
import re

from app.services.rag import MATERIALS


SYSTEM_PROMPT = (
    "당신은 사용자의 질문에 한국어로 명확하고 간결하게 답하는 도우미입니다. "
    "사실을 모르면 추측하지 말고 불확실하다고 밝히세요. "
    "화학물질이나 안전 관련 질문에는 일반 참고정보임을 명시하고, "
    "실제 취급은 제품별 MSDS와 안전 담당자의 확인을 따르도록 안내하세요. "
    "답변은 음성으로 읽기 쉬운 자연스러운 문장으로 작성하세요."
)

PARTICLES = {"", "은", "는", "이", "가", "을", "를", "의", "에", "에서",
             "과", "와", "도", "만", "로", "으로", "부터", "까지", "에는"}


def _one_edit(left: str, right: str) -> bool:
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) == 1
    if len(left) > len(right):
        left, right = right, left
    return any(left == right[:i] + right[i + 1:] for i in range(len(right)))


def _canonical_question(question: str) -> tuple[str, str | None, str | None]:
    """Correct a unique Korean chemical-name typo, leaving ambiguous text alone."""
    names = tuple(name for name, _cas in MATERIALS.values())
    if any(name in question for name in names):
        return question, None, None

    candidates = []
    for match in re.finditer(r"[가-힣]+", question):
        word = match.group()
        for name in names:
            for length in (len(name) - 1, len(name), len(name) + 1):
                if (3 <= length <= len(word) and word[length:] in PARTICLES
                        and _one_edit(word[:length], name)):
                    candidates.append((match.start(), length, word[:length], name))
    if len({name for _start, _length, _typo, name in candidates}) != 1:
        return question, None, None
    start, length, typo, name = candidates[0]
    return question[:start] + name + question[start + length:], typo, name


class ChatConfigurationError(RuntimeError):
    """Raised when the answer model has no server-side credential."""


class ChatProviderError(RuntimeError):
    """Raised when the external answer model cannot complete a request."""


class ChatService:
    def __init__(self, llm=None):
        self.llm = llm

    def answer(self, question: str) -> str:
        canonical_question, typo, chemical_name = _canonical_question(question)
        if self.llm is None:
            api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ChatConfigurationError("LLM_API_KEY is not configured")
            try:
                from langchain_openai import ChatOpenAI

                self.llm = ChatOpenAI(
                    model=os.getenv("VOICE_CHAT_MODEL", "gpt-4o-mini"),
                    api_key=api_key,
                    temperature=0.2,
                    timeout=30,
                    max_retries=1,
                )
            except Exception as exc:
                raise ChatConfigurationError("answer model could not be configured") from exc
        try:
            response = self.llm.invoke([
                ("system", SYSTEM_PROMPT),
                ("human", canonical_question if chemical_name is None else
                 f"표준 물질명은 {chemical_name}입니다. 답변에도 이 이름을 사용하세요.\n"
                 f"질문: {canonical_question}"),
            ])
            answer = response.content if isinstance(response.content, str) else ""
        except ChatConfigurationError:
            raise
        except Exception as exc:
            raise ChatProviderError("answer model request failed") from exc
        if not answer.strip():
            raise ChatProviderError("answer model returned an empty response")
        answer = answer.strip()
        return answer.replace(typo, chemical_name) if typo and chemical_name else answer
