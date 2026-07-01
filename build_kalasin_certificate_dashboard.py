import html
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT_FOLDER_ID = "1nWJa_JXYKz-sbqtKktMy1JBpXJMxiVv8"
OUTPUT_HTML = Path("index.html")
SNAPSHOT_JSON = Path("kalasin-certificate-dashboard-data.json")

DISTRICT_ORDER = [
    "อำเภอเมืองกาฬสินธุ์",
    "อำเภอนามน",
    "อำเภอกมลาไสย",
    "อำเภอร่องคำ",
    "อำเภอกุฉินารายณ์",
    "อำเภอเขาวง",
    "อำเภอยางตลาด",
    "อำเภอห้วยเม็ก",
    "อำเภอสหัสขันธ์",
    "อำเภอคำม่วง",
    "อำเภอท่าคันโท",
    "อำเภอหนองกุงศรี",
    "อำเภอสมเด็จ",
    "อำเภอห้วยผึ้ง",
    "อำเภอสามชัย",
    "อำเภอนาคู",
    "อำเภอดอนจาน",
    "อำเภอฆ้องชัย",
]

EXCLUDED_UNITS = {
    ("อำเภอเมืองกาฬสินธุ์", "โรงพยาบาลกาฬสินธุ์ ธนบุรี"),
    ("อำเภอเมืองกาฬสินธุ์", "โรงพยาบาลธีรวัฒน์"),
}


def drive_folder_url(folder_id):
    return f"https://drive.google.com/drive/folders/{folder_id}"


def drive_file_url(file_id):
    return f"https://drive.google.com/file/d/{file_id}/view"


def clean_text(value):
    value = re.sub(r"<.*?>", "", value, flags=re.S)
    value = html.unescape(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def fetch_folder_items(folder_id):
    req = urllib.request.Request(
        drive_folder_url(folder_id),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    page = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", errors="replace")
    rows = re.findall(r'<tr\s+data-selectable\s+data-id="([^"]+)"(.*?)</tr>', page, flags=re.S)
    items = []
    for file_id, body in rows:
        name_match = re.search(r'<strong class="DNoYtb">(.*?)</strong>', body, flags=re.S)
        if not name_match:
            continue

        label_match = re.search(r'aria-label="([^"]+)"', body)
        label = html.unescape(label_match.group(1)) if label_match else ""
        modified_match = re.search(r'aria-label="Modified ([^"]+)"', body)
        is_folder = "folder" in label.lower()
        name = clean_text(name_match.group(1))

        items.append(
            {
                "id": file_id,
                "name": name,
                "is_folder": is_folder,
                "modified": modified_match.group(1) if modified_match else "",
                "url": drive_folder_url(file_id) if is_folder else drive_file_url(file_id),
            }
        )
    return items


def district_sort_key(name):
    try:
        return (0, DISTRICT_ORDER.index(name))
    except ValueError:
        return (1, name)


def collect_unit_status(unit):
    try:
        children = fetch_folder_items(unit["id"])
        files = [item for item in children if not item["is_folder"]]
        folders = [item for item in children if item["is_folder"]]

        # A certificate is expected as a direct upload, but look one level deeper
        # so a nested upload folder still counts in the dashboard.
        nested_files = []
        if not files and folders:
            for folder in folders:
                for item in fetch_folder_items(folder["id"]):
                    if not item["is_folder"]:
                        nested = dict(item)
                        nested["name"] = f'{folder["name"]} / {item["name"]}'
                        nested_files.append(nested)

        uploaded_files = files or nested_files
        return {
            **unit,
            "uploaded": bool(uploaded_files),
            "file_count": len(uploaded_files),
            "files": uploaded_files,
            "child_folder_count": len(folders),
            "error": "",
        }
    except Exception as exc:
        return {
            **unit,
            "uploaded": False,
            "file_count": 0,
            "files": [],
            "child_folder_count": 0,
            "error": str(exc),
        }


def build_snapshot():
    districts = sorted(fetch_folder_items(ROOT_FOLDER_ID), key=lambda item: district_sort_key(item["name"]))
    units = []
    for district in districts:
        district_units = fetch_folder_items(district["id"])
        for unit in district_units:
            if (district["name"], unit["name"]) in EXCLUDED_UNITS:
                continue
            units.append(
                {
                    "id": unit["id"],
                    "name": unit["name"],
                    "district": district["name"],
                    "folder_url": unit["url"],
                    "folder_modified": unit["modified"],
                }
            )

    statuses = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(collect_unit_status, unit) for unit in units]
        for future in as_completed(futures):
            statuses.append(future.result())

    statuses.sort(key=lambda item: (district_sort_key(item["district"]), item["name"]))
    now = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "source": drive_folder_url(ROOT_FOLDER_ID),
        "updated_at": now,
        "districts": [item["name"] for item in districts],
        "units": statuses,
    }


def render_html(snapshot):
    data_json = json.dumps(snapshot, ensure_ascii=False)
    safe_updated = html.escape(snapshot["updated_at"])
    total = len(snapshot["units"])
    uploaded = sum(1 for item in snapshot["units"] if item["uploaded"])
    pending = total - uploaded
    percent = round((uploaded / total) * 100, 1) if total else 0

    return f"""<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard อัปโหลดใบประกาศ จังหวัดกาฬสินธุ์ เพื่อประกอบการตรวจราชการรอบที่ 2/2569</title>
  <style>
    :root {{
      --ink: #18202a;
      --muted: #667085;
      --line: #d8dee8;
      --panel: #ffffff;
      --page: #f6f8fb;
      --green: #16803c;
      --green-bg: #e8f6ee;
      --red: #b42318;
      --red-bg: #fff0ee;
      --gold: #8a5a00;
      --blue: #155eef;
      --blue-bg: #eef4ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--page);
      font-family: Arial, Tahoma, sans-serif;
      line-height: 1.55;
    }}
    header {{
      background: #ffffff;
      border-bottom: 1px solid var(--line);
      padding: 24px clamp(16px, 4vw, 40px);
    }}
    .header-layout {{
      display: grid;
      gap: 16px;
      justify-items: center;
      text-align: center;
    }}
    main {{
      width: min(1320px, 100%);
      margin: 0 auto;
      padding: 22px clamp(14px, 3vw, 28px) 44px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: clamp(24px, 3vw, 36px);
      letter-spacing: 0;
    }}
    .subhead {{
      color: var(--muted);
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 8px 18px;
      font-size: 14px;
    }}
    .upload-cta {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 56px;
      padding: 14px 28px;
      border-radius: 8px;
      background: #155eef;
      color: #ffffff;
      font-size: 17px;
      font-weight: 700;
      box-shadow: 0 14px 30px rgba(21, 94, 239, 0.28);
      text-decoration: none;
      white-space: nowrap;
    }}
    .upload-cta:hover {{
      background: #0f49bd;
      text-decoration: none;
    }}
    .upload-cta:focus-visible {{
      outline: 3px solid #9bb7ff;
      outline-offset: 3px;
    }}
    .upload-notice {{
      max-width: 760px;
      border: 2px solid #a7f3d0;
      background: #ecfdf3;
      color: #05603a;
      border-radius: 8px;
      padding: 14px 18px;
      box-shadow: 0 10px 24px rgba(5, 96, 58, 0.12);
    }}
    .upload-notice span {{
      display: block;
      font-size: clamp(20px, 2.4vw, 28px);
      font-weight: 700;
      color: #067647;
    }}
    .instruction-panel {{
      margin: 18px 0;
      border: 1px solid #bfdbfe;
      background: #eff6ff;
      border-radius: 8px;
      padding: 16px 18px;
      color: #17375e;
    }}
    .instruction-panel h2 {{
      margin: 0 0 8px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    .instruction-panel ol {{
      margin: 0;
      padding-left: 22px;
    }}
    .instruction-panel li {{
      margin: 4px 0;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}
    .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      min-height: 104px;
    }}
    .metric span {{
      color: var(--muted);
      display: block;
      font-size: 13px;
    }}
    .metric strong {{
      display: block;
      margin-top: 8px;
      font-size: 30px;
      line-height: 1.1;
    }}
    .metric.total {{
      border-color: #bfdbfe;
      background: #eff6ff;
    }}
    .metric.done {{
      border-color: #bbf7d0;
      background: #f0fdf4;
    }}
    .metric.todo {{
      border-color: #fecaca;
      background: #fff1f2;
    }}
    .metric.progress-card {{
      border-color: #fde68a;
      background: #fffbeb;
    }}
    .metric.updated {{
      border-color: #9bb7ff;
      background: var(--blue-bg);
    }}
    .metric.updated strong {{
      font-size: 20px;
      line-height: 1.25;
    }}
    .updated-line {{
      white-space: nowrap;
    }}
    .toolbar {{
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 10px;
      align-items: center;
      margin: 18px 0;
    }}
    .status-buttons {{
      display: inline-grid;
      grid-template-columns: repeat(3, auto);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }}
    .status-button {{
      border: 0;
      border-right: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      min-height: 43px;
      padding: 0 12px;
      font: inherit;
      cursor: pointer;
      white-space: nowrap;
    }}
    .status-button:last-child {{
      border-right: 0;
    }}
    .status-button.active {{
      background: #155eef;
      color: #fff;
      font-weight: 700;
    }}
    .district-overview {{
      margin: 18px 0;
    }}
    .section-title {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin: 0 0 10px;
    }}
    .section-title h2 {{
      margin: 0;
      font-size: 18px;
      letter-spacing: 0;
    }}
    .section-title span {{
      color: var(--muted);
      font-size: 13px;
      text-align: right;
    }}
    .district-summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
    }}
    .district-card {{
      width: 100%;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      padding: 12px;
      color: var(--ink);
      text-align: left;
      font: inherit;
      cursor: pointer;
    }}
    .district-card.zero {{
      border-color: #fecaca;
      background: #fff7f7;
    }}
    .district-card.complete {{
      border-color: #bbf7d0;
      background: #f0fdf4;
    }}
    .district-card:hover {{
      border-color: #9bb7ff;
      background: var(--blue-bg);
    }}
    .district-card strong {{
      display: block;
      font-size: 15px;
      line-height: 1.35;
    }}
    .district-card span {{
      color: var(--muted);
      display: block;
      font-size: 13px;
      margin-top: 5px;
    }}
    .mini-progress {{
      height: 11px;
      margin-top: 10px;
      background: #e9edf4;
      border-radius: 999px;
      overflow: hidden;
    }}
    .mini-progress > div {{
      height: 100%;
      background: var(--green);
    }}
    .district-pct {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-top: 9px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}
    .zero-panel {{
      margin: 14px 0 18px;
      border: 1px solid #fecaca;
      background: #fff7f7;
      border-radius: 8px;
      padding: 14px 16px;
    }}
    .zero-panel h2 {{
      margin: 0 0 8px;
      font-size: 18px;
      letter-spacing: 0;
      color: #9f1239;
    }}
    .zero-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .zero-chip {{
      border: 1px solid #fecaca;
      background: #fff;
      color: #9f1239;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 13px;
      font-weight: 700;
    }}
    input, select {{
      width: 100%;
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 8px;
      padding: 11px 12px;
      color: var(--ink);
      font: inherit;
    }}
    select {{ min-width: 180px; }}
    .district {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin: 14px 0;
      overflow: hidden;
    }}
    .district-head {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }}
    .district h2 {{
      margin: 0;
      font-size: 18px;
      letter-spacing: 0;
    }}
    .district-meta {{
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    th, td {{
      border-bottom: 1px solid #eef1f6;
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }}
    th {{
      color: var(--muted);
      background: #fff;
      font-size: 12px;
      font-weight: 700;
      position: sticky;
      top: 0;
      z-index: 2;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    .unit-col {{ width: 32%; }}
    .upload-col {{ width: 150px; }}
    .status-col {{ width: 140px; }}
    .file-col {{ width: 32%; }}
    .time-col {{ width: 120px; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 7px;
      border-radius: 999px;
      padding: 6px 12px;
      font-size: 14px;
      font-weight: 800;
      white-space: nowrap;
    }}
    .badge::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: currentColor;
    }}
    .row-upload {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 34px;
      padding: 7px 11px;
      border-radius: 8px;
      background: #155eef;
      color: #ffffff;
      font-size: 13px;
      font-weight: 700;
      text-decoration: none;
      white-space: nowrap;
    }}
    .row-upload:hover {{
      background: #0f49bd;
      text-decoration: none;
    }}
    .row-upload.uploaded-link {{
      background: #e7eefb;
      color: #52709d;
      box-shadow: none;
    }}
    .row-upload.uploaded-link:hover {{
      background: #dbe7f7;
      color: #36577e;
    }}
    .uploaded {{ color: #05603a; background: #dcfae6; border: 1px solid #86efac; }}
    .pending {{ color: #b42318; background: #ffe4e0; border: 1px solid #fda29b; }}
    .error {{ color: var(--gold); background: #fff7df; }}
    a {{ color: var(--blue); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .file-list {{
      display: grid;
      gap: 4px;
    }}
    .empty {{
      color: var(--muted);
    }}
    .progress {{
      height: 10px;
      background: #e9edf4;
      border-radius: 999px;
      overflow: hidden;
      margin-top: 14px;
    }}
    .progress > div {{
      width: {percent}%;
      height: 100%;
      background: linear-gradient(90deg, #16803c, #155eef);
    }}
    .hidden {{ display: none; }}
    @media (max-width: 820px) {{
      .upload-cta {{ width: 100%; }}
      .summary {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .toolbar {{ grid-template-columns: 1fr; }}
      .status-buttons {{ grid-template-columns: 1fr; }}
      .status-button {{ border-right: 0; border-bottom: 1px solid var(--line); }}
      .status-button:last-child {{ border-bottom: 0; }}
      .section-title {{ display: block; }}
      .section-title span {{ display: block; text-align: left; margin-top: 3px; }}
      table, thead, tbody, tr, th, td {{ display: block; }}
      thead {{ display: none; }}
      th {{ position: static; }}
      tr {{ border-bottom: 1px solid #eef1f6; padding: 8px 0; }}
      tr:last-child {{ border-bottom: 0; }}
      td {{ border-bottom: 0; padding: 6px 12px; }}
      td::before {{
        content: attr(data-label);
        display: block;
        color: var(--muted);
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 2px;
      }}
      .district-head {{ grid-template-columns: 1fr; }}
      .district-meta {{ white-space: normal; }}
    }}
    @media (max-width: 520px) {{
      .summary {{ grid-template-columns: 1fr; }}
      header {{ padding-top: 18px; }}
      .metric strong {{ font-size: 26px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-layout">
      <div>
        <h1>Dashboard อัปโหลดใบประกาศ จังหวัดกาฬสินธุ์ เพื่อประกอบการตรวจราชการรอบที่ 2/2569</h1>
        <div class="subhead">
          <span>ข้อมูลจาก Google Drive</span>
          <span>อัปเดตล่าสุด: {safe_updated} น.</span>
        </div>
      </div>
      <a class="upload-cta" href="{html.escape(snapshot["source"])}" target="_blank" rel="noopener">อัพโหลดใบประกาศ</a>
      <div class="upload-notice" role="status">
        <span>ระบบ Dashboard จะอัปเดตข้อมูลทุก ๆ 30 นาที</span>
      </div>
    </div>
  </header>
  <main>
    <section class="instruction-panel" aria-label="คำแนะนำการอัปโหลด">
      <h2>คำแนะนำการอัปโหลดใบประกาศ</h2>
      <ol>
        <li>ค้นหาหรือเลือกอำเภอของหน่วยบริการ</li>
        <li>ตั้งชื่อใบประกาศ เช่น <strong>ชื่อ-สกุล หน่วยบริการ</strong></li>
        <li>กดปุ่ม <strong>อัพโหลดใบประกาศ</strong> ในแถวของหน่วยบริการตนเอง</li>
        <li>อัปโหลดไฟล์ลงใน Google Drive folder ที่เปิดขึ้นมาโดยตรง</li>
        <li>หลังอัปโหลดแล้ว Dashboard จะปรับสถานะในการอัปเดตรอบถัดไป ภายในประมาณ 30 นาที</li>
      </ol>
    </section>

    <section class="summary" aria-label="สรุปภาพรวม">
      <div class="metric total"><span>หน่วยบริการทั้งหมด</span><strong id="totalMetric">{total}</strong></div>
      <div class="metric done"><span>อัปโหลดแล้ว</span><strong id="uploadedMetric">{uploaded}</strong></div>
      <div class="metric todo"><span>ยังไม่อัปโหลด</span><strong id="pendingMetric">{pending}</strong></div>
      <div class="metric progress-card"><span>ความคืบหน้า</span><strong id="percentMetric">{percent}%</strong><div class="progress"><div id="progressBar"></div></div></div>
      <div class="metric updated"><span>อัปเดตล่าสุด</span><strong class="updated-line">{safe_updated} น.</strong></div>
    </section>

    <section class="district-overview" aria-label="สรุปรายอำเภอ">
      <div class="section-title">
        <h2>สรุปรายอำเภอ</h2>
        <span>จำนวนหน่วยบริการที่อัปโหลดแล้ว / หน่วยบริการทั้งหมด</span>
      </div>
      <div id="districtSummary" class="district-summary"></div>
    </section>

    <section id="zeroPanel" class="zero-panel" aria-label="อำเภอที่ยังไม่มีการอัปโหลด"></section>

    <section class="toolbar" aria-label="ตัวกรอง">
      <input id="searchInput" type="search" placeholder="ค้นหาหน่วยบริการหรือชื่อไฟล์">
      <select id="districtFilter"><option value="all">ทุกอำเภอ</option></select>
      <div class="status-buttons" role="group" aria-label="ตัวกรองสถานะ">
        <button class="status-button active" type="button" data-status="all">ทั้งหมด</button>
        <button class="status-button" type="button" data-status="uploaded">อัปโหลดแล้ว</button>
        <button class="status-button" type="button" data-status="pending">ยังไม่อัปโหลด</button>
      </div>
    </section>

    <section id="districts"></section>
  </main>

  <script>
    const snapshot = {data_json};
    const districtOrder = {json.dumps(DISTRICT_ORDER, ensure_ascii=False)};
    const units = snapshot.units;

    const districtFilter = document.getElementById("districtFilter");
    const statusFilter = document.getElementById("statusFilter");
    const searchInput = document.getElementById("searchInput");
    const districtsEl = document.getElementById("districts");
    const districtSummaryEl = document.getElementById("districtSummary");
    const zeroPanelEl = document.getElementById("zeroPanel");
    const statusButtons = [...document.querySelectorAll(".status-button")];
    let selectedStatus = "all";

    for (const district of snapshot.districts) {{
      const option = document.createElement("option");
      option.value = district;
      option.textContent = district;
      districtFilter.appendChild(option);
    }}

    function fileLinks(unit) {{
      if (!unit.files.length) return '<span class="empty">ไม่มีไฟล์ในโฟลเดอร์</span>';
      return `<div class="file-list">${{unit.files.map(file => `<a href="${{file.url}}" target="_blank" rel="noopener">${{escapeHtml(file.name)}}</a>`).join("")}}</div>`;
    }}

    function escapeHtml(value) {{
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }}

    function statusBadge(unit) {{
      if (unit.error) return '<span class="badge error">ตรวจไม่ได้</span>';
      return unit.uploaded
        ? '<span class="badge uploaded">อัปโหลดแล้ว</span>'
        : '<span class="badge pending">ยังไม่อัปโหลด</span>';
    }}

    function uploadLinkClass(unit) {{
      return unit.uploaded ? "row-upload uploaded-link" : "row-upload";
    }}

    function allUnitsForDistrict(district) {{
      return units.filter(unit => unit.district === district);
    }}

    function renderDistrictSummary() {{
      districtSummaryEl.innerHTML = snapshot.districts.map(district => {{
        const rows = allUnitsForDistrict(district);
        const done = rows.filter(unit => unit.uploaded).length;
        const total = rows.length;
        const pct = total ? Math.round((done / total) * 1000) / 10 : 0;
        const stateClass = done === 0 ? "zero" : done === total ? "complete" : "";
        return `
          <button class="district-card ${{stateClass}}" type="button" data-district="${{escapeHtml(district)}}" aria-label="${{escapeHtml(district)}} อัปโหลดแล้ว ${{done}} จาก ${{total}}">
            <strong>${{escapeHtml(district)}}</strong>
            <span>อัปโหลดแล้ว ${{done}} / ${{total}}</span>
            <div class="district-pct"><span>${{pct}}%</span><span>${{total - done}} ต้องติดตาม</span></div>
            <div class="mini-progress" aria-hidden="true"><div style="width: ${{pct}}%"></div></div>
          </button>
        `;
      }}).join("");

      for (const card of districtSummaryEl.querySelectorAll(".district-card")) {{
        card.addEventListener("click", () => {{
          districtFilter.value = card.dataset.district;
          render();
          document.querySelector(".toolbar").scrollIntoView({{ behavior: "smooth", block: "start" }});
        }});
      }}
    }}

    function renderZeroPanel() {{
      const zeroDistricts = snapshot.districts.filter(district => {{
        const rows = allUnitsForDistrict(district);
        return rows.length > 0 && rows.every(unit => !unit.uploaded);
      }});
      zeroPanelEl.innerHTML = zeroDistricts.length
        ? `<h2>อำเภอที่ยัง 0%</h2><div class="zero-list">${{zeroDistricts.map(district => `<button class="zero-chip" type="button" data-district="${{escapeHtml(district)}}">${{escapeHtml(district)}}</button>`).join("")}}</div>`
        : `<h2>ไม่มีอำเภอที่ยัง 0%</h2><div class="zero-list"><span class="zero-chip">ทุกอำเภอมีการอัปโหลดแล้ว</span></div>`;
      for (const chip of zeroPanelEl.querySelectorAll("[data-district]")) {{
        chip.addEventListener("click", () => {{
          districtFilter.value = chip.dataset.district;
          render();
          document.querySelector(".toolbar").scrollIntoView({{ behavior: "smooth", block: "start" }});
        }});
      }}
    }}

    function matches(unit, query, district, status) {{
      const haystack = [unit.name, unit.district, ...unit.files.map(file => file.name)].join(" ").toLowerCase();
      const byQuery = !query || haystack.includes(query);
      const byDistrict = district === "all" || unit.district === district;
      const byStatus = status === "all" || (status === "uploaded" ? unit.uploaded : !unit.uploaded);
      return byQuery && byDistrict && byStatus;
    }}

    function render() {{
      const query = searchInput.value.trim().toLowerCase();
      const selectedDistrict = districtFilter.value;
      const filtered = units.filter(unit => matches(unit, query, selectedDistrict, selectedStatus));

      const uploaded = filtered.filter(unit => unit.uploaded).length;
      const pending = filtered.length - uploaded;
      const percent = filtered.length ? Math.round((uploaded / filtered.length) * 1000) / 10 : 0;
      document.getElementById("totalMetric").textContent = filtered.length;
      document.getElementById("uploadedMetric").textContent = uploaded;
      document.getElementById("pendingMetric").textContent = pending;
      document.getElementById("percentMetric").textContent = `${{percent}}%`;
      document.getElementById("progressBar").style.width = `${{percent}}%`;

      const byDistrict = new Map();
      for (const unit of filtered) {{
        if (!byDistrict.has(unit.district)) byDistrict.set(unit.district, []);
        byDistrict.get(unit.district).push(unit);
      }}

      const districts = [...byDistrict.keys()].sort((a, b) => {{
        const ai = districtOrder.indexOf(a);
        const bi = districtOrder.indexOf(b);
        return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi) || a.localeCompare(b, "th");
      }});

      districtsEl.innerHTML = districts.map(district => {{
        const rows = byDistrict.get(district);
        const done = rows.filter(unit => unit.uploaded).length;
        const districtTotalRows = allUnitsForDistrict(district);
        const districtDone = districtTotalRows.filter(unit => unit.uploaded).length;
        return `
          <article class="district">
            <div class="district-head">
              <h2>${{escapeHtml(district)}}</h2>
              <div class="district-meta">อัปโหลดแล้ว ${{districtDone}} / ${{districtTotalRows.length}} หน่วยบริการ</div>
            </div>
            <table>
              <thead>
                <tr>
                  <th class="unit-col">หน่วยบริการ</th>
                  <th class="status-col">สถานะ</th>
                  <th class="file-col">ไฟล์ใบประกาศ</th>
                  <th class="upload-col">อัพโหลด</th>
                  <th class="time-col">แก้ไขล่าสุด</th>
                </tr>
              </thead>
              <tbody>
                ${{rows.map(unit => `
                  <tr>
                    <td data-label="หน่วยบริการ"><a href="${{unit.folder_url}}" target="_blank" rel="noopener">${{escapeHtml(unit.name)}}</a></td>
                    <td data-label="สถานะ">${{statusBadge(unit)}}</td>
                    <td data-label="ไฟล์ใบประกาศ">${{unit.error ? escapeHtml(unit.error) : fileLinks(unit)}}</td>
                    <td data-label="อัพโหลด"><a class="${{uploadLinkClass(unit)}}" href="${{unit.folder_url}}" target="_blank" rel="noopener">อัพโหลดใบประกาศ</a></td>
                    <td data-label="แก้ไขล่าสุด">${{escapeHtml(unit.folder_modified || "-")}}</td>
                  </tr>
                `).join("")}}
              </tbody>
            </table>
          </article>
        `;
      }}).join("") || '<p class="empty">ไม่พบข้อมูลตามตัวกรอง</p>';
    }}

    searchInput.addEventListener("input", render);
    districtFilter.addEventListener("change", render);
    for (const button of statusButtons) {{
      button.addEventListener("click", () => {{
        selectedStatus = button.dataset.status;
        for (const item of statusButtons) item.classList.toggle("active", item === button);
        render();
      }});
    }}
    renderDistrictSummary();
    renderZeroPanel();
    render();
  </script>
</body>
</html>
"""


def main():
    snapshot = build_snapshot()
    SNAPSHOT_JSON.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_HTML.write_text(render_html(snapshot), encoding="utf-8")

    total = len(snapshot["units"])
    uploaded = sum(1 for item in snapshot["units"] if item["uploaded"])
    print(f"wrote {OUTPUT_HTML.resolve()}")
    print(f"wrote {SNAPSHOT_JSON.resolve()}")
    print(f"total={total} uploaded={uploaded} pending={total - uploaded}")
    for unit in snapshot["units"]:
        if unit["uploaded"]:
            files = ", ".join(file["name"] for file in unit["files"])
            print(f'UPLOADED {unit["district"]} | {unit["name"]} | {files}')


if __name__ == "__main__":
    main()
