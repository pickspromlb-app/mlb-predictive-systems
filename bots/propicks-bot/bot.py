import os, httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
TOKEN = os.getenv('PROPICKS_TELEGRAM_BOT_TOKEN')
API_URL = os.getenv('API_URL') or os.getenv('NEXT_PUBLIC_API_URL') or 'http://localhost:8000'
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('ProPicksMLB activo. Usa /today.')
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with httpx.AsyncClient(timeout=20) as client:
        data = (await client.get(API_URL.rstrip() + '/propicks/edges/today')).json()
    rows = data.get('rows', [])[:10]
    text = ['ProPicksMLB — edges de hoy']
    for r in rows:
        text.append(f"{r.get('team','')} vs {r.get('opponent','')} | {r.get('projected_label')} | score {r.get('score')}")
    await update.message.reply_text('\n'.join(text) if rows else 'Sin datos todavía.')
def main():
    if not TOKEN: raise RuntimeError('PROPICKS_TELEGRAM_BOT_TOKEN missing')
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start)); app.add_handler(CommandHandler('today', today)); app.run_polling()
if __name__ == '__main__': main()
