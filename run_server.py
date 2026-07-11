import uvicorn
from cpe.config import settings

if __name__ == "__main__":
    print(f"Starting CPE FastAPI Server at http://{settings.CPE_HOST}:{settings.CPE_PORT}")
    print("API docs available at: http://127.0.0.1:8000/docs")
    uvicorn.run(
        "cpe.main:app",
        host=settings.CPE_HOST,
        port=settings.CPE_PORT,
        reload=True
    )
