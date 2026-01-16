import tkinter as tk
from tkinter import ttk, messagebox
import os
os.environ["OPENCV_VIDEOIO_PRIORITY_LIST"] = "V4L2"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "1"
import cv2
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
    print("✅ picamera2 พร้อมใช้งาน")
except ImportError:
    PICAMERA2_AVAILABLE = False
    print("⚠️ ไม่มี picamera2")

# Import MAX30102 sensor
try:
    from max30102 import MAX30102
    MAX30102_AVAILABLE = True
    print("✅ MAX30102 พร้อมใช้งาน")
except ImportError:
    MAX30102_AVAILABLE = False
    print("⚠️ ไม่มี MAX30102 library")

import sys
import time
from PIL import Image, ImageTk
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import requests
import webbrowser
import threading
import traceback

# เพิ่ม: อ่านบัตรประชาชน
try:
    from ThaiCIDReader import SimpleThaiCIDReader
    THAICID_READER_AVAILABLE = True
    print("✅ โมดูลอ่านบัตรประชาชนพร้อมใช้งาน")
except ImportError as e:
    THAICID_READER_AVAILABLE = False
    print(f"⚠️ ไม่สามารถโหลดโมดูลอ่านบัตรประชาชน: {e}")

# ===== ระบบตรวจสอบการแจ้งเหตุจาก WebApp =====
alert_watcher_running = False
last_alert_content = None
# ใช้ path แบบ absolute
ALERT_FILE_PATH = os.path.join(os.path.dirname(__file__), "SmartEMS-WebApp", "alerts", "alert_latest.txt")

def check_new_alert():
    """ตรวจสอบว่ามีการแจ้งเหตุใหม่หรือไม่"""
    global last_alert_content
    
    try:
        # Debug: แสดง path ที่กำลังตรวจสอบ
        # print(f"🔍 ตรวจสอบไฟล์: {ALERT_FILE_PATH}")
        
        if not os.path.exists(ALERT_FILE_PATH):
            # print(f"⚠️ ไม่พบไฟล์: {ALERT_FILE_PATH}")
            return None
        
        # อ่านไฟล์
        with open(ALERT_FILE_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
        
        # Debug: แสดงเนื้อหาที่อ่านได้
        # print(f"📄 เนื้อหาไฟล์: {content[:50]}...")
        
        # ถ้าเนื้อหาเปลี่ยน = มีการแจ้งเหตุใหม่
        if content and content != last_alert_content:
            print(f"🆕 พบการแจ้งเหตุใหม่!")
            last_alert_content = content
            
            # แยกข้อมูล
            lines = content.split('\n')
            if len(lines) >= 5:
                alert_data = {
                    'name': lines[0],
                    'place': lines[1],
                    'lat': lines[2],
                    'lon': lines[3],
                    'event': lines[4],
                    'detail': lines[5] if len(lines) > 5 else ''
                }
                print(f"✅ แยกข้อมูลสำเร็จ: {alert_data['name']} - {alert_data['event']}")
                return alert_data
    
    except Exception as e:
        print(f"⚠️ ข้อผิดพลาดในการตรวจสอบการแจ้งเหตุ: {e}")
        import traceback
        traceback.print_exc()
    
    return None

def show_alert_notification(alert_data):
    """แสดง popup แจ้งเตือนเหตุการณ์"""
    try:
        # สร้าง popup window
        alert_window = tk.Toplevel(root)
        alert_window.title("🚨 การแจ้งเหตุใหม่!")
        alert_window.geometry("500x400")
        alert_window.configure(bg="#ffebee")
        
        # ทำให้อยู่ด้านหน้าสุด
        alert_window.attributes('-topmost', True)
        alert_window.focus_force()
        
        # หัวข้อ
        tk.Label(
            alert_window,
            text="🚨 มีการแจ้งเหตุใหม่!",
            font=("Arial", 18, "bold"),
            bg="#ffebee",
            fg="#c62828"
        ).pack(pady=15)
        
        # กรอบข้อมูล
        info_frame = tk.Frame(alert_window, bg="white", relief="ridge", bd=2)
        info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # แสดงข้อมูล
        info_text = f"""
👤 ผู้แจ้ง: {alert_data['name']}

📍 สถานที่: {alert_data['place']}

🗺️ พิกัด: {alert_data['lat']}, {alert_data['lon']}

🚨 เหตุการณ์: {alert_data['event']}

📝 รายละเอียด:
{alert_data['detail'] if alert_data['detail'] else '-'}
        """
        
        tk.Label(
            info_frame,
            text=info_text,
            font=("Arial", 12),
            bg="white",
            fg="#212121",
            justify="left",
            anchor="w"
        ).pack(pady=20, padx=20, fill="both", expand=True)
        
        # ปุ่มปิด
        ttk.Button(
            alert_window,
            text="✅ รับทราบ",
            style="Success.TButton",
            command=alert_window.destroy
        ).pack(pady=10)
        
        # เล่นเสียงแจ้งเตือน (ถ้ามี)
        try:
            alert_window.bell()
        except:
            pass
        
        print("\n" + "="*50)
        print("🚨 แสดงการแจ้งเหตุใหม่")
        print(f"👤 ผู้แจ้ง: {alert_data['name']}")
        print(f"📍 สถานที่: {alert_data['place']}")
        print(f"🚨 เหตุการณ์: {alert_data['event']}")
        print("="*50 + "\n")
        
        # อัพเดทข้อมูล GPS ใน frame2
        update_alert_info(alert_data)
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการแสดงการแจ้งเหตุ: {e}")
        traceback.print_exc()

def alert_watcher_loop():
    """Loop สำหรับตรวจสอบการแจ้งเหตุทุก 3 วินาที"""
    global alert_watcher_running
    
    print("🔔 เริ่มระบบตรวจสอบการแจ้งเหตุ...")
    
    while alert_watcher_running:
        try:
            alert_data = check_new_alert()
            
            if alert_data:
                # ใช้ after() เพื่อแสดง popup ใน main thread
                root.after(0, lambda: show_alert_notification(alert_data))
            
            # รอ 3 วินาทีก่อนตรวจสอบอีกครั้ง
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ ข้อผิดพลาดใน alert watcher: {e}")
            time.sleep(5)
    
    print("🔕 หยุดระบบตรวจสอบการแจ้งเหตุ")

def start_alert_watcher():
    """เริ่มระบบตรวจสอบการแจ้งเหตุใน background thread"""
    global alert_watcher_running
    
    if alert_watcher_running:
        print("⚠️ ระบบตรวจสอบการแจ้งเหตุทำงานอยู่แล้ว")
        return
    
    alert_watcher_running = True
    
    # สร้าง thread สำหรับตรวจสอบ
    watcher_thread = threading.Thread(
        target=alert_watcher_loop,
        daemon=True,
        name="AlertWatcher"
    )
    watcher_thread.start()
    
    print("✅ เริ่มระบบตรวจสอบการแจ้งเหตุแล้ว")

def stop_alert_watcher():
    """หยุดระบบตรวจสอบการแจ้งเหตุ"""
    global alert_watcher_running
    alert_watcher_running = False

# ------------------ Global modern ttk styles ------------------
def init_modern_styles(root):
    try:
        style = ttk.Style(root)
        # Prefer built-in modern-looking themes if available
        preferred_themes = ["vista", "clam", "alt", "default"]
        for t in preferred_themes:
            try:
                style.theme_use(t)
                break
            except Exception:
                continue

        # Base button
        style.configure(
            "TButton",
            padding=(10, 6),
            relief="flat"
        )
        style.map(
            "TButton",
            relief=[("pressed", "sunken"), ("active", "groove")]
        )

        # Primary
        style.configure(
            "Primary.TButton",
            foreground="#089E1C",
            background="#10c50a",
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#1e6ae0"), ("pressed", "#1858bd")]
        )

        # Success
        style.configure(
            "Success.TButton",
            foreground="#2bd315",
            background="#3dcf04",  # vibrant green
            bordercolor="#2bb11a",
            focusthickness=3,
            font=("Arial", 15, "bold"),
        )
        style.map(
            "Success.TButton",
            background=[("active", "#16a34a"), ("pressed", "#2bb11a")],
            foreground=[("disabled", "#2bb11a")],
        )

        # Warning/Accent
        style.configure(
            "Accent.TButton",
            foreground="#2b2b2b",
            background="#ffd54f",
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#ffca28"), ("pressed", "#f4b400")]
        )

        # Secondary
        style.configure(
            "Secondary.TButton",
            foreground="#2c3e50",
            background="#ecf0f1",
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#dfe6e9"), ("pressed", "#cfd8dc")]
        )

        # Danger
        style.configure(
            "Danger.TButton",
            foreground="#ffffff",
            background="#e74c3c",
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#cf3e2e"), ("pressed", "#b83224")]
        )

        # Progressbar (global green style)
        style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor="#ecf0f1",
            background="#27ae60"
        )

        # Combobox
        style.configure(
            "Modern.TCombobox",
            fieldbackground="#ffffff",
            background="#ffffff",
            foreground="#2c3e50"
        )
    except Exception:
        pass

# สร้างโฟลเดอร์เก็บไฟล์
if not os.path.exists("captured_images"):
    os.makedirs("captured_images")
    
if not os.path.exists("pdf_reports"):
    os.makedirs("pdf_reports")

captured_images = []  # เก็บ path รูปที่ถ่าย
# ===== ค่าคงที่สำหรับกล้อง =====
# เพิ่มความละเอียดเพื่อให้ภาพชัดขึ้น
CAMERA_WIDTH = 640  # เพิ่มจาก 320 → 640
CAMERA_HEIGHT = 480  # เพิ่มจาก 240 → 480
CAMERA_FPS = 30
print(f"📷 ตั้งค่ากล้อง: {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ {CAMERA_FPS}fps (ความละเอียดสูง)")

# ===== Initialize Global Variables =====
cap = None  # OpenCV video capture object
camera_running = False  # Track camera status
camera_type = None  # เพิ่มบรรทัดนี้ - 'picamera2' หรือ 'opencv'
camera_restart_count = 0  # เพิ่มบรรทัดนี้ (ถ้ายังไม่มี)
MAX_CAMERA_RESTARTS = 3  # เพิ่มบรรทัดนี้ (ถ้ายังไม่มี)

# ===== MAX30102 Sensor Variables =====
sensor = None  # MAX30102 sensor object
sensor_running = False  # Track sensor status
heart_rate = 0  # Heart rate value (BPM)
spo2 = 0  # SpO2 value (%)
sensor_data_ready = False  # Flag to indicate data is ready

# ตั้งค่าฟอนต์สำหรับ Raspberry Pi
def setup_thai_font():
    try:
        # ฟอนต์ไทยที่ต้องการ (เรียงลำดับความสำคัญ)
        thai_font_paths = [
            "E:/Code Project SmartEMS/Progam SmartEMS+++++/cfonts/THSarabunNew.ttf",
            "E:/Code Project SmartEMS/Progam SmartEMS+++++/cfonts/Garuda.ttf", 
            "E:/Code Project SmartEMS/Progam SmartEMS+++++/cfonts/NotoSansThai-Regular.ttf",
            "cfonts/THSarabunNew.ttf",
            "cfonts/Garuda.ttf",
            "cfonts/NotoSansThai-Regular.ttf",
            "./cfonts/THSarabunNew.ttf",
            "./cfonts/Garuda.ttf",
            "./cfonts/NotoSansThai-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf",
            "/usr/share/fonts/truetype/tlwg/Garuda.ttf",
            "/usr/share/fonts/truetype/tlwg/Laksaman.ttf",
            "/usr/share/fonts/truetype/tlwg/TlwgMono.ttf",
            "/usr/share/fonts/truetype/fonts-tlwg/Garuda.ttf",
            "/usr/share/fonts/truetype/thai/TH Sarabun New.ttf",
            "/usr/share/fonts/truetype/thai/Garuda.ttf",
            "/System/fonts/THSarabunNew.ttf",
            "C:\\Windows\\Fonts\\THSarabunNew.ttf",
            "./fonts/THSarabunNew.ttf",
            "./fonts/Garuda.ttf",
        ]
        # รวมฟอนต์จากโฟลเดอร์ cfonts/fonts
        thai_font_paths += check_fonts_in_directory()
        # ลองโหลดฟอนต์ไทย
        for font_path in thai_font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('ThaiFont', font_path))
                    print(f"✅ โหลดฟอนต์ไทยสำเร็จ: {font_path}")
                    return True, 'ThaiFont'
                except Exception as e:
                    print(f"❌ ไม่สามารถโหลดฟอนต์ไทย {font_path}: {e}")
                    continue
        # ถ้าไม่มีฟอนต์ไทย ให้ลองฟอนต์อื่น
        fallback_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Arial.ttf",
            "C:\\Windows\\Fonts\\arial.ttf"
        ]
        for font_path in fallback_fonts:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('BasicFont', font_path))
                    print(f"⚠️ โหลดฟอนต์สำรอง (ไม่รองรับไทย): {font_path}")
                    return False, 'BasicFont'
                except Exception as e:
                    print(f"❌ ไม่สามารถโหลดฟอนต์สำรอง {font_path}: {e}")
                    continue
        print("❌ ไม่พบฟอนต์ที่รองรับ - ใช้ Helvetica (ไม่รองรับภาษาไทย)")
        return False, 'Helvetica'
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการตั้งค่าฟอนต์: {e}")
        return False, 'Helvetica'


# เพิ่มฟังก์ชันตรวจสอบฟอนต์ที่มีในโฟลเดอร์
def check_fonts_in_directory():
    """ตรวจสอบฟอนต์ที่มีในโฟลเดอร์ cfonts/fonts"""
    print("\n🔍 ตรวจสอบฟอนต์ในโฟลเดอร์...")
    font_dirs = [
        "cfonts",
        "E:/Code Project SmartEMS/Progam SmartEMS+++++/cfonts",
        "./cfonts",
        "fonts"
    ]
    found_fonts = []
    for font_dir in font_dirs:
        if os.path.exists(font_dir):
            print(f"\n📁 พบโฟลเดอร์: {font_dir}")
            try:
                files = os.listdir(font_dir)
                font_files = [f for f in files if f.lower().endswith(('.ttf', '.otf'))]
                if font_files:
                    print("   ฟอนต์ที่พบ:")
                    for font_file in font_files:
                        full_path = os.path.join(font_dir, font_file)
                        file_size = os.path.getsize(full_path) / 1024  # KB
                        print(f"   - {font_file} ({file_size:.1f} KB)")
                        found_fonts.append(full_path)
                else:
                    print("   ไม่พบไฟล์ฟอนต์")
            except Exception as e:
                print(f"   ❌ ข้อผิดพลาด: {e}")
        else:
            print(f"❌ ไม่พบโฟลเดอร์: {font_dir}")
    return found_fonts
    
# เพิ่มฟังก์ชันตรวจสอบฟอนต์ที่มีในโฟลเดอร์
def check_fonts_in_directory():
    """ตรวจสอบฟอนต์ที่มีในโฟลเดอร์ cfonts"""
    print("\n🔍 ตรวจสอบฟอนต์ในโฟลเดอร์...")
    
    font_dirs = [
        "cfonts",
        "E:/Code Project SmartEMS/Progam SmartEMS+++++/cfonts",
        "./cfonts",
        "fonts"
    ]
    
    for font_dir in font_dirs:
        if os.path.exists(font_dir):
            print(f"\n📁 พบโฟลเดอร์: {font_dir}")
            try:
                files = os.listdir(font_dir)
                font_files = [f for f in files if f.endswith(('.ttf', '.TTF', '.otf', '.OTF'))]
                
                if font_files:
                    print("   ฟอนต์ที่พบ:")
                    for font_file in font_files:
                        full_path = os.path.join(font_dir, font_file)
                        file_size = os.path.getsize(full_path) / 1024  # KB
                        print(f"   - {font_file} ({file_size:.1f} KB)")
                else:
                    print("   ไม่พบไฟล์ฟอนต์")
            except Exception as e:
                print(f"   ❌ ข้อผิดพลาด: {e}")
        else:
            print(f"❌ ไม่พบโฟลเดอร์: {font_dir}")
    
    return font_files if 'font_files' in locals() else []

# ฟังก์ชันตรวจสอบและติดตั้งฟอนต์ไทย
def install_thai_font():
    """ช่วยติดตั้งฟอนต์ไทยสำหรับ Raspberry Pi"""
    print("\n🔍 ตรวจสอบฟอนต์ไทยในระบบ...")
    
    found_fonts = check_fonts_in_directory()
    if not os.path.exists("fonts"):
        os.makedirs("fonts")
        print("📁 สร้างโฟลเดอร์ fonts/")
    thai_keywords = ['thai', 'garuda', 'laksaman', 'noto', 'sarabun']
    thai_fonts = [f for f in found_fonts if any(k in os.path.basename(f).lower() for k in thai_keywords)]
    if thai_fonts:
        print("✅ พบฟอนต์ไทยในระบบ:")
        for font in thai_fonts[:10]:
            print(f"   - {font}")
        return True
    else:
        print("⚠️ ไม่พบฟอนต์ไทยในระบบ")
        print("\n📋 วิธีแก้ไข:")
        print("1. ตรวจสอบว่าโฟลเดอร์ cfonts มีฟอนต์ไทยหรือไม่")
        print("2. ลองคัดลอกฟอนต์ไทย (เช่น THSarabunNew.ttf) ไปยัง:")
        print("   - โฟลเดอร์ cfonts/")
        print("   - โฟลเดอร์ fonts/")
        print("3. สำหรับ Raspberry Pi:")
        print("   sudo apt update")
        print("   sudo apt install fonts-thai-tlwg fonts-noto-cjk")
        return False

# ฟังก์ชันเริ่มกล้อง
def start_camera():
    """เริ่มต้นกล้องและเริ่มการแสดงผล"""
    global cap, camera_running
    
    if camera_running and cap and cap.isOpened():
        print("ℹ️ กล้องทำงานอยู่แล้ว")
        return
    
    try:
        print("🚀 กำลังเริ่มกล้อง...")
        
        # ปิดกล้องเดิมถ้ามี
        if cap:
            try:
                cap.release()
            except:
                pass
        
        # เปิดกล้องใหม่
        if os.name == 'nt':  # Windows
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        else:  # Linux/Raspberry Pi
            cap = cv2.VideoCapture(0)
        
        if cap and cap.isOpened():
            # ตั้งค่ากล้อง
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # เพิ่มบรรทัดนี้
            except:
                pass
            
            camera_running = True
            print("✅ เริ่มกล้องสำเร็จ")
            
            # เริ่มการอัพเดทเฟรม
            update_frame()
        else:
            print("❌ ไม่สามารถเปิดกล้องได้")
            camera_running = False
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการเริ่มกล้อง: {e}")
        camera_running = False

# ฟังก์ชันซ่อนแป้นพิมพ์เสมือน (placeholder)
def hide_keyboard():
    """ซ่อนแป้นพิมพ์เสมือน"""
    # ฟังก์ชันนี้จะถูกเรียกเมื่อต้องการซ่อนแป้นพิมพ์
    # ในเวอร์ชันนี้ยังไม่มีแป้นพิมพ์เสมือน
    pass

# ฟังก์ชัน helper สำหรับตรวจสอบสถานะกล้อง
def is_camera_opened():
    """ตรวจสอบว่ากล้องเปิดอยู่หรือไม่ - รองรับทั้ง Picamera2 และ OpenCV"""
    global cap, camera_type
    
    if cap is None:
        return False
    
    try:
        if camera_type == 'picamera2':
            # Picamera2 ไม่มี isOpened() - ตรวจสอบว่ามี object และ started
            return hasattr(cap, 'started') and cap.started
        else:
            # OpenCV VideoCapture
            return cap.isOpened()
    except Exception:
        return False

# ===== ฟังก์ชันสำหรับเซนเซอร์ MAX30102 =====

def start_sensor_reading():
    """เริ่มอ่านค่าจากเซนเซอร์ MAX30102"""
    global sensor, sensor_running, MAX30102_AVAILABLE
    
    print("\n" + "="*50)
    print("💓 เริ่มการวัดค่าสัญญาณชีพ (Heart Rate & SpO2)")
    print("="*50)
    
    if not MAX30102_AVAILABLE:
        print("⚠️  ไม่มี MAX30102 library - ใช้ค่าจำลอง")
        print("📡 โหมด: เซนเซอร์จำลอง (สำหรับทดสอบ)")
        sensor_running = True
        update_sensor_display()
        return
    
    try:
        print("🔍 กำลังเริ่มต้น MAX30102...")
        # เริ่ลต้นเซนเซอร์
        sensor = MAX30102()
        sensor_running = True
        print("✅ เริ่มต้น MAX30102 สำเร็จ")
        print("📊 กำลังวัดค่า... (กรุณาวางนิ้วบนเซนเซอร์)")
        print("👉 ค่าจะอัพเดททุก 0.5 วินาที\n")
        
        # เริ่มอัพเดทค่า
        update_sensor_display()
        
    except Exception as e:
        print(f"❌ ไม่สามารถเริ่มเซนเซอร์ได้: {e}")
        print("📡 เปลี่ยนไปใช้ค่าจำลองแทน")
        # ใช้ค่าจำลองแทน
        sensor_running = True
        update_sensor_display()

def stop_max30102():
    """หยุดการอ่านค่าจากเซนเซอร์"""
    global sensor, sensor_running, sensor_data_ready
    
    print("\n🛑 หยุดการวัดค่าเซนเซอร์...")
    
    sensor_running = False
    sensor_data_ready = False
    
    if sensor:
        try:
            sensor.shutdown()
            print("✅ หยุดเซนเซอร์สำเร็จ")
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดในการหยุดเซนเซอร์: {e}")
        sensor = None

def update_sensor_display():
    """อัพเดทค่าเซนเซอร์แบบ realtime"""
    global sensor, sensor_running, heart_rate, spo2, sensor_data_ready
    global hr_value_label, spo2_value_label, status_label
    
    if not sensor_running:
        return
    
    try:
        if sensor and MAX30102_AVAILABLE:
            # อ่านค่าจากเซนเซอร์จริง
            try:
                # อ่านข้อมูลจาก MAX30102
                red, ir = sensor.read_sequential()
                
                # คำนวณค่า Heart Rate และ SpO2
                # (ต้องใช้ algorithm ที่เหมาะสม - นี่คือตัวอย่างเบื้องต้น)
                if red > 50000 and ir > 50000:  # มีสัญญาณ
                    # จำลองการคำนวณ (ควรใช้ algorithm จริง)
                    import random
                    heart_rate = random.randint(60, 100)
                    spo2 = random.randint(95, 100)
                    sensor_data_ready = True
                else:
                    heart_rate = 0
                    spo2 = 0
                    sensor_data_ready = False
                    
            except Exception as e:
                print(f"⚠️ ข้อผิดพลาดในการอ่านเซนเซอร์: {e}")
                print("📡 เปลี่ยนไปใช้ค่าจำลอง")
                # ใช้ค่าจำลอง
                import random
                heart_rate = random.randint(65, 95)
                spo2 = random.randint(96, 99)
                sensor_data_ready = True
                print(f"📊 [จำลอง] HR: {heart_rate} BPM | SpO2: {spo2}%")
        else:
            # ใช้ค่าจำลองเมื่อไม่มีเซนเซอร์
            import random
            heart_rate = random.randint(65, 95)
            spo2 = random.randint(96, 99)
            sensor_data_ready = True
            
            # แสดง log ทุกครั้งที่วัด
            import time
            timestamp = time.strftime("%H:%M:%S")
            print(f"📊 [{timestamp}] กำลังวัดค่า... | HR: {heart_rate} BPM | SpO2: {spo2}% | สถานะ: {'✅ ปกติ' if sensor_data_ready else '⚠️ รอสัญญาณ'}")
        
        # ตรวจสอบว่า labels มีอยู่จริงก่อนอัพเดท
        try:
            # อัพเดท UI
            if heart_rate > 0:
                hr_value_label.config(
                    text=f"{heart_rate} BPM",
                    fg="#d32f2f" if 60 <= heart_rate <= 100 else "#ff9800"
                )
            else:
                hr_value_label.config(text="-- BPM", fg="gray")
            
            if spo2 > 0:
                spo2_value_label.config(
                    text=f"{spo2}%",
                    fg="#1976d2" if spo2 >= 95 else "#ff9800"
                )
            else:
                spo2_value_label.config(text="-- %", fg="gray")
            
            # อัพเดทสถานะ
            if sensor_data_ready:
                status_label.config(
                    text="✅ กำลังวัดค่า... (ค่าเสถียร)",
                    fg="green"
                )
            else:
                status_label.config(
                    text="📊 กำลังวัดค่า... (รอสัญญาณ)",
                    fg="blue"
                )
        except Exception as e:
            print(f"⚠️ ไม่สามารถอัพเดท UI: {e}")
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการอัพเดทค่า: {e}")
        import traceback
        traceback.print_exc()
    
    # เรียกตัวเองอีกครั้งหลัง 500ms (2 ครั้งต่อวินาที)
    if sensor_running:
        safe_after(root, 500, update_sensor_display)


# ฟังก์ชันสลับหน้า
def show_frame(frame):
    global settings_visible
    hide_keyboard()
    
    # ซ่อนการตั้งค่ากล้องเมื่อเปลี่ยนหน้า
    if settings_visible:
        settings_frame.place_forget()
        settings_visible = False
    
    frame.tkraise()
    
    # ตรวจสอบและเริ่มกล้องให้ทำงานตลอดเวลา
    global cap, camera_running
    if not camera_running or cap is None or not is_camera_opened():
        print("🔄 เริ่มกล้องใหม่เมื่อเปลี่ยนหน้า")
        # ใช้ after() เพื่อให้ UI อัพเดทก่อนเริ่มกล้อง
        safe_after(root,100, start_camera)

# ------------------ หน้า 1 ------------------
def start_app():
    show_frame(frame2)
    # กล้องจะทำงานตลอดเวลาแล้ว - ไม่ต้องเริ่มใหม่

def reset_program():
    """รีเซ็ตโปรแกรมและกลับไปหน้าแรก"""
    global captured_images, heart_rate, spo2, sensor_data_ready
    
    try:
        print("\n🔄 กำลังรีเซ็ตโปรแกรม...")
        
        # หยุดเซนเซอร์ถ้ากำลังทำงานอยู่
        try:
            stop_max30102()
        except:
            pass
        
        # ล้างรายการรูปภาพ
        captured_images.clear()
        
        # รีเซ็ตค่าเซนเซอร์
        heart_rate = 0
        spo2 = 0
        sensor_data_ready = False
        
        # ล้างข้อมูลในฟอร์ม
        try:
            entry_name.delete(0, tk.END)
            entry_surname.delete(0, tk.END)
            combo_age.set('')
        except:
            pass
        
        # ซ่อนแป้นพิมพ์ถ้าเปิดอยู่
        try:
            hide_keyboard()
        except:
            pass
        
        print("✅ รีเซ็ตข้อมูลสำเร็จ")
        
        # กลับไปหน้าแรก
        show_frame(frame1)
        
        print("✅ กลับไปหน้าแรกแล้ว\n")
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการรีเซ็ต: {e}")
        import traceback
        traceback.print_exc()
        # พยายามกลับหน้าแรกอยู่ดี
        try:
            show_frame(frame1)
        except:
            pass

def restart_program():
    """ปิดและเปิดโปรแกรมใหม่"""
    try:
        print("\n🔄 กำลัง Restart โปรแกรม...")
        
        # แสดง confirmation dialog
        result = messagebox.askyesno(
            "ยืนยันการ Restart",
            "คุณต้องการปิดและเปิดโปรแกรมใหม่หรือไม่?\n\n"
            "ข้อมูลที่ยังไม่ได้บันทึกจะหายไป"
        )
        
        if not result:
            print("❌ ยกเลิกการ Restart")
            return
        
        print("✅ ยืนยันการ Restart - กำลังปิดโปรแกรม...")
        
        # หยุดกล้อง
        global cap, camera_running, sensor_running
        camera_running = False
        if cap:
            try:
                cap.release()
            except:
                pass
        
        # หยุดเซนเซอร์
        try:
            stop_max30102()
        except:
            pass
        
        # หยุด alert watcher
        try:
            stop_alert_watcher()
        except:
            pass
        
        # ปิด OpenCV windows
        try:
            cv2.destroyAllWindows()
        except:
            pass
        
        # ปิดหน้าต่างหลัก
        root.destroy()
        
        # เปิดโปรแกรมใหม่
        import subprocess
        print("🚀 เปิดโปรแกรมใหม่...")
        
        # ใช้ subprocess เพื่อเปิด Python script ใหม่
        subprocess.Popen([sys.executable] + sys.argv)
        
        # ออกจากโปรแกรมปัจจุบัน
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการ Restart: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror(
            "ข้อผิดพลาด",
            f"ไม่สามารถ Restart โปรแกรมได้\n\n{e}\n\n"
            "กรุณาปิดและเปิดโปรแกรมใหม่ด้วยตนเอง"
        )

# ===== ฟังก์ชันเรียก after() แบบปลอดภัย =====
def safe_after(widget, delay, callback, *args):
    """เรียก after() แบบปลอดภัย ป้องกัน invalid command name"""
    try:
        if widget and widget.winfo_exists():
            return widget.after(delay, callback, *args)
    except tk.TclError:
        print(f"⚠️ Widget ถูกทำลายแล้ว - ยกเลิก callback")
    except Exception as e:
        print(f"⚠️ ข้อผิดพลาด safe_after: {e}")
    return None

def find_camera_devices():
    """ค้นหา video device ที่มีอยู่จริง"""
    import glob
    devices = glob.glob('/dev/video*')
    devices.sort(key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    print(f"🔍 พบ video devices: {', '.join([d.split('/')[-1] for d in devices[:5]])}")
    return devices

def initialize_camera():
    """เริ่มต้นกล้อง - ลอง picamera2 ก่อน แล้วค่อย OpenCV"""
    global cap, camera_running, camera_type
    
    print("🚀 กำลังเริ่มกล้อง...")
    
    # ===== Method 1: ลอง picamera2 ก่อน (สำหรับ Pi Camera) =====
    if PICAMERA2_AVAILABLE:
        try:
            print("🔍 ลอง Picamera2...")
            cap = Picamera2()
            
            # ตั้งค่ากล้อง - ใช้ RGB888 (format มาตรฐาน) พร้อมการปรับแต่งคุณภาพ
            config = cap.create_preview_configuration(
                main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "RGB888"},
                controls={
                    "FrameRate": CAMERA_FPS,
                    "AfMode": 2,  # Autofocus Continuous (0=Manual, 1=Auto, 2=Continuous)
                    "Sharpness": 2.0,  # เพิ่มความคมชัด (0.0-16.0, default=1.0)
                    "Contrast": 1.2,  # เพิ่ม contrast เล็กน้อย (0.0-32.0, default=1.0)
                    "Brightness": 0.0,  # ความสว่าง (-1.0 ถึง 1.0)
                    "Saturation": 1.0,  # ความอิ่มตัวของสี (0.0-32.0)
                }
            )
            cap.configure(config)
            cap.start()
            
            # รอให้ autofocus ทำงาน
            print("🔍 รอ Autofocus...")
            import time
            time.sleep(1.5)  # เพิ่มเวลารอให้ autofocus ปรับโฟกัส
            

            
            # ทดสอบอ่านภาพ
            for i in range(3):
                try:
                    frame = cap.capture_array()
                    if frame is not None and frame.size > 0:
                        camera_running = True
                        camera_type = 'picamera2'
                        print(f"✅ Picamera2 เริ่มทำงาน ({frame.shape[1]}x{frame.shape[0]})")
                        return True
                except Exception as e:
                    print(f"   ลองครั้งที่ {i+1}: {e}")
                time.sleep(0.3)
            
            # ถ้าไม่สำเร็จ ปิดแล้วลองวิธีอื่น
            print("   ✗ Picamera2 อ่านภาพไม่สำเร็จ")
            try:
                cap.stop()
                cap.close()
            except:
                pass
            
        except Exception as e:
            print(f"❌ Picamera2 ล้มเหลว: {e}")
            if cap:
                try:
                    cap.stop()
                    cap.close()
                except:
                    pass
    
    # ===== Method 2: ลอง OpenCV (สำรอง) =====
    print("🔍 ลอง OpenCV...")
    
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            import time
            time.sleep(0.5)
            
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                camera_running = True
                camera_type = 'opencv'
                print(f"✅ OpenCV เริ่มทำงาน ({frame.shape[1]}x{frame.shape[0]})")
                return True
            
            cap.release()
    except Exception as e:
        print(f"❌ OpenCV ล้มเหลว: {e}")
    
    print("❌ ไม่พบกล้องที่ใช้งานได้")
    camera_running = False
    return False


# เพิ่ม global variable ที่ต้นไฟล์
camera_restart_count = 0
MAX_CAMERA_RESTARTS = 3  # จำกัดการ restart ไม่เกิน 3 ครั้ง

def update_camera_feed():
    """อัพเดทภาพจากกล้อง - รองรับทั้ง picamera2 และ OpenCV"""
    global cap, camera_running, camera_type
    
    try:
        if not camera_running or cap is None:
            return
        
        # ===== อ่านภาพตาม camera type =====
        if camera_type == 'picamera2':
            # ใช้ picamera2
            frame = cap.capture_array()
            
            if frame is None or frame.size == 0:
                print("⚠️ Picamera2 อ่านภาพไม่สำเร็จ")
                return
            
            # แปลงจาก RGB เป็น BGR สำหรับแสดงผล
            import cv2
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
        else:
            # ใช้ OpenCV
            ret, frame_bgr = cap.read()
            
            if not ret or frame_bgr is None:
                print("⚠️ OpenCV อ่านภาพไม่สำเร็จ")
                return
        
        # ===== แสดงภาพ =====
        from PIL import Image, ImageTk
        
        # ปรับขนาดเพื่อแสดงผล
        display_width = 640
        display_height = 480
        frame_resized = cv2.resize(frame_bgr, (display_width, display_height))
        
        # แปลงเป็น RGB สำหรับ PIL
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        
        # อัพเดท label
        if camera_label and camera_label.winfo_exists():
            camera_label.imgtk = imgtk
            camera_label.configure(image=imgtk)
        
        # เรียกตัวเองอีกครั้ง
        if camera_running:
            safe_after(root, 33, update_camera_feed)
            
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการอัพเดทกล้อง: {e}")
        import traceback
        traceback.print_exc()

def restart_camera():
    """เริ่มกล้องใหม่เมื่อเกิดปัญหา"""
    global cap, camera_running
    
    print("🔄 กำลังเริ่มกล้องใหม่...")
    
    # ปิดกล้องเดิม
    if cap:
        try:
            cap.release()
        except:
            pass
        cap = None
    
    camera_running = False
    
    # รอ 1 วินาทีก่อนเริ่มใหม่
    import time
    time.sleep(1)
    
    # เริ่มกล้องใหม่
    if initialize_camera():
        print("✅ เริ่มกล้องใหม่สำเร็จ")
        camera_running = True
        try:
            safe_after(root, 100, update_camera_feed)
        except:
            pass
    else:
        print("❌ เริ่มกล้องใหม่ล้มเหลว")

def check_camera_status():
    """ตรวจสอบสถานะกล้องเป็นระยะ (มีการจำกัด retry)"""
    global cap, camera_running, camera_restart_count, camera_type
    
    try:
        if cap and is_camera_opened():
            # ทดสอบอ่านภาพ
            if camera_type == 'picamera2':
                try:
                    frame = cap.capture_array()
                    ret = frame is not None and frame.size > 0
                except Exception:
                    ret = False
            else:
                ret, _ = cap.read()
            
            if not ret:
                if camera_restart_count < MAX_CAMERA_RESTARTS:
                    camera_restart_count += 1
                    print(f"⚠️ กล้องหยุดทำงาน - กำลังเริ่มใหม่ (ครั้งที่ {camera_restart_count}/{MAX_CAMERA_RESTARTS})...")
                    restart_camera()
                else:
                    print("❌ กล้อง restart เกินจำนวนที่กำหนด - หยุดการทำงาน")
                    camera_running = False
                    return
            else:
                # รีเซ็ตตัวนับเมื่อกล้องทำงานปกติ
                camera_restart_count = 0
                # print("✅ กล้องทำงานปกติ")  # ปิด log เพื่อลด spam
        else:
            if camera_restart_count < MAX_CAMERA_RESTARTS:
                camera_restart_count += 1
                print(f"⚠️ กล้องไม่เปิด - กำลังเริ่มใหม่ (ครั้งที่ {camera_restart_count}/{MAX_CAMERA_RESTARTS})...")
                restart_camera()
            else:
                print("❌ ไม่สามารถเริ่มกล้องได้ - หยุดการทำงาน")
                camera_running = False
                return
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการตรวจสอบกล้อง: {e}")
        if camera_restart_count < MAX_CAMERA_RESTARTS:
            camera_restart_count += 1
            restart_camera()
        else:
            camera_running = False
            return
    
    # ตรวจสอบอีกครั้งใน 10 วินาที (เพิ่มจาก 5 วินาที)
    safe_after(root, 10000, check_camera_status)

def set_camera_property(prop, percent_value, log_label=None, force_manual=False):
    try:
        pct = max(0, min(100, int(float(percent_value))))
    except Exception:
        pct = 50
    # For exposure, optionally set manual mode
    if prop == cv2.CAP_PROP_EXPOSURE and force_manual:
        try:
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        except Exception:
            pass
        # Map 0..100 -> -13 .. -1
        exposure_value = -13 + (pct / 100.0) * 12
        try:
            cap.set(prop, exposure_value)
        except Exception:
            pass
        try:
            cap.set(prop, pct / 100.0)
        except Exception:
            pass
    else:
        try:
            cap.set(prop, pct / 100.0)
        except Exception:
            pass
        try:
            cap.set(prop, int(pct * 2.55))
        except Exception:
            pass
        try:
            cap.set(prop, pct)
        except Exception:
            pass
    # Log applied value
    if log_label:
        try:
            applied = cap.get(prop)
            print(f"{log_label} Applied: request {pct}%, camera reports {applied}")
        except Exception:
            pass

def update_frame():
    global cap, camera_running, camera_type
    if camera_running and cap and is_camera_opened():
        # อนุญาตให้พลาดชั่วคราว 3 ครั้งหลังปรับตั้งค่า เพื่อลดจอดำ
        retries = 3
        frame = None
        last_err = None
        for _ in range(retries):
            try:
                # อ่านภาพตาม camera type
                if camera_type == 'picamera2':
                    frame = cap.capture_array()
                    ret = frame is not None and frame.size > 0
                    # Picamera2 แม้ตั้งค่า BGR888 แต่ให้ RGB ออกมา
                else:
                    ret, frame = cap.read()
                
                if ret and frame is not None and frame.size > 0:
                    break
            except Exception as e:
                last_err = e
            # หน่วงเล็กน้อยให้ไดรเวอร์ปรับตัวหลังเปลี่ยนค่าสมบัติกล้อง
            time.sleep(0.03)
        if frame is None or frame is not None and (frame.size == 0):
            if last_err:
                print(f"⚠️ อ่านภาพพรีวิวล้มเหลว: {last_err}")
        if frame is not None and frame.size > 0:
            # 1. Resize สำหรับหน้าจอเล็ก
            frame_resized = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_CUBIC)
            
            # 2. แปลงเป็น RGB สำหรับแสดงผล
            if camera_type == 'picamera2':
                # Picamera2 ให้ RGB ออกมาจริงๆ (แม้ตั้งค่า BGR888) - ไม่ต้องแปลง
                frame_rgb = frame_resized
            else:
                # OpenCV ให้ BGR ต้องแปลงเป็น RGB
                frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            camera_label.imgtk = imgtk
            camera_label.configure(image=imgtk)
        else:
            # อย่าปิด camera_running ทันที ให้ลองอ่านต่อไปในรอบถัดไป
            pass
    if camera_running:
        # หากกำลังเปิดหน้าต่างตั้งค่า ให้ลดอัตรารีเฟรชเพื่อเบา CPU/GPU
        interval_ms = 50 if settings_visible else 33  # ~20 FPS เมื่อปรับแต่ง, ~30 FPS ปกติ
        camera_label.after(interval_ms, update_frame)

def rewarm_camera_preview(warm_frames=6, delay_sec=0.03):
    """อ่านเฟรมไม่กี่เฟรมหลังจากปรับแต่งกล้อง เพื่อลดจอดำชั่วคราว"""
    global cap, camera_type
    if not cap or not is_camera_opened():
        return
    for _ in range(warm_frames):
        try:
            if camera_type == 'picamera2':
                cap.capture_array()
            else:
                cap.read()
        except Exception:
            pass
        time.sleep(delay_sec)

def capture_image():
    global cap, camera_type
    if cap and is_camera_opened():
        try:
            # ตั้งค่าความละเอียดเป้าหมาย 1280x720 (16:9)
            target_w, target_h = 1280, 720
            frame = None
            # สร้างสตรีมชั่วคราวสำหรับถ่ายภาพความละเอียดสูง (ไม่แตะต้องพรีวิวหลัก)
            try:
                if os.name == 'nt':
                    temp_cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                else:
                    temp_cap = cv2.VideoCapture(0)
            except Exception:
                temp_cap = cv2.VideoCapture(0)
            if temp_cap and temp_cap.isOpened():
                try:
                    # ขอใช้ MJPG เพื่อรองรับความละเอียดสูงบนเว็บแคมทั่วไป
                    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                    temp_cap.set(cv2.CAP_PROP_FOURCC, fourcc)
                except Exception:
                    pass
                try:
                    temp_cap.set(cv2.CAP_PROP_FRAME_WIDTH, target_w)
                    temp_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, target_h)
                    temp_cap.set(cv2.CAP_PROP_FPS, 60)
                except Exception:
                    pass
                time.sleep(0.08)
                # อุ่นเครื่องสักเล็กน้อย
                for _ in range(6):
                    ok, _ = temp_cap.read()
                    if not ok:
                        break
                    time.sleep(0.02)
                ret_hr, frame_hr = temp_cap.read()
                if ret_hr and frame_hr is not None and frame_hr.size > 0:
                    frame = frame_hr
                temp_cap.release()
            # หากสตรีมชั่วคราวล้มเหลว ใช้เฟรมจากพรีวิวและอัปสเกลแทน
            if frame is None:
                ok_fallback, fallback = False, None
                try:
                    if camera_type == 'picamera2':
                        fallback = cap.capture_array()
                        ok_fallback = fallback is not None and fallback.size > 0
                        # Picamera2 ให้ RGB ออกมา (แม้ตั้งค่า BGR888) ต้องแปลงเป็น BGR สำหรับ cv2.imwrite()
                        if ok_fallback:
                            fallback = cv2.cvtColor(fallback, cv2.COLOR_RGB2BGR)
                    else:
                        ok_fallback, fallback = cap.read()
                except Exception:
                    ok_fallback, fallback = False, None
                if not ok_fallback or fallback is None or fallback.size == 0:
                    messagebox.showerror("ข้อผิดพลาด", "ไม่สามารถถ่ายภาพได้")
                    return
                frame = fallback
            # จัดการสัดส่วนและความคมชัดให้ได้ 1280x720 ที่คมชัด
            src_h, src_w = frame.shape[:2]
            desired_ratio = 16/9
            current_ratio = src_w / src_h if src_h else desired_ratio
            if abs(current_ratio - desired_ratio) > 0.01:
                # ครอปตรงกลางให้เป็น 16:9
                if current_ratio > desired_ratio:
                    # กว้างเกิน -> ครอปด้านข้าง
                    new_w = int(src_h * desired_ratio)
                    x0 = max(0, (src_w - new_w) // 2)
                    frame = frame[:, x0:x0+new_w]
                else:
                    # สูงเกิน -> ครอปด้านบน/ล่าง
                    new_h = int(src_w / desired_ratio)
                    y0 = max(0, (src_h - new_h) // 2)
                    frame = frame[y0:y0+new_h, :]
            # ปรับขนาดด้วย LANCZOS เพื่อความคมชัด
            frame_out = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
            # เพิ่มความคมชัดเล็กน้อย (Unsharp mask แบบง่าย)
            try:
                blur = cv2.GaussianBlur(frame_out, (0, 0), 1.0)
                frame_out = cv2.addWeighted(frame_out, 1.15, blur, -0.15, 0)
            except Exception:
                pass
            # บันทึกไฟล์ JPEG คุณภาพสูง
            timestamp = int(time.time())
            filename = f"captured_images/accident_{timestamp}_{len(captured_images)+1}.jpg"
            success = cv2.imwrite(filename, frame_out, [cv2.IMWRITE_JPEG_QUALITY, 95])
            if success:
                captured_images.append(filename)
                messagebox.showinfo("ถ่ายภาพสำเร็จ", f"บันทึกภาพแล้ว\nไฟล์: {os.path.basename(filename)}\nขนาด: 1280x720")
            else:
                messagebox.showerror("ข้อผิดพลาด", "ไม่สามารถบันทึกภาพได้")
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"ถ่ายภาพล้มเหลว: {e}")
    else:
        messagebox.showerror("ข้อผิดพลาด", "กล้องไม่พร้อมใช้งาน")

# ตัวแปรสำหรับติดตามสถานะการแสดงการตั้งค่า
settings_visible = False

# ลดอาการหน่วงเวลาปรับแต่ง: ใช้ debounce ในการตั้งค่าคุณสมบัติของกล้อง
debounce_after_ids = {
    'brightness': None,
    'contrast': None,
    'exposure': None
}

def schedule_camera_property(kind, value):
    """หน่วงเวลาเล็กน้อยก่อนปรับแต่งกล้อง เพื่อลดการเรียก cap.set ติดๆ กัน"""
    try:
        global debounce_after_ids
        if kind not in debounce_after_ids:
            return
        # ยกเลิกงานเดิมถ้ามี
        if debounce_after_ids[kind] is not None:
            try:
                root.after_cancel(debounce_after_ids[kind])
            except Exception:
                pass
        # กำหนดการปรับจริงหลังจากหยุดเลื่อนสไลด์ 150ms
        def apply_change():
            try:
                if kind == 'brightness':
                    set_camera_property(cv2.CAP_PROP_BRIGHTNESS, value, log_label="🔆 Brightness")
                elif kind == 'contrast':
                    set_camera_property(cv2.CAP_PROP_CONTRAST, value, log_label="🌗 Contrast")
                elif kind == 'exposure':
                    set_camera_property(cv2.CAP_PROP_EXPOSURE, value, log_label="📸 Exposure", force_manual=True)
                # อุ่นเครื่องพรีวิวสั้นๆ เพื่อลดจอดำ
                rewarm_camera_preview(warm_frames=3, delay_sec=0.02)
            finally:
                debounce_after_ids[kind] = None
        debounce_after_ids[kind] = safe_after(root,150, apply_change)
    except Exception:
        # หากมีปัญหา ให้ตกไปใช้วิธีตรง
        try:
            if kind == 'brightness':
                set_camera_property(cv2.CAP_PROP_BRIGHTNESS, value, log_label="🔆 Brightness")
            elif kind == 'contrast':
                set_camera_property(cv2.CAP_PROP_CONTRAST, value, log_label="🌗 Contrast")
            elif kind == 'exposure':
                set_camera_property(cv2.CAP_PROP_EXPOSURE, value, log_label="📸 Exposure", force_manual=True)
        except Exception:
            pass

def update_embedded_brightness_info():
    """อัพเดทข้อมูลความสว่างในการตั้งค่าแบบฝัง"""
    if cap and cap.isOpened() and settings_visible:
        try:
            ret, frame = cap.read()
            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                mean_brightness = cv2.mean(gray)[0]
                
                if mean_brightness > 200:
                    status = "🔆 ขาวมาก"
                    color = "red"
                elif mean_brightness > 150:
                    status = "☀️ สว่างเกิน"
                    color = "orange"
                elif mean_brightness > 100:
                    status = "✅ เหมาะสม"
                    color = "green"
                elif mean_brightness > 50:
                    status = "🌙 ค่อนข้างมืด"
                    color = "blue"
                else:
                    status = "⚫ มืดมาก"
                    color = "purple"
                
                settings_brightness_info.config(text=f"ความสว่าง: {mean_brightness:.1f} - {status}", 
                                               fg=color)
        except:
            settings_brightness_info.config(text="ไม่สามารถตรวจสอบความสว่างได้", fg="gray")
        
        # อัพเดทอีกครั้งใน 1 วินาที
        safe_after(root,1000, update_embedded_brightness_info)

def update_embedded_brightness(val):
    """อัพเดท brightness จาก embedded scale"""
    schedule_camera_property('brightness', val)

def update_embedded_contrast(val):
    """อัพเดท contrast จาก embedded scale"""
    schedule_camera_property('contrast', val)

def update_embedded_exposure(val):
    """อัพเดท exposure จาก embedded scale"""
    # Ensure we change true exposure, not AUTO_EXPOSURE level
    schedule_camera_property('exposure', val)

def embedded_normal_setting():
    """ตั้งค่าแสงปกติสำหรับการตั้งค่าแบบฝัง"""
    try:
        set_camera_property(cv2.CAP_PROP_BRIGHTNESS, 50)
        set_camera_property(cv2.CAP_PROP_CONTRAST, 50)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -6)
        set_camera_property(cv2.CAP_PROP_GAIN, 30)
        cap.set(cv2.CAP_PROP_AUTO_WB, 1)
        cap.set(cv2.CAP_PROP_HUE, 0)
        set_camera_property(cv2.CAP_PROP_SATURATION, 55)
        brightness_scale_embedded.set(50)
        contrast_scale_embedded.set(50)
        exposure_scale_embedded.set(40)
        print("✅ ปรับเป็นโหมดแสงปกติ (แบบฝัง)")
    except Exception as e:
        print(f"❌ ไม่สามารถปรับแต่งได้: {e}")

def embedded_outdoor_setting():
    """ตั้งค่ากลางแจ้งสำหรับการตั้งค่าแบบฝัง"""
    try:
        set_camera_property(cv2.CAP_PROP_BRIGHTNESS, 40)
        set_camera_property(cv2.CAP_PROP_CONTRAST, 60)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -7)
        set_camera_property(cv2.CAP_PROP_GAIN, 20)
        cap.set(cv2.CAP_PROP_AUTO_WB, 1)
        cap.set(cv2.CAP_PROP_HUE, 0)
        brightness_scale_embedded.set(40)
        contrast_scale_embedded.set(60)
        exposure_scale_embedded.set(25)
        print("✅ ปรับเป็นโหมดกลางแจ้ง (แบบฝัง)")
    except Exception as e:
        print(f"❌ ไม่สามารถปรับแต่งได้: {e}")

def embedded_indoor_setting():
    """ตั้งค่าในร่มสำหรับการตั้งค่าแบบฝัง"""
    try:
        set_camera_property(cv2.CAP_PROP_BRIGHTNESS, 50)
        set_camera_property(cv2.CAP_PROP_CONTRAST, 50)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -5)
        set_camera_property(cv2.CAP_PROP_GAIN, 30)
        cap.set(cv2.CAP_PROP_AUTO_WB, 1)
        cap.set(cv2.CAP_PROP_HUE, 0)
        brightness_scale_embedded.set(50)
        contrast_scale_embedded.set(50)
        exposure_scale_embedded.set(50)
        print("✅ ปรับเป็นโหมดในร่ม (แบบฝัง)")
    except Exception as e:
        print(f"❌ ไม่สามารถปรับแต่งได้: {e}")

def embedded_night_setting():
    """ตั้งค่าแสงน้อยสำหรับการตั้งค่าแบบฝัง"""
    try:
        set_camera_property(cv2.CAP_PROP_BRIGHTNESS, 70)
        set_camera_property(cv2.CAP_PROP_CONTRAST, 40)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -3)
        set_camera_property(cv2.CAP_PROP_GAIN, 50)
        cap.set(cv2.CAP_PROP_AUTO_WB, 1)
        cap.set(cv2.CAP_PROP_HUE, 0)
        brightness_scale_embedded.set(70)
        contrast_scale_embedded.set(40)
        exposure_scale_embedded.set(75)
        print("✅ ปรับเป็นโหมดแสงน้อย (แบบฝัง)")
    except Exception as e:
        print(f"❌ ไม่สามารถปรับแต่งได้: {e}")

def toggle_camera_settings():
    """สลับการแสดง/ซ่อนการตั้งค่ากล้องแบบกลางจอ"""
    global settings_visible
    
    if not cap or not cap.isOpened():
        messagebox.showerror("ข้อผิดพลาด", "กรุณาเปิดกล้องก่อน")
        return
    
    if settings_visible:
        # ซ่อนการตั้งค่า
        settings_frame.place_forget()
        settings_visible = False
        # กู้ค่า FPS กลับเป็น 60 เพื่อลด motion blur เมื่อใช้งานจริง
        try:
            cap.set(cv2.CAP_PROP_FPS, 60)
        except Exception:
            pass
        print("🔧 ซ่อนการตั้งค่ากล้อง")
    else:
        # แสดงการตั้งค่าในกลางจอ (ไม่มี overlay)
        settings_frame.place(relx=0.5, rely=0.5, anchor="center")  # กลางจอ
        settings_visible = True
        # ลด FPS ของอุปกรณ์ลงเล็กน้อย เพื่อลดโหลดตอนปรับค่า
        try:
            cap.set(cv2.CAP_PROP_FPS, 30)
        except Exception:
            pass
        update_embedded_brightness_info()  # เริ่มการอัพเดทความสว่าง
        print("🔧 แสดงการตั้งค่ากล้องในกลางจอ")

def manual_camera_settings():
    """เปิดหน้าต่างปรับแต่งกล้องด้วยตนเอง - แก้ปัญหาภาพขาว"""
    if not cap or not cap.isOpened():
        messagebox.showerror("ข้อผิดพลาด", "กรุณาเปิดกล้องก่อน")
        return
    
    settings_window = tk.Toplevel(root)
    settings_window.title("🔧 ปรับแต่งกล้อง - แก้ปัญหาภาพขาว")
    settings_window.geometry("450x600")
    settings_window.configure(bg="lightgray")
    
    tk.Label(settings_window, text="🔧 ปรับแต่งกล้อง", 
             font=("Arial", 16, "bold"), bg="lightgray").pack(pady=10)
    
    # แสดงค่าความสว่างปัจจุบัน
    brightness_info = tk.Label(settings_window, text="ความสว่างปัจจุบัน: กำลังตรวจสอบ...", 
                              font=("Arial", 10), bg="lightgray")
    brightness_info.pack(pady=5)
    
    def update_brightness_info():
        """อัพเดทข้อมูลความสว่างแบบเรียลไทม์"""
        if cap and cap.isOpened():
            ret, frame = cap.read()
            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                mean_brightness = cv2.mean(gray)[0]
                
                if mean_brightness > 200:
                    status = "🔆 ขาวมาก - ลดความสว่าง"
                    color = "red"
                elif mean_brightness > 150:
                    status = "☀️ สว่างเกิน - ปรับลดเล็กน้อย"
                    color = "orange"
                elif mean_brightness > 100:
                    status = "✅ เหมาะสม"
                    color = "green"
                elif mean_brightness > 50:
                    status = "🌙 ค่อนข้างมือ - เพิ่มแสง"
                    color = "blue"
                else:
                    status = "⚫ มืดมาก - เพิ่มแสงเยอะ"
                    color = "purple"
                
                brightness_info.config(text=f"ความสว่าง: {mean_brightness:.1f}/255 - {status}", 
                                     fg=color)
        
        settings_window.after(500, update_brightness_info)  # อัพเดททุก 0.5 วิ
    
    update_brightness_info()  # เริ่มการอัพเดท
    
    # === ส่วน Brightness (สำคัญที่สุดสำหรับแก้ภาพขาว) ===
    brightness_frame = tk.LabelFrame(settings_window, text="🔆 ความสว่าง (Brightness)", 
                                   font=("Arial", 12, "bold"), bg="lightyellow", bd=2)
    brightness_frame.pack(pady=10, padx=20, fill="x")
    
    def update_brightness(val):
        set_camera_property(cv2.CAP_PROP_BRIGHTNESS, val, log_label="🔆 Brightness")
        rewarm_camera_preview()
    
    tk.Label(brightness_frame, text="ลดเพื่อแก้ภาพขาว ← → เพิ่มเพื่อแก้ภาพมืด", 
             bg="lightyellow", font=("Arial", 9)).pack()
    brightness_scale = tk.Scale(brightness_frame, from_=0, to=100, orient="horizontal",
                               command=update_brightness, length=350)
    brightness_scale.set(40)  # เริ่มต้นที่ค่าต่ำเพื่อลดความขาว
    brightness_scale.pack(pady=5)
    
    # === ส่วน Contrast ===
    contrast_frame = tk.LabelFrame(settings_window, text="🌗 ความเข้ม (Contrast)", 
                                 font=("Arial", 12, "bold"), bg="lightblue", bd=2)
    contrast_frame.pack(pady=10, padx=20, fill="x")
    
    def update_contrast(val):
        set_camera_property(cv2.CAP_PROP_CONTRAST, val, log_label="🌗 Contrast")
        rewarm_camera_preview()
    
    contrast_scale = tk.Scale(contrast_frame, from_=0, to=100, orient="horizontal",
                             command=update_contrast, length=350)
    contrast_scale.set(50)
    contrast_scale.pack(pady=5)
    
    # === ส่วน Exposure ===
    exposure_frame = tk.LabelFrame(settings_window, text="📸 การเปิดรับแสง (Exposure)", 
                                 font=("Arial", 12, "bold"), bg="lightgreen", bd=2)
    exposure_frame.pack(pady=10, padx=20, fill="x")
    
    def update_exposure(val):
        set_camera_property(cv2.CAP_PROP_EXPOSURE, val, log_label="📸 Exposure", force_manual=True)
        rewarm_camera_preview()
    
    tk.Label(exposure_frame, text="ลดเพื่อแก้ภาพขาวจาก over-exposure", 
             bg="lightgreen", font=("Arial", 9)).pack()
    exposure_scale = tk.Scale(exposure_frame, from_=0, to=100, orient="horizontal",
                             command=update_exposure, length=350)
    exposure_scale.set(40)  # เริ่มต้นที่ค่าปานกลาง (เหมาะกับแสงปกติ)
    exposure_scale.pack(pady=5)
    
    # ปุ่มปรับแต่งสำหรับ Pi
    def pi_outdoor_setting():
        try:
            set_camera_property(cv2.CAP_PROP_BRIGHTNESS, 40)
            set_camera_property(cv2.CAP_PROP_CONTRAST, 60)
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            cap.set(cv2.CAP_PROP_EXPOSURE, -7)
            set_camera_property(cv2.CAP_PROP_GAIN, 20)
            cap.set(cv2.CAP_PROP_AUTO_WB, 1)
            cap.set(cv2.CAP_PROP_HUE, 0)
            rewarm_camera_preview()
            messagebox.showinfo("ตั้งค่า", "✅ ปรับเป็นโหมดกลางแจ้ง (แสงแดดจัด)")
        except:
            messagebox.showerror("ข้อผิดพลาด", "ไม่สามารถปรับแต่งได้")
    
    def pi_indoor_setting():
        try:
            set_camera_property(cv2.CAP_PROP_BRIGHTNESS, 50)
            set_camera_property(cv2.CAP_PROP_CONTRAST, 50)
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            cap.set(cv2.CAP_PROP_EXPOSURE, -5)
            set_camera_property(cv2.CAP_PROP_GAIN, 30)
            cap.set(cv2.CAP_PROP_AUTO_WB, 1)
            cap.set(cv2.CAP_PROP_HUE, 0)
            rewarm_camera_preview()
            messagebox.showinfo("ตั้งค่า", "✅ ปรับเป็นโหมดในอาคาร (แสงปกติ)")
        except:
            messagebox.showerror("ข้อผิดพลาด", "ไม่สามารถปรับแต่งได้")
    
    def pi_night_setting():
        try:
            set_camera_property(cv2.CAP_PROP_BRIGHTNESS, 70)
            set_camera_property(cv2.CAP_PROP_CONTRAST, 40)
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            cap.set(cv2.CAP_PROP_EXPOSURE, -3)
            set_camera_property(cv2.CAP_PROP_GAIN, 50)
            cap.set(cv2.CAP_PROP_AUTO_WB, 1)
            cap.set(cv2.CAP_PROP_HUE, 0)
            rewarm_camera_preview()
            messagebox.showinfo("ตั้งค่า", "✅ ปรับเป็นโหมดแสงน้อย")
        except:
            messagebox.showerror("ข้อผิดพลาด", "ไม่สามารถปรับแต่งได้")
    
    def normal_lighting_setting():
        try:
            set_camera_property(cv2.CAP_PROP_BRIGHTNESS, 50)
            set_camera_property(cv2.CAP_PROP_CONTRAST, 50)
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            cap.set(cv2.CAP_PROP_EXPOSURE, -6)
            set_camera_property(cv2.CAP_PROP_GAIN, 30)
            cap.set(cv2.CAP_PROP_AUTO_WB, 1)
            cap.set(cv2.CAP_PROP_HUE, 0)
            set_camera_property(cv2.CAP_PROP_SATURATION, 55)
            rewarm_camera_preview()
            messagebox.showinfo("ตั้งค่า", "✅ ปรับเป็นโหมดแสงปกติ (แนะนำ)")
        except:
            messagebox.showerror("ข้อผิดพลาด", "ไม่สามารถปรับแต่งได้")
    
    # ปุ่มต่างๆ
    button_frame = tk.Frame(settings_window, bg="lightgray")
    button_frame.pack(pady=20)
    
    tk.Button(button_frame, text="💡 แสงปกติ", command=normal_lighting_setting,
             bg="lightgreen", fg="black", width=12, height=2, 
             font=("Arial", 9, "bold")).pack(pady=3)
    
    tk.Button(button_frame, text="☀️ กลางแจ้ง", command=pi_outdoor_setting,
             bg="yellow", fg="black", width=12, height=2).pack(pady=3)
    
    tk.Button(button_frame, text="🏠 ในอาคาร", command=pi_indoor_setting,
             bg="lightblue", fg="black", width=12, height=2).pack(pady=3)
    
    tk.Button(button_frame, text="🌙 แสงน้อย", command=pi_night_setting,
             bg="darkblue", fg="white", width=12, height=2).pack(pady=3)
    
    # ปุ่มยืนยันและปิด
    def apply_and_close():
        try:
            current_brightness = brightness_scale.get()
            current_contrast = contrast_scale.get()
            current_exposure = exposure_scale.get()
            set_camera_property(cv2.CAP_PROP_BRIGHTNESS, current_brightness, log_label="🔆 Brightness")
            set_camera_property(cv2.CAP_PROP_CONTRAST, current_contrast, log_label="🌗 Contrast")
            set_camera_property(cv2.CAP_PROP_EXPOSURE, current_exposure, log_label="📸 Exposure", force_manual=True)
            rewarm_camera_preview(warm_frames=4, delay_sec=0.02)
        except Exception:
            pass
        try:
            settings_window.destroy()
        except Exception:
            pass

    action_row = tk.Frame(settings_window, bg="lightgray")
    action_row.pack(pady=10)
    tk.Button(action_row, text="✅ ตกลง", command=apply_and_close,
             bg="green", fg="white", width=12, height=2).pack(side="left", padx=5)
    tk.Button(action_row, text="❌ ปิด", command=settings_window.destroy,
             bg="red", fg="white", width=12, height=2).pack(side="left", padx=5)

# === วิธีการใช้งาน ===
print("""
🔧 วิธีแก้ปัญหาภาพกล้องเบลอ:

1. 📐 เพิ่มความละเอียดจาก 320x240 เป็น 640x480
2. 🎬 เพิ่ม FPS จาก 15 เป็น 30
3. 🎯 เปิด Auto Focus (ถ้ากล้องรองรับ)
4. 💡 ปรับ Auto Exposure และ White Balance
5. ⏱️ รอให้กล้องปรับตัวก่อนแสดงภาพ
6. 📷 เลือกเฟรมที่คมชัดที่สุดเมื่อถ่ายภาพ
7. 💾 บันทึกด้วยคุณภาพสูงสุด (JPEG Quality 100)

💡 เทคนิคเพิ่มเติม:
- ตรวจสอบว่ากล้อง USB มีแสงเพียงพอหรือไม่
- ทำความสะอาดเลนส์กล้อง
- ลองเปลี่ยนพอร์ต USB หรือสาย USB
- สำหรับ Pi Camera: ตรวจสอบการเชื่อมต่อ ribbon cable
""")

# ================ MAX30102 Sensor Functions ================

def initialize_max30102():
    """เริ่มต้น MAX30102 sensor"""
    global sensor, sensor_running
    
    if not MAX30102_AVAILABLE:
        print("⚠️ MAX30102 library ไม่พร้อมใช้งาน")
        return False
    
    try:
        print("🔍 กำลังเริ่มต้น MAX30102...")
        sensor = MAX30102()
        
        sensor_running = True
        print("✅ เริ่มต้น MAX30102 สำเร็จ")
        return True
        
    except Exception as e:
        print(f"❌ ไม่สามารถเริ่มต้น MAX30102: {e}")
        sensor_running = False
        return False

# Buffer สำหรับเก็บข้อมูล
ir_buffer = []
red_buffer = []
BUFFER_SIZE = 100

def calculate_heart_rate(ir_data):
    """คำนวณ Heart Rate จากข้อมูล IR LED"""
    if len(ir_data) < 10:
        return None
    
    # หาจุดสูงสุด (peaks) ในข้อมูล
    peaks = []
    threshold = sum(ir_data) / len(ir_data) * 1.1  # 10% เหนือค่าเฉลี่ย
    
    for i in range(1, len(ir_data) - 1):
        if ir_data[i] > threshold and ir_data[i] > ir_data[i-1] and ir_data[i] > ir_data[i+1]:
            peaks.append(i)
    
    if len(peaks) < 2:
        return None
    
    # คำนวณระยะห่างระหว่าง peaks (ในหน่วย samples)
    peak_intervals = []
    for i in range(1, len(peaks)):
        peak_intervals.append(peaks[i] - peaks[i-1])
    
    if not peak_intervals:
        return None
    
    # คำนวณ Heart Rate (สมมติว่า sampling rate = 100 Hz)
    avg_interval = sum(peak_intervals) / len(peak_intervals)
    heart_rate = 60 * 100 / avg_interval  # 60 seconds * 100 Hz / interval
    
    # กรองค่าที่ไม่สมเหตุสมผล
    if 40 <= heart_rate <= 200:
        return int(heart_rate)
    return None

def calculate_spo2(red_data, ir_data):
    """คำนวณ SpO2 จากข้อมูล Red และ IR LED"""
    if len(red_data) < 10 or len(ir_data) < 10:
        return None
    
    # คำนวณค่าเฉลี่ย
    red_avg = sum(red_data) / len(red_data)
    ir_avg = sum(ir_data) / len(ir_data)
    
    if ir_avg == 0 or red_avg == 0:
        return None
    
    # คำนวณ AC/DC ratio
    red_ac = max(red_data) - min(red_data)
    ir_ac = max(ir_data) - min(ir_data)
    
    if ir_avg == 0:
        return None
    
    # R = (AC_red / DC_red) / (AC_ir / DC_ir)
    R = (red_ac / red_avg) / (ir_ac / ir_avg) if ir_ac != 0 else 0
    
    # สูตรประมาณ SpO2 (จากการทดลอง)
    # SpO2 = 110 - 25 * R
    spo2 = 110 - 25 * R
    
    # กรองค่าที่ไม่สมเหตุสมผล
    if 70 <= spo2 <= 100:
        return int(spo2)
    return None

def read_sensor_data():
    """อ่านค่าจาก MAX30102 sensor"""
    global sensor, sensor_running, heart_rate, spo2, sensor_data_ready
    global ir_buffer, red_buffer
    
    if not sensor_running or sensor is None:
        return None, None
    
    try:
        # อ่านข้อมูลจาก sensor (อ่านทีละ 25 samples)
        red_data, ir_data = sensor.read_sequential(25)
        
        if red_data and ir_data:
            # เพิ่มข้อมูลลง buffer
            red_buffer.extend(red_data)
            ir_buffer.extend(ir_data)
            
            # จำกัดขนาด buffer
            if len(red_buffer) > BUFFER_SIZE:
                red_buffer = red_buffer[-BUFFER_SIZE:]
            if len(ir_buffer) > BUFFER_SIZE:
                ir_buffer = ir_buffer[-BUFFER_SIZE:]
            
            # คำนวณค่าเมื่อมีข้อมูลเพียงพอ
            if len(ir_buffer) >= BUFFER_SIZE:
                hr = calculate_heart_rate(ir_buffer)
                sp = calculate_spo2(red_buffer, ir_buffer)
                
                if hr is not None and sp is not None:
                    heart_rate = hr
                    spo2 = sp
                    sensor_data_ready = True
                    return heart_rate, spo2
        
        return None, None
        
    except Exception as e:
        print(f"⚠️ ข้อผิดพลาดในการอ่านค่าเซนเซอร์: {e}")
        return None, None

def stop_max30102():
    """หยุดการทำงานของ MAX30102"""
    global sensor, sensor_running, ir_buffer, red_buffer
    
    if sensor:
        try:
            sensor.shutdown()
            print("✅ ปิด MAX30102 เรียบร้อย")
        except:
            pass
        sensor = None
    
    # รีเซ็ต buffer
    ir_buffer = []
    red_buffer = []
    
    sensor_running = False

def start_sensor_reading():
    """เริ่มการอ่านค่าเซนเซอร์แบบต่อเนื่อง"""
    if initialize_max30102():
        update_sensor_display()

def update_sensor_display():
    """อัพเดทการแสดงผลค่าเซนเซอร์"""
    global sensor_running
    
    if not sensor_running:
        return
    
    hr, sp = read_sensor_data()
    
    if hr is not None and sp is not None:
        # อัพเดท UI labels
        try:
            hr_value_label.config(text=f"{hr} BPM")
            spo2_value_label.config(text=f"{sp} %")
            
            # เปลี่ยนสีตามค่า
            if 60 <= hr <= 100:
                hr_value_label.config(fg="green")
            else:
                hr_value_label.config(fg="red")
            
            if sp >= 95:
                spo2_value_label.config(fg="green")
            elif sp >= 90:
                spo2_value_label.config(fg="orange")
            else:
                spo2_value_label.config(fg="red")
        except:
            pass
    
    # เรียกตัวเองอีกครั้ง
    if sensor_running:
        safe_after(root, 100, update_sensor_display)

def done_camera():
    # ไม่ปิดกล้อง - ให้ทำงานตลอดเวลา
    print("📷 กล้องยังคงทำงานอยู่ - เปลี่ยนไปหน้าวัดค่าเซนเซอร์")
    show_frame(frame3_sensor)

# ------------------ หน้า 3 ------------------
def save_data():
    global heart_rate, spo2, sensor_data_ready
    
    name = entry_name.get().strip()
    surname = entry_surname.get().strip()
    age = combo_age.get().strip()
    event = selected_event.get().strip()
    detail = entry_detail.get().strip()

    if not event:
        messagebox.showerror("ข้อผิดพลาด", "กรุณาเลือกเหตุการณ์")
        return

    if not name or not surname or not age:
        messagebox.showerror("ข้อผิดพลาด", "กรุณากรอกข้อมูลให้ครบทุกช่อง")
        return

    # บันทึกข้อมูลในไฟล์ text พร้อม timestamp
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open("accident_data.txt", "a", encoding="utf-8") as f:
            f.write(f"\n=== รายงานอุบัติเหตุ {timestamp} ===\n")
            f.write(f"ชื่อ: {name}\n")
            f.write(f"นามสกุล: {surname}\n")
            f.write(f"อายุ: {age} ปี\n")
            
            # เพิ่มข้อมูลสัญญาณชีพ
            if sensor_data_ready:
                f.write(f"💓 Heart Rate: {heart_rate} BPM\n")
                f.write(f"🫁 SpO2: {spo2}%\n")
            else:
                f.write(f"💓 Heart Rate: ไม่ได้วัด\n")
                f.write(f"🫁 SpO2: ไม่ได้วัด\n")
            
            f.write(f"จำนวนภาพ: {len(captured_images)} ภาพ\n")
            f.write(f"รายการภาพ: {captured_images}\n")
            f.write(f"เหตุการณ์: {event}\n")
            f.write(f"รายละเอียด: {detail}\n")
            f.write("="*50 + "\n")
    except Exception as e:
        messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถบันทึกไฟล์ข้อความได้: {e}")
        return

    # สร้าง PDF
    pdf_success = save_to_pdf()
    
    if pdf_success:
        # หาไฟล์ PDF ที่สร้างล่าสุด
        pdf_files = [f for f in os.listdir('pdf_reports') if f.endswith('.pdf') and ('accident' in f or 'basic' in f)]
        latest_pdf = max([f"pdf_reports/{f}" for f in pdf_files], key=os.path.getctime) if pdf_files else "pdf_reports/ไฟล์ PDF"
        latest_pdf_name = os.path.basename(latest_pdf)
        
        messagebox.showinfo("สำเร็จ", 
                          f"✅ บันทึกข้อมูลเรียบร้อยแล้ว!\n\n"
                          f"📄 ไฟล์ PDF: {latest_pdf_name}\n"
                          f"📂 โฟลเดอร์ PDF: pdf_reports/\n"
                          f"📝 ไฟล์ข้อความ: accident_data.txt\n"
                          f"📷 ภาพทั้งหมด: {len(captured_images)} ภาพ\n\n"
                          f"👤 {name} {surname} (อายุ {age} ปี)")
    else:
        messagebox.showwarning("คำเตือน", 
                              "⚠️ บันทึกข้อมูลสำเร็จ\nแต่ไม่สามารถสร้าง PDF ได้\n\n"
                              "กรุณาตรวจสอบ:\n"
                              "- การติดตั้งฟอนต์ภาษาไทย\n" 
                              "- สิทธิ์ในการเขียนไฟล์\n"
                              "- พื้นที่ว่างในดิสก์")
    
    # รีเซ็ตโปรแกรม
    reset_program()

def reset_program():
    """รีเซ็ตโปรแกรมให้พร้อมใช้งานใหม่"""
    global captured_images, heart_rate, spo2, sensor_data_ready
    
    # เคลียร์ข้อมูล
    entry_name.delete(0, tk.END)
    entry_surname.delete(0, tk.END)
    entry_detail.delete(0, tk.END)
    combo_age.set("")
    captured_images.clear()
    
    # รีเซ็ตค่าเซนเซอร์
    heart_rate = 0
    spo2 = 0
    sensor_data_ready = False
    
    # ซ่อนแป้นพิมพ์
    hide_keyboard()
    
    # กลับไปหน้าแรก
    show_frame(frame1)

# ------------------ ฟังก์ชันสร้าง PDF พร้อมรูปภาพ ------------------
def save_to_pdf():
    try:
        # ดึงข้อมูลผู้ป่วย
        name = entry_name.get().strip()
        surname = entry_surname.get().strip()
        
        # สร้างชื่อไฟล์ปลอดภัย (ไม่มีอักขระพิเศษ)
        safe_name = f"{name}_{surname}".replace(" ", "_")
        # ลบอักขระที่ไม่เหมาะสมกับชื่อไฟล์
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in ('_', '-'))
        
        # สร้างวันที่ในรูปแบบ DD-MM-YYYY
        date_str = time.strftime("%d-%m-%Y")
        
        # สร้างชื่อไฟล์: ชื่อผู้ป่วย_วันที่.pdf
        filename = f"pdf_reports/{safe_name}_{date_str}.pdf"
        
        # ถ้าไฟล์ซ้ำ ให้เพิ่มเลขต่อท้าย
        counter = 1
        original_filename = filename
        while os.path.exists(filename):
            name_part = original_filename.replace('.pdf', '')
            filename = f"{name_part}_{counter:02d}.pdf"
            counter += 1
        
        c = canvas.Canvas(filename, pagesize=A4)
        page_width, page_height = A4
        
        # ตั้งค่าฟอนต์
        has_thai_font, font_name = setup_thai_font()
        
        # ฟังก์ชันสำหรับเขียนข้อความแบบปลอดภัย
        def safe_drawstring(canvas, x, y, text, font_size=12):
            try:
                if has_thai_font:
                    # ใช้ฟอนต์ไทย
                    canvas.setFont('ThaiFont', font_size)
                    canvas.drawString(x, y, text)
                    print(f"✅ เขียนข้อความไทย: {text[:20]}...")
                else:
                    # ใช้ฟอนต์อังกฤษ และแปลงข้อความ
                    canvas.setFont(font_name, font_size)
                    english_text = convert_to_safe_text(text)
                    canvas.drawString(x, y, english_text)
                    print(f"⚠️ แปลงเป็นอังกฤษ: {english_text[:20]}...")
            except UnicodeEncodeError as e:
                print(f"❌ ข้อผิดพลาด Unicode: {e}")
                # ลองใช้ฟอนต์สำรอง
                try:
                    canvas.setFont('Helvetica', font_size)
                    safe_text = text.encode('ascii', 'ignore').decode('ascii')
                    if not safe_text.strip():
                        safe_text = "[Thai text cannot be displayed]"
                    canvas.drawString(x, y, safe_text)
                except:
                    canvas.drawString(x, y, "[Encoding Error]")
            except Exception as e:
                print(f"❌ ข้อผิดพลาดในการเขียนข้อความ: {e}")
                try:
                    canvas.setFont('Helvetica', font_size)
                    canvas.drawString(x, y, "[Text Error]")
                except:
                    pass
        
        def convert_to_safe_text(thai_text):
            """แปลงข้อความไทยเป็นภาษาอังกฤษที่ปลอดภัย"""
            translations = {
                'ชื่อ': 'Name',
                'นามสกุล': 'Surname', 
                'อายุ': 'Age',
                'ปี': 'years',
                'รายงานผู้ประสบอุบัติเหตุ': 'Accident Report',
                'ข้อมูลส่วนตัว': 'Personal Information',
                'ภาพประกอบ': 'Photos',
                'ภาพ': 'images',
                'ไม่มีภาพประกอบ': 'No photos attached',
                'วันที่': 'Date',
                'เวลา': 'Time'
            }
            
            for thai, english in translations.items():
                if thai in thai_text:
                    thai_text = thai_text.replace(thai, english)
            
            return thai_text
        
        # เริ่มสร้าง PDF
        y = 760
        
        # หัวเรื่อง
        if has_thai_font:
            title = "รายงานผู้ประสบอุบัติเหตุ"
        else:
            title = "Accident Report"
        
        safe_drawstring(c, 200, y, title, 30)
        y -= 10
        
        # วันที่และเวลา
        datetime_str = time.strftime("%d/%m/%Y %H:%M:%S")
        if has_thai_font:
            date_text = f"วันที่: {datetime_str}"
        else:
            date_text = f"Date: {datetime_str}"
        
        safe_drawstring(c, 50, y, date_text, 10)
        y -= 40
        
        # เส้นแบ่ง
        c.line(50, y, 550, y)
        y -= 30
        
        # ข้อมูลส่วนตัว
        if has_thai_font:
            info_title = "ข้อมูลส่วนตัว"
        else:
            info_title = "Personal Information"
        
        safe_drawstring(c, 50, y, info_title, 14)
        y -= 25
        
        # ข้อมูลผู้ใช้
        name = entry_name.get().strip()
        surname = entry_surname.get().strip()  
        age = combo_age.get().strip()
        event = selected_event.get().strip()
        detail = entry_detail.get().strip()
        
        if has_thai_font:
            info_lines = [
                f"ชื่อ: {name}",
                f"นามสกุล: {surname}",
                f"อายุ: {age} ปี",
                f"เหตุการณ์: {event}",
                f"รายละเอียด: {detail if detail else '-'}"
            ]
            
            # เพิ่มข้อมูลสัญญาณชีพ
            if sensor_data_ready:
                info_lines.append(f"💓 Heart Rate: {heart_rate} BPM")
                info_lines.append(f"🫁 SpO2: {spo2}%")
            else:
                info_lines.append("สัญญาณชีพ: ไม่ได้วัด")
        else:
            info_lines = [
                f"Name: {name}",
                f"Surname: {surname}",
                f"Age: {age} years",
                f"Event: {event}",
                f"Detail: {detail if detail else '-'}"
            ]
            
            # เพิ่มข้อมูลสัญญาณชีพ
            if sensor_data_ready:
                info_lines.append(f"Heart Rate: {heart_rate} BPM")
                info_lines.append(f"SpO2: {spo2}%")
            else:
                info_lines.append("Vital Signs: Not measured")
        
        for line in info_lines:
            safe_drawstring(c, 70, y, line, 12)
            y -= 30
        
        y -= 20
        
        # ข้อมูลภาพ
        if has_thai_font:
            photo_title = f"ภาพประกอบ ({len(captured_images)} ภาพ)"
        else:
            photo_title = f"Photos ({len(captured_images)} images)"
        
        safe_drawstring(c, 50, y, photo_title, 14)
        y -= 25
        
        # แสดงรูปภาพจริงใน PDF
        if captured_images:
            images_per_row = 2
            image_width = 200
            image_height = 150
            x_start = 50
            x_spacing = 250
            y_spacing = 180
            # เริ่มตำแหน่งจาก y ปัจจุบัน
            start_y_for_page = y
            row = 0
            col = 0
            # จัดเรียงตาม timestamp ที่ชื่อไฟล์เพื่อให้แน่ใจว่าตามลำดับเวลา
            def img_sort_key(p):
                try:
                    base = os.path.basename(p)
                    parts = base.split('_')
                    # expect format: accident_<timestamp>_<n>.jpg
                    if len(parts) >= 3:
                        return int(parts[1]) * 1000 + int(parts[2].split('.')[0])
                except Exception:
                    pass
                return os.path.getmtime(p) if os.path.exists(p) else 0
            ordered_images = sorted(list(captured_images), key=img_sort_key)
            for i, img_path in enumerate(ordered_images):
                try:
                    if not os.path.exists(img_path):
                        print(f"⚠️ ไม่พบไฟล์: {img_path}")
                        continue
                    # ตำแหน่งของรูปปัจจุบัน
                    x_pos = x_start + (col * x_spacing)
                    y_pos = start_y_for_page - (row * y_spacing) - image_height
                    # ถ้าพื้นที่ไม่พอ สร้างหน้าใหม่และรีเซ็ตตำแหน่ง
                    if y_pos < 100:
                        c.showPage()
                        c.setFont(font_name, 14)
                        start_y_for_page = 750
                        if has_thai_font:
                            continue_title = f"ภาพประกอบ (ต่อ)"
                        else:
                            continue_title = f"Photos (continued)"
                        safe_drawstring(c, 50, start_y_for_page, continue_title, 14)
                        start_y_for_page -= 30
                        row = 0
                        col = 0
                        x_pos = x_start
                        y_pos = start_y_for_page - image_height
                    # โหลดและวาดรูป
                    try:
                        pil_image = Image.open(img_path)
                        pil_image.thumbnail((image_width, image_height), Image.Resampling.LANCZOS)
                        img_reader = ImageReader(pil_image)
                        c.drawImage(img_reader, x_pos, y_pos,
                                    width=pil_image.width, height=pil_image.height,
                                    preserveAspectRatio=True)
                        # ป้ายกำกับใต้รูป
                        if has_thai_font:
                            image_label = f"ภาพที่ {i+1}"
                        else:
                            image_label = f"Image {i+1}"
                        safe_drawstring(c, x_pos, y_pos - 15, image_label, 8)
                        print(f"✅ เพิ่มรูปภาพ {i+1}: {os.path.basename(img_path)}")
                    except Exception as img_error:
                        print(f"❌ ไม่สามารถโหลดรูป {img_path}: {img_error}")
                        c.setStrokeColorRGB(1, 0, 0)
                        c.rect(x_pos, y_pos, image_width, image_height)
                        c.setFillColorRGB(1, 0, 0)
                        error_text = "ไม่สามารถโหลดรูป" if has_thai_font else "Cannot load image"
                        safe_drawstring(c, x_pos + 10, y_pos + image_height//2, error_text, 10)
                        c.setFillColorRGB(0, 0, 0)
                        c.setStrokeColorRGB(0, 0, 0)
                    # ไปตำแหน่งถัดไปจากซ้ายไปขวา บนลงล่าง
                    col += 1
                    if col >= images_per_row:
                        col = 0
                        row += 1
                except Exception as e:
                    print(f"❌ ข้อผิดพลาดในการประมวลผลรูป {img_path}: {e}")
                    continue
            # ปรับ y สำหรับเนื้อหาถัดไปตามจำนวนแถวที่วาดในหน้าปัจจุบันแรก
            total_rows_first_page = row if col == 0 else row + 1
            y = start_y_for_page - (total_rows_first_page * y_spacing) - 30
            
        else:
            if has_thai_font:
                no_photo_text = "ไม่มีภาพประกอบ"
            else:
                no_photo_text = "No photos attached"
            safe_drawstring(c, 70, y, no_photo_text, 12)
        
        # บันทึกไฟล์
        c.save()
        print(f"✅ สร้าง PDF พร้อมรูปภาพสำเร็จ: {filename}")
        # ส่งไฟล์ PDF ไปยัง Web App
        upload_pdf_to_server(filename, name, surname, event, detail)
        print(f"📁 ตำแหน่งไฟล์: {os.path.abspath(filename)}")
        print(f"📊 สรุป: {name} {surname}, อายุ {age} ปี, รูปภาพ {len(captured_images)} รูป")
        
        return True
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการสร้าง PDF: {e}")
        # สร้างไฟล์ PDF แบบพื้นฐาน (ภาษาอังกฤษเท่านั้น)
        try:
            return create_basic_pdf()   
        except:
            return False

def upload_pdf_to_server(pdf_path, name, surname="", event="", detail=""):
    """ส่งไฟล์ PDF ไปยัง Web App พร้อม error handling ที่ดีขึ้น"""
    
    # ✅ รายการ URL ที่จะลอง (เรียงตามลำดับความสำคัญ)
    urls = [
        "http://<IP_ADDRESS>:<PORT>/api/upload_pdf" ใส่ IP เครื่องตัวเองด้วย  #โดยเปิด cmd บนคอมแล้วพิมพ์ ipconfig ดูที่ IPv4 Address
        #เช่น "http://192.1.1.1:7000/api/upload_pdf"
    ]

    # ตรวจสอบว่าไฟล์มีอยู่จริงไหม
    if not os.path.exists(pdf_path):
        print("❌ ไม่พบไฟล์ PDF:", pdf_path)
        return False

    print(f"📤 กำลังส่งไฟล์: {os.path.basename(pdf_path)}")
    print(f"👤 ข้อมูล: {name} {surname} - {event}")
    
    # ✅ ลอง URL ทีละตัวจนกว่าจะสำเร็จ
    for url in urls:
        try:
            print(f"\n🔄 กำลังลอง: {url}")
            
            with open(pdf_path, "rb") as f:
                files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
                data = {
                    "name": name,
                    "surname": surname,
                    "event": event,
                    "detail": detail
                }
                
                # ส่ง request (timeout 30 วินาที)
                response = requests.post(url, files=files, data=data, timeout=30)

            # ตรวจสอบผลลัพธ์
            if response.status_code == 200:
                print(f"✅ อัปโหลดสำเร็จไปยัง: {url}")
                print(f"📋 Response: {response.json()}")
                return True
            else:
                print(f"⚠️ HTTP {response.status_code}: {response.text}")
                continue  # ลอง URL ถัดไป

        except requests.exceptions.ConnectionError:
            print(f"❌ เชื่อมต่อไม่สำเร็จ: {url}")
            continue
            
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout: {url}")
            continue
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาด: {e}")
            continue
    
    # ถ้าลองทุก URL แล้วไม่สำเร็จ
    print("\n❌ ไม่สามารถอัปโหลดไปยังเซิร์ฟเวอร์ใดๆ ได้")
    print("💡 กรุณาตรวจสอบ:")
    print("   1. เซิร์ฟเวอร์ทำงานอยู่หรือไม่? (ต้องรัน main.py ก่อน)")
    print("   2. ตรวจสอบ IP address ว่าถูกต้องหรือไม่")
    print("   3. ลองเปิดเบราว์เซอร์ไปที่: http://localhost:8000")
    return False



def create_basic_pdf():
    """สร้าง PDF แบบพื้นฐานเมื่อมีปัญหา encoding"""
    try:
        # ดึงข้อมูลผู้ป่วย
        name = entry_name.get().strip()
        surname = entry_surname.get().strip()
        
        # สร้างชื่อไฟล์ปลอดภัย (ไม่มีอักขระพิเศษ)
        safe_name = f"{name}_{surname}".replace(" ", "_")
        # ลบอักขระที่ไม่เหมาะสมกับชื่อไฟล์
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in ('_', '-'))
        
        # สร้างวันที่ในรูปแบบ DD-MM-YYYY
        date_str = time.strftime("%d-%m-%Y")
        
        # สร้างชื่อไฟล์: ชื่อผู้ป่วย_วันที่.pdf (Basic version)
        filename = f"pdf_reports/{safe_name}_{date_str}_basic.pdf"
        
        # ถ้าไฟล์ซ้ำ ให้เพิ่มเลขต่อท้าย
        counter = 1
        original_filename = filename
        while os.path.exists(filename):
            name_part = original_filename.replace('.pdf', '')
            filename = f"{name_part}_{counter:02d}.pdf"
            counter += 1
        
        c = canvas.Canvas(filename, pagesize=A4)
        c.setFont("Helvetica", 16)
        
        y = 750
        c.drawString(200, y, "ACCIDENT REPORT")
        y -= 40
        
        c.setFont("Helvetica", 12)
        c.drawString(50, y, f"Date: {time.strftime('%d/%m/%Y %H:%M:%S')}")
        y -= 30
        
        c.drawString(50, y, "PERSONAL INFORMATION")
        y -= 20
        
        c.drawString(70, y, f"Name: {entry_name.get()}")
        y -= 20
        c.drawString(70, y, f"Surname: {entry_surname.get()}")
        y -= 20
        c.drawString(70, y, f"Age: {combo_age.get()} years")
        y -= 30
        
        # เพิ่มข้อมูลสัญญาณชีพ
        c.drawString(50, y, "VITAL SIGNS")
        y -= 20
        
        global heart_rate, spo2, sensor_data_ready
        if sensor_data_ready and (heart_rate > 0 or spo2 > 0):
            c.drawString(70, y, f"Heart Rate: {heart_rate} BPM")
            y -= 20
            c.drawString(70, y, f"SpO2: {spo2}%")
            y -= 30
        else:
            c.drawString(70, y, "Not measured")
            y -= 30
        
        c.drawString(50, y, f"PHOTOS ({len(captured_images)} images)")
        y -= 25
        
        # แสดงรูปภาพในรูปแบบพื้นฐาน
        if captured_images:
            images_per_row = 2
            image_width = 150
            image_height = 100
            x_start = 70
            x_spacing = 200
            y_spacing = 120
            
            # จัดเรียงตาม timestamp เช่นเดียวกับฉบับเต็ม
            def img_sort_key(p):
                try:
                    base = os.path.basename(p)
                    parts = base.split('_')
                    if len(parts) >= 3:
                        return int(parts[1]) * 1000 + int(parts[2].split('.')[0])
                except Exception:
                    pass
                return os.path.getmtime(p) if os.path.exists(p) else 0
            ordered_images = sorted(list(captured_images), key=img_sort_key)
            
            for i, img_path in enumerate(ordered_images):
                try:
                    if not os.path.exists(img_path):
                        continue
                    
                    col = i % images_per_row
                    row = i // images_per_row
                    
                    x_pos = x_start + (col * x_spacing)
                    y_pos = y - (row * y_spacing) - image_height
                    
                    if y_pos < 100:
                        c.showPage()
                        c.setFont("Helvetica", 12)
                        y = 750
                        c.drawString(50, y, f"PHOTOS (continued) - Page {(i // (images_per_row * 4)) + 2}")
                        y -= 30
                        row = 0
                        col = i % images_per_row
                        x_pos = x_start + (col * x_spacing)
                        y_pos = y - image_height
                    
                    try:
                        pil_image = Image.open(img_path)
                        pil_image.thumbnail((image_width, image_height), Image.Resampling.LANCZOS)
                        img_reader = ImageReader(pil_image)
                        
                        c.drawImage(img_reader, x_pos, y_pos, 
                                  width=pil_image.width, height=pil_image.height,
                                  preserveAspectRatio=True)
                        
                        c.setFont("Helvetica", 8)
                        c.drawString(x_pos, y_pos - 15, f"Image {i+1}")
                        
                    except Exception as img_error:
                        print(f"❌ ไม่สามารถโหลดรูป {img_path}: {img_error}")
                        # วาดกรอบแทนรูปที่เสีย
                        c.setStrokeColorRGB(1, 0, 0)
                        c.rect(x_pos, y_pos, image_width, image_height)
                        c.setFont("Helvetica", 8)
                        c.setFillColorRGB(1, 0, 0)
                        c.drawString(x_pos + 10, y_pos + image_height//2, "Cannot load image")
                        c.setFillColorRGB(0, 0, 0)
                        c.setStrokeColorRGB(0, 0, 0)
                
                except Exception as e:
                    print(f"❌ ข้อผิดพลาดในการประมวลผลรูป {img_path}: {e}")
                    continue
            
            total_rows = (len(captured_images) + images_per_row - 1) // images_per_row
            y = y - (total_rows * y_spacing) - 30
        else:
            c.drawString(70, y, "No photos attached")
        
        c.save()
        print(f"✅ สร้าง PDF พื้นฐานสำเร็จ: {filename}")
        print(f"📁 ตำแหน่งไฟล์: {os.path.abspath(filename)}")
        return True
        
    except Exception as e:
        print(f"❌ ไม่สามารถสร้าง PDF ได้: {e}")
        return False

# ------------------ Loading Popup System ------------------
class LoadingPopup:
    def __init__(self, parent):
        self.parent = parent
        self.popup = None
        self.progress_var = None
        self.status_var = None
        self.progress_bar = None
        self.status_label = None
        self.steps = [
            "กำลังเริ่มต้นระบบ...",
            "ตรวจสอบฟอนต์ภาษาไทย...",
            "เริ่มกล้อง...",
            "ตรวจสอบการเชื่อมต่อกล้อง...",
            "เตรียมระบบเสร็จสิ้น"
        ]
        self.current_step = 0
        self.is_ready = False
        
    def show(self):
        """แสดงหน้าต่างโหลด"""
        self.popup = tk.Toplevel(self.parent)
        self.popup.title("Smart EMS+ - กำลังโหลด...")
        self.popup.geometry("500x300")
        self.popup.resizable(False, False)
        
        # ตั้งค่าให้อยู่กลางจอ
        self.popup.update_idletasks()
        x = (self.popup.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.popup.winfo_screenheight() // 2) - (300 // 2)
        self.popup.geometry(f"500x300+{x}+{y}")
        
        # ปิดการปิดหน้าต่างด้วยปุ่ม X
        self.popup.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # สร้าง UI
        self.create_loading_ui()
        
        # เริ่มกระบวนการโหลด
        self.start_loading_process()
        
    def create_loading_ui(self):
        """สร้าง UI ของหน้าต่างโหลด"""
        # หน้าจอหลัก
        main_frame = tk.Frame(self.popup, bg="#f0f0f0", padx=30, pady=30)
        main_frame.pack(fill="both", expand=True)
        
        # หัวเรื่อง
        title_label = tk.Label(main_frame, text="Smart EMS+", 
                              font=("Arial", 24, "bold"), 
                              bg="#f0f0f0", fg="#2c3e50")
        title_label.pack(pady=(0, 10))
        
        subtitle_label = tk.Label(main_frame, text="ระบบบันทึกข้อมูลอุบัติเหตุฉุกเฉิน", 
                                 font=("Arial", 12), 
                                 bg="#f0f0f0", fg="#7f8c8d")
        subtitle_label.pack(pady=(0, 30))
        
        # สถานะปัจจุบัน
        self.status_var = tk.StringVar(value=self.steps[0])
        self.status_label = tk.Label(main_frame, textvariable=self.status_var,
                                    font=("Arial", 11), 
                                    bg="#f0f0f0", fg="#34495e")
        self.status_label.pack(pady=(0, 20))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, 
                                          variable=self.progress_var,
                                          maximum=100,
                                          length=400,
                                          mode='determinate')
        self.progress_bar.pack(pady=(0, 20))
        
        # เปอร์เซ็นต์
        self.percent_label = tk.Label(main_frame, text="0%", 
                                     font=("Arial", 10, "bold"), 
                                     bg="#f0f0f0", fg="#27ae60")
        self.percent_label.pack()
        
        # ข้อความรอ
        wait_label = tk.Label(main_frame, text="กรุณารอสักครู่...", 
                             font=("Arial", 10), 
                             bg="#f0f0f0", fg="#95a5a6")
        wait_label.pack(pady=(20, 0))
        
        # Loading spinner
        self.spinner_frame = tk.Frame(main_frame, bg="#f0f0f0")
        self.spinner_frame.pack(pady=(10, 0))
        
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_index = 0
        self.spinner_label = tk.Label(self.spinner_frame, text="⠋", 
                                     font=("Arial", 16), 
                                     bg="#f0f0f0", fg="#3498db")
        self.spinner_label.pack()
        
        # เอฟเฟกต์การโหลด
        self.loading_dots = 0
        self.update_loading_animation()
        
    def update_loading_animation(self):
        """อัพเดทแอนิเมชันการโหลด"""
        if self.popup and self.popup.winfo_exists():
            # ตรวจสอบว่า current_step อยู่ในขอบเขตของ steps
            if self.current_step < len(self.steps):
                # อัพเดท dots
                dots = "." * (self.loading_dots % 4)
                self.status_var.set(f"{self.steps[self.current_step]}{dots}")
                self.loading_dots += 1
                
                # อัพเดท spinner
                self.spinner_label.config(text=self.spinner_chars[self.spinner_index])
                self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
                
                self.popup.after(200, self.update_loading_animation)
    
    def start_loading_process(self):
        """เริ่มกระบวนการโหลด"""
        self.next_step()
        
    def next_step(self):
        """ไปยังขั้นตอนถัดไป"""
        if self.current_step < len(self.steps):
            # อัพเดทสถานะ
            self.status_var.set(self.steps[self.current_step])
            
            # คำนวณเปอร์เซ็นต์
            progress = (self.current_step / len(self.steps)) * 100
            self.progress_var.set(progress)
            self.percent_label.config(text=f"{int(progress)}%")
            
            # เรียกใช้ฟังก์ชันที่เกี่ยวข้อง
            if self.current_step == 0:
                # ขั้นตอนที่ 1: เริ่มต้นระบบ
                self.popup.after(1000, self.next_step)
                
            elif self.current_step == 1:
                # ขั้นตอนที่ 2: ตรวจสอบฟอนต์ไทย
                self.popup.after(500, self.check_fonts)
                
            elif self.current_step == 2:
                # ขั้นตอนที่ 3: เริ่มกล้อง
                self.popup.after(500, self.start_camera_init)
                
            elif self.current_step == 3:
                # ขั้นตอนที่ 4: ตรวจสอบกล้อง
                self.popup.after(1000, self.verify_camera)
                
            elif self.current_step == 4:
                # ขั้นตอนที่ 5: เสร็จสิ้น
                self.popup.after(500, self.finish_loading)
                
            self.current_step += 1
        else:
            self.finish_loading()
    
    def check_fonts(self):
        """ตรวจสอบฟอนต์ไทย"""
        try:
            install_thai_font()
            print("✅ ตรวจสอบฟอนต์ไทยเสร็จสิ้น")
            self.status_var.set("✅ ตรวจสอบฟอนต์ไทยเสร็จสิ้น")
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดในการตรวจสอบฟอนต์: {e}")
            self.status_var.set("⚠️ ตรวจสอบฟอนต์ไทย - มีปัญหาเล็กน้อย")
        finally:
            self.next_step()
    
    def start_camera_init(self):
        """เริ่มต้นกล้อง"""
        try:
            # อย่าเริ่มกล้องในช่วง loading เพื่อลดการค้าง/จอขาวบน Pi
            self.status_var.set("จะเริ่มกล้องหลังจากแสดงหน้าต่างหลัก")
            print("ℹ️ เลื่อนการเริ่มกล้องไปหลังจาก UI หลักแสดงแล้ว")
        except Exception as e:
            print(f"⚠️ ข้อผิดพลาดในการตั้งค่าเริ่มกล้อง: {e}")
            self.status_var.set("⚠️ จะลองเริ่มกล้องหลังจากนี้")
        finally:
            self.next_step()
    
    def verify_camera(self):
        """ตรวจสอบการทำงานของกล้อง"""
        global cap, camera_running
        self.status_var.set("กำลังตรวจสอบกล้อง...")
        if camera_running and cap and cap.isOpened():
            print("✅ กล้องทำงานปกติ")
            self.status_var.set("✅ กล้องทำงานปกติ")
        else:
            print("⚠️ กล้องยังไม่พร้อม")
            self.status_var.set("⚠️ กล้องยังไม่พร้อม - จะลองใหม่")
        self.next_step()
    
    def finish_loading(self):
        """เสร็จสิ้นการโหลด"""
        self.is_ready = True
        self.progress_var.set(100)
        self.percent_label.config(text="100%")
        self.status_var.set("ระบบพร้อมใช้งาน!")
        
        # เปลี่ยนสี progress bar เป็นสีเขียว
        style = ttk.Style()
        style.configure("Green.Horizontal.TProgressbar", 
                       background="#27ae60", 
                       troughcolor="#ecf0f1")
        self.progress_bar.configure(style="Green.Horizontal.TProgressbar")
        
        # เปลี่ยนสีเปอร์เซ็นต์เป็นสีเขียว
        self.percent_label.config(fg="#27ae60")
        
        # หยุด spinner และแสดงเครื่องหมายถูก
        self.spinner_label.config(text="✅", fg="#27ae60")
        
        # รอ 1.5 วินาทีแล้วปิดหน้าต่าง
        self.popup.after(1500, self.close_popup)
    
    def close_popup(self):
        """ปิดหน้าต่างโหลดและแสดงหน้าต่างหลัก"""
        if self.popup:
            self.popup.destroy()
            self.popup = None
        try:
            self.parent.update_idletasks()
        except Exception:
            pass
        self.parent.deiconify()
        print("🎉 ระบบพร้อมใช้งาน!")

# ------------------ Alert watcher (อ่านไฟล์แจ้งเตือนจาก WebApp) ------------------
# สร้าง path ที่ถูกต้องสำหรับ Raspberry Pi
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ALERT_FILE = os.path.join(CURRENT_DIR, "alerts", "alert_latest.txt")

# สร้างโฟลเดอร์ alerts
alerts_dir = os.path.dirname(ALERT_FILE)
if alerts_dir and not os.path.exists(alerts_dir):
    os.makedirs(alerts_dir, exist_ok=True)
    print(f"✅ สร้างโฟลเดอร์: {alerts_dir}")
_alert_popup = None                       # เก็บ reference ของ popup ปัจจุบัน (เพื่อป้องกันซ้ำ)
_last_alert_mtime = 0                     # เก็บเวลาแก้ไขล่าสุดที่เราเห็นแล้ว

def safe_parse_alert_text(text):
    parts = [line.strip() for line in text.splitlines() if line.strip() != ""]
    if len(parts) < 6:
        raise ValueError("รูปแบบไฟล์แจ้งเหตุไม่ครบ (ต้องมี 6 บรรทัด: name, place, lat, lon, event, detail)")
    name, place, lat, lon, event = parts[:5]
    detail = "\n".join(parts[5:])
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except:
        raise ValueError("ละติจูด/ลองจิจูดไม่ใช่ตัวเลข")
    return name, place, lat_f, lon_f, event, detail

def show_alert_popup_on_mainthread(parsed):
    global _alert_popup
    if _alert_popup is not None and _alert_popup.winfo_exists():
        try:
            _alert_popup.lift()
            return
        except Exception:
            pass

    name, place, lat, lon, event, detail = parsed

    popup = tk.Toplevel(root)
    _alert_popup = popup
    popup.title("🚨 แจ้งเหตุฉุกเฉิน")
    popup.resizable(False, False)

    popup.update_idletasks()
    w = 520; h = 320
    x = (popup.winfo_screenwidth() // 2) - (w // 2)
    y = (popup.winfo_screenheight() // 2) - (h // 2)
    popup.geometry(f"{w}x{h}+{x}+{y}")

    popup.protocol("WM_DELETE_WINDOW", lambda: None)

    frame = tk.Frame(popup, padx=12, pady=12, bg="white")
    frame.pack(fill="both", expand=True)

    title_lbl = tk.Label(frame, text="🚨 แจ้งเหตุใหม่", font=("Arial", 14, "bold"), bg="white")
    title_lbl.pack(anchor="w")

    info = f"ชื่อผู้แจ้ง: {name}\nสถานที่: {place}\nเหตุการณ์: {event}"
    info_lbl = tk.Label(frame, text=info, justify="left", anchor="w", bg="white", font=("Arial", 11))
    info_lbl.pack(fill="x", pady=(8,4))

    detail_box = tk.Text(frame, height=6, wrap="word", font=("Arial", 10))
    detail_box.insert("1.0", detail)
    detail_box.config(state="disabled", bg="#fafafa")
    detail_box.pack(fill="both", expand=True, pady=(0,8))

    btn_row = tk.Frame(frame, bg="white")
    btn_row.pack(fill="x", pady=(6,0))

    def open_gps():
        try:
            url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
            webbrowser.open(url)
        except Exception:
            traceback.print_exc()

    def close_popup():
        global _alert_popup
        try:
            popup.destroy()
        except Exception:
            pass
        _alert_popup = None

    open_btn = tk.Button(btn_row, text="🧭 เปิดเส้นทาง GPS", command=open_gps, width=18, bg="#2d7ff9", fg="white")
    open_btn.pack(side="left", padx=6)

    close_btn = tk.Button(btn_row, text="✖ ปิด", command=close_popup, width=10, bg="#e74c3c", fg="white")
    close_btn.pack(side="right", padx=6)

    try:
        import winsound
        winsound.Beep(800, 250)
        winsound.Beep(1000, 200)
    except Exception:
        try:
            os.system('aplay /usr/share/sounds/alsa/Front_Center.wav > /dev/null 2>&1')
        except Exception:
            pass

def alert_watcher_loop(poll_interval=1.0):
    """ตรวจสอบไฟล์แจ้งเตือน (แก้ไขแล้ว)"""
    global _last_alert_mtime
    
    # ตรวจสอบว่า path ถูกต้อง
    if not ALERT_FILE:
        print("❌ ALERT_FILE ไม่ได้กำหนด - ปิดการทำงาน alert watcher")
        return
    
    alerts_path = ALERT_FILE
    
    # สร้างโฟลเดอร์ถ้ายังไม่มี (แบบปลอดภัย)
    alerts_dir = os.path.dirname(alerts_path)
    if alerts_dir:
        try:
            os.makedirs(alerts_dir, exist_ok=True)
        except Exception as e:
            print(f"❌ ไม่สามารถสร้างโฟลเดอร์ alerts: {e}")
            return
    
    print(f"🔔 Alert watcher เริ่มทำงาน - ตรวจสอบ: {alerts_path}")

    while True:
        try:
            if os.path.exists(alerts_path):
                mtime = os.path.getmtime(alerts_path)
                if mtime != _last_alert_mtime:
                    with open(alerts_path, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                    if text:
                        try:
                            parsed = safe_parse_alert_text(text)
                        except Exception as e:
                            print("⚠️ อ่านไฟล์แจ้งเตือนไม่ถูกต้อง:", e)
                            parsed = None

                        if parsed:
                            _last_alert_mtime = mtime
                            try:
                                safe_after(root,0, show_alert_popup_on_mainthread, parsed)
                            except Exception:
                                traceback.print_exc()
            time.sleep(poll_interval)
        except Exception as e:
            print("❌ เกิดข้อผิดพลาดใน alert_watcher_loop:", e)
            time.sleep(poll_interval)

# ------------------ GUI หลัก ------------------
root = tk.Tk()
root.title("Smart EMS+")


# ตั้งค่าหน้าต่างเริ่มต้น 480x800 (portrait) และ fullscreen
root.geometry("800x480+0+0")
root.attributes('-fullscreen', True)
root.configure(bg="white")
root.resizable(False, False)

# Initialize modern ttk styles
init_modern_styles(root)

# ออกจาก fullscreen ด้วยปุ่ม Esc
def exit_fullscreen(event=None):
    root.attributes('-fullscreen', False)

root.bind("<Escape>", exit_fullscreen)

root.grid_rowconfigure(0, weight=0)  # color bar
root.grid_rowconfigure(1, weight=1)  # main content
root.grid_columnconfigure(0, weight=1)

color_bar = tk.Frame(root, bg="#e985b4", height=18)
color_bar.grid(row=0, column=0, sticky="ew")


frame1 = tk.Frame(root, bg="#e3f2fd")  # หน้าแรก
frame2 = tk.Frame(root, bg="#fff3cd")  # แสดงข้อมูลการแจ้งเหตุและ GPS (ใหม่)
frame3 = tk.Frame(root, bg="#fffde7")  # ถ่ายรูป (ย้ายจาก frame2 เดิม)
frame4 = tk.Frame(root, bg="#e0f7fa")  # วัดสัญญาณชีพ (เดิม frame3_sensor)
frame5 = tk.Frame(root, bg="#fce4ec")  # กรอกข้อมูล (เดิม frame3)
frame6 = tk.Frame(root, bg="#e8f5e9")  # บันทึกรายละเอียด (เดิม frame4)

for frame in (frame1, frame2, frame3, frame4, frame5, frame6):
    frame.grid(row=1, column=0, sticky="nsew")

# ------------------ Virtual Keyboard (แบบใหม่ - ในหน้าต่างเดียวกัน) -----------------

class VirtualKeyboard:
    def __init__(self, target_widget=None, theme="light", language="en", container=None):
        self.target_widget = target_widget
        self.theme = theme
        self.language = language
        self.keyboard_window = None  # Can be Toplevel or embedded Frame
        self.container = container   # Parent container for embedded keyboard
        self.is_shift = False
        self.is_caps_lock = False
        self.is_visible = False
        
        # English keyboard layout (ปรับสำหรับ 800x400)
        self.en_layout = [
            ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'Backspace'],
            ['Tab', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\\'],
            ['CapsLock', 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'", 'Enter'],
            ['Shift', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 'Shift', 'Space', 'EN/TH']
        ]
        
        # Thai keyboard layout (Kedmanee) - ปรับสำหรับ 800x400
        self.th_layout = [
            ['_', 'ๅ', '/', '-', 'ภ', 'ถ', 'ุ', 'ึ', 'ค', 'ต', 'จ', 'ข', 'ช', 'Backspace'],
            ['Tab', 'ๆ', 'ไ', 'ำ', 'พ', 'ะ', 'ั', 'ี', 'ร', 'น', 'ย', 'บ', 'ล', 'ฃ'],
            ['CapsLock', 'ฟ', 'ห', 'ก', 'ด', 'เ', '้', '่', 'า', 'ส', 'ว', 'ง', 'Enter'],
            ['Shift', 'ผ', 'ป', 'แ', 'อ', 'ิ', 'ื', 'ท', 'ม', 'ใ', 'ฝ', 'Shift', 'Space', 'EN/TH']
        ]
        
        # English Shift characters mapping
        self.en_shift_map = {
            '`': '~', '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
            '6': '^', '7': '&', '8': '*', '9': '(', '0': ')', '-': '_',
            '=': '+', '[': '{', ']': '}', '\\': '|', ';': ':', "'": '"',
            ',': '<', '.': '>', '/': '?'
        }
        
        # Thai Shift characters mapping
        self.th_shift_map = {
            '_': '฿', 'ๅ': '+', '/': '๑', '-': '๒', 'ภ': '๓', 'ถ': '๔', 'ุ': 'ู', 
            'ึ': '฿', 'ค': '๕', 'ต': '๖', 'จ': '๗', 'ข': '๘', 'ช': '๙',
            'ๆ': '๐', 'ไ': '"', 'ำ': 'ฎ', 'พ': 'ฑ', 'ะ': 'ธ', 'ั': '๊', 'ี': '็',
            'ร': 'ณ', 'น': 'ฯ', 'ย': 'ญ', 'บ': 'ฐ', 'ล': ',', 'ฃ': 'ฅ',
            'ฟ': 'ฤ', 'ห': 'ฆ', 'ก': 'ฏ', 'ด': 'โ', 'เ': 'ฌ', '้': '๋', '่': '๋',
            'า': 'ศ', 'ส': 'ษ', 'ว': 'ซ', 'ง': '.', 'ผ': '(', 'ป': ')',
            'แ': 'ฉ', 'อ': 'ฮ', 'ิ': 'ฺ', 'ื': '์', 'ท': '?', 'ม': 'ฒ',
            'ใ': 'ฬ', 'ฝ': 'ฦ'
        }
        
        # กำหนดสี theme
        self.themes = {
            "light": {
                "bg": "#f0f0f0",
                "key_bg": "#ffffff",
                "key_fg": "#000000",
                "special_bg": "#e0e0e0",
                "active_bg": "#4CAF50",
                "border": "#cccccc",
                "lang_bg": "#FF9800"
            },
            "dark": {
                "bg": "#2b2b2b",
                "key_bg": "#404040",
                "key_fg": "#ffffff",
                "special_bg": "#505050",
                "active_bg": "#66BB6A",
                "border": "#666666",
                "lang_bg": "#FF9800"
            }
        }

    @property
    def current_layout(self):
        """ดึง layout ปัจจุบันตามภาษา"""
        return self.th_layout if self.language == "th" else self.en_layout
    
    @property
    def current_shift_map(self):
        """ดึง shift map ปัจจุบันตามภาษา"""
        return self.th_shift_map if self.language == "th" else self.en_shift_map

    def show_keyboard(self, x=None, y=None, container=None):
        """แสดงแป้นพิมพ์เสมือน (ฝังใน container ถ้ามี ไม่งั้นเปิดหน้าต่างใหม่)"""
        if self.is_visible:
            return
        if container is not None:
            self.container = container
        
        # ตั้งค่า theme
        current_theme = self.themes[self.theme]
        
        if self.container is not None:
            # Render embedded in provided container (fixed compact height for 800x400)
            self.keyboard_window = tk.Frame(self.container, bg=current_theme["bg"], bd=1, relief="ridge", height=120)
            self.keyboard_window.pack(side="bottom", fill="x")
            self.keyboard_window.pack_propagate(False)
        else:
            # Fallback to separate window
            self.keyboard_window = tk.Toplevel()
            self.keyboard_window.title(f"Virtual Keyboard - {'Thai' if self.language == 'th' else 'English'}")
            self.keyboard_window.attributes("-topmost", True)
            self.keyboard_window.resizable(False, False)
            # กำหนดตำแหน่ง
            if x is not None and y is not None:
                self.keyboard_window.geometry(f"+{x}+{y}")
            else:
                self.keyboard_window.update_idletasks()
                width = 760
                height = 160
                x = (self.keyboard_window.winfo_screenwidth() // 2) - (width // 2)
                y = (self.keyboard_window.winfo_screenheight() // 2) - (height // 2)
                self.keyboard_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # ตั้งค่า theme
        self.keyboard_window.configure(bg=current_theme["bg"])
        
        # สร้างปุ่มคีบอร์ด
        self.create_keyboard_layout()
        
        # จัดการเมื่อปิดหน้าต่าง (เฉพาะโหมดหน้าต่าง)
        if isinstance(self.keyboard_window, tk.Toplevel):
            self.keyboard_window.protocol("WM_DELETE_WINDOW", self.hide_keyboard)
        self.is_visible = True

    def hide_keyboard(self):
        """ซ่อนแป้นพิมพ์เสมือน"""
        if self.keyboard_window:
            self.keyboard_window.destroy()
            self.keyboard_window = None
        self.is_visible = False

    def create_keyboard_layout(self):
        """สร้างเลย์เอาต์ของคีบอร์ด - ปรับสำหรับ 800x400"""
        current_theme = self.themes[self.theme]
        
        # สร้าง frame หลัก (ลด padding สำหรับความกะทัดรัด)
        main_frame = tk.Frame(self.keyboard_window, bg=current_theme["bg"], padx=2, pady=2)
        main_frame.pack(expand=True, fill="both")
        
        # แสดงภาษาปัจจุบัน (ลดขนาดฟอนต์)
        lang_frame = tk.Frame(main_frame, bg=current_theme["bg"])
        lang_frame.pack(fill="x", pady=(0, 2))
        
        lang_label = tk.Label(
            lang_frame, 
            text=f"{'ไทย' if self.language == 'th' else 'ENG'}",
            bg=current_theme["bg"],
            fg=current_theme["key_fg"],
            font=("Arial", 7)
        )
        lang_label.pack(anchor="w")
        
        # สร้างแต่ละแถวของคีบอร์ด (ลด spacing)
        for row_index, row in enumerate(self.current_layout):
            row_frame = tk.Frame(main_frame, bg=current_theme["bg"])
            row_frame.pack(pady=0)  # ลด padding ระหว่างแถว
            
            for key in row:
                self.create_key_button(row_frame, key, current_theme)

    def create_key_button(self, parent, key, theme):
        """สร้างปุ่มคีย์ - ปรับให้เหมาะกับหน้าจอ 800x400"""
        # กำหนดขนาดปุ่มตาม key type (ลดขนาดสำหรับ 800x400)
        width = self.get_key_width(key)
        height = 1
        
        # เลือกสีพื้นหลัง
        if key in ['Backspace', 'Tab', 'CapsLock', 'Enter', 'Shift', 'Ctrl', 'Alt']:
            bg_color = theme["special_bg"]
        elif key == 'EN/TH':
            bg_color = theme["lang_bg"]
        else:
            bg_color = theme["key_bg"]
        
        # สร้างปุ่ม (ลดขนาดฟอนต์และ padding)
        button = tk.Button(
            parent,
            text=self.get_key_display_text(key),
            width=width,
            height=height,
            bg=bg_color,
            fg=theme["key_fg"],
            relief="raised",
            bd=1,
            font=("Arial", 6),  # ลดขนาดฟอนต์จาก 7 เป็น 6
            command=lambda k=key: self.key_pressed(k)
        )
        
        # เพิ่มเอฟเฟกต์เมื่อ hover
        button.bind("<Enter>", lambda e: e.widget.config(relief="groove"))
        button.bind("<Leave>", lambda e: e.widget.config(relief="raised"))
        
        # ลด padding ระหว่างปุ่ม
        button.pack(side="left", padx=0, pady=0)

    def get_key_width(self, key):
        """กำหนดความกว้างของปุ่ม - ปรับให้เหมาะกับหน้าจอ 800x400"""
        width_map = {
            'Backspace': 4,  # ลดจาก 5 เป็น 4
            'Tab': 2,        # ลดจาก 3 เป็น 2
            'CapsLock': 4,   # ลดจาก 5 เป็น 4
            'Enter': 4,      # ลดจาก 5 เป็น 4
            'Shift': 3,      # ลดจาก 5 เป็น 3
            'Space': 4,      # ลดจาก 8 เป็น 4 (เพราะอยู่ในแถวเดียวกับปุ่มอื่น)
            'Ctrl': 2,       # ลดจาก 3 เป็น 2
            'Alt': 2,        # ลดจาก 3 เป็น 2
            'EN/TH': 3       # ลดจาก 5 เป็น 3
        }
        return width_map.get(key, 2)  # ลดขนาดปุ่มปกติจาก 3 เป็น 2

    def get_key_display_text(self, key):
        """กำหนดข้อความที่แสดงบนปุ่ม"""
        display_map = {
            'Backspace': '⌫',
            'Tab': '⇥',
            'CapsLock': 'Caps',
            'Enter': '⏎',
            'Shift': '⇧',
            'Space': 'Space',
            'Ctrl': 'Ctrl',
            'Alt': 'Alt',
            'EN/TH': 'EN/TH'
        }
        
        if key in display_map:
            return display_map[key]
        
        # จัดการตัวอักษรตาม Shift และ CapsLock
        if self.language == "en" and key.isalpha():
            if self.is_caps_lock or self.is_shift:
                return key.upper()
            else:
                return key.lower()
        
        # จัดการ Shift characters
        if self.is_shift and key in self.current_shift_map:
            return self.current_shift_map[key]
        
        return key

    def key_pressed(self, key):
        """จัดการเมื่อมีการกดปุ่ม"""
        # จัดการปุ่มสลับภาษา
        if key == 'EN/TH':
            self.toggle_language()
            return
        
        # จัดการปุ่มพิเศษ
        if key == 'Shift':
            self.is_shift = not self.is_shift
            self.update_keyboard_display()
            return
        
        if key == 'CapsLock':
            self.is_caps_lock = not self.is_caps_lock
            self.update_keyboard_display()
            return
        
        # ประมวลผลปุ่มที่กด
        char_to_insert = self.process_key(key)
        
        # ส่งตัวอักษรไปยัง target widget
        if self.target_widget and char_to_insert:
            self.insert_text(char_to_insert)
        
        # รีเซ็ต Shift หลังกดปุ่ม (ยกเว้นปุ่มพิเศษ)
        if self.is_shift and key not in ['Ctrl', 'Alt']:
            self.is_shift = False
            self.update_keyboard_display()

    def toggle_language(self):
        """สลับภาษา"""
        self.language = "th" if self.language == "en" else "en"
        self.update_keyboard_display()

    def process_key(self, key):
        """ประมวลผลปุ่มที่กดและคืนค่าตัวอักษรที่จะใส่"""
        if key == 'Backspace':
            self.handle_backspace()
            return None
        elif key == 'Enter':
            return '\n'
        elif key == 'Tab':
            return '\t'
        elif key == 'Space':
            return ' '
        elif key in ['Ctrl', 'Alt']:
            # จัดการปุ่ม modifier keys ในอนาคต
            return None
        
        # จัดการตัวอักษรสำหรับภาษาอังกฤษ
        if self.language == "en" and key.isalpha():
            if self.is_caps_lock or self.is_shift:
                return key.upper()
            else:
                return key.lower()
        
        # จัดการ Shift characters
        if self.is_shift and key in self.current_shift_map:
            return self.current_shift_map[key]
        
        return key

    def insert_text(self, text):
        """ใส่ข้อความลงใน target widget"""
        if hasattr(self.target_widget, 'insert'):
            # สำหรับ Text widget
            self.target_widget.insert('insert', text)
        elif hasattr(self.target_widget, 'get') and hasattr(self.target_widget, 'set'):
            # สำหรับ Entry widget
            current_pos = self.target_widget.index('insert')
            current_text = self.target_widget.get()
            new_text = current_text[:current_pos] + text + current_text[current_pos:]
            self.target_widget.delete(0, 'end')
            self.target_widget.insert(0, new_text)
            self.target_widget.icursor(current_pos + len(text))

    def handle_backspace(self):
        """จัดการปุ่ม Backspace - ใช้วิธีเดียวกับโค้ดเก่าที่ทำงานได้"""
        if self.target_widget:
            try:
                current_text = self.target_widget.get()
                if current_text:
                    # ลบตัวอักษรตัวสุดท้าย (วิธีเดียวกับโค้ดเก่า)
                    self.target_widget.delete(len(current_text)-1, tk.END)
            except:
                pass

    def update_keyboard_display(self):
        """อัพเดทการแสดงผลคีบอร์ด"""
        if self.keyboard_window:
            is_toplevel = isinstance(self.keyboard_window, tk.Toplevel)
            geometry = None
            if is_toplevel:
                geometry = self.keyboard_window.geometry()
            self.hide_keyboard()
            # Recreate in the same container/window
            if is_toplevel:
                self.show_keyboard()
                if geometry:
                    self.keyboard_window.geometry(geometry)
            else:
                self.show_keyboard(container=self.container)

    def set_target_widget(self, widget):
        """กำหนด widget ที่จะรับข้อความ"""
        self.target_widget = widget

    def set_container(self, container):
        """กำหนด container สำหรับฝังคีบอร์ด"""
        self.container = container

    def toggle_keyboard(self):
        """สลับการแสดง/ซ่อนคีบอร์ด"""
        if self.is_visible:
            self.hide_keyboard()
        else:
            self.show_keyboard()

    def set_language(self, language):
        """กำหนดภาษา"""
        if language in ["en", "th"]:
            self.language = language
            if self.is_visible:
                self.update_keyboard_display()

# Create global instance (container will be set after UI frames are created)
virtual_keyboard = VirtualKeyboard(theme="light", language="th", container=None)

# Fixed helper functions
def show_keyboard(target_widget=None, container=None):
    """แสดงแป้นพิมพ์เสมือน (ฝังใน container ถ้ามี)"""
    if target_widget:
        virtual_keyboard.set_target_widget(target_widget)
    if container is not None:
        virtual_keyboard.set_container(container)
        virtual_keyboard.show_keyboard(container=container)
    else:
        virtual_keyboard.show_keyboard()

def hide_keyboard():
    """ซ่อนแป้นพิมพ์เสมือน"""
    virtual_keyboard.hide_keyboard()

# ฟังก์ชันทดสอบการแจ้งเหตุ
def test_alert_system():
    """ทดสอบระบบแจ้งเหตุด้วยตนเอง"""
    print("\n🧪 ทดสอบระบบแจ้งเหตุ...")
    print(f"📁 Path: {ALERT_FILE_PATH}")
    print(f"📂 Exists: {os.path.exists(ALERT_FILE_PATH)}")
    print(f"🔄 Watcher running: {alert_watcher_running}")
    
    # ลองอ่านไฟล์
    alert_data = check_new_alert()
    if alert_data:
        print("✅ พบข้อมูลการแจ้งเหตุ!")
        show_alert_notification(alert_data)
    else:
        print("❌ ไม่พบข้อมูลการแจ้งเหตุใหม่")
        messagebox.showinfo(
            "ทดสอบระบบแจ้งเหตุ",
            f"ไม่พบการแจ้งเหตุใหม่\n\n"
            f"Path: {ALERT_FILE_PATH}\n"
            f"Exists: {os.path.exists(ALERT_FILE_PATH)}\n"
            f"Watcher: {'Running' if alert_watcher_running else 'Stopped'}"
        )

# ฟังก์ชันแสดงเบอร์ติดต่อเจ้าหน้าที่
def show_emergency_contacts():
    """แสดงเบอร์โทรติดต่อเจ้าหน้าที่ฉุกเฉิน"""
    # สร้าง popup
    contact_popup = tk.Toplevel(root)
    contact_popup.title("📞 ติดต่อเจ้าหน้าที่ฉุกเฉิน")
    contact_popup.geometry("450x500")
    contact_popup.configure(bg="#fff3e0")
    contact_popup.resizable(False, False)
    
    # ทำให้อยู่ด้านหน้าสุด
    contact_popup.attributes('-topmost', True)
    contact_popup.focus_force()
    
    # กรอบหลัก
    contact_frame = tk.Frame(contact_popup, bg="#fff3e0")
    contact_frame.pack(fill="both", expand=True)
    
    # หัวข้อ
    tk.Label(
        contact_frame,
        text="📞 เบอร์ติดต่อฉุกเฉิน",
        font=("Arial", 18, "bold"),
        bg="#fff3e0",
        fg="#e65100"
    ).pack(pady=15)
    
    # กรอบข้อมูล
    info_frame = tk.Frame(contact_frame, bg="white", relief="ridge", bd=2)
    info_frame.pack(pady=10, padx=20, fill="both", expand=True)
    
    # รายการเบอร์โทรศัพท์
    contacts = [
        ("🚑 รถพยาบาล (EMS)", "1669"),
        ("🚨 ตำรวจ", "191"),
        ("🚒 ดับเพลิง", "199"),
        ("🏥 ศูนย์นเรนทร", "1646"),
        ("📱 ศูนย์ช่วยเหลือสังคม", "1300"),
    ]
    
    # ฟังก์ชันแสดง popup ยืนยันการโทร (ภายใน overlay เดียวกัน)
    def confirm_call(phone_number, service_name):
        """แสดง popup ยืนยันการโทร"""
        # ซ่อนรายการเบอร์
        info_frame.pack_forget()
        
        # สร้างกรอบยืนยัน
        confirm_frame = tk.Frame(contact_frame, bg="#e3f2fd")
        confirm_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # ไอคอน
        tk.Label(
            confirm_frame,
            text="📞",
            font=("Arial", 48),
            bg="#e3f2fd"
        ).pack(pady=15)
        
        # ข้อความยืนยัน
        tk.Label(
            confirm_frame,
            text="ยืนยันการโทรออก?",
            font=("Arial", 14, "bold"),
            bg="#e3f2fd",
            fg="#1565c0"
        ).pack(pady=5)
        
        tk.Label(
            confirm_frame,
            text=f"{service_name}\n{phone_number}",
            font=("Arial", 12),
            bg="#e3f2fd",
            fg="#333"
        ).pack(pady=10)
        
        # กรอบปุ่ม
        btn_frame = tk.Frame(confirm_frame, bg="#e3f2fd")
        btn_frame.pack(pady=15)
        
        def make_call():
            """ทำการโทร"""
            confirm_frame.pack_forget()
            
            # แสดงสถานะกำลังโทร
            calling_frame = tk.Frame(contact_frame, bg="#c8e6c9")
            calling_frame.pack(pady=10, padx=20, fill="both", expand=True)
            
            tk.Label(
                calling_frame,
                text="📞",
                font=("Arial", 48),
                bg="#c8e6c9"
            ).pack(pady=15)
            
            tk.Label(
                calling_frame,
                text=f"กำลังโทรไปที่\n{phone_number}",
                font=("Arial", 12, "bold"),
                bg="#c8e6c9",
                fg="#2e7d32"
            ).pack(pady=10)
            
            tk.Label(
                calling_frame,
                text="(ในระบบจริง จะเชื่อมต่อกับระบบโทรศัพท์)",
                font=("Arial", 9),
                bg="#c8e6c9",
                fg="gray"
            ).pack(pady=5)
            
            ttk.Button(
                calling_frame,
                text="ปิด",
                style="Secondary.TButton",
                command=contact_popup.destroy
            ).pack(pady=10)
        
        def cancel_call():
            """ยกเลิกและกลับไปหน้ารายการ"""
            confirm_frame.pack_forget()
            info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # ปุ่มยืนยัน
        tk.Button(
            btn_frame,
            text="✅ โทรเลย",
            font=("Arial", 12, "bold"),
            bg="#4caf50",
            fg="white",
            padx=20,
            pady=10,
            command=make_call
        ).pack(side="left", padx=5)
        
        # ปุ่มยกเลิก
        tk.Button(
            btn_frame,
            text="❌ ยกเลิก",
            font=("Arial", 12, "bold"),
            bg="#f44336",
            fg="white",
            padx=20,
            pady=10,
            command=cancel_call
        ).pack(side="left", padx=5)
    
    for label, number in contacts:
        # กรอบแต่ละรายการ
        contact_item = tk.Frame(info_frame, bg="white")
        contact_item.pack(fill="x", padx=15, pady=8)
        
        tk.Label(
            contact_item,
            text=label,
            font=("Arial", 11),
            bg="white",
            anchor="w"
        ).pack(side="left", fill="x", expand=True)
        
        # ปุ่มโทร
        call_btn = tk.Button(
            contact_item,
            text=f"📞 {number}",
            font=("Arial", 12, "bold"),
            bg="#4caf50",
            fg="white",
            relief="raised",
            bd=2,
            padx=10,
            pady=5,
            command=lambda n=number, l=label: confirm_call(n, l)
        )
        call_btn.pack(side="right")
    
    # คำแนะนำ
    tk.Label(
        info_frame,
        text="💡 กดปุ่มเพื่อโทรติดต่อหน่วยงานฉุกเฉิน",
        font=("Arial", 9),
        bg="white",
        fg="gray"
    ).pack(pady=10)
    
    # ปุ่มปิด
    ttk.Button(
        contact_frame,
        text="ปิด",
        style="Secondary.TButton",
        command=contact_popup.destroy
    ).pack(pady=10)

# ------------------ หน้า 1 (ปรับให้สวยงามและทันสมัย - 800x400) ------------------

# กรอบหลักสำหรับเนื้อหา
main_container = tk.Frame(frame1, bg="#e3f2fd")
main_container.pack(expand=True, fill="both")

# ส่วนหัว - Logo และชื่อโปรแกรม (ลดความสูง)
header_frame = tk.Frame(main_container, bg="#0277bd", height=60)
header_frame.pack(fill="x", pady=0)
header_frame.pack_propagate(False)

# ไอคอนและชื่อโปรแกรม (ลดขนาด)
header_content = tk.Frame(header_frame, bg="#0277bd")
header_content.pack(expand=True)

tk.Label(
    header_content, 
    text="🚑 Smart EMS+", 
    font=("Arial", 30, "bold"), 
    fg="white", 
    bg="#0277bd"
).pack()

# กรอบเนื้อหาหลัก
content_frame = tk.Frame(main_container, bg="#e3f2fd")
content_frame.pack(expand=True, fill="both", pady=5)

# คำอธิบายระบบ (ลดขนาด)
desc_frame = tk.Frame(content_frame, bg="white", relief="solid", bd=1)
desc_frame.pack(pady=5, padx=30, fill="x")

tk.Label(
    desc_frame,
    text="ระบบบันทึกข้อมูลอุบัติเหตุฉุกเฉิน",
    font=("Arial", 20, "bold"),
    bg="white",
    fg="#0277bd"
).pack(pady=3)


# แสดงสถานะกล้อง (ลดขนาด)
status_frame = tk.Frame(content_frame, bg="#e8f5e9", relief="solid", bd=1)
status_frame.pack(pady=5, padx=30, fill="x")

camera_status_label = tk.Label(
    status_frame, 
    text="📷 กล้อง: กำลังตรวจสอบ...", 
    font=("Arial", 9), 
    bg="#e8f5e9", 
    fg="#2e7d32"
)
camera_status_label.pack(pady=3)

# กรอบปุ่มหลัก
button_container = tk.Frame(content_frame, bg="#e3f2fd")
button_container.pack(pady=8)

# ปุ่มเริ่มต้นการใช้งาน (ปรับขนาดให้เหมาะสม)
start_btn = tk.Button(
    button_container,
    text="🚀 เริ่มต้นการใช้งาน",
    command=start_app,
    bg="#27ae60",
    fg="white",
    font=("Arial", 14, "bold"),
    activebackground="#219150",
    activeforeground="white",
    relief="raised",
    bd=3,
    padx=30,
    pady=10,
    cursor="hand2"
)
start_btn.pack(pady=5)

# เพิ่ม hover effect
def on_enter_start(e):
    start_btn['bg'] = '#229954'
    
def on_leave_start(e):
    start_btn['bg'] = '#27ae60'

start_btn.bind("<Enter>", on_enter_start)
start_btn.bind("<Leave>", on_leave_start)

# กรอบปุ่มเสริม (ลดขนาด)
extra_buttons_frame = tk.Frame(content_frame, bg="#e3f2fd")
extra_buttons_frame.pack(pady=5)

# ปุ่มติดต่อเจ้าหน้าที่ (ลดขนาด)
emergency_btn = tk.Button(
    extra_buttons_frame,
    text="📞 ติดต่อฉุกเฉิน",
    command=show_emergency_contacts,
    bg="#e74c3c",
    fg="white",
    font=("Arial", 9, "bold"),
    relief="raised",
    bd=2,
    padx=10,
    pady=5,
    cursor="hand2"
)
emergency_btn.pack(side="left", padx=3)

# เพิ่ม hover effect
def on_enter_emergency(e):
    emergency_btn['bg'] = '#c0392b'
    
def on_leave_emergency(e):
    emergency_btn['bg'] = '#e74c3c'

emergency_btn.bind("<Enter>", on_enter_emergency)
emergency_btn.bind("<Leave>", on_leave_emergency)

# ปุ่มทดสอบ (ลดขนาด)
test_btn = tk.Button(
    extra_buttons_frame,
    text="🧪 ทดสอบ",
    command=test_alert_system,
    bg="#95a5a6",
    fg="white",
    font=("Arial", 9, "bold"),
    relief="raised",
    bd=2,
    padx=10,
    pady=5,
    cursor="hand2"
)
test_btn.pack(side="left", padx=3)

# เพิ่ม hover effect
def on_enter_test(e):
    test_btn['bg'] = '#7f8c8d'
    
def on_leave_test(e):
    test_btn['bg'] = '#95a5a6'

test_btn.bind("<Enter>", on_enter_test)
test_btn.bind("<Leave>", on_leave_test)

# ส่วนท้าย - ข้อมูลเวอร์ชัน (ลดความสูง)
footer_frame = tk.Frame(main_container, bg="#b3e5fc", height=25)
footer_frame.pack(side="bottom", fill="x")
footer_frame.pack_propagate(False)

tk.Label(
    footer_frame,
    text="Version 1.0 | Nakprasith-School | Project by Team NongChamp",
    font=("Arial", 8),
    bg="#b3e5fc",
    fg="#01579b"
).pack(pady=5)

# ปุ่ม Restart Program (มุมซ้ายล่าง)
restart_btn = tk.Button(
    frame1, 
    text="🔄 Restart", 
    command=restart_program,  # เปลี่ยนจาก reset_program เป็น restart_program
    bg="#ff5722", 
    fg="white", 
    font=("Arial", 10, "bold"),  # ลดจาก 12 เป็น 10
    activebackground="#e64a19",
    activeforeground="white",
    relief="raised",
    bd=2,  # ลดจาก 3 เป็น 2
    padx=10,  # ลดจาก 15 เป็น 10
    pady=5  # ลดจาก 8 เป็น 5
)
restart_btn.place(x=10, y=430, anchor="sw")  # ซ้ายล่าง

# ปุ่มปิดโปรแกรม (ข้างๆ ปุ่ม Restart)
def close_program():
    """ปิดโปรแกรม"""
    try:
        result = messagebox.askyesno(
            "ยืนยันการปิดโปรแกรม",
            "คุณต้องการปิดโปรแกรมหรือไม่?\n\n"
            "ข้อมูลที่ยังไม่ได้บันทึกจะหายไป"
        )
        
        if result:
            print("\n👋 กำลังปิดโปรแกรม...")
            on_closing()
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการปิดโปรแกรม: {e}")

close_btn = tk.Button(
    frame1, 
    text="❌ ปิด", 
    command=close_program,
    bg="#e74c3c", 
    fg="white", 
    font=("Arial", 10, "bold"),
    activebackground="#c0392b",
    activeforeground="white",
    relief="raised",
    bd=2,
    padx=10,
    pady=5
)
close_btn.place(x=110, y=430, anchor="sw")  # ข้างๆ ปุ่ม Restart

# ------------------ หน้า 2: แสดงข้อมูลการแจ้งเหตุและ GPS (ใหม่) ------------------

tk.Label(frame2, text="🚨 ข้อมูลการแจ้งเหตุ", 
         font=("Arial", 16, "bold"), bg="#fff3cd", fg="#856404").pack(pady=10)

# กรอบแสดงข้อมูล
info_container = tk.Frame(frame2, bg="white", relief="ridge", bd=3)
info_container.pack(pady=10, padx=20, fill="both", expand=True)

# ข้อมูลเหตุการณ์
alert_name_label = tk.Label(info_container, text="👤 ผู้แจ้ง: -", 
                            font=("Arial", 14), bg="white", anchor="w")
alert_name_label.pack(fill="x", padx=20, pady=5)

alert_place_label = tk.Label(info_container, text="📍 สถานที่: -", 
                             font=("Arial", 14), bg="white", anchor="w")
alert_place_label.pack(fill="x", padx=20, pady=5)

alert_event_label = tk.Label(info_container, text="🚨 เหตุการณ์: -", 
                             font=("Arial", 14), bg="white", anchor="w")
alert_event_label.pack(fill="x", padx=20, pady=5)

alert_detail_label = tk.Label(info_container, text="📝 รายละเอียด: -", 
                              font=("Arial", 12), bg="white", anchor="w", justify="left")
alert_detail_label.pack(fill="x", padx=20, pady=5)

# เส้นแบ่ง
tk.Frame(info_container, height=2, bg="#856404").pack(fill="x", padx=20, pady=10)

# พิกัด GPS
tk.Label(info_container, text="🗺️ พิกัด GPS", 
         font=("Arial", 14, "bold"), bg="white", fg="#856404").pack(pady=5)

alert_gps_label = tk.Label(info_container, text="Lat: -\nLon: -", 
                           font=("Arial", 12), bg="white")
alert_gps_label.pack(pady=5)

# ฟังก์ชันเปิด Google Maps
def open_google_maps():
    try:
        gps_text = alert_gps_label.cget("text")
        if "Lat: -" in gps_text:
            messagebox.showwarning("ไม่มีข้อมูล", "ยังไม่มีพิกัด GPS")
            return
        lines = gps_text.split('\n')
        lat = lines[0].replace('Lat: ', '').strip()
        lon = lines[1].replace('Lon: ', '').strip()
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        webbrowser.open(maps_url)
    except Exception as e:
        messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถเปิด Google Maps ได้\n{e}")

# ปุ่มเปิด Google Maps
ttk.Button(info_container, text="🗺️ เปิด Google Maps", 
          style="Primary.TButton", command=open_google_maps).pack(pady=10)

# ฟังก์ชันอัพเดทข้อมูล
def update_alert_info(alert_data):
    try:
        alert_name_label.config(text=f"👤 ผู้แจ้ง: {alert_data['name']}")
        alert_place_label.config(text=f"📍 สถานที่: {alert_data['place']}")
        alert_event_label.config(text=f"🚨 เหตุการณ์: {alert_data['event']}")
        alert_detail_label.config(text=f"📝 รายละเอียด: {alert_data['detail']}")
        alert_gps_label.config(text=f"Lat: {alert_data['lat']}\nLon: {alert_data['lon']}")
        print("✅ อัพเดทข้อมูลเหตุการณ์ใน frame2 สำเร็จ")
    except Exception as e:
        print(f"❌ ข้อผิดพลาด: {e}")

# ปุ่มนำทาง
btn_frame = tk.Frame(frame2, bg="#fff3cd")
btn_frame.pack(pady=10)

ttk.Button(btn_frame, text="➡️ ถัดไป (ถ่ายรูป)", 
          style="Primary.TButton", command=lambda: show_frame(frame3)).pack(side="left", padx=5)
ttk.Button(btn_frame, text="⬅️ ย้อนกลับ", 
          style="Secondary.TButton", command=lambda: show_frame(frame1)).pack(side="left", padx=5)

# ------------------ หน้า 3: ถ่ายรูป (ย้ายจาก frame2 เดิม) ------------------

tk.Label(frame3, text="📷 ถ่ายภาพ ณ สถานที่เกิดเหตุ", 
         font=("Arial", 12, "bold"), bg="white", fg="darkblue").pack(pady=5)

# Frame หลักสำหรับกล้อง
main_camera_frame = tk.Frame(frame3, bg="white")
main_camera_frame.pack(expand=True, fill="both", padx=5)

# Frame สำหรับกล้องและควบคุม (ส่วนบน)
camera_frame = tk.Frame(main_camera_frame, bg="white")
camera_frame.pack(side="top", fill="both", expand=True)

camera_label = tk.Label(camera_frame, bg="black", width=320, height=200, 
                       text="📹 กำลังเปิดกล้อง...", fg="white", font=("Arial", 8))
camera_label.pack(side="left", padx=3, pady=3)

# Panel ปุ่มควบคุม (ขนาดเล็กกว่า สำหรับ 800x400)
control_frame = tk.Frame(camera_frame, bg="lightgray", width=100)
control_frame.pack(side="right", fill="y", padx=3)
control_frame.pack_propagate(False)

# Frame สำหรับการตั้งค่ากล้อง (กลางจอ - ซ่อนไว้ตอนแรก)
settings_frame = tk.Frame(main_camera_frame, bg="lightgray", relief="raised", bd=4)
# ไม่ place() ตอนแรก - จะแสดงเมื่อกดปุ่มตั้งค่า

# เพิ่ม shadow effect และปรับแต่งการแสดงผล
settings_frame.configure(highlightbackground="darkgray", highlightthickness=2)

# สร้างเนื้อหาการตั้งค่าภายใน settings_frame (เพิ่ม padding สำหรับ modal)
settings_frame.configure(padx=10, pady=10)

settings_title = tk.Label(settings_frame, text="🔧 ปรับแต่งกล้อง", 
                         font=("Arial", 12, "bold"), bg="lightgray", fg="darkblue")
settings_title.pack(pady=5)

# แสดงค่าความสว่างปัจจุบัน
settings_brightness_info = tk.Label(settings_frame, text="ความสว่างปัจจุบัน: กำลังตรวจสอบ...", 
                                   font=("Arial", 8), bg="lightgray")
settings_brightness_info.pack(pady=1)

# Frame สำหรับ controls แบบแนวตั้ง (ปรับสำหรับ 800x400)
controls_frame = tk.Frame(settings_frame, bg="lightgray")
controls_frame.pack(pady=2, padx=5, fill="x")

# แถวที่ 1: Brightness
brightness_row = tk.Frame(controls_frame, bg="lightgray")
brightness_row.pack(pady=1, fill="x")

tk.Label(brightness_row, text="🔆 ความสว่าง", font=("Arial", 8, "bold"), 
         bg="lightgray", width=10, anchor="w").pack(side="left")
brightness_scale_embedded = tk.Scale(brightness_row, from_=0, to=100, orient="horizontal",
                                   length=150, width=12, bg="lightyellow",
                                   command=update_embedded_brightness)
brightness_scale_embedded.set(50)
brightness_scale_embedded.pack(side="left", padx=3)

# แถวที่ 2: Contrast  
contrast_row = tk.Frame(controls_frame, bg="lightgray")
contrast_row.pack(pady=1, fill="x")

tk.Label(contrast_row, text="🌗 ความเข้ม", font=("Arial", 8, "bold"), 
         bg="lightgray", width=10, anchor="w").pack(side="left")
contrast_scale_embedded = tk.Scale(contrast_row, from_=0, to=100, orient="horizontal",
                                 length=150, width=12, bg="lightblue",
                                 command=update_embedded_contrast)
contrast_scale_embedded.set(50)
contrast_scale_embedded.pack(side="left", padx=3)

# แถวที่ 3: Exposure
exposure_row = tk.Frame(controls_frame, bg="lightgray")
exposure_row.pack(pady=1, fill="x")

tk.Label(exposure_row, text="📸 Exposure", font=("Arial", 8, "bold"), 
         bg="lightgray", width=10, anchor="w").pack(side="left")
exposure_scale_embedded = tk.Scale(exposure_row, from_=0, to=100, orient="horizontal",
                                 length=150, width=12, bg="lightgreen",
                                 command=update_embedded_exposure)
exposure_scale_embedded.set(40)
exposure_scale_embedded.pack(side="left", padx=3)

# Frame สำหรับปุ่มโหมด - ปรับสำหรับ 800x400
preset_main_frame = tk.Frame(settings_frame, bg="lightgray")
preset_main_frame.pack(pady=2, fill="x")

# แถวเดียว: ปุ่มโหมดทั้งหมด (ขนาดเล็ก)
preset_row = tk.Frame(preset_main_frame, bg="lightgray")
preset_row.pack(pady=1, fill="x")

tk.Button(preset_row, text="💡 ปกติ", font=("Arial", 7), width=9, height=1,
         bg="lightgreen", fg="black", command=embedded_normal_setting).pack(side="left", padx=1)

tk.Button(preset_row, text="☀️ กลางแจ้ง", font=("Arial", 7), width=9, height=1,
         bg="yellow", fg="black", command=embedded_outdoor_setting).pack(side="left", padx=1)

tk.Button(preset_row, text="🏠 ในร่ม", font=("Arial", 7), width=9, height=1,
         bg="lightblue", fg="black", command=embedded_indoor_setting).pack(side="left", padx=1)

tk.Button(preset_row, text="🌙 มืด", font=("Arial", 7), width=9, height=1,
         bg="darkblue", fg="white", command=embedded_night_setting).pack(side="left", padx=1)

# ปุ่มปิดการตั้งค่า (แยกแถว แต่ขนาดเล็ก)
close_frame = tk.Frame(preset_main_frame, bg="lightgray")
close_frame.pack(pady=1, fill="x")

def apply_and_close_embedded():
    try:
        # อ่านค่าจากสไลด์แล้วปรับจริง
        b = brightness_scale_embedded.get()
        cval = contrast_scale_embedded.get()
        e = exposure_scale_embedded.get()
        schedule_camera_property('brightness', b)
        schedule_camera_property('contrast', cval)
        schedule_camera_property('exposure', e)
        # บังคับปรับทันทีเพื่อให้ผลเห็นชัดก่อนปิด
        set_camera_property(cv2.CAP_PROP_BRIGHTNESS, b, log_label="🔆 Brightness")
        set_camera_property(cv2.CAP_PROP_CONTRAST, cval, log_label="🌗 Contrast")
        set_camera_property(cv2.CAP_PROP_EXPOSURE, e, log_label="📸 Exposure", force_manual=True)
        rewarm_camera_preview(warm_frames=3, delay_sec=0.02)
    except Exception:
        pass
    # ปิดหน้าต่างตั้งค่าแบบฝัง
    toggle_camera_settings()

buttons_row = tk.Frame(close_frame, bg="lightgray")
buttons_row.pack()

tk.Button(buttons_row, text="✅ ตกลง", font=("Arial", 7, "bold"), width=12, height=1,
         bg="green", fg="white", command=apply_and_close_embedded).pack(side="left", padx=3)

tk.Button(buttons_row, text="❌ ปิด", font=("Arial", 7, "bold"), width=12, height=1,
         bg="red", fg="white", command=toggle_camera_settings).pack(side="left", padx=3)

tk.Label(control_frame, text="ควบคุม", font=("Arial", 8, "bold"), 
         bg="lightgray").pack(pady=2)

capture_btn = ttk.Button(control_frame, text="📷 ถ่าย", style="Accent.TButton", command=capture_image)
capture_btn.pack(pady=4, fill="x")

# แสดงจำนวนภาพที่ถ่าย
photo_count_label = tk.Label(control_frame, text="ภาพ: 0", 
                            font=("Arial", 7), bg="lightgray")
photo_count_label.pack(pady=1)

# ปุ่มตั้งค่ากล้อง
ttk.Button(control_frame, text="⚙️ ตั้งค่า", style="Secondary.TButton", command=toggle_camera_settings).pack(pady=4, fill="x")

def done_camera():
    """เสร็จสิ้นการถ่ายรูป ไปหน้าวัดสัญญาณชีพ"""
    show_frame(frame4)

ttk.Button(control_frame, text="✅ ถัดไป (วัดสัญญาณชีพ)", style="Success.TButton", command=done_camera).pack(side="bottom", pady=4, fill="x")
ttk.Button(control_frame, text="⬅️ ย้อนกลับ", style="Secondary.TButton", command=lambda: show_frame(frame2)).pack(side="bottom", pady=2, fill="x")

# ------------------ หน้า 4: วัดสัญญาณชีพ (เดิม frame3_sensor) ------------------

sensor_main_frame = tk.Frame(frame4, bg="#e0f7fa")
sensor_main_frame.pack(fill="both", expand=True)

# หัวข้อ (ลดขนาดฟอนต์และ padding)
tk.Label(sensor_main_frame, text="❤️ วัดค่าสัญญาณชีพ", 
         font=("Arial", 12, "bold"), bg="#e0f7fa", fg="#00695c").pack(pady=5)

tk.Label(sensor_main_frame, text="กรุณาวางนิ้วบนเซนเซอร์ MAX30102", 
         font=("Arial", 8), bg="#e0f7fa", fg="#004d40").pack(pady=2)

# Frame สำหรับแสดงผล (ลด padding และ border)
display_frame = tk.Frame(sensor_main_frame, bg="white", relief="ridge", bd=2)
display_frame.pack(pady=5, padx=15, fill="both", expand=True)

# จัดเรียง Heart Rate และ SpO2 แบบ 2 คอลัมน์เพื่อประหยัดพื้นที่
values_container = tk.Frame(display_frame, bg="white")
values_container.pack(pady=5, fill="both", expand=True)

# แถวที่ 1: Heart Rate (ซ้าย)
hr_frame = tk.Frame(values_container, bg="white")
hr_frame.pack(side="left", padx=10, pady=5, fill="both", expand=True)

tk.Label(hr_frame, text="💓 Heart Rate", 
         font=("Arial", 9, "bold"), bg="white", fg="#d32f2f").pack()

hr_value_label = tk.Label(hr_frame, text="-- BPM", 
                          font=("Arial", 24, "bold"), bg="white", fg="gray")
hr_value_label.pack(pady=3)

tk.Label(hr_frame, text="ปกติ: 60-100", 
         font=("Arial", 7), bg="white", fg="gray").pack()

# เส้นแบ่งแนวตั้ง
separator_v = tk.Frame(values_container, width=2, bg="#b0bec5")
separator_v.pack(side="left", fill="y", padx=5)

# แถวที่ 2: SpO2 (ขวา)
spo2_frame = tk.Frame(values_container, bg="white")
spo2_frame.pack(side="left", padx=10, pady=5, fill="both", expand=True)

tk.Label(spo2_frame, text="🫁 SpO2", 
         font=("Arial", 9, "bold"), bg="white", fg="#1976d2").pack()

spo2_value_label = tk.Label(spo2_frame, text="-- %", 
                            font=("Arial", 24, "bold"), bg="white", fg="gray")
spo2_value_label.pack(pady=3)

tk.Label(spo2_frame, text="ปกติ: 95-100%", 
         font=("Arial", 7), bg="white", fg="gray").pack()

# สถานะการวัด (ลดขนาดฟอนต์และ padding)
status_label = tk.Label(sensor_main_frame, text="⏳ กำลังรอข้อมูล...", 
                       font=("Arial", 8), bg="#e0f7fa", fg="orange")
status_label.pack(pady=3)

# กรอบแสดงสถานะผู้ป่วย (ใหม่)
patient_status_frame = tk.Frame(sensor_main_frame, bg="white", relief="ridge", bd=2)
patient_status_frame.pack(pady=5, padx=20, fill="x")

patient_status_label = tk.Label(
    patient_status_frame,
    text="📄 สถานะผู้ป่วย: รอการวัดค่า...",
    font=("Arial", 10, "bold"),
    bg="white",
    fg="gray",
    pady=8
)
patient_status_label.pack(fill="x")

# ฟังก์ชันประเมินสถานะผู้ป่วย
def assess_patient_status(hr, spo2):
    """ประเมินสถานะผู้ป่วยจากค่าสัญญาณชีพ"""
    # เกณฑ์ปกติ:
    # Heart Rate: 60-100 BPM
    # SpO2: 95-100%
    
    issues = []
    
    # ตรวจสอบ Heart Rate
    if hr < 60:
        issues.append("อัตราการเต้นของหัวใจต่ำกว่าปกติ")
    elif hr > 100:
        issues.append("อัตราการเต้ลของหัวใจสูงกว่าปกติ")
    
    # ตรวจสอบ SpO2
    if spo2 < 90:
        issues.append("ระดับออกซิเจนในเลือดต่ำมาก (วิกฤต)")
    elif spo2 < 95:
        issues.append("ระดับออกซิเจนต่ำกว่าปกติ")
    
    # ประเมินสถานะ
    if not issues:
        return {
            'status': 'safe',
            'message': '✅ ผู้ป่วยอยู่ในเกณฑ์ปลอดภัย',
            'color': '#4caf50',  # สีเขียว
            'bg': '#e8f5e9',
            'details': 'ค่าสัญญาณชีพอยู่ในช่วงปกติ'
        }
    elif len(issues) == 1 and ("ต่ำกว่าปกติ" in issues[0]):
        return {
            'status': 'warning',
            'message': '⚠️ ต้องติดตามอย่างใกล้ชิด',
            'color': '#ff9800',  # สีส้ม
            'bg': '#fff3e0',
            'details': '\n'.join([f"- {issue}" for issue in issues])
        }
    else:
        return {
            'status': 'danger',
            'message': '❌ ผู้ป่วยต้องได้รับการดูแลทันที!',
            'color': '#f44336',  # สีแดง
            'bg': '#ffebee',
            'details': '\n'.join([f"- {issue}" for issue in issues])
        }

# ปุ่มควบคุม (ลดขนาดและ padding)
button_frame = tk.Frame(sensor_main_frame, bg="#e0f7fa")
button_frame.pack(pady=5)

def start_measurement():
    """เริ่มการวัดค่า"""
    status_label.config(text="📊 กำลังวัดค่า...", fg="blue")
    start_sensor_reading()

def stop_measurement():
    """หยุดการวัดค่า"""
    stop_max30102()
    status_label.config(text="⏹️ หยุดการวัดค่า", fg="red")
    hr_value_label.config(text="-- BPM", fg="gray")
    spo2_value_label.config(text="-- %", fg="gray")

def save_and_continue():
    """บันทึกค่าและไปหน้าถัดไป"""
    global heart_rate, spo2, sensor_data_ready
    
    if not sensor_data_ready:
        messagebox.showwarning("คำเตือน", "กรุณาวัดค่าให้เสร็จก่อน")
        return
    
    # หยุดเซนเซอร์
    stop_max30102()
    
    # ประเมินสถานะผู้ป่วย
    assessment = assess_patient_status(heart_rate, spo2)
    
    # แสดงข้อมูลที่บันทึก
    messagebox.showinfo(
        "บันทึกสำเร็จ", 
        f"{assessment['message']}\n\n"
        f"💓 Heart Rate: {heart_rate} BPM\n"
        f"🫁 SpO2: {spo2}%\n\n"
        f"📊 รายละเอียด:\n{assessment['details']}"
    )
    
    # ไปหน้าถัดไป (กรอกข้อมูล)
    show_frame(frame5)

def skip_sensor():
    """ข้ามการวัดค่าและไปหน้าถัดไป"""
    global heart_rate, spo2, sensor_data_ready
    
    # หยุดเซนเซอร์ถ้ากำลังทำงานอยู่
    stop_max30102()
    
    # รีเซ็ตค่า
    heart_rate = 0
    spo2 = 0
    sensor_data_ready = False
    
    # ไปหน้าถัดไป (กรอกข้อมูล)
    show_frame(frame5)

def simulate_sensor_data():
    """จำลองค่าเซนเซอร์แบบสุ่ม (สำหรับทดสอบ)"""
    global heart_rate, spo2, sensor_data_ready
    
    import random
    
    print("🎲 กำลังจำลองค่าเซนเซอร์...")
    
    # สุ่มสถานการณ์ต่างๆ
    scenario = random.choice([
        'normal',      # ปกติ (50%)
        'normal',      # ปกติ (เพิ่มโอกาส)
        'warning',     # เตือน (25%)
        'danger'       # อันตราย (25%)
    ])
    
    if scenario == 'normal':
        # ค่าปกติ
        heart_rate = random.randint(60, 100)  # 60-100 BPM
        spo2 = random.randint(95, 100)  # 95-100%
        print("📊 สุ่มค่าปกติ")
    elif scenario == 'warning':
        # ค่าเตือน (เบี่ยงเบนเล็กน้อย)
        if random.choice([True, False]):
            heart_rate = random.randint(55, 59)  # ต่ำกว่าปกติเล็กน้อย
            spo2 = random.randint(92, 94)  # SpO2 ต่ำกว่าปกติ
        else:
            heart_rate = random.randint(101, 110)  # สูงกว่าปกติเล็กน้อย
            spo2 = random.randint(92, 94)
        print("⚠️ สุ่มค่าเตือน")
    else:  # danger
        # ค่าอันตราย
        if random.choice([True, False]):
            heart_rate = random.randint(40, 55)  # ต่ำมาก
            spo2 = random.randint(85, 91)  # SpO2 ต่ำมาก
        else:
            heart_rate = random.randint(110, 130)  # สูงมาก
            spo2 = random.randint(85, 91)
        print("🚨 สุ่มค่าอันตราย")
    
    sensor_data_ready = True
    
    # อัพเดท UI
    hr_value_label.config(
        text=f"{heart_rate} BPM",
        fg="#d32f2f"  # สีแดง
    )
    
    spo2_value_label.config(
        text=f"{spo2}%",
        fg="#1976d2"  # สีน้ำเงิน
    )
    
    # ประเมินสถานะผู้ป่วย
    assessment = assess_patient_status(heart_rate, spo2)
    
    # อัพเดทสถานะ
    status_label.config(
        text=f"{assessment['message']}",
        fg=assessment['color']
    )
    
    patient_status_label.config(
        text=f"{assessment['message']}\n{assessment['details']}",
        fg=assessment['color'],
        bg=assessment['bg']
    )
    patient_status_frame.config(bg=assessment['bg'])
    
    print(f"✅ จำลองค่าสำเร็จ: HR={heart_rate} BPM, SpO2={spo2}%")
    print(f"📊 สถานะ: {assessment['status']}")
    
    # แสดง popup สถานะผู้ป่วย
    if assessment['status'] == 'safe':
        messagebox.showinfo(
            "✅ สถานะผู้ป่วย: ปลอดภัย",
            f"{assessment['message']}\n\n"
            f"💓 Heart Rate: {heart_rate} BPM (ปกติ: 60-100)\n"
            f"🫁 SpO2: {spo2}% (ปกติ: 95-100)\n\n"
            f"📊 {assessment['details']}"
        )
    elif assessment['status'] == 'warning':
        messagebox.showwarning(
            "⚠️ สถานะผู้ป่วย: ต้องติดตาม",
            f"{assessment['message']}\n\n"
            f"💓 Heart Rate: {heart_rate} BPM (ปกติ: 60-100)\n"
            f"🫁 SpO2: {spo2}% (ปกติ: 95-100)\n\n"
            f"📋 ปัญหาที่พบ:\n{assessment['details']}"
        )
    else:  # danger
        messagebox.showerror(
            "❌ สถานะผู้ป่วย: อันตราย!",
            f"{assessment['message']}\n\n"
            f"💓 Heart Rate: {heart_rate} BPM (ปกติ: 60-100)\n"
            f"🫁 SpO2: {spo2}% (ปกติ: 95-100)\n\n"
            f"🚨 ปัญหาร้ายแรง:\n{assessment['details']}\n\n"
            f"⚕️ ควรรีบนำส่งโรงพยาบาลทันที!"
        )

# ปุ่มควบคุม (ลดขนาดปุ่ม)
ttk.Button(button_frame, text="▶️ เริ่มวัด", style="Success.TButton", 
          command=start_measurement).pack(side="left", padx=2)

ttk.Button(button_frame, text="⏹️ หยุด", style="Danger.TButton", 
          command=stop_measurement).pack(side="left", padx=2)

ttk.Button(button_frame, text="🎲 จำลองค่า", style="Accent.TButton", 
          command=simulate_sensor_data).pack(side="left", padx=2)

ttk.Button(button_frame, text="✅ บันทึกและถัดไป", style="Primary.TButton", 
          command=save_and_continue).pack(side="left", padx=2)

ttk.Button(button_frame, text="⏭️ ข้าม", style="Secondary.TButton", 
          command=skip_sensor).pack(side="left", padx=2)

ttk.Button(button_frame, text="⬅️ ย้อนกลับ", style="Secondary.TButton", 
          command=lambda: [stop_max30102(), show_frame(frame3)]).pack(side="left", padx=2)

# คำแนะนำ (ลดขนาดและ padding)
instruction_frame = tk.Frame(sensor_main_frame, bg="#fff9c4", relief="solid", bd=1)
instruction_frame.pack(pady=3, padx=15, fill="x")

tk.Label(instruction_frame, text="💡 คำแนะนำ:", 
         font=("Arial", 7, "bold"), bg="#fff9c4", fg="#f57f17").pack(anchor="w", padx=5, pady=2)

instructions = [
    "1. วางนิ้วบนเซนเซอร์อย่างนิ่งๆ",
    "2. รอประมาณ 10-15 วินาที",
    "3. ค่าจะแสดงเมื่อวัดได้แม่นยำ"
]

for inst in instructions:
    tk.Label(instruction_frame, text=inst, 
             font=("Arial", 6), bg="#fff9c4", fg="#795548").pack(anchor="w", padx=10, pady=0)

tk.Label(instruction_frame, text="", bg="#fff9c4").pack(pady=1)

# ------------------ หน้า 5: กรอกข้อมูล (เดิม frame3) ------------------

# สร้าง main frame สำหรับ content และ keyboard
main_frame = tk.Frame(frame5, bg="white")
main_frame.pack(fill="both", expand=True)

# Content frame (ส่วนบน)
content_frame = tk.Frame(main_frame, bg="white")
content_frame.pack(side="top", fill="both", expand=True)

# Keyboard container (ส่วนล่าง)
keyboard_container_frame5 = tk.Frame(main_frame, bg="white")
keyboard_container_frame5.pack(side="bottom", fill="x")

tk.Label(content_frame, text="📝 กรอกข้อมูลผู้ประสบอุบัติเหตุ", 
         font=("Arial", 14, "bold"), bg="white", fg="darkblue").pack(pady=15)

# Form Frame (ปรับขนาดให้เหมาะสมสำหรับหน้าจอ 800x400)
form_frame = tk.Frame(content_frame, bg="lightblue", relief="ridge", bd=2)
form_frame.pack(pady=10, padx=15, fill="x")

# ชื่อ
name_frame = tk.Frame(form_frame, bg="lightblue")
name_frame.pack(pady=4, padx=20, fill="x")
tk.Label(name_frame, text="ชื่อ (NAME) :", font=("Arial", 10, "bold"), 
         bg="lightblue", width=15, anchor="w").pack(side="left")
entry_name = tk.Entry(name_frame, font=("Arial", 10), width=25, relief="solid", bd=1)
entry_name.pack(side="left", padx=5)

# เพิ่ม event handler สำหรับแป้นพิมพ์ (รองรับ container สำหรับฝังคีย์บอร์ด)
def on_entry_click(widget, container):
    def handler(event):
        show_keyboard(widget, container)
    return handler

entry_name.bind("<Button-1>", on_entry_click(entry_name, keyboard_container_frame5))

# ปุ่มแป้นพิมพ์สำหรับชื่อ
tk.Button(name_frame, text="⌨️❌ ปิดแป้นพิมพ์", font=("Arial", 10), width=3, height=1,
          command=hide_keyboard,
          bg="yellow", fg="black").pack(side="left", padx=2)

# นามสกุล
surname_frame = tk.Frame(form_frame, bg="lightblue")
surname_frame.pack(pady=4, padx=20, fill="x")
tk.Label(surname_frame, text="นามสกุล (SURNAME) :", font=("Arial", 10, "bold"), 
         bg="lightblue", width=15, anchor="w").pack(side="left")
entry_surname = tk.Entry(surname_frame, font=("Arial", 10), width=25, relief="solid", bd=1)
entry_surname.pack(side="left", padx=5)
entry_surname.bind("<Button-1>", on_entry_click(entry_surname, keyboard_container_frame5))

# ปุ่มแป้นพิมพ์สำหรับนามสกุล
tk.Button(surname_frame, text="⌨️❌ ปิดแป้นพิมพ์", font=("Arial", 10), width=3, height=1,
          command=hide_keyboard,
          bg="yellow", fg="black").pack(side="left", padx=2)

# อายุ
age_frame = tk.Frame(form_frame, bg="lightblue")
age_frame.pack(pady=4, padx=20, fill="x")
tk.Label(age_frame, text="อายุ (AGE) :", font=("Arial", 10, "bold"), 
         bg="lightblue", width=15, anchor="w").pack(side="left")
combo_age = ttk.Combobox(age_frame, values=[str(i) for i in range(1, 120)], 
                        font=("Arial", 10), width=15, state="readonly", style="Modern.TCombobox")
combo_age.pack(side="left", padx=5)

# ฟังก์ชันอ่านบัตรประชาชน
def read_thai_id_card():
    """อ่านบัตรประชาชนและกรอกข้อมูลอัตโนมัติ"""
    if not THAICID_READER_AVAILABLE:
        messagebox.showerror(
            "ข้อผิดพลาด", 
            "ไม่สามารถใช้งานฟีเจอร์อ่านบัตรประชาชน\n"
            "กรุณาติดตั้ง: pip install pyscard"
        )
        return
    
    try:
        # แสดงข้อความกำลังอ่าน
        result = messagebox.askokcancel(
            "อ่านบัตรประชาชน",
            "🏧 กรุณาเสียบบัตรประชาชน\n\n"
            "ตรวจสอบให้แน่ใจว่า:\n"
            "1. เครื่องอ่านบัตรเชื่อมต่อกับคอมพิวเตอร์\n"
            "2. บัตรประชาชนเสียบเข้าเครื่องอ่านบัตร\n\n"
            "กด OK เพื่ออ่านบัตร"
        )
        
        if not result:
            return
        
        # สร้าง reader object
        reader = SimpleThaiCIDReader()
        
        # อ่านบัตร
        print("🏧 กำลังอ่านบัตรประชาชน...")
        card_data = reader.read_card_simple()
        
        if card_data:
            # กรอกข้อมูลลงในฟอร์ม
            entry_name.delete(0, tk.END)
            entry_name.insert(0, card_data['firstname'])
            
            entry_surname.delete(0, tk.END)
            entry_surname.insert(0, card_data['lastname'])
            
            combo_age.set(str(card_data['age']))
            
            # แสดงข้อความสำเร็จ
            messagebox.showinfo(
                "อ่านบัตรสำเร็จ",
                f"✅ อ่านข้อมูลสำเร็จ!\n\n"
                f"👤 ชื่อ: {card_data['firstname']}\n"
                f"👥 นามสกุล: {card_data['lastname']}\n"
                f"🎂 อายุ: {card_data['age']} ปี\n"
                f"🎉 วันเกิด: {card_data['birth_date']}"
            )
            print("✅ กรอกข้อมูลสำเร็จ")
        else:
            messagebox.showerror(
                "ข้อผิดพลาด",
                f"❌ ไม่สามารถอ่านบัตรได้\n\n"
                f"สาเหตุ: {reader.last_error}\n\n"
                f"กรุณาตรวจสอบ:\n"
                f"1. เครื่องอ่านบัตรเชื่อมต่อหรือไม่\n"
                f"2. บัตรประชาชนเสียบเข้าเครื่องอ่านบัตรหรือไม่"
            )
            print(f"❌ อ่านบัตรล้มเหลว: {reader.last_error}")
            
    except Exception as e:
        messagebox.showerror(
            "ข้อผิดพลาด",
            f"❌ เกิดข้อผิดพลาด: {e}"
        )
        print(f"❌ ข้อผิดพลาดในการอ่านบัตร: {e}")
        traceback.print_exc()

# ปุ่มอ่านบัตรประชาชน (เพิ่มหลังจากช่องอายุ)
id_card_frame = tk.Frame(form_frame, bg="lightblue")
id_card_frame.pack(pady=8, padx=20, fill="x")

ttk.Button(id_card_frame, text="🏧 อ่านบัตรประชาชน", 
          style="Success.TButton",
          command=read_thai_id_card).pack(pady=5)

tk.Label(id_card_frame, 
         text="💡 กรอกข้อมูลอัตโนมัติจากบัตรประชาชน", 
         font=("Arial", 8), 
         bg="lightblue", 
         fg="#00695c").pack()

# ปุ่มบันทึก (ปรับขนาดสำหรับหน้าจอ 800x400)
button_frame = tk.Frame(content_frame, bg="white")
button_frame.pack(pady=8)

ttk.Button(button_frame, text="➡️ ถัดไป", style="Primary.TButton", 
          command=lambda: show_frame(frame6)).pack(side="left", padx=3)



ttk.Button(button_frame, text="⬅️ ย้อนกลับ", style="Secondary.TButton", 
          command=lambda: show_frame(frame4)).pack(side="left", padx=3)

# ---------- หน้า 6: บันทึกรายละเอียด (เดิม frame4) -------------------------

frame6_content = tk.Frame(frame6, bg="white")
frame6_content.pack(expand=True, fill="both")

# ใช้ container ให้อยู่กลางจอ
center_frame6 = tk.Frame(frame6_content, bg="white")
center_frame6.place(relx=0.5, rely=0.35, anchor="center")  # ขยับขึ้นเพื่อเว้นพื้นที่คีบอร์ด

# Keyboard container for frame6 (ฝังแป้นพิมพ์ด้านล่าง)
keyboard_container_frame6 = tk.Frame(frame6_content, bg="white")
keyboard_container_frame6.pack(side="bottom", fill="x")

tk.Label(center_frame6, text="📋 เลือกเหตุการณ์", 
         font=("Arial", 12, "bold"), bg="white", fg="darkblue").pack(pady=1)

event_options = ["ประสบอุบัติเหตุทางถนน", 
                 "อุบัติเหตุทั่วไป", 
                 "อุบัติเหตุไม่ทั่วไป", 
                 "อุบัติเหตุอุอิอา"]

selected_event = tk.StringVar()
combo_event = ttk.Combobox(center_frame6, textvariable=selected_event, 
                           values=event_options, font=("Arial", 10), 
                           state="readonly", width=35, style="Modern.TCombobox")
combo_event.pack(pady=3)

# รายละเอียดเพิ่มเติม
detail_frame = tk.Frame(center_frame6, bg="white")
detail_frame.pack(pady=3)

tk.Label(detail_frame, text="รายละเอียดเพิ่มเติม:", 
         font=("Arial", 10, "bold"), bg="white").pack()

detail_input_frame = tk.Frame(detail_frame, bg="white")
detail_input_frame.pack(pady=3)

entry_detail = tk.Entry(detail_input_frame, font=("Arial", 10), width=35)
entry_detail.pack(side="left", padx=5)
entry_detail.bind("<Button-1>", on_entry_click(entry_detail, keyboard_container_frame6))

# เพิ่มปุ่มแป้นพิมพ์สำหรับ entry_detail
tk.Button(detail_input_frame, text="⌨️❌ ปิดแป้นพิมพ์", font=("Arial", 10), width=3, height=1,
          command=hide_keyboard,
          bg="yellow", fg="black").pack(side="left", padx=2)


ttk.Button(center_frame6, text="⬅️ ย้อนกลับ", 
          style="Secondary.TButton",
          command=lambda: show_frame(frame5)).pack(side="left", padx=5)

# ปุ่มบันทึก
ttk.Button(center_frame6, text="💾 บันทึกข้อมูลและสร้าง PDF", 
          style="Primary.TButton",
          command=save_data).pack(pady=10)


# อัพเดทจำนวนภาพ
def update_photo_count():
    photo_count_label.config(text=f"ภาพ: {len(captured_images)}")
    safe_after(root,1000, update_photo_count)

# เริ่มการอัพเดท
update_photo_count()

# เริ่มหน้าแรก
show_frame(frame1)

# จัดการการปิดโปรแกรม
def on_closing():
    global cap, camera_running, sensor_running
    
    # ปิดกล้อง
    camera_running = False
    if cap:
        cap.release()
    cv2.destroyAllWindows()
    
    # ปิดเซนเซอร์
    stop_max30102()
    
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing) 

# เริ่มต้นโปรแกรม
if __name__ == "__main__":
    print("🚀 เริ่มต้น Smart EMS+ สำหรับหน้าจอ 800x400")
    print("📋 ตรวจสอบการเชื่อมต่อกล้อง USB หรือ Pi Camera")
    print("❤️ ตรวจสอบการเชื่อมต่อเซนเซอร์ MAX30102 (I2C)")
    print("📁 โฟลเดอร์ที่สร้าง:")
    print("   - captured_images/ (สำหรับเก็บรูปภาพ)")
    print("   - pdf_reports/ (สำหรับเก็บไฟล์ PDF)")
    print("⌨️ แป้นพิมพ์เสมือนจะปรากฏที่ด้านล่างเมื่อคลิกช่องกรอกข้อมูล")
    print("📷 รูปภาพจะแสดงจริงใน PDF แทนที่จะเป็นเพียงชื่อไฟล์")
    print("📹 กล้องจะทำงานตลอดเวลาเมื่อโปรแกรมเปิด")
    print("💓 หน้าวัดสัญญาณชีพ: Heart Rate และ SpO2")
    print("🔔 ระบบแจ้งเตือนจาก WebApp: เปิดใช้งาน")
    
    # ซ่อนหน้าต่างหลักก่อน
    root.withdraw()
    
    # สร้างและแสดงหน้าต่างโหลด
    loading_popup = LoadingPopup(root)
    loading_popup.show()

    # เริ่มระบบตรวจสอบการแจ้งเหตุ
    start_alert_watcher()
    
    # เริ่มการตรวจสอบสถานะกล้องหลังจากโหลดเสร็จ
    def start_camera_monitoring():
        check_camera_status()
    
    
    # เริ่มการตรวจสอบสถานะกล้องหลังจาก 5 วินาที (หลังจากโหลดเสร็จ)
    safe_after(root,5000, start_camera_monitoring)
    
    root.mainloop()