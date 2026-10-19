"""Read-only Etsy + B2B draft workflow. No external accounts or outgoing actions."""
import argparse
import csv
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import pandas as pd

UNKNOWN="NEEDS_CONFIRMATION"
ALIASES={
 "sku":["sku","listing id","listing_id","商品编号","货号"],
 "title":["title","name","listing_title","商品名称","产品名称","名称"],
 "tags":["tags","tag","关键词","标签"],
 "description":["description","商品描述","描述"],
 "material":["material","materials","材质","材料"],
 "size":["size","dimensions","规格","尺寸"],
 "quantity":["towel quantity","毛巾数量"],
 "lead":["processing days","制作时间","生产周期"],
 "shipping":["shipping days","物流时间","交货期"],
}
SEGMENTS=[
 ("Gift retailers","gift boutique; specialty gift retailer","Owner / Buyer"),
 ("Gift distributors","gift wholesaler; gift distributor","Purchasing Manager"),
 ("Floral gift shops","floral boutique; flower gift shop","Owner / Buyer"),
 ("Wedding suppliers","wedding favor supplier; event gift supplier","Event Buyer"),
 ("Corporate gifting","corporate gifting company; promotional gift supplier","Sourcing Manager"),
]
def parse_tags(value):
 return [t.strip() for t in re.split(r"[,;|，；\n]+",str(value or "")) if t.strip()]
def columns_for(columns):
 found={str(c).strip().lower().replace("_"," "):c for c in columns}
 return {k:next((found[a.lower().replace("_"," ")] for a in aliases if a.lower().replace("_"," ") in found),None) for k,aliases in ALIASES.items()}
def read_tables(path):
 if path.suffix.lower()==".csv":
  last=None
  for encoding in ("utf-8-sig","utf-8","gb18030"):
   try:return [("CSV",pd.read_csv(path,dtype=str,keep_default_na=False,encoding=encoding))]
   except UnicodeError as e:last=e
  raise ValueError(f"cannot decode CSV: {last}")
 return list(pd.read_excel(path,sheet_name=None,dtype=str,keep_default_na=False).items())
def audit(row,mapping,source,sheet,line):
 def val(k):
  c=mapping[k]
  return str(row.get(c,"")).strip() if c is not None else ""
 title=val("title"); tags=parse_tags(val("tags")); issues=[]
 for key in ("title","material","size","quantity","lead","shipping"):
  if not val(key):issues.append(f"{key}: {UNKNOWN}")
 if not val("description"):issues.append("description: NOT_IN_EXPORT_OR_EMPTY; check original listing")
 if not tags:issues.append("tags: NOT_IN_EXPORT_OR_EMPTY")
 else:
  if len(tags)!=13:issues.append(f"tags_count: {len(tags)}")
  long=[t for t in tags if len(t)>20]
  if long:issues.append(f"tags_over_20_chars: {long}")
  repeats=[k for k,c in Counter(t.casefold() for t in tags).items() if c>1]
  if repeats:issues.append(f"duplicate_tags: {repeats}")
  title_words=set(re.findall(r"[a-z]{3,}",title.lower()))-{"with","and","for","gift","handmade"}
  tag_words=set(re.findall(r"[a-z]{3,}"," ".join(tags).lower()))
  if title_words and not title_words.intersection(tag_words):issues.append("title_tag_alignment: REVIEW")
 return {"sku":val("sku") or f"{source}:{sheet}:{line}","title":title or UNKNOWN,
 "source":source,"sheet":sheet,"source_row":line,"material":val("material") or UNKNOWN,
 "dimensions":val("size") or UNKNOWN,"towel_quantity":val("quantity") or UNKNOWN,
 "processing_days":val("lead") or UNKNOWN,"shipping_days":val("shipping") or UNKNOWN,
 "description_available":bool(val("description")),"tags":tags,"issues":issues}
def run(input_dir,output_dir,shop="HoryalfTowelFlowers",max_rows=500):
 input_dir=Path(input_dir);output_dir=Path(output_dir)
 if not input_dir.is_dir():raise ValueError("input directory does not exist")
 if output_dir.resolve()==input_dir.resolve() or input_dir.resolve() in output_dir.resolve().parents:
  raise ValueError("output cannot be inside input")
 files=sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in (".csv",".xlsx",".xls"))
 if not files:raise ValueError("put CSV or Excel product files in data/inbox")
 records=[];skipped=[];processed=[]
 for file in files:
  if file.stat().st_size>20*1024*1024:
   skipped.append({"file":file.name,"reason":"over 20 MB"});continue
  try:
   for sheet,frame in read_tables(file):
    mapping=columns_for(frame.columns)
    if mapping["title"] is None:
     skipped.append({"file":file.name,"sheet":sheet,"reason":"missing title column"});continue
    limit=min(len(frame),max_rows-len(records))
    for line,row in enumerate(frame.head(limit).to_dict(orient="records"),start=2):
     records.append(audit(row,mapping,file.name,sheet,line))
    processed.append({"file":file.name,"sheet":sheet,"rows":limit})
    if len(records)>=max_rows:break
  except Exception as err:
   skipped.append({"file":file.name,"reason":f"parse failure ({type(err).__name__})"})
  if len(records)>=max_rows:break
 if not records:raise ValueError("no supported product rows; check spreadsheet headers")
 date=datetime.now(timezone.utc).strftime("%Y-%m-%d")
 name=re.sub(r"[^A-Za-z0-9_-]+","_",shop)
 folder=output_dir/date/name
 if folder.exists():folder=folder.parent/(name+"_"+datetime.now(timezone.utc).strftime("%H%M%S%f"))
 folder.mkdir(parents=True,exist_ok=False)
 fields=["sku","title","source","sheet","source_row","material","dimensions","towel_quantity",
         "processing_days","shipping_days","description_available","tags","issues"]
 with (folder/"sku_audit.csv").open("w",encoding="utf-8-sig",newline="") as f:
  writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
  for record in records:
   writer.writerow({**record,"tags":" | ".join(record["tags"]),"issues":" | ".join(record["issues"])})
 with (folder/"buyer_segments.csv").open("w",encoding="utf-8-sig",newline="") as f:
  writer=csv.writer(f);writer.writerow(["buyer_segment","search_terms","role","status"])
  for segment,terms,role in SEGMENTS:writer.writerow([segment,terms,role,"DRAFT_ONLY"])
 (folder/"outreach_drafts.md").write_text(
  f"""# {shop} — Unsent B2B draft
Verify company details, MOQ, lead times and product facts before use.

**Subject:** A different flower gift for your store

Hi {{first_name}},

I came across {{company_name}} and thought our hand-folded towel flower bouquets
and gift-ready arrangements might be a fit for your shop. They look like flower
gifts, but the towels can be unfolded and used.

Would you be interested in reviewing a short product catalog?

Best,
{{verified_sender_name}}
{shop}
{{verified_contact_details}}

If this isn't relevant, please let me know and I won't follow up.

**Not sent.** Do not invent buyers, certifications, prices, samples or delivery promises.
""",encoding="utf-8")
 report={"shop":shop,"products_reviewed":len(records),
 "findings_count":sum(len(x["issues"]) for x in records),"processed":processed,"skipped":skipped,
 "outbound_actions":0,"status":"REVIEW_REQUIRED","created_at_utc":datetime.now(timezone.utc).isoformat()}
 (folder/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 return folder,report
def main(argv=None):
 p=argparse.ArgumentParser(description="Read-only Etsy operations audit")
 p.add_argument("--input",default="data/inbox");p.add_argument("--output",default="output")
 p.add_argument("--shop",default="HoryalfTowelFlowers");p.add_argument("--max-rows",type=int,default=500)
 args=p.parse_args(argv)
 if not 1<=args.max_rows<=5000:p.error("max-rows must be 1..5000")
 try:folder,report=run(args.input,args.output,args.shop,args.max_rows)
 except (ValueError,OSError) as err:
  print(f"ERROR: {err}",file=sys.stderr);return 1
 print(json.dumps({"folder":str(folder),**report},ensure_ascii=False,indent=2))
 return 0
if __name__=="__main__":raise SystemExit(main())
