import io
import os
import re
import math
import secrets
import html
import json
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import Depends, FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse

REPORT_VERSION = "0.4.0"

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

app = FastAPI(title="ETSY CSV 店铺分析", version=REPORT_VERSION, dependencies=[Depends(authenticate)])

FIELD_ALIASES = {
    "title": ["title", "name", "listing_title", "listing name"],
    "tags": ["tags", "tag", "keywords"],
    "description": ["description", "listing_description", "item description"],
    "category": ["category", "taxonomy_path"],
    "attributes": ["attributes", "attribute"],
    "materials": ["materials", "material"],
    "views": ["views", "listing_views"],
    "visits": ["visits"],
    "orders": ["orders", "order_count"],
    "units": ["quantity_sold"],
    "image_count": ["image_count", "photo_count"],
    "status": ["status", "listing_status"],
    "period_start": ["period_start"],
    "period_end": ["period_end"],
}
LABELS = {"title": "标题", "tags": "标签", "description": "描述", "category": "分类",
          "attributes": "属性", "materials": "材质", "views": "浏览量", "visits": "访问量",
          "orders": "订单数", "image_count": "图片数量", "status": "上架状态",
          "period_start": "统计起日", "period_end": "统计止日", "units": "售出件数"}
STOPWORDS = set("a an the with and or for of to in on by from is it this that handmade gift ready small".split())


def locate(columns, names):
    lowered = {str(c).strip().lower(): c for c in columns}
    return next((lowered[n] for n in names if n in lowered), None)


def words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOPWORDS


def number(value):
    if value is None or not str(value).strip():
        return None
    try:
        n = float(str(value).replace(",", ""))
        return n if math.isfinite(n) and n >= 0 and n.is_integer() else None
    except (ValueError, TypeError):
        return None


def finding(code, area, severity, status, evidence, interpretation, reason, actions, verification,
            confidence="中", alternatives="本结论仅针对上传资料；尚未核对 Etsy 后台和实际买家行为。"):
    return dict(code=code, area=area, severity=severity, status=status, evidence=evidence,
                interpretation=interpretation, reason=reason, actions=actions,
                verification=verification, confidence=confidence, alternatives=alternatives)


def diagnose(record, cols, index):
    get = lambda key: str(record.get(cols[key], "")).strip() if cols.get(key) else ""
    title, tag_text, description = get("title"), get("tags"), get("description")
    tags = [t.strip() for t in re.split(r"[,;|，]", tag_text) if t.strip()]
    unique = list(dict.fromkeys(t.casefold() for t in tags))
    findings = []
    def add(*args, **kwargs):
        findings.append(finding(*args, **kwargs))
    # Length is a review trigger, never proof of poor search ranking.
    if not title:
        add("title_empty", "标题", "高", "已观察", "标题列存在，但本行为空。", "商品身份无法从本行资料识别。",
            "消费者和检索系统都需要明确的商品名称。", ["补写真实产品名称，再补充已确认的形态、规格等区分信息。"],
            "重新导入后标题非空；人工能在一眼内说出卖的是什么。", "高")
    elif len(title) > 140:
        add("title_long", "标题", "高", "已观察", f"标题 {len(title)} 字符，超过本工具 140 字符检查上限。",
            "标题需要压缩；不能据此推断已有流量损失。", "较长的修饰语会增加阅读成本；字符限制请以当前 Etsy 编辑器为准。",
            ["保留商品名和真实差异点；删掉重复修饰语。", "把泛送礼词移入相关标签或描述，避免为了填满字符而堆词。"],
            "在 Etsy 编辑器确认可保存；人工检查标题清晰度。", "高")
    elif len(title.split()) > 15:
        add("title_readability", "标题", "中", "待验证", f"标题含 {len(title.split())} 个空格分词；原文：{title}",
            "修饰信息较多，建议人工检查读者是否先看到产品本体。", "15 词是内部可读性筛查阈值，不是平台处罚线。",
            ["圈出不可删的商品名、数量和包装差异；去掉意思重复的 gift、handmade 等表达。", "不要仅为 SEO 删除区分产品所必需的信息。"],
            "让未看过商品的人复述产品；若有同口径点击数据，后续比较点击表现。")
    if len(unique) < 13:
        add("tag_coverage", "TAG 覆盖", "中", "已观察", f"识别 {len(tags)} 个标签，去重后 {len(unique)} 个；当前标签：{tag_text or '空'}。",
            "可进一步检查是否遗漏产品形态、用途等相关检索表达；不足 13 个不等于排名差。",
            "相关的多词标签可以覆盖不同购买表达；无关词即使补满也没有价值。",
            ["先确定一个准确产品词，再整理真实的形态、包装、用途、对象词。", "仅补充与实物吻合且有依据的表达；不要用无关热门词凑满。"],
            "逐个核实相关性、长度和重复；保存前检查 Etsy 编辑器限制。", "高")
    duplicates = [t for t, c in Counter(t.casefold() for t in tags).items() if c > 1]
    long_tags = [t for t in tags if len(t) > 20]
    if duplicates or long_tags or len(tags) > 13:
        add("tag_format", "TAG 格式", "高", "已观察", f"重复标签：{duplicates or '无'}；超过 20 字符：{long_tags or '无'}；标签总数：{len(tags)}。",
            "这些标签需要人工检查编辑器可接受性；CSV 中出现不代表后台已原样保存。",
            "格式或重复问题会浪费有限标签位置，先解决这一项再比较搜索需求。",
            ["删除完全相同的重复标签。", "超长短语缩成自然且准确的多词标签；以 Etsy 编辑器的当前校验为准。"],
            "无完全重复、无超长标签；变更前后都留存一份导出。", "高")
    title_words = words(title)
    tag_words = set().union(*(words(t) for t in tags)) if tags else set()
    overlap = sorted(title_words & tag_words)
    uncovered = sorted(title_words - tag_words)
    coverage = round(len(overlap) / len(title_words) * 100) if title_words else None
    if title_words:
        add("lexical_match", "标题与 TAG", "中" if coverage < 50 else "低", "待验证",
            f"英文实词覆盖 {coverage}%；交集：{', '.join(overlap) or '无'}；标题未在标签中逐词出现：{', '.join(uncovered) or '无'}。",
            "这是词面覆盖率，不是语义匹配分或 Etsy 排名分。先检查核心产品词，再判断修饰词是否需要覆盖。",
            "买家表达应与商品身份一致；逐词重复不能代替相关性，也不需要追求 100% 覆盖。",
            [f"人工确认标题中的核心产品词：{title}。", "若核心产品短语未被任一标签准确表达，替换一个无关或过泛标签；保留不同但相关的长尾表达。"],
            "核心产品意图一致，且无标签误导；不能用覆盖率上升直接证明排名改善。",
            alternatives="同义词、词形和多语言可能词面不重合；数字、包装细节不一定都需要成为标签。")
    checks = {
        "产品与包含内容": r"towel|bouquet|rose|bear|flower|includes?|contains?|piece|毛巾|花束|包含|礼盒",
        "可核实规格": r"\d+(?:\.\d+)?\s*(?:cm|mm|inch|inches|oz|g|kg|厘米|毫米)|dimensions|size:|尺寸",
        "材质": r"cotton|microfib(?:er|re)|polyester|linen|material|棉|材质|纤维",
        "场景或送礼对象": r"birthday|housewarming|hostess|mother|friend|christmas|gift for|生日|乔迁|送给",
        "包装与交付": r"packag|wrapp|gift box|ship|delivery|processing|包装|发货|配送",
        "使用或维护": r"wash|care|unfold|reus|instruction|清洗|展开|使用|护理",
    }
    if not cols["description"]:
        add("description_unknown", "描述买点", "中", "资料未提供", "CSV 没有描述列。", "无法判断你的线上描述是否清晰，更不能认定线上没有描述。",
            "没有原文就无法核对产品价值、规格及交付承诺。", ["下一次导入带 description 列的商品资料；不要为补齐报表随意编写商品承诺。"],
            "描述原文可读取后，再逐项核对买家疑问。", "高")
    else:
        covered = [name for name, pattern in checks.items() if re.search(pattern, description, re.I)]
        missing = [name for name in checks if name not in covered]
        if not description or missing:
            add("description_clarity", "描述买点", "高" if not description else "中", "已观察" if not description else "待验证",
                f"描述 {len(description)} 字符。规则发现线索：{'、'.join(covered) or '无'}；未识别：{'、'.join(missing) or '无'}。首段摘录：{description[:200] or '空'}",
                "描述为空。" if not description else "部分购买疑问没有被规则识别；需回看原文，同义表达可能漏检。篇幅长不等于买点清楚。",
                "读者需要知道收到什么、适不适合、是否来得及收到；缺少信息可能增加犹豫，但本规则不能证明因此丢单。",
                ["首段用真实信息写清：产品是什么 → 与普通选择的区别 → 适用场景。",
                 "依次补核：" + "、".join(missing) + "；所有规格和承诺以实物与履约能力为准。",
                 "毛巾花礼可说明是否可拆开使用、包含几条毛巾及包装内容；未经确认不要声称纯棉、环保或可定制。"],
                "让读者仅看描述回答：收到什么、尺寸/材质、是否含包装、何时发货、如何使用。逐项人工验收。",
                alternatives="词语匹配仅能定位需复核段落，不能替代语义理解、合规审核或实际买家访谈。")
    for key in ("category", "attributes", "materials", "image_count"):
        if not cols[key] or not get(key):
            status = "资料未提供" if not cols[key] else "导出值为空"
            add(key + "_unknown", LABELS[key], "低", status,
                f"{LABELS[key]}：{'CSV 不含该字段' if not cols[key] else '当前行没有值'}。",
                "只能说当前资料不可核验，不能推断线上未设置。",
                "分类/属性有助于明确商品；图片数量不代表首图质量。店铺 section 也不等于商品分类。",
                [f"到 Etsy 商品编辑页核对{LABELS[key]}，再把实际值补回资料。", "图片人工检查：产品全貌、比例/尺寸、包装内容、展开使用；不要单靠图片数量判断质量。" if key == "image_count" else "保留真实且最具体的选项；材质和属性分别记录。"],
                "人工核验完成，并在下一次导入中可追溯到实际设置。", "高")
    views, visits, orders = number(get("views")), number(get("visits")), number(get("orders"))
    period_ok = False
    try:
        start, end = datetime.fromisoformat(get("period_start")), datetime.fromisoformat(get("period_end"))
        period_ok = start <= end
    except ValueError:
        pass
    rate = round(orders / visits * 100, 2) if period_ok and visits and orders is not None and orders <= visits else None
    if rate is None:
        add("performance_unknown", "经营漏斗", "中", "资料不足",
            f"浏览量 views={views}，访问量 visits={visits}，订单 orders={orders}；统计周期：{get('period_start') or '未提供'} 至 {get('period_end') or '未提供'}。",
            "不能确定卡点在搜索曝光、点击还是下单；缺少数据不是零流量或零转化。",
            "views 是浏览量，visits 是访问量；售出件数不等于订单数。转化率需要同周期且可归因的访问量与订单。",
            ["补充同一商品、同一时区及统计周期的 visits、orders、period_start、period_end；若只有 views，先单独观察浏览变化。", "另取自然/广告来源、搜索词、收藏和配送信息，再判断流量质量及购买阻力。"],
            "先核对统计范围及归因一致；没有曝光和点击数据时不生成点击率。", "高")
    else:
        add("performance_review", "经营漏斗", "中", "待验证", f"同一行声明周期内 {int(visits)} 次访问、{int(orders)} 笔订单；计算转化率 {rate}%。",
            "可以记录本次水平；单期数据不足以判断增长、下降或行业表现。0 笔订单是观测值，不足以证明 SEO 出错。",
            "访问量、渠道构成、季节和统计周期都会影响转化；不存在适用于所有类目的固定合格线。",
            ["选择同类商品及相同长度历史周期比较，记录广告占比和价格/运费。", "先验证商品详情、到手总价和预计送达，再设计单变量修改。"],
            "7/14/30 天复查相同口径；访问量少时延长观察，报告次数和订单数，不只看百分比。")
    add("keyword_unverified", "搜索需求与长尾词", "低", "未验证", f"本次只有商品资料；当前 {len(unique)} 个不同 TAG。未连接 eRank，未采集 Etsy 搜索量。",
        "无法给出真实竞争度、搜索度、趋势或高机会词排名。候选词只能先作为待研究假设。",
        "产品相关性、需求和竞争是三项不同判断；标题词面匹配无法证明需求。",
        ["在已有关键词导出中核对核心产品词，保留来源、日期、目标市场、搜索度及竞争字段。", "候选长尾按产品形态＋真实差异/用途组合；先排除不符实物的词，再比较同来源同周期数据。"],
        "每个推荐词都应列出原始指标和来源；没有数据的词标记待验证。", "高")
    core = re.split(r"\s+(?:with|for)\s+|,", title, maxsplit=1, flags=re.I)[0].strip()
    draft = f"{core} — [已确认的规格或包装差异]" if core else "[产品名称] — [已确认差异]"
    return {"id": index, "title": title or f"第 {index} 行无标题", "status": get("status") or "未提供（不能推断已上架/未上架）",
            "tags": tags, "lexical_coverage": coverage, "conversion_rate": rate, "title_words": sorted(title_words),
            "findings": findings, "title_draft": draft,
            "description_template": "这是一款[真实产品名称]，采用[已确认材质/工艺]，适用于[已确认场景]。包含[数量及清单]，尺寸为[实测值]；包装为[实际包装]。处理时间[实际天数]，配送以结账预计为准。使用/清洗：[实际方法]。",
            "priority": "先整改可核实问题" if any(f["severity"] == "高" for f in findings) else "先核实信息再测试优化"}


def analyze(data: bytes):
    try:
        df = pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except Exception:
        raise HTTPException(400, "CSV 无法读取。请使用 UTF-8 编码的逗号分隔文件。")
    if df.empty:
        raise HTTPException(422, "CSV 没有商品记录")
    if len(df) > 1000:
        raise HTTPException(422, "单次最多分析 1000 条商品，请拆分文件。")
    cols = {key: locate(df.columns, names) for key, names in FIELD_ALIASES.items()}
    if not cols["title"] or not cols["tags"]:
        raise HTTPException(422, "请提供 title 和 tags 列；流量列可选。")
    listings = [diagnose(record, cols, i + 1) for i, record in enumerate(df.to_dict(orient="records"))]
    groups = {}
    for listing in listings:
        for f in listing["findings"]:
            if f["code"] not in groups:
                groups[f["code"]] = {**f, "count": 0, "examples": []}
            groups[f["code"]]["count"] += 1
            if len(groups[f["code"]]["examples"]) < 3:
                groups[f["code"]]["examples"].append(listing["title"])
    severity = {"高": 0, "中": 1, "低": 2}
    bottlenecks = sorted(groups.values(), key=lambda f: (severity[f["severity"]], -f["count"]))
    return {"version": REPORT_VERSION, "rows": len(listings), "listings": listings, "bottlenecks": bottlenecks,
            "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
            "field_map": {LABELS[k]: v for k, v in cols.items()},
            "scope": "仅分析这次上传的商品快照；没有自动访问店铺、Etsy 搜索或 eRank。不能从单期内容资料确定实际流量损失或销售趋势。"}


def analyze_many(files, shop_url=""):
    """Analyze independent exports together without pretending that unlike files are one metric table."""
    if not files:
        raise HTTPException(422, "请至少选择一个 CSV 文件。")
    results = []
    for source_name, payload in files:
        result = analyze(payload)
        for listing in result["listings"]:
            listing["source_file"] = source_name
        results.append(result)
    listings = [listing for result in results for listing in result["listings"]]
    for number, listing in enumerate(listings, 1):
        listing["id"] = number
    groups = {}
    for result in results:
        for item in result["bottlenecks"]:
            if item["code"] not in groups:
                groups[item["code"]] = {**item, "count": 0, "examples": []}
            groups[item["code"]]["count"] += item["count"]
            for example in item["examples"]:
                if example not in groups[item["code"]]["examples"] and len(groups[item["code"]]["examples"]) < 3:
                    groups[item["code"]]["examples"].append(example)
    severity = {"高": 0, "中": 1, "低": 2}
    bottlenecks = sorted(groups.values(), key=lambda f: (severity[f["severity"]], -f["count"]))
    fields = {}
    for (source_name, _), result in zip(files, results):
        fields[source_name] = result["field_map"]
    scope = ("本次合并分析了 " + ", ".join(name for name, _ in files) + "；每一行保留来源文件。"
             "店铺网址仅作为报告上下文，未抓取登录页面或私有数据。搜索量、竞争度和真实排名仍需官方导出或合规的关键词资料。")
    return {"version": REPORT_VERSION, "rows": len(listings), "listings": listings, "bottlenecks": bottlenecks,
            "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
            "field_map": fields, "shop_url": shop_url.strip(), "sources": [name for name, _ in files], "scope": scope}


def esc(value):
    return html.escape(str(value))


def page(title, body):
    return f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)}</title>
    <style>body{{font:16px/1.8 system-ui,sans-serif;background:#f3f5f8;color:#16223a;margin:0}}main{{max-width:1160px;margin:auto;padding:24px}}h1,h2,h3{{line-height:1.4}}section,article{{background:white;padding:24px;border-radius:12px;margin:18px 0;border:1px solid #dde3ed}}a{{color:#1758ac}}small,.muted{{color:#52617a}}.notice{{border-left:5px solid #bf7a17;background:#fff8e9;padding:16px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}}.badge{{background:#e9f0fb;padding:3px 8px;border-radius:5px;font-size:14px}}dt{{font-weight:700;margin-top:12px}}dd{{margin:4px 0 12px}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ddd;padding:10px;text-align:left;overflow-wrap:anywhere}}button{{padding:10px 18px;background:#1758ac;color:white;border:0;border-radius:6px;cursor:pointer}}li{{margin-bottom:8px}}summary{{cursor:pointer;font-weight:700}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:12px}}@media print{{button,form{{display:none}}details>*{{display:block}}body{{background:white}}section,article{{break-inside:avoid}}}}</style>
    <main><p class="muted">ETSY 经营诊断 · 报告版本 {REPORT_VERSION}</p>{body}</main></html>"""


def render_report(result):
    summary = "".join(f"<li><b>{esc(f['area'])}</b> · {f['count']}/{result['rows']} 个商品 · {esc(f['status'])}<br>{esc(f['interpretation'])}<br><small>示例：{esc('；'.join(f['examples']))}</small></li>" for f in result["bottlenecks"][:5])
    if result.get("sources"):
        field_rows = "".join(f"<tr><td>{esc(source)}</td><td>{esc(json.dumps(fields, ensure_ascii=False))}</td></tr>" for source, fields in result["field_map"].items())
    else:
        field_rows = "".join(f"<tr><td>{esc(k)}</td><td>{esc(v) if v else '未提供，结论受限'}</td></tr>" for k, v in result["field_map"].items())
    listings_html = []
    for listing in result["listings"]:
        findings_html = []
        for f in listing["findings"]:
            actions = "".join(f"<li>{esc(a)}</li>" for a in f["actions"])
            findings_html.append(f"<details open><summary>{esc(f['area'])} <span class='badge'>{esc(f['severity'])}优先级 · {esc(f['status'])}</span></summary><dl>"
                f"<dt>① 观察证据</dt><dd>{esc(f['evidence'])}</dd><dt>② 判断与可能原因</dt><dd>{esc(f['interpretation'])}</dd>"
                f"<dt>③ 为什么这样优化</dt><dd>{esc(f['reason'])}</dd><dt>④ 执行动作</dt><dd><ol>{actions}</ol></dd>"
                f"<dt>⑤ 如何验收 / 何时复查</dt><dd>{esc(f['verification'])}</dd><dt>⑥ 置信度与其他解释</dt><dd>对上述证据/有限结论的置信度：{esc(f['confidence'])}。{esc(f['alternatives'])}</dd></dl></details><hr>")
        rate = "暂无可比数据" if listing["conversion_rate"] is None else f"{listing['conversion_rate']}%（按本行声明的同周期 visits/orders）"
        tag_audit = []
        for tag in listing["tags"]:
            shared = sorted(words(tag) & set(listing["title_words"]))
            verdict = "与标题有词面交集；仍需核实是否准确表达实物" if shared else "没有英文实词交集；可能是场景词/同义词，不可直接删除"
            tag_audit.append(f"<tr><td>{esc(tag)}</td><td>{len(tag)} 字符</td><td>{esc(', '.join(shared) or '无')}</td><td>{esc(verdict)}</td><td>搜索度 / 竞争度未知；需有日期、市场和来源的数据</td></tr>")
        tag_table = "<h3>逐 TAG 核对记录</h3><table><tr><th>原 TAG</th><th>长度</th><th>标题实词交集</th><th>解释与处理原则</th><th>需求证据</th></tr>" + "".join(tag_audit) + "</table>"
        listings_html.append(f"<article id='listing-{listing['id']}'><h2>{listing['id']}. {esc(listing['title'])}</h2><p>{esc(listing['priority'])} · 状态：{esc(listing['status'])} · 来源文件：{esc(listing.get('source_file', '本次上传'))}</p>"
            f"<p>转化率：{esc(rate)}。不再给出混合了未知数据的 SEO 总分。</p><p>当前 TAG：{esc(' / '.join(listing['tags']))}</p>" + "".join(findings_html) + tag_table +
            f"<h3>可编辑文案骨架（需人工核实，不能直接当作定稿）</h3><p>标题草稿：</p><pre>{esc(listing['title_draft'])}</pre><p>描述草稿：</p><pre>{esc(listing['description_template'])}</pre></article>")
    tasks = []
    for f in result["bottlenecks"][:5]:
        tasks.append(f"<tr><td>{esc(f['area'])}（{f['count']} 个商品）</td><td>{esc(f['actions'][0])}</td><td>{esc(f['verification'])}</td></tr>")
    return page("ETSY 经营诊断报告", f"<h1>这次上传揭示了哪些问题？</h1><p>生成时间：{esc(result['generated_at'])}（北京时间） · 商品 {result['rows']} 个</p>"
        f"<p class='notice'>{esc(result['scope'])} 下列是待处理的证据与核查任务，不能等同于已证实的店铺销售卡点。</p>"
        "<button onclick='window.print()'>打印 / 保存 PDF</button> <a href='/'>返回上传</a>"
        f"<section><h2>先看这五项：主要阻碍与证据边界</h2><ol>{summary}</ol></section>"
        f"<section><h2>本周执行清单</h2><p>先处理高优先级的可核实问题，再补数据；不要一次改完所有商品。建议选 1—2 个代表商品，逐项留存变更记录。</p><table><tr><th>任务范围</th><th>第一步动作</th><th>验收依据</th></tr>{''.join(tasks)}</table>"
        "<h3>跟进节奏</h3><ol><li>当天：保存原始导出与截图，核实实物和字段；记录商品 ID、修改时间、修改前后内容、假设和负责人。</li><li>第 1—3 天：先修格式/缺漏，再选择标题、标签或首图中的一个变量测试；保留相近商品作为参照。</li><li>第 7 / 14 天：核对同周期、同渠道访问与订单；同时记录广告、促销、价格、运费变化。</li><li>第 30 天或样本足够时：比较效果，决定保留、回退或延长观察；节日及流量变化可能造成干扰，不能保证因果。</li></ol></section>"
        "<section><h2>平台机制、内部规则和未知项</h2><p>内容相关性、买家理解及交易体验是核查方向；本工具没有还原 Etsy 排名算法。标题词数、描述关键字和覆盖率都是内部筛查，不是官方权重或处罚线。</p>"
        "<p>标题与 TAG 的词面一致不等于语义一致或高搜索量。无 eRank/搜索数据时不输出虚构竞争度、搜索度或热门长尾词。没有图片原件时不评价首图美观度；没有渠道和历史数据时不归因流量下降。</p>"
        "<p>官方核对入口：<a href='https://www.etsy.com/seller-handbook/article/375461474487' target='_blank' rel='noopener'>Etsy：How Etsy Search Works</a>、<a href='https://www.etsy.com/legal/creativity/' target='_blank' rel='noopener'>Etsy Creativity Standards</a>。本次未能实时读取官方页面，不能称为已按最新算法校验；以官方最新原文及编辑器为准。</p></section>"
        f"<section><h2>数据识别记录</h2><p>店铺上下文：{esc(result.get('shop_url') or '未提供')}</p><p>本次文件：{esc('、'.join(result.get('sources', [])) or '单个上传文件')}</p><table><tr><th>文件</th><th>识别到的字段</th></tr>{field_rows}</table><p>section 不当成 category，materials 不当成 attributes，quantity_sold 不当成 orders，views 不当成 visits。</p></section>"
        + "".join(listings_html))


@app.exception_handler(HTTPException)
async def readable_error(request: Request, exc: HTTPException):
    return HTMLResponse(page("需要处理的信息", f"<h1>本次操作未完成</h1><p>{esc(exc.detail)}</p><a href='/'>返回上传页面</a>"), status_code=exc.status_code, headers=exc.headers)


@app.get("/", response_class=HTMLResponse)
def index():
    return page("ETSY CSV 经营诊断", "<h1>把商品资料变成具体执行清单</h1><p>一次选择多个 CSV，报告会保留每一行的来源文件，并逐商品展示：证据 → 原因假设 → 优化理由 → 动作 → 验收与复查。</p>"
        "<p>必需：title、tags。可选：description、category、attributes、materials、image_count、status、views、visits、orders、period_start、period_end。缺失字段显示未知，不伪装为 0 或未设置。</p>"
        "<p>可以同时上传商品资料、Etsy 流量、订单汇总和关键词资料；只有能识别 title/tags 的商品表会进入逐商品诊断，其他格式会显示具体原因。文件仅用于本次分析，不会保存到应用磁盘。</p>"
        "<p class='notice'>上传通过临时文件/内存解析，应用不建立文件档案或保存报告。请去掉买家个人信息；正式使用前须配置 HTTPS。当前不连接 Etsy/eRank 或 COS，不提供自动日报。</p>"
        "<form action='/analyze' method='post' enctype='multipart/form-data'><label>店铺网址（仅作为报告上下文）：<input type='url' name='shop_url' size='60' placeholder='https://www.etsy.com/shop/HoryalfTowelFlowers'></label><br><br><input type='file' name='files' accept='.csv' multiple required><button>生成多文件详细报告</button></form><p>UTF-8 CSV，单文件最大 10 MB、单次最多 20 个文件、每个文件最多 1000 行。报告可以通过浏览器打印保存 PDF。</p>")


@app.post("/analyze", response_class=HTMLResponse)
async def upload(files: list[UploadFile] = File(...), shop_url: str = Form("")):
    if shop_url and not shop_url.startswith("https://www.etsy.com/shop/"):
        raise HTTPException(422, "店铺网址请使用 https://www.etsy.com/shop/ 开头的公开店铺地址。")
    if len(files) > 20:
        raise HTTPException(413, "单次最多上传 20 个 CSV 文件。")
    payloads = []
    try:
        for file in files:
            if not (file.filename or "").lower().endswith(".csv"):
                raise HTTPException(415, f"只支持 CSV 文件：{file.filename or '未命名文件'}")
            data = await file.read(10 * 1024 * 1024 + 1)
            if len(data) > 10 * 1024 * 1024:
                raise HTTPException(413, f"文件不能超过 10 MB：{file.filename}")
            payloads.append((file.filename or "未命名.csv", data))
        return HTMLResponse(render_report(analyze_many(payloads, shop_url)))
    finally:
        for file in files:
            await file.close()
