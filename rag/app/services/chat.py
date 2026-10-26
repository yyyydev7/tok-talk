"""General question answering that does not depend on the KOSHA/FAISS index."""

import os


SYSTEM_PROMPT = (
    "당신은 사용자의 질문에 한국어로 명확하고 간결하게 답하는 도우미입니다. "
    "사실을 모르면 추측하지 말고 불확실하다고 밝히세요. "
    "화학물질이나 안전 관련 질문에는 일반 참고정보임을 명시하고, "
    "실제 취급은 제품별 MSDS와 안전 담당자의 확인을 따르도록 안내하세요. "
    "답변은 음성으로 읽기 쉬운 자연스러운 문장으로 작성하세요."
)


class ChatConfigurationError(RuntimeError):
    """Raised when the answer model has no server-side credential."""


class ChatProviderError(RuntimeError):
    """Raised when the external answer model cannot complete a request."""


class ChatService:
    def __init__(self, llm=None):
        self.llm = llm

    def answer(self, question: str) -> str:
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
                ("human", question),
            ])
            answer = response.content if isinstance(response.content, str) else ""
        except ChatConfigurationError:
            raise
        except Exception as exc:
            raise ChatProviderError("answer model request failed") from exc
        if not answer.strip():
            raise ChatProviderError("answer model returned an empty response")
        return answer.strip()
