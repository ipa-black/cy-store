from http.server import BaseHTTPRequestHandler
import json
import requests
import base64

# === بياناتك مدمجة بالكامل وثابتة ===
BOT_TOKEN = "8828583983:AAH1M4PFuW7zHNwKkpvhdErYVoT0KEilJjU"
MY_CHAT_ID = 8509558203
GITHUB_TOKEN = "Ghp_PtjQyUaevBt57hd1vsLyrIlGorcNg34WOCEf"
GITHUB_REPO = "ipa-black/cy-store"
WORKFLOW_ID = "sign.yml"

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        update = json.loads(post_data.decode('utf-8'))
        
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            
            # حماية البوت: قفل الاستجابة على حسابك أنت فقط
            if chat_id != MY_CHAT_ID:
                self.send_response(200)
                self.end_headers()
                return
                
            if "document" in message:
                document = message["document"]
                file_name = document.get("file_name", "")
                
                # التحقق من إرسال ملف الشهادات المضغوط .zip
                if file_name.endswith(".zip"):
                    file_id = document["file_id"]
                    password = message.get("caption", "").strip()
                    
                    if not password:
                        self.send_msg(chat_id, "❌ الرجاء إرسال ملف الـ ZIP مع كتابة كلمة مرور الشهادة في تعليق الملف (Caption).")
                        self.send_response(200)
                        self.end_headers()
                        return
                        
                    self.send_msg(chat_id, "⏳ جاري جلب الملف وتمريره إلى GitHub Actions لبدء توقيع CY STORE...")
                    
                    # تحميل الملف مؤقتاً من خوادم تيليجرام لترميزه
                    file_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
                    if file_info.get("ok"):
                        file_path = file_info["result"]["file_path"]
                        file_content = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}").content
                        
                        # تحويل الملف إلى Base64 لتمريره عبر الـ API
                        zip_b64 = base64.b64encode(file_content).decode('utf-8')
                        
                        # استدعاء الأتمتة في جيت هب
                        gh_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{WORKFLOW_ID}/dispatches"
                        gh_headers = {
                            "Accept": "application/vnd.github+json",
                            "Authorization": f"Bearer {GITHUB_TOKEN}"
                        }
                        gh_data = {
                            "ref": "main",
                            "inputs": {
                                "zip_base64": zip_b64,
                                "password": password,
                                "chat_id": str(chat_id)
                            }
                        }
                        
                        gh_res = requests.post(gh_url, headers=gh_headers, json=gh_data)
                        if gh_res.status_code == 204:
                            self.send_msg(chat_id, "🚀 تم تشغيل سرفر جيت هب بنجاح! جاري فك الضغط والتوقيع...")
                        else:
                            self.send_msg(chat_id, f"❌ حدث خطأ أثناء تشغيل جيت هب: {gh_res.text}")
                    else:
                        self.send_msg(chat_id, "❌ فشل تحميل الملف من خوادم تيليجرام.")
            
            elif "text" in message and message["text"] == "/start":
                self.send_msg(chat_id, "👋 مرحباً بك في بوت توقيع CY STORE الذكي.\n\nاضغط ملف الشهادة (.p12) وملف الوصف (.mobileprovision) معاً في ملف واحد بصيغة (.zip)، ثم أرسله هنا واكتب كلمة مرور الشهادة في تعليق الملف.")
                
        self.send_response(200)
        self.end_headers()

    def send_msg(self, chat_id, text):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text})
