from pathlib import Path
import io
import os
import secrets
from fastapi import Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse

security = HTTPBasic()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = os.environ.get("APP_USER", "")
    password = os.environ.get("APP_PASSWORD", "")
    if not username or not password:
        raise HTTPException(503, "服务尚未配置登录凭据")
    valid_user = secrets.compare_digest(credentials.username.encode(), username.encode())
    valid_password = secrets.compare_digest(credentials.password.encode(), password.encode())
    if not (valid_user and valid_password):
        raise HTTPException(401, "用户名或密码错误", headers={"WWW-Authenticate": "Basic"})

app = FastAPI(title="ETSY CSV 店铺分析 MVP", version="0.1.0", dependencies=[Depends(authenticate)])

REQUIRED = {"title": ["title", "name", "listing_title"], "tags": ["tags", "tag"],
            "views": ["views", "listing_views"], "orders": ["orders", "quantity_sold"]}

def locate(columns, names):
    lowered = {str(c).strip().lower(): c for c in columns}
    return next((lowered[n] for n in names if n in lowered), None)

def analyze(data: bytes):
    try:
        df = pd.read_csv(io.BytesIO(data))
    except Exception as exc:
        raise HTTPException(400, f"CSV 无法读取：{exc}")
    if df.empty:
        raise HTTPException(422, "CSV 没有商品记录")
    cols = {key: locate(df.columns, names) for key, names in REQUIRED.items()}
    missing = [key for key, value in cols.items() if value is None]
    if missing:
        raise HTTPException(422, "缺少必需字段：" + ", ".join(missing) + "。支持 Etsy 导出字段或对应英文别名。")
    out = pd.DataFrame()
    out["title"] = df[cols["title"]].fillna("").astype(str)
    out["tags"] = df[cols["tags"]].fillna("").astype(str)
    out["views"] = pd.to_numeric(df[cols["views"]], errors="coerce").fillna(0)
    out["orders"] = pd.to_numeric(df[cols["orders"]], errors="coerce").fillna(0)
    out["conversion_rate"] = (out["orders"] / out["views"].replace(0, pd.NA) * 100).fillna(0).round(2)
    out["seo_score"] = (out["title"].str.len().between(30, 140).astype(int) * 35
        + out["tags"].str.split(r"[,|;]").str.len().clip(upper=13).div(13).mul(35)
        + (out["views"] > 0).astype(int) * 15 + (out["conversion_rate"] > 1).astype(int) * 15).round(0).astype(int)
    out["priority"] = out.apply(lambda r: "转化优化" if r.conversion_rate < 1 and r.views > 50 else ("SEO优化" if r.seo_score < 60 else "保持观察"), axis=1)
    return {"rows": len(out), "avg_conversion_rate": round(float(out.conversion_rate.mean()), 2),
            "avg_seo_score": round(float(out.seo_score.mean()), 2),
            "issues": out["priority"].value_counts().to_dict(),
            "listings": out.sort_values(["seo_score", "views"]).head(50).to_dict(orient="records")}

@app.get("/", response_class=HTMLResponse)
def index():
    return """<h1>ETSY CSV 店铺分析</h1><p>上传 Etsy 商品 CSV（文件仅在内存中处理，不会写入磁盘）。</p><form action='/analyze' method='post' enctype='multipart/form-data'><input type='file' name='file' accept='.csv' required><button>开始分析</button></form>"""

@app.post("/analyze")
async def upload(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(415, "只支持 CSV 文件")
    data = await file.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "文件不能超过 10 MB")
    return analyze(data)
