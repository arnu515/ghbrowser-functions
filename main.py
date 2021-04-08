from clone import app as clone
import fastapi
import uvicorn
import os

app = fastapi.FastAPI()
app.include_router(clone)

if __name__ == "__main__":
    uvicorn.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), app="main:app")
