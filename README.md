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
