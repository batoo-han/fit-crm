"""FastAPI application for CRM system."""
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from loguru import logger
import uvicorn
import os
from fastapi.staticfiles import StaticFiles

# Создаём директорию для логов, если её нет
os.makedirs("logs", exist_ok=True)

from crm_api.routers import auth, clients, pipeline, programs, progress, actions, contacts, analytics, website, website_chat, website_settings, reminders, payments, faq, sales_scenarios, uploads, pipelines, marketing, integrations_amocrm, social_posts, promocodes
from database.init_crm import init_crm


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events - initialize on startup."""
    # Настраиваем логирование для API
    import sys
    logger.remove()  # Удаляем стандартный handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    logger.add(
        "logs/api.log",
        rotation="10 MB",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
    )
    
    logger.info("Starting CRM API...")
    # Initialize CRM database
    try:
        init_crm()
    except Exception as e:
        logger.error(f"Error initializing CRM: {e}")
    yield
    logger.info("Shutting down CRM API...")


app = FastAPI(
    title="Fitness Trainer CRM API",
    description="CRM system for managing fitness training clients, programs, and sales pipeline",
    version="1.0.0",
    lifespan=lifespan
)

# Кастомный обработчик для null origin (file:// протокол) - должен быть ПЕРЕД CORS middleware
from fastapi import Request
from fastapi.responses import JSONResponse

@app.middleware("http")
async def cors_handler(request: Request, call_next):
    """Дополнительная обработка CORS для null origin и preflight запросов."""
    # Обработка preflight запросов (OPTIONS)
    if request.method == "OPTIONS":
        response = JSONResponse(content={})
        origin = request.headers.get("origin")
        if origin is None or origin == "null" or origin == "":
            response.headers["Access-Control-Allow-Origin"] = "*"
        else:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response
    
    # Обработка обычных запросов
    response = await call_next(request)
    
    # Если origin отсутствует (null origin для file://), добавляем заголовки
    origin = request.headers.get("origin")
    if origin is None or origin == "null" or origin == "":
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

# CORS middleware
# Для локальной разработки разрешаем все localhost и 127.0.0.1 на любых портах
is_dev = os.getenv("ENVIRONMENT", "development") == "development"

cors_origins = [
    "https://www.batoohan.ru",
    "https://batoohan.ru",
]

# В режиме разработки добавляем все возможные локальные адреса
if is_dev:
    # Добавляем стандартные порты для разработки
    local_origins = [
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:8009",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8009",
        # Добавляем варианты для статического сайта на разных портах
        "http://localhost:5500",  # Live Server
        "http://localhost:8080",  # Python http.server
        "http://localhost:5000",  # Flask default
        "http://127.0.0.1:5500",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5000",
        "file:///",
    ]
    cors_origins.extend(local_origins)

# Настройка CORS с поддержкой null origin для file:// протокола
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"http://localhost:\d+|http://127\.0\.0\.1:\d+",  # Разрешаем любой порт localhost
    allow_credentials=False,  # Отключаем credentials для работы с null origin
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Static files (uploads)
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(programs.router, prefix="/api/programs", tags=["programs"])
app.include_router(progress.router, prefix="/api/progress", tags=["progress"])
app.include_router(actions.router, prefix="/api/actions", tags=["actions"])
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(website.router, prefix="/api/website", tags=["website"])
app.include_router(website_chat.router, prefix="/api/website", tags=["website-chat"])
app.include_router(website_settings.router, prefix="/api/website", tags=["website-settings"])
app.include_router(reminders.router, prefix="/api/reminders", tags=["reminders"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(faq.router, prefix="/api/faq", tags=["faq"])
app.include_router(sales_scenarios.router, prefix="/api/sales-scenarios", tags=["sales-scenarios"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])
app.include_router(pipelines.router, prefix="/api/pipelines", tags=["pipelines"])
app.include_router(marketing.router, prefix="/api/marketing", tags=["marketing"])
app.include_router(integrations_amocrm.router, prefix="/api/integrations/amocrm", tags=["integrations-amocrm"])
app.include_router(social_posts.router, prefix="/api/social-posts", tags=["social-posts"])
app.include_router(promocodes.router, prefix="/api/promocodes", tags=["promocodes"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Fitness Trainer CRM API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload when running directly
        log_level="info"
    )

