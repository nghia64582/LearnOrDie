from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Xin chào, FastAPI của bạn đã chạy thành công!"}

@app.get("/hello/{name}")
def read_item(name: str):
    return {"message": f"Hello {name}, đây là API từ máy của bạn."}
