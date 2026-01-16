from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os, sqlite3, shutil
from datetime import datetime
from fastapi import Body

app = FastAPI()

# เพิ่ม CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# เชื่อมโฟลเดอร์ static
app.mount("/static", StaticFiles(directory="static"), name="static")

# ตั้งค่าโฟลเดอร์ templates
templates = Jinja2Templates(directory="templates")

# ----------------------------- เตรียมโฟลเดอร์ -----------------------------
os.makedirs("uploads/reports", exist_ok=True)
db = sqlite3.connect("cases.db", check_same_thread=False)
db.execute("""
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    surname TEXT,
    event TEXT,
    detail TEXT,
    pdf_path TEXT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
db.commit()

print("✅ Database and upload folder ready.")

# ----------------------------- หน้าเว็บหลัก -----------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    cur = db.execute("SELECT * FROM cases ORDER BY created DESC")
    cases = cur.fetchall()
    print(f"📊 หน้าหลัก: พบข้อมูล {len(cases)} เคส")
    return templates.TemplateResponse("index.html", {"request": request, "cases": cases})

# ----------------------------- รับไฟล์ PDF จาก EMS+ -----------------------------
@app.post("/api/upload_pdf")
async def upload_pdf(
    file: UploadFile, 
    name: str = Form(...), 
    surname: str = Form(""), 
    event: str = Form(""), 
    detail: str = Form("")
):
    print("\n" + "="*50)
    print("📥 รับคำขอ upload ใหม่")
    print(f"📄 ชื่อไฟล์: {file.filename}")
    print(f"👤 ผู้ป่วย: {name} {surname}")
    print(f"🚨 เหตุการณ์: {event}")
    print(f"📝 รายละเอียด: {detail[:50]}..." if len(detail) > 50 else f"📝 รายละเอียด: {detail}")
    
    save_path = f"uploads/reports/{file.filename}"
    
    try:
        # บันทึกไฟล์
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        file_size = os.path.getsize(save_path) / 1024  # KB
        print(f"💾 บันทึกไฟล์สำเร็จ: {save_path} ({file_size:.1f} KB)")
        
        # บันทึกลง database
        cursor = db.execute(
            "INSERT INTO cases (name, surname, event, detail, pdf_path) VALUES (?,?,?,?,?)", 
            (name, surname, event, detail, save_path)
        )
        db.commit()
        
        case_id = cursor.lastrowid
        print(f"✅ บันทึกข้อมูลลง database สำเร็จ (ID: {case_id})")
        print("="*50 + "\n")
        
        return {
            "status": "ok", 
            "path": save_path, 
            "case_id": case_id,
            "message": "อัปโหลดสำเร็จ"
        }
    
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        import traceback
        traceback.print_exc()
        print("="*50 + "\n")
        return {"status": "error", "message": str(e)}
        
@app.post("/api/alert")
def alert_event(
    name: str = Form(...),
    place: str = Form(...),
    lat: str = Form(...),
    lon: str = Form(...),
    event: str = Form(...),
    detail: str = Form("")
):
    print("🚨 มีเหตุแจ้งเข้ามาใหม่!")
    print("ชื่อ:", name)
    print("สถานที่:", place)
    print("GPS:", lat, lon)
    print("เหตุการณ์:", event)
    print("รายละเอียด:", detail)

    # สร้างโฟลเดอร์สำหรับแจ้งเตือน
    os.makedirs("alerts", exist_ok=True)
    filename = "alerts/alert_latest.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"{name}\n{place}\n{lat}\n{lon}\n{event}\n{detail}")

    return {"status": "ok", "message": "ส่งแจ้งเตือนสำเร็จ"}

@app.get("/report", response_class=HTMLResponse)
def report_page(request: Request):
    return templates.TemplateResponse("report.html", {"request": request})


# ----------------------------- API อื่นๆ -----------------------------
@app.get("/api/cases")
def list_cases():
    cur = db.execute("SELECT * FROM cases ORDER BY created DESC")
    cols = [c[0] for c in cur.description]
    results = [dict(zip(cols, row)) for row in cur.fetchall()]
    print(f"📊 API /cases: ส่งข้อมูล {len(results)} เคส")
    return results

@app.get("/health")
def health_check():
    case_count = db.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    return {
        "status": "ok", 
        "message": "Server is running",
        "cases_count": case_count,
        "timestamp": datetime.now().isoformat()
    }

# ----------------------------- Static Files -----------------------------
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ----------------------------- Startup Event -----------------------------
@app.on_event("startup")
def startup_event():
    print("-"*50)
    print("\t🎉 Welcome to SmartEMS+ WebApp! 📝\n")
    print("🌐 เปิดเบราว์เซอร์ไปที่: (IP ที่เปิด)")
    print("📊 Health Check: (IP ที่เปิด)/health")
    print("📋 API Cases: (IP ที่เปิด)/api/cases\n")
    print("-"*50 + "\n")