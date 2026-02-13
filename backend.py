# backend.py
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
