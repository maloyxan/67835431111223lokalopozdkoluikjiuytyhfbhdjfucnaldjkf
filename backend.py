# backend.py
import os 
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from aiocryptopay import AioCryptoPay, Networks
from pydantic import BaseModel

# --- НАСТРОЙКИ ---
# Вставь сюда свой токен от @CryptoBot
CRYPTO_BOT_TOKEN = "488878:AAEYsdgmETPsCvrqpkkEDxhkGkLFmT3Ep0w" 
# Используй Networks.MAIN_NET для реальных денег, TEST_NET для тестов
NETWORK = Networks.MAIN_NET 

app = FastAPI()
cryptopay = AioCryptoPay(token=CRYPTO_BOT_TOKEN, network=NETWORK)

# ========== ПОИСК ПАПКИ FRONTEND ==========
print("=" * 50)
print("🔍 ПОИСК ПАПКИ FRONTEND")

# Где мы сейчас?
current_dir = os.getcwd()
print(f"Текущая директория: {current_dir}")

# Проверяем разные возможные места
possible_paths = [
    "frontend",                                   # прямо здесь
    "./frontend",                                 # относительный путь
    "/opt/render/project/src/frontend",           # стандартный путь на Render
    os.path.join(current_dir, "frontend"),        # полный путь от текущей
    os.path.join(os.path.dirname(__file__), "frontend"),  # где лежит backend.py
]

frontend_path = None
for path in possible_paths:
    if os.path.exists(path) and os.path.isdir(path):
        frontend_path = path
        print(f"✅ НАЙДЕНО: {path}")
        # Показываем содержимое
        try:
            files = os.listdir(frontend_path)
            print(f"   Содержимое: {files}")
            if 'index.html' in files:
                print("   ✅ index.html есть")
            if 'assets' in files:
                print("   ✅ папка assets есть")
        except:
            pass
        break

if not frontend_path:
    print("❌ Папка frontend НЕ НАЙДЕНА!")
    print("Ищем во всей структуре...")
    # Рекурсивный поиск (на всякий случай)
    for root, dirs, files in os.walk(current_dir):
        if 'frontend' in dirs:
            frontend_path = os.path.join(root, 'frontend')
            print(f"✅ Нашли глубоко: {frontend_path}")
            break

if frontend_path:
    # Монтируем assets
    assets_path = os.path.join(frontend_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
        print("✅ Assets примонтированы")
    
    # Для остальных файлов (vite.svg и т.д.)
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
else:
    print("❌ КРИТИЧНО: фронтенд не найден, сайт работать не будет!")

print("=" * 50)
# ========== КОНЕЦ ПОИСКА ==========

# Разрешаем React-приложению стучаться к нам (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # В продакшене лучше указать конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceRequest(BaseModel):
    amount: float
    description: str

@app.post("/create-invoice")
async def create_invoice(req: InvoiceRequest):
    try:
        invoice = await cryptopay.create_invoice(
            asset='USDT', # Или TON, BTC, RUB (если поддерживается)
            amount=req.amount,
            description=req.description,
            # paid_btn_name='callback',
            # paid_btn_url='https://t.me/YourBot' 
        )
        return {
            "invoice_id": invoice.invoice_id,
            "pay_url": invoice.bot_invoice_url, # Ссылка на оплату
            "amount": invoice.amount
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/check-invoice/{invoice_id}")
async def check_invoice(invoice_id: int):
    try:
        invoices = await cryptopay.get_invoices(invoice_ids=invoice_id)
        if invoices:
            status = invoices[0].status
            return {"status": status, "paid": status == 'paid'}
        return {"status": "not_found", "paid": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Запуск: uvicorn backend:app --reload --port 8000
