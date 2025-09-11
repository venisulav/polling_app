from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import admin, polls, voting, websockets

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Polling App")

# Include all routers
app.include_router(polls.router)
app.include_router(voting.router)
app.include_router(websockets.router)
app.include_router(admin.router)

origins = [
    "http://localhost:3000",  # React default dev server
    "http://127.0.0.1:3000",
    # You can add more origins or use "*" for all
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)
