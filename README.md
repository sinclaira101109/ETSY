# ETSY CSV 店铺分析 MVP

## 启动

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000`，上传 Etsy 商品 CSV。当前版本只在内存中处理文件，不保存 Etsy 登录信息、Cookie 或买家个人信息。

支持字段：标题 `title/name/listing_title`、标签 `tags/tag`、浏览量 `views/listing_views`、订单 `orders/quantity_sold`。后续可根据实际 Etsy 导出文件补充字段映射和报告下载。


## Codex operations workflow

See `AGENTS.md` for operating rules and `docs/automation-roadmap.md` for the phased build plan. This workflow begins in draft-and-review mode; it does not publish Etsy listings, send emails, spend lead credits, or change prices automatically.

### First run

1. Open this repository in Codex.
2. Ask Codex to read `AGENTS.md`, `docs/automation-roadmap.md`, and `config/workflow.example.yaml`.
3. Copy only the product data needed for the pilot into a local, untracked `data/inbox/` folder.
4. Start with 5–10 SKUs from one shop and ask for a read-only inventory and data-quality report.
5. Review all assumptions and generated drafts before expanding scope.

### Suggested first prompt

```text
Read AGENTS.md, docs/automation-roadmap.md, and config/workflow.example.yaml.
Do a read-only inspection of the current repository and any files in data/inbox/.
Do not modify source data or connect to external accounts.
Report the current structure, missing product facts, and the smallest safe first pilot.
```
