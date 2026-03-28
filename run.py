import os
import threading
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler

load_dotenv()

import bot

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"They Never Told Us Bot is running!")

    def log_message(self, format, *args):
        pass

def run_server():
    port   = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    server.serve_forever()

print("=" * 50)
print("  They Never Told Us — Bot Suite")
print("=" * 50)
print()

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
print(f"Keep-alive server started on port {os.getenv('PORT', 8080)}")

bot_thread = threading.Thread(target=bot.run, daemon=True)
bot_thread.start()

bot_thread.join()
