"""LeadPilot B2B desktop companion. Local-only drafts, no unofficial login/API calls."""
import csv
import io
import os
import shutil
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

OFFICIAL_URL = "https://gopluxa.com/"
MAX_IMPORT_MB = 8
COLUMNS = ["Company","Country","Contact","Email","Segment","Status","Notes"]
SEGMENTS = {
    "Gift boutiques": {
        "keywords": "gift boutique, independent gift shop, specialty gift retailer",
        "role": "Owner / Buyer",
        "angle": "gift-ready towel flower bouquets for independent gift shops"
    },
    "Gift wholesalers": {
        "keywords": "gift wholesaler, gift distributor, wholesale gift supplier",
        "role": "Purchasing Manager / Category Manager",
        "angle": "towel bouquet collections for wholesale gift catalogs"
    },
    "Florists": {
        "keywords": "floral boutique, flower gift shop, florist gift shop",
        "role": "Owner / Buyer",
        "angle": "non-fresh flower gift alternatives with usable towels"
    },
    "Wedding & events": {
        "keywords": "wedding favor supplier, wedding gift supplier, event gift supplier",
        "role": "Event Buyer / Owner",
        "angle": "hand-folded towel gifts for events and wedding favors"
    },
    "Corporate gifting": {
        "keywords": "corporate gifting company, promotional gifts supplier, employee gift supplier",
        "role": "Sourcing Manager / Product Manager",
        "angle": "practical gift-ready towel bouquets for corporate gifting"
    },
    "Baby gift retailers": {
        "keywords": "baby gift boutique, baby shower gift shop, newborn gift retailer",
        "role": "Buyer / Store Owner",
        "angle": "selected towel gift arrangements for new baby gifting"
    },
}
FOLLOWUPS = [
    ("Initial outreach", 0),
    ("First follow-up", 5),
    ("Final follow-up", 12),
]
def draft(segment, first_name="{first_name}", company="{company_name}"):
    angle = SEGMENTS[segment]["angle"]
    return (
      "Subject: A different gift idea for your store\n\n"
      f"Hi {first_name},\n\n"
      f"I came across {company} and thought our {angle} might be worth a look.\n\n"
      "We create decorative flower bouquets and gift boxes by carefully folding real towels. "
      "They look like flowers, but the towels can also be unfolded and used.\n\n"
      "Would you be interested in seeing a short product catalog and discussing wholesale options?\n\n"
      "Best regards,\nHoryalfTowelFlowers\n"
      "https://www.etsy.com/shop/HoryalfTowelFlowers\n\n"
      "If this isn't relevant, please let me know and I won't follow up."
    )
def validate_email(email):
    email=email.strip()
    return not email or ("@" in email and "." in email.rsplit("@",1)[-1] and "\n" not in email)
def normalize_rows(text):
    reader=csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV must have a header row")
    lookup={str(c).strip().lower():c for c in reader.fieldnames}
    aliases={
        "Company":["company","company name","企业","公司"],
        "Country":["country","国家"],
        "Contact":["contact","contact name","name","联系人"],
        "Email":["email","邮箱"],
        "Segment":["segment","buyer segment","客户类型"],
        "Status":["status","阶段"],
        "Notes":["notes","备注"],
    }
    if not any(a in lookup for a in aliases["Company"]):
        raise ValueError("CSV must include a Company (公司) column")
    rows=[]
    for index,row in enumerate(reader,2):
        converted={key:next((str(row.get(lookup[a],"") or "").strip() for a in names if a in lookup),"")
                   for key,names in aliases.items()}
        if not converted["Company"]:continue
        if not validate_email(converted["Email"]):
            converted["Notes"]=(converted["Notes"]+" | Email needs review").strip(" |")
        converted["Status"]=converted["Status"] or "New"
        rows.append(converted)
        if len(rows)>5000:raise ValueError("Maximum import is 5,000 companies")
    return rows
def csv_bytes(rows):
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=COLUMNS)
    writer.writeheader()
    for row in rows:writer.writerow({k:row.get(k,"") for k in COLUMNS})
    return out.getvalue().encode("utf-8-sig")
def app_data_dir():
    base=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))
    path=base/"HoryalfLeadPilot"
    path.mkdir(parents=True,exist_ok=True)
    return path
def open_leadpilot():
    """Prefer user's existing installed shortcut. Otherwise open the real vendor site."""
    bases=[Path(os.environ.get("APPDATA",""))/"Microsoft/Windows/Start Menu/Programs",
           Path(os.environ.get("PROGRAMDATA",""))/"Microsoft/Windows/Start Menu/Programs"]
    if sys.platform=="win32":
        for base in bases:
            if base.is_dir():
                try:
                    for shortcut in base.rglob("LeadPilot*.lnk"):
                        os.startfile(str(shortcut))
                        return "installed"
                except OSError:
                    pass
    webbrowser.open(OFFICIAL_URL)
    return "browser"
class Dashboard:
    def __init__(self,root):
        self.root=root
        self.root.title("Horyalf | LeadPilot B2B 工作台")
        self.root.geometry("1040x720")
        self.root.minsize(860,620)
        self.rows=[]
        self.path=app_data_dir()/"prospects.csv"
        self.load()
        outer=ttk.Frame(root,padding=18);outer.pack(fill="both",expand=True)
        ttk.Label(outer,text="Horyalf | LeadPilot B2B 客户开发工作台",
                  font=("Microsoft YaHei UI",18,"bold")).pack(anchor="w")
        ttk.Label(outer,text="本地辅助工具 · 登录保留在 LeadPilot 官方客户端/浏览器 · 不会自动购买线索或发送邮件",
                  foreground="#555").pack(anchor="w",pady=(2,12))
        bar=ttk.Frame(outer);bar.pack(fill="x",pady=8)
        ttk.Button(bar,text="① 打开 LeadPilot 账号",command=self.launch).pack(side="left",padx=(0,10))
        ttk.Button(bar,text="② 导入线索 CSV",command=self.import_csv).pack(side="left",padx=(0,10))
        ttk.Button(bar,text="③ 导出本地线索",command=self.export_csv).pack(side="left",padx=(0,10))
        ttk.Button(bar,text="打开 LeadPilot 官网",command=lambda:webbrowser.open(OFFICIAL_URL)).pack(side="left")
        tabs=ttk.Notebook(outer);tabs.pack(fill="both",expand=True,pady=(10,0))
        search=ttk.Frame(tabs,padding=12);tabs.add(search,text="找客户")
        emails=ttk.Frame(tabs,padding=12);tabs.add(emails,text="开发邮件")
        leads=ttk.Frame(tabs,padding=12);tabs.add(leads,text="本地线索")
        helpframe=ttk.Frame(tabs,padding=12);tabs.add(helpframe,text="工作流程")
        self.segment=tk.StringVar(value="Gift boutiques")
        ttk.Label(search,text="选择采购商类型：").pack(anchor="w")
        ttk.Combobox(search,textvariable=self.segment,values=list(SEGMENTS),state="readonly",width=35).pack(anchor="w",pady=(4,12))
        ttk.Button(search,text="生成关键词与筛选条件",command=self.show_search).pack(anchor="w")
        self.search_text=tk.Text(search,height=14,wrap="word",font=("Consolas",11))
        self.search_text.pack(fill="both",expand=True,pady=10)
        ttk.Button(search,text="复制搜索方案",command=lambda:self.copy(self.search_text.get("1.0","end").strip())).pack(anchor="e")
        ttk.Label(emails,text="按采购商类型生成英文首封邮件：").pack(anchor="w")
        email_bar=ttk.Frame(emails);email_bar.pack(fill="x",pady=8)
        ttk.Button(email_bar,text="生成邮件草稿",command=self.show_draft).pack(side="left")
        ttk.Button(email_bar,text="复制邮件",command=lambda:self.copy(self.mail_text.get("1.0","end").strip())).pack(side="left",padx=8)
        self.mail_text=tk.Text(emails,wrap="word",font=("Consolas",11))
        self.mail_text.pack(fill="both",expand=True,pady=10)
        ttk.Label(emails,text="邮件须人工核对客户匹配度、发送主体和退订方式；此工具不会替你发送。",foreground="#555").pack(anchor="w")
        self.table=ttk.Treeview(leads,columns=COLUMNS,show="headings",height=12)
        for col in COLUMNS:
            self.table.heading(col,text=col)
            self.table.column(col,width=125 if col not in ("Company","Notes") else 180)
        self.table.pack(fill="both",expand=True)
        editbar=ttk.Frame(leads);editbar.pack(fill="x",pady=8)
        ttk.Button(editbar,text="标为已联系",command=lambda:self.mark("Contacted")).pack(side="left",padx=4)
        ttk.Button(editbar,text="标为有意向",command=lambda:self.mark("Interested")).pack(side="left",padx=4)
        ttk.Button(editbar,text="标为不再联系",command=lambda:self.mark("Do not contact")).pack(side="left",padx=4)
        ttk.Label(helpframe,text=(
          "推荐操作顺序：\n\n"
          "1. 点击“打开 LeadPilot 账号”。若已安装客户端，优先打开客户端；否则进入官网。\n"
          "2. 在 LeadPilot 官方登录页面由你本人登录。工具不读取密码和 Cookie。\n"
          "3. 选择采购商类型，复制 2–3 个关键词到 LeadPilot 的线索雷达。\n"
          "4. 搜索时先选美国、Buyer/Owner，先找 5–10 家企业；不自动扣费。\n"
          "5. 审核公司网站和业务匹配度后，再决定是否获取已验证联系人。\n"
          "6. 使用 LeadPilot 导出线索 CSV，并在本地工作台中导入整理。\n"
          "7. 在开发邮件页面生成草稿，核对个性化内容，再手工批准发送。\n"
          "8. 记录有意向、已联系、不再联系，尊重退订请求。\n\n"
          "说明：LeadPilot 官方文档未提供可用的公开 API 契约；本版本不模拟登录，\n"
          "不抓取账户私有页面，也不绕过登录验证。真正双向同步需要官方 API 或明确授权接口。"
        ),justify="left",font=("Microsoft YaHei UI",11)).pack(anchor="nw",pady=12)
        self.show_search();self.show_draft();self.refresh()
    def launch(self):
        result=open_leadpilot()
        messagebox.showinfo("LeadPilot","已尝试打开"+("本机 LeadPilot 客户端" if result=="installed" else "LeadPilot 官方网站")+
          "。如未登录，请在官方页面登录一次。")
    def show_search(self):
        s=SEGMENTS[self.segment.get()]
        text=("采购商类型: "+self.segment.get()+"\n搜索词: "+s["keywords"]+"\n联系人职位: "+s["role"]+
          "\n国家: United States (first pilot)\n数量: 5–10 leads\n处理方式: 只找线索 / 人工审核"+
          "\nWhatsApp 验证: 关闭\n邮件方式: 草稿待审\n\n可在 LeadPilot 线索雷达中分别测试各关键词。")
        self.search_text.delete("1.0","end");self.search_text.insert("1.0",text)
    def show_draft(self):
        self.mail_text.delete("1.0","end");self.mail_text.insert("1.0",draft(self.segment.get()))
    def copy(self,text):
        self.root.clipboard_clear();self.root.clipboard_append(text)
        self.root.update()
        messagebox.showinfo("已复制","内容已复制到剪贴板。")
    def load(self):
        if self.path.exists():
            try:self.rows=normalize_rows(self.path.read_text(encoding="utf-8-sig"))
            except (ValueError,UnicodeError,OSError):self.rows=[]
    def save(self):
        self.path.write_bytes(csv_bytes(self.rows))
    def import_csv(self):
        file=filedialog.askopenfilename(title="选择 LeadPilot 导出的 CSV",filetypes=[("CSV files","*.csv")])
        if not file:return
        path=Path(file)
        if path.stat().st_size>MAX_IMPORT_MB*1024*1024:
            messagebox.showerror("文件过大","单次 CSV 最大 8 MB");return
        try:
            raw=path.read_bytes()
            try:body=raw.decode("utf-8-sig")
            except UnicodeError:body=raw.decode("gb18030")
            incoming=normalize_rows(body)
        except (ValueError,UnicodeError,OSError) as e:
            messagebox.showerror("导入失败",str(e));return
        keys={(r["Company"].casefold(),r["Email"].casefold()) for r in self.rows}
        added=0
        for row in incoming:
            key=(row["Company"].casefold(),row["Email"].casefold())
            if key not in keys:self.rows.append(row);keys.add(key);added+=1
        self.save();self.refresh()
        messagebox.showinfo("导入完成",f"新增 {added} 条，跳过重复 {len(incoming)-added} 条")
    def export_csv(self):
        dest=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV files","*.csv")],
                                          initialfile="leadpilot_prospects.csv")
        if dest:Path(dest).write_bytes(csv_bytes(self.rows))
    def refresh(self):
        for item in self.table.get_children():self.table.delete(item)
        for i,row in enumerate(self.rows):
            self.table.insert("",tk.END,iid=str(i),values=[row.get(k,"") for k in COLUMNS])
    def mark(self,status):
        for iid in self.table.selection():
            self.rows[int(iid)]["Status"]=status
        self.save();self.refresh()
def main():
    root=tk.Tk()
    try:ttk.Style().theme_use("clam")
    except tk.TclError:pass
    Dashboard(root)
    root.mainloop()
if __name__=="__main__":main()
