from fastapi import APIRouter

from app.schemas.hello import HelloResponse

router = APIRouter(tags=["hello"])


@router.get("/hello", response_model=HelloResponse)
def hello_world() -> HelloResponse:
    return HelloResponse(message="Hello, World!")
