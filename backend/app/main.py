from fastapi import FastAPI

app = FastAPI(title="VC Cold Emailer API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
