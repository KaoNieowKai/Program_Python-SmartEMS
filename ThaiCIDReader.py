"""
Simple Thai CID Reader for Smart EMS+
อ่านเฉพาะ ชื่อ นามสกุล และวันเกิด (เพื่อคำนวณอายุ)
"""

import sys
import os

# เพิ่ม path ของโฟลเดอร์ที่มี ThaiCIDHelper
sys.path.append(os.path.join(os.path.dirname(__file__), 'python_ThaiCID-GUI-PyQT6-main'))

try:
    from ThaiCIDHelper import ThaiCIDHelper
    from DataThaiCID import SaveType
    THAICID_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ไม่สามารถ import ThaiCIDHelper: {e}")
    THAICID_AVAILABLE = False

from datetime import datetime


class SimpleThaiCIDReader:
    """อ่านบัตรประชาชนไทยแบบง่าย สำหรับ Smart EMS+"""
    
    def __init__(self):
        self.reader = None
        self.card_data = {}
        self.last_error = ""
        
    def check_reader_available(self):
        """ตรวจสอบว่ามีเครื่องอ่านบัตรหรือไม่"""
        if not THAICID_AVAILABLE:
            self.last_error = "ไม่มี pyscard library"
            return False
        
        try:
            self.reader = ThaiCIDHelper(
                ShowThaiDate=False,  # ใช้รูปแบบวันที่แบบสากล
                pathTempFile="tmp"
            )
            
            if self.reader.CardReaderCount == 0:
                self.last_error = "ไม่พบเครื่องอ่านบัตร"
                return False
            
            return True
            
        except Exception as e:
            self.last_error = f"ข้อผิดพลาด: {e}"
            return False
    
    def read_card_simple(self):
        """
        อ่านบัตรประชาชน (เฉพาะชื่อ นามสกุล และอายุ)
        Returns: dict {'firstname': str, 'lastname': str, 'age': int} หรือ None
        """
        if not THAICID_AVAILABLE:
            self.last_error = "ไม่มี pyscard library - กรุณาติดตั้ง: pip install pyscard"
            return None
        
        try:
            print("\n" + "="*50)
            print("🆔 เริ่มอ่านบัตรประชาชน")
            print("="*50)
            
            # ตรวจสอบเครื่องอ่านบัตร
            if not self.check_reader_available():
                print(f"❌ {self.last_error}")
                return None
            
            print(f"✅ พบเครื่องอ่านบัตร: {self.reader.CardReaderCount} เครื่อง")
            
            # เชื่อมต่อกับเครื่องอ่านบัตรตัวแรก
            connection = self.reader.connectReader(0)
            if not connection:
                self.last_error = "ไม่สามารถเชื่อมต่อกับเครื่องอ่านบัตร"
                print(f"❌ {self.last_error}")
                return None
            
            print("✅ เชื่อมต่อกับเครื่องอ่านบัตรสำเร็จ")
            print("📖 กำลังอ่านข้อมูล...")
            
            # อ่านข้อมูลจากบัตร (ไม่อ่านรูปภาพเพื่อความเร็ว)
            self.reader.readData(
                readPhoto=False,
                saveText=SaveType.NONE,
                savePhoto=SaveType.NONE
            )
            
            # ดึงข้อมูลที่ต้องการ
            card_data = self.reader.CardData
            
            if not card_data:
                self.last_error = "ไม่สามารถอ่านข้อมูลจากบัตรได้"
                print(f"❌ {self.last_error}")
                return None
            
            # แยกชื่อ-นามสกุล (ภาษาไทย)
            fullname_th = card_data.get('FULLNAME-TH', '')
            name_parts = fullname_th.split(' ', 1)  # แยกที่ช่องว่างตัวแรก
            
            firstname = name_parts[0] if len(name_parts) > 0 else ''
            lastname = name_parts[1] if len(name_parts) > 1 else ''
            
            # คำนวณอายุจากวันเกิด
            birth_date_str = card_data.get('BIRTH', '')  # รูปแบบ: YYYY-MM-DD
            age = self._calculate_age(birth_date_str)
            
            result = {
                'firstname': firstname.strip(),
                'lastname': lastname.strip(),
                'age': age,
                'birth_date': birth_date_str,
                'fullname': fullname_th
            }
            
            print("\n✅ อ่านบัตรสำเร็จ!")
            print(f"   ชื่อ: {result['firstname']}")
            print(f"   นามสกุล: {result['lastname']}")
            print(f"   อายุ: {result['age']} ปี")
            print(f"   วันเกิด: {result['birth_date']}")
            print("="*50 + "\n")
            
            # ปิดการเชื่อมต่อ
            try:
                self.reader.disconnect()
            except:
                pass
            
            return result
            
        except Exception as e:
            self.last_error = f"ข้อผิดพลาดในการอ่านบัตร: {e}"
            print(f"❌ {self.last_error}")
            import traceback
            traceback.print_exc()
            return None
    
    def _calculate_age(self, birth_date_str):
        """
        คำนวณอายุจากวันเกิด
        birth_date_str: รูปแบบ YYYY-MM-DD (ค.ศ.)
        """
        if not birth_date_str or len(birth_date_str) < 8:
            return 0
        
        try:
            # แปลงจาก string เป็น datetime
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
            today = datetime.today()
            
            # คำนวณอายุ
            age = today.year - birth_date.year
            
            # ปรับอายุถ้ายังไม่ถึงวันเกิดในปีนี้
            if (today.month, today.day) < (birth_date.month, birth_date.day):
                age -= 1
            
            return age
            
        except Exception as e:
            print(f"⚠️ ไม่สามารถคำนวณอายุได้: {e}")
            return 0


# ฟังก์ชันทดสอบ
if __name__ == "__main__":
    reader = SimpleThaiCIDReader()
    
    print("🔍 ตรวจสอบเครื่องอ่านบัตร...")
    if reader.check_reader_available():
        print("✅ พร้อมใช้งาน!")
        print("\n📌 กรุณาเสียบบัตรประชาชนแล้วกด Enter...")
        input()
        
        result = reader.read_card_simple()
        if result:
            print("\n✅ ผลลัพธ์:")
            print(f"   ชื่อ: {result['firstname']}")
            print(f"   นามสกุล: {result['lastname']}")
            print(f"   อายุ: {result['age']} ปี")
        else:
            print(f"\n❌ ไม่สามารถอ่านบัตรได้: {reader.last_error}")
    else:
        print(f"❌ {reader.last_error}")
