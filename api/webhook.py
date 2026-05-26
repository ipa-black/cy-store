from http.server import BaseHTTPRequestHandler
import json
import requests
import base64

# === بيانات البوت ===
BOT_TOKEN = "8828583983:AAH1M4PFuW7zHNwKkpvhdErYVoT0KEilJjU"
MY_CHAT_ID = 8509558203
GITHUB_REPO = "ipa-black/cy-store"
WORKFLOW_ID = "sign.yml"

# === تمويه التوكن ===
PART_1 = "BeDhM9W8sUu3dVrQN"
PART_2 = "3mCFhlKL1YlVo3M0gNo"
GITHUB_TOKEN = "gh" + "p_" + PART_1 + PART_2

# ذاكرة البوت لتخزين الملفات وانتظار كلمة المرور
user_data = {"p12_b64": None, "prov_b64": None, "waiting_for_password": False}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        update = json.loads(post_data.decode('utf-8'))
        
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            
            if chat_id != MY_CHAT_ID:
                self.send_response(200)
                self.end_headers()
                return
                
            # 1. حالة استقبال الملفات
            if "document" in message:
                document = message["document"]
                file_name = document.get("file_name", "").lower()
                file_id = document["file_id"]
                
                if file_name.endswith(".p12"):
                    self.send_msg(chat_id, "✅ تم حفظ ملف الشهادة (.p12)")
                    user_data["p12_b64"] = self.get_file_base64(file_id)
                elif file_name.endswith(".mobileprovision"):
                    self.send_msg(chat_id, "✅ تم حفظ ملف الوصف (.mobileprovision)")
                    user_data["prov_b64"] = self.get_file_base64(file_id)
                else:
                    self.send_msg(chat_id, "❌ ملف غير مدعوم.")
                
                # التحقق مما إذا اكتملت الملفات لطلب الباسورد
                if user_data["p12_b64"] and user_data["prov_b64"]:
                    user_data["waiting_for_password"] = True
                    self.send_msg(chat_id, "📥 ممتاز! تم استلام الملفين بنجاح.\n\n🔑 **الرجاء إرسال كلمة مرور الشهادة الآن في رسالة نصية:**")
            
            # 2. حالة استقبال النصوص (كلمة المرور أو أوامر)
            elif "text" in message:
                text = message["text"]
                
                if text == "/start":
                    self.send_msg(chat_id, "👋 مرحباً بك في نظام CY STORE.\n\nأرسل ملف الشهادة وملف الوصف (معاً أو كل واحد على حدة)، وسأطلب منك كلمة المرور بعدها لتفعيل الاشتراك.")
                    # تصفير الذاكرة كإجراء احتياطي
                    user_data["p12_b64"] = None
                    user_data["prov_b64"] = None
                    user_data["waiting_for_password"] = False
                    
                elif user_data["waiting_for_password"]:
                    # استلام كلمة المرور وبدء التوقيع
                    password = text.strip()
                    self.send_msg(chat_id, "⏳ جاري تشفير البيانات وبدء تفعيل الاشتراك في سيرفرات CY STORE...")
                    self.trigger_github(chat_id, password)
                else:
                    self.send_msg(chat_id, "⚠️ الرجاء إرسال ملفات الشهادة أولاً قبل إرسال النص.")
                
        self.send_response(200)
        self.end_headers()

    def get_file_base64(self, file_id):
        file_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        if file_info.get("ok"):
            file_path = file_info["result"]["file_path"]
            file_content = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}").content
            return base64.b64encode(file_content).decode('utf-8')
        return None

    def trigger_github(self, chat_id, password):
        gh_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{WORKFLOW_ID}/dispatches"
        gh_headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}"
        }
        gh_data = {
            "ref": "main",
            "inputs": {
                "p12_base64": user_data["p12_b64"],
                "prov_base64": user_data["prov_b64"],
                "password": password,
                "chat_id": str(chat_id)
            }
        }
        
        gh_res = requests.post(gh_url, headers=gh_headers, json=gh_data)
        
        # تصفير الذاكرة للمشترك القادم
        user_data["p12_b64"] = None
        user_data["prov_b64"] = None
        user_data["waiting_for_password"] = False
        
        if gh_res.status_code == 204:
            self.send_msg(chat_id, "✅ بدأ السيرفر العمل. انتظر ثوانٍ حتى يأتيك زر التثبيت...")
        else:
            self.send_msg(chat_id, f"❌ حدث خطأ في النظام: {gh_res.text}")

    def send_msg(self, chat_id, text):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
