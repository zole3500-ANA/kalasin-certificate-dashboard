# คู่มือดูแล Dashboard อัปโหลดใบประกาศ จังหวัดกาฬสินธุ์

เอกสารนี้ทำไว้เพื่อให้เครื่องอื่นหรือผู้ดูแลระบบคนอื่นสามารถเข้าใจโครงการนี้ และดูแลต่อได้โดยไม่ต้องเริ่มไล่ไฟล์ใหม่ทั้งหมด

## ภาพรวม

Dashboard นี้ใช้ติดตามว่าแต่ละหน่วยบริการในจังหวัดกาฬสินธุ์อัปโหลดใบประกาศแล้วหรือยัง โดยแยกข้อมูลเป็นรายอำเภอ

- หน้าเว็บ Dashboard: https://zole3500-ana.github.io/kalasin-certificate-dashboard/
- Repository: https://github.com/zole3500-ANA/kalasin-certificate-dashboard
- Folder ต้นทางใน Google Drive: https://drive.google.com/drive/folders/1nWJa_JXYKz-sbqtKktMy1JBpXJMxiVv8
- ระบบอัปเดตอัตโนมัติ: GitHub Actions ทุก 1 ชั่วโมง ที่นาที `5` ของทุกชั่วโมง

หมายเหตุ: GitHub Actions แบบตั้งเวลาเป็น best effort อาจไม่ได้เริ่มตรงนาทีเป๊ะทุกครั้ง ถ้า GitHub มีคิวงานหนาแน่นอาจหน่วงได้

## โครงสร้างไฟล์สำคัญ

| ไฟล์ | หน้าที่ |
| --- | --- |
| `build_kalasin_certificate_dashboard.py` | Script หลักสำหรับอ่านข้อมูลจาก Google Drive, สร้างข้อมูลสรุป และสร้างหน้า Dashboard |
| `index.html` | หน้าเว็บ Dashboard ที่ GitHub Pages ใช้แสดงผล |
| `kalasin-certificate-dashboard-data.json` | Snapshot ข้อมูลล่าสุดที่ script สร้างไว้ ใช้ตรวจสอบข้อมูลย้อนหลังหรือ debug |
| `.github/workflows/update-dashboard.yml` | Workflow ของ GitHub Actions สำหรับอัปเดต Dashboard อัตโนมัติ |
| `README.md` | หน้าแนะนำสั้น ๆ ของ repository |
| `DASHBOARD_GUIDE.md` | คู่มือฉบับนี้ |

## การทำงานของข้อมูล

1. Script อ่าน folder หลักจาก Google Drive ด้วยค่า `ROOT_FOLDER_ID`
2. ใน folder หลัก ระบบจะนับเฉพาะ folder ที่ชื่อขึ้นต้นด้วย `อำเภอ`
3. ในแต่ละอำเภอ ระบบจะนับ folder ย่อยเป็นรายชื่อหน่วยบริการ
4. ถ้าใน folder หน่วยบริการมีไฟล์ใบประกาศ ระบบจะถือว่า `อัปโหลดแล้ว`
5. ถ้ายังไม่มีไฟล์ ระบบจะแสดงเป็น `ยังไม่อัปโหลด`
6. เมื่อสร้างข้อมูลเสร็จ script จะเขียนทับ `index.html` และ `kalasin-certificate-dashboard-data.json`

## การอัปเดตอัตโนมัติ

ระบบใช้ไฟล์ `.github/workflows/update-dashboard.yml`

Workflow นี้ทำงาน 2 แบบ:

- อัตโนมัติทุก 1 ชั่วโมง ด้วย cron `5 * * * *`
- กดรันเองได้จากหน้า GitHub Actions ด้วยปุ่ม `Run workflow`

เมื่อ workflow ทำงาน จะรันคำสั่ง:

```bash
python build_kalasin_certificate_dashboard.py
```

ถ้า `index.html` หรือ `kalasin-certificate-dashboard-data.json` เปลี่ยนแปลง ระบบจะ commit และ push กลับเข้า branch `main` ให้อัตโนมัติ

## วิธีรันเองบนเครื่อง

เปิด PowerShell แล้วเข้า folder repository:

```powershell
cd "E:\Mobile Project\kalasin-certificate-dashboard-github\kalasin-certificate-dashboard"
```

ถ้าเครื่องมี Python ใน PATH:

```powershell
python build_kalasin_certificate_dashboard.py
```

ถ้าใช้ Python ที่ bundled มากับ Codex เครื่องนี้:

```powershell
& "C:\Users\CDCKsn2\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" build_kalasin_certificate_dashboard.py
```

หลังรันเสร็จ ให้ตรวจไฟล์ที่เปลี่ยน:

```powershell
git status
```

ถ้าต้องการส่งขึ้น GitHub:

```powershell
git add index.html kalasin-certificate-dashboard-data.json
git commit -m "Update dashboard data"
git pull --rebase origin main
git push
```

## วิธีเพิ่มหน่วยบริการ

วิธีที่แนะนำที่สุดคือเพิ่ม folder ใน Google Drive ให้ถูกตำแหน่ง

1. เปิด folder Google Drive ต้นทาง
2. เข้า folder อำเภอที่ต้องการ
3. สร้าง folder ย่อยโดยใช้ชื่อหน่วยบริการ
4. ให้หน่วยบริการอัปโหลดใบประกาศเข้า folder นั้น
5. รอระบบอัปเดตอัตโนมัติ หรือกดรัน workflow เองจาก GitHub Actions

ถ้าจำเป็นต้องเพิ่มหน่วยบริการแบบ manual ใน code ให้แก้ `MANUAL_UNITS` ใน `build_kalasin_certificate_dashboard.py`

ตัวอย่าง:

```python
MANUAL_UNITS = [
    {
        "district": "อำเภอเมืองกาฬสินธุ์",
        "name": "ศูนย์สุขภาพชุมชนเมืองโรงพยาบาลกาฬสินธุ์(77738)",
    },
]
```

ถ้าภายหลังมี folder จริงใน Google Drive ที่ชื่อเดียวกัน ระบบจะไม่เพิ่มซ้ำ

## วิธีตัดหน่วยบริการออกจากเป้าหมาย

แก้ `EXCLUDED_UNITS` ใน `build_kalasin_certificate_dashboard.py`

ตัวอย่างปัจจุบัน:

```python
EXCLUDED_UNITS = {
    ("อำเภอเมืองกาฬสินธุ์", "โรงพยาบาลกาฬสินธุ์ ธนบุรี"),
    ("อำเภอเมืองกาฬสินธุ์", "โรงพยาบาลธีรวัฒน์"),
}
```

หลังแก้แล้วให้รัน script ใหม่ และ commit ไฟล์ที่เปลี่ยน

## วิธีแก้ข้อความหรือหน้าตา Dashboard

ข้อความและหน้าตาส่วนใหญ่สร้างจาก function `render_html(snapshot)` ในไฟล์ `build_kalasin_certificate_dashboard.py`

แนวทางแก้:

1. แก้ CSS หรือ HTML ใน `render_html(snapshot)`
2. รัน `python build_kalasin_certificate_dashboard.py`
3. เปิด `index.html` ตรวจดูหน้าจอ
4. commit และ push ขึ้น GitHub

ไม่แนะนำให้แก้ `index.html` โดยตรงเป็นหลัก เพราะเมื่อ workflow ทำงานครั้งต่อไป `index.html` จะถูกสร้างใหม่จาก script และอาจทับการแก้ไข

## วิธีดูว่าอัปโหลดแล้วหรือยัง

ระบบดูจากไฟล์ที่อยู่ใน folder ของหน่วยบริการ

- มีไฟล์ใน folder หน่วยบริการ = อัปโหลดแล้ว
- ไม่มีไฟล์ = ยังไม่อัปโหลด
- ถ้ามีการวางไฟล์ผิด folder หรือชื่อ folder หน่วยบริการไม่ตรง ระบบอาจไม่จับสถานะให้

## การแก้ปัญหาที่พบบ่อย

### อัปโหลดไฟล์แล้ว แต่ Dashboard ยังไม่เปลี่ยน

ให้ตรวจตามลำดับนี้:

1. ไฟล์ถูกอัปโหลดเข้า folder ของหน่วยบริการที่ถูกต้องหรือไม่
2. รอรอบอัปเดตถัดไป ประมาณ 1 ชั่วโมง
3. เปิด GitHub Actions ดูว่า workflow `Update dashboard` ทำงานสำเร็จหรือไม่
4. ลอง hard refresh หน้าเว็บด้วย `Ctrl + F5`
5. ถ้ารีบ ให้กด `Run workflow` เองจากหน้า GitHub Actions

### GitHub Pages ไม่แสดงหน้าเว็บ

ตรวจว่า repository เป็น public แล้ว เพราะ GitHub Pages ของบัญชีทั่วไปต้องใช้ public repository หากไม่ใช้แผนที่รองรับ private Pages

### Workflow ไม่ทำงานตรงทุก 1 ชั่วโมง

ตารางตั้งไว้ทุก 1 ชั่วโมงแล้วที่นาทีที่ `5` แต่ GitHub อาจหน่วงเวลาเริ่มงานได้ หากต้องการให้ข้อมูลเปลี่ยนทันที ให้กดรัน workflow เอง

### ภาษาไทยเพี้ยนใน PowerShell

ไฟล์ใช้ UTF-8 ถ้า PowerShell แสดงภาษาไทยเพี้ยน ไม่ได้แปลว่าไฟล์เสียเสมอไป ให้เปิดด้วย editor ที่รองรับ UTF-8 เช่น VS Code หรือ GitHub web editor

## สิ่งที่ควรระวัง

- Repository และ GitHub Pages เป็น public จึงไม่ควรใส่ token, password, หรือข้อมูลลับใน code
- อย่าแก้ `index.html` เป็นหลัก ถ้าต้องการแก้ถาวรให้แก้ใน `build_kalasin_certificate_dashboard.py`
- หากแก้โครงสร้าง folder ใน Google Drive มาก ควรรัน script แล้วตรวจ Dashboard ก่อนแจ้งผู้ใช้งาน
- ถ้าเพิ่ม/ลบหน่วยบริการ ควรตรวจยอดรวมทั้งหมดและยอดรายอำเภอหลังอัปเดต

## Checklist สำหรับส่งต่อเครื่องอื่น

1. Clone repository จาก GitHub
2. ติดตั้ง Python 3.12 หรือเวอร์ชันใกล้เคียง
3. รัน `python build_kalasin_certificate_dashboard.py`
4. ตรวจว่าเกิดไฟล์ `index.html` และ `kalasin-certificate-dashboard-data.json`
5. เปิด `index.html` ดูหน้า Dashboard
6. ถ้าจะแก้แล้วส่งขึ้น GitHub ให้ใช้ `git add`, `git commit`, `git pull --rebase`, และ `git push`

