# Kalasin Certificate Upload Dashboard

Dashboard สำหรับติดตามสถานะการอัปโหลดใบประกาศของหน่วยบริการ จังหวัดกาฬสินธุ์ แยกรายอำเภอ

## Files

- `index.html` - หน้า dashboard พร้อมข้อมูล snapshot ล่าสุด เปิดผ่าน browser หรือ GitHub Pages ได้ทันที
- `kalasin-certificate-dashboard-data.json` - ข้อมูล snapshot จาก Google Drive ณ เวลาที่สร้าง dashboard
- `build_kalasin_certificate_dashboard.py` - สคริปต์ดึงข้อมูลจาก Google Drive public folder และสร้าง dashboard ใหม่

## Update Dashboard

รันจากโฟลเดอร์โปรเจกต์หลัก:

```powershell
python build_kalasin_certificate_dashboard.py
```

จากนั้น copy `kalasin-certificate-dashboard.html` เป็น `index.html` ใน repo นี้ แล้ว commit/push ขึ้น GitHub อีกครั้ง

