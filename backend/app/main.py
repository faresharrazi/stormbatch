from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.jobs import router as jobs_router
from app.routes.preview import router as preview_router
from app.routes.registration import router as registration_router


app = FastAPI(title="StormBatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(preview_router, prefix="/api")
app.include_router(registration_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
