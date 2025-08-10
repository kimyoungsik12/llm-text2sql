from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .services.prompt_manager import PromptManager
from .models.db_manager import DatabaseManager
from .routes.query import router as query_router
from .services.logger import AppLogger


app = FastAPI(title="NL2SQL Answer Server")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)


prompt_manager = PromptManager()
db_manager = DatabaseManager()
app_logger = AppLogger()


@app.on_event("startup")
def on_startup() -> None:
  db_manager.load_config()
  db_manager.connect_all()
  prompt_manager.ensure_directories()
  prompt_manager.generate_db_structure_prompts(db_manager)


@app.on_event("shutdown")
def on_shutdown() -> None:
  db_manager.close_all()


app.include_router(query_router, prefix="/api")


@app.get("/health")
def health() -> dict:
  return {"ok": True}

