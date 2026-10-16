from pathlib import Path
import io
import os
import secrets
import html
import json
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

FIELD_ALIASES = {
    "title": ["title", "name", "listing_title", "listing name"],
    "tags": ["tags", "tag", "keywords"],
    "description": ["description", "listing_description", "item description"],
    "category": ["category", "taxonomy_path", "section"],
    "attributes": ["attributes", "attribute", "materials", "material"],
    "image_count": ["image_count", "images", "photo_count"],
    "views": ["views", "listing_views", "visits"],
    "orders": ["orders", "quantity_sold", "sales"],
}

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
    cols = {key: locate(df.columns, names) for key, names in FIELD_ALIASES.items()}
    missing = [key for key, value in cols.items() if value is None and key in ("title", "tags")]
    if missing:
        raise HTTPException(422, "缺少必需字段：" + ", ".join(missing) + "。请至少提供商品标题和标签列。")
    out = pd.DataFrame()
    out["title"] = df[cols["title"]].fillna("").astype(str)
    out["tags"] = df[cols["tags"]].fillna("").astype(str)
    for key in ("description", "category", "attributes"):
        out[key] = df[cols[key]].fillna("").astype(str) if cols[key] else ""
    out["image_count"] = pd.to_numeric(df[cols["image_count"]], errors="coerce").fillna(0) if cols["image_count"] else 0
    out["views"] = pd.to_numeric(df[cols["views"]], errors="coerce").fillna(0) if cols["views"] else 0
    out["orders"] = pd.to_numeric(df[cols["orders"]], errors="coerce").fillna(0) if cols["orders"] else 0
    out["conversion_rate"] = (out["orders"] / out["views"].replace(0, pd.NA) * 100).fillna(0).round(2)
    def diagnose(row):
        tags = [x.strip().lower() for x in str(row.tags).replace("|", ",").replace(";", ",").split(",") if x.strip()]
        issues, actions = [], []
        title_len = len(str(row.title).strip())
        if title_len < 30:
            issues.append("标题过短，搜索意图表达不足"); actions.append("补充材质、用途、场景或送礼对象，保持自然可读")
        elif title_len > 140:
            issues.append("标题过长，可能稀释核心词"); actions.append("把最重要的商品词和购买意图放在标题前半段")
        if len(set(tags)) < 10:
            issues.append(f"有效标签仅 {len(set(tags))} 个"); actions.append("补齐 13 个相关长尾标签，避免重复和无关词")
        if not str(row.description).strip():
            issues.append("缺少商品描述"); actions.append("补充尺寸、材质、用途、包装、配送和定制说明")
        elif len(str(row.description).strip()) < 300:
            issues.append("描述信息偏少"); actions.append("按购买疑虑补充规格、使用场景、礼物对象和配送信息")
        if not str(row.category).strip():
            issues.append("未提供分类字段"); actions.append("核对 Etsy 最具体的分类和属性，不要只依赖标题关键词")
        if not str(row.attributes).strip():
            issues.append("未提供属性/材质字段"); actions.append("填写 Etsy 属性和材料字段，覆盖筛选条件")
        if row.image_count and row.image_count < 5:
            issues.append(f"图片数量为 {int(row.image_count)}"); actions.append("准备多角度、尺寸、包装和使用场景图")
        if not row.views:
            issues.append("没有流量数据"); actions.append("导入 Etsy 流量 CSV 后再判断曝光、点击和转化")
        if row.views > 50 and row.conversion_rate < 1:
            issues.append("有流量但转化率低于 1%"); actions.append("优先检查首图、价格、配送、评价和详情页承接")
        score = min(100, int((25 if 30 <= title_len <= 140 else 10)
            + min(25, len(set(tags)) / 13 * 25)
            + (15 if len(str(row.description).strip()) >= 300 else 5 if str(row.description).strip() else 0)
            + (10 if str(row.category).strip() else 0)
            + (10 if str(row.attributes).strip() else 0)
            + (10 if row.image_count >= 5 else 0)))
        priority = "数据待补充" if not row.views else ("转化优化" if row.conversion_rate < 1 and row.views > 50 else ("SEO整改" if score < 70 else "保持观察"))
        return pd.Series({"seo_score": score, "priority": priority, "issues_detail": "；".join(issues) or "暂未发现规则问题", "actions": "；".join(actions) or "继续观察并记录变更后的数据"})
    out[["seo_score", "priority", "issues_detail", "actions"]] = out.apply(diagnose, axis=1)
    return {"rows": len(out), "avg_conversion_rate": round(float(out.conversion_rate.mean()), 2),
            "avg_seo_score": round(float(out.seo_score.mean()), 2),
            "issues": out["priority"].value_counts().to_dict(),
            "data_notes": ["未提供 views/orders 时，转化结论不可用" if not cols["views"] or not cols["orders"] else "流量字段已识别"],
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
    result = analyze(data)
    rows = "".join(f"<tr><td>{html.escape(str(r['title']))}</td><td>{r['seo_score']}</td><td>{r['conversion_rate']}%</td><td>{html.escape(str(r['priority']))}</td><td>{html.escape(str(r['issues_detail']))}</td><td>{html.escape(str(r['actions']))}</td></tr>" for r in result["listings"])
    return HTMLResponse(f"""<h1>ETSY 分析报告</h1><p>商品数：{result['rows']}；平均 SEO 分数：{result['avg_seo_score']}；平均转化率：{result['avg_conversion_rate']}%</p><p>问题分类：{html.escape(json.dumps(result['issues'], ensure_ascii=False))}</p><p>{html.escape('；'.join(result['data_notes']))}</p><table border='1' cellpadding='6'><tr><th>商品标题</th><th>SEO 分数</th><th>转化率</th><th>优先级</th><th>具体问题</th><th>整改建议</th></tr>{rows}</table><p><a href='/'>返回继续上传</a></p>""")
