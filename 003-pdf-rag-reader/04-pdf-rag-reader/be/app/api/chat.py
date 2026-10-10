from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field, field_validator

router = APIRouter(tags=['chat'])


class ChatRequest(BaseModel):
    question: str = Field(strict=True, max_length=10000)

    @field_validator('question')
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Question must not be blank')
        return value


@router.post('/chat')
def ask(body: ChatRequest, request: Request):
    return request.app.state.chat.ask(body.question)


@router.get('/chat')
def history(request: Request, limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)):
    return request.app.state.chat_history.page(limit, offset)
