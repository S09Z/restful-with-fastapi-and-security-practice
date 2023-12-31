from fastapi import FastAPI
from app.api.v1.user_routes import router as user_router

app = FastAPI()

# Include the router from user_routes
app.include_router(user_router, prefix="/api/v1")

@app.get("/")
async def read_root():
    return {"message": "Hello World"}