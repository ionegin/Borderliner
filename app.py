print("TEST RUN MY APP")

import os
import asyncio
from aiohttp import web
from bot import bot, dp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN

scheduler = AsyncIOScheduler()

async def health_check(request):
    return web.Response(text="Borderliner Bot is running!", status=200)

async def debug_info(request):
    debug_data = {
        "bot_token_exists": bool(BOT_TOKEN),
        "bot_token_length": len(BOT_TOKEN) if BOT_TOKEN else 0,
        "bot_token_prefix": BOT_TOKEN[:10] + "..." if BOT_TOKEN and len(BOT_TOKEN) > 10 else "INVALID"
    }
    return web.json_response(debug_data)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_get("/debug", debug_info)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 7860)
    await site.start()
    print("🌐 Health check server started on port 7860")

async def main():
    print("🚀 APP3.PY MAIN FUNCTION STARTED")
    print("Starting Borderliner Bot...")
    print(f"🔧 Bot token exists: {bool(BOT_TOKEN)}")
    
    if BOT_TOKEN:
        print("🔄 Testing Telegram API connection...")
        try:
            me = await bot.get_me()
            print(f"✅ Bot connected: @{me.username}")
            
            if not scheduler.running:
                scheduler.start()
            
            print("🤖 Setting bot commands...")
            from aiogram.types import BotCommand
            await bot.set_my_commands([
                BotCommand(command="start", description="Главное меню"),
                BotCommand(command="daily", description="Пройти опрос")
            ])
            
            print("🤖 Starting bot polling...")
            await dp.start_polling(bot, handle_signals=False)
        except Exception as e:
            print(f"❌ Cannot connect to Telegram API: {e}")
            print("🔄 Running in demo mode...")
            
            if not scheduler.running:
                scheduler.start()
            
            print("📊 Bot is running in demo mode.")
            while True:
                await asyncio.sleep(60)
    else:
        print("❌ TELEGRAM_TOKEN not found!")

print("🔥 AUTO-STARTING main() via asyncio.run()...")
asyncio.run(main())
