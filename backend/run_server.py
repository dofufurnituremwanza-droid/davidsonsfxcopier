import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"============================================================")
    print(f"   {settings.APP_NAME} - CLOUD COPIER ENGINE")
    print(f"   Web Dashboard: http://localhost:{settings.PORT}")
    print(f"   API Docs:      http://localhost:{settings.PORT}/docs")
    print(f"============================================================")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)

