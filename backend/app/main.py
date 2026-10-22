from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="ScamShield TH API")
app.include_router(router)
