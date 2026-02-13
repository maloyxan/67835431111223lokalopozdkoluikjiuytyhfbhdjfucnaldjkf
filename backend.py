import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from aiocryptopay import AioCryptoPay, Networks
from pydantic import BaseModel

# --- НАСТРОЙКИ ---
CRYPTO_BOT_TOKEN = "488878:AAEYsdgmETPsCvrqpkkEDxhkGkLFmT3Ep0w"
# Важно: для реальных денег MAIN_NET, для тестов TEST_NET
NETWORK = Networks.MAIN_NET 

app = FastAPI()
cryptopay = AioCryptoPay(token=CRYPTO_BOT_TOKEN, network=NETWORK)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceRequest(BaseModel):
    amount: float
    description: str

# --- API МЕТОДЫ ---

@app.post("/create-invoice")
async def create_invoice(req: InvoiceRequest):
    try:
        invoice = await cryptopay.create_invoice(
            asset='USDT',
            amount=req.amount,
            description=req.description,
        )
        return {
            "invoice_id": invoice.invoice_id,
            "pay_url": invoice.bot_invoice_url,
            "amount": invoice.amount
        }
    except Exception as e:
        print(f"Error creating invoice: {e}")
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

# --- ЛОГИКА РАЗДАЧИ ФРОНТЕНДА (REACT) ---

# Определяем абсолютные пути, чтобы Render точно нашел файлы
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
ASSETS_DIR = os.path.join(FRONTEND_DIR, "assets")

if os.path.exists(FRONTEND_DIR) and os.path.exists(ASSETS_DIR):
    print(f"✅ Фронтенд найден: {FRONTEND_DIR}")
    
    # 1. Раздаем папку assets (JS и CSS)
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    # 2. Главная страница (Корень сайта)
    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    # 3. SPA Catch-All (Ловушка для React Router)
    # Если пользователь обновит страницу на /profile или /catalog, 
    # сервер вернет index.html, а React сам разберется, что показать.
    @app.exception_handler(404)
    async def spa_fallback(request: Request, exc):
        # Если запрос идет к API, возвращаем реальную 404 (JSON)
        if request.url.path.startswith("/api") or request.url.path.startswith("/create-invoice") or request.url.path.startswith("/check-invoice"):
             return JSONResponse(status_code=404, content={"detail": "API method not found"})
        
        # Для всего остального возвращаем React (index.html)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

else:
    print("❌ ПАПКА FRONTEND НЕ НАЙДЕНА! Проверьте структуру файлов.")
    @app.get("/")
    def fallback():
        return "Backend is running, but frontend files are missing."
