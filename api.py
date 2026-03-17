from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from storage.sheets import GoogleSheetsStorage

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

storage = GoogleSheetsStorage()

@app.get("/api/data")
def get_data():
    try:
        worksheet = storage.sh.get_worksheet(0)
        all_values = worksheet.get_all_values()
        if not all_values:
            return JSONResponse(content={"headers": [], "rows": []})

        headers = [h.strip() for h in all_values[0]]
        rows = []
        for row in all_values[1:]:
            if not any(v.strip() for v in row):
                continue
            obj = {}
            for i, h in enumerate(headers):
                val = row[i].strip() if i < len(row) else ""
                obj[h] = val
            rows.append(obj)

        return JSONResponse(content={"headers": headers, "rows": rows})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}