import os
import asyncio
from aiohttp import web
from bot import bot, dp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN

scheduler = AsyncIOScheduler()

async def health_check(request):
    """Health check endpoint для Hugging Face"""
    return web.Response(text="Borderliner Bot is running!", status=200)

async def debug_info(request):
    """Debug endpoint для проверки конфигурации"""
    debug_data = {
        "bot_token_exists": bool(BOT_TOKEN),
        "bot_token_length": len(BOT_TOKEN) if BOT_TOKEN else 0,
        "bot_token_prefix": BOT_TOKEN[:10] + "..." if BOT_TOKEN and len(BOT_TOKEN) > 10 else "INVALID"
    }
    return web.json_response(debug_data)

async def start_web_server():
    """Запуск веб-сервера для health check"""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_get("/debug", debug_info)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 7860)
    await site.start()
    print("🌐 Health check server started on port 7860")
    print("🔍 Debug info available at: /debug")

async def main():
    print("Starting Borderliner Bot for Hugging Face Spaces...")
    print(f"🔧 Bot token exists: {bool(BOT_TOKEN)}")
    print(f"🔧 Bot token length: {len(BOT_TOKEN) if BOT_TOKEN else 0}")
    
    if BOT_TOKEN:
        print(f"🔧 Bot token prefix: {BOT_TOKEN[:10]}...")
        # Проверяем формат токена (должен начинаться с цифр)
        if not BOT_TOKEN.isdigit():
            print("⚠️ WARNING: Bot token should start with numbers!")
    else:
        print("❌ TELEGRAM_TOKEN not found in environment variables!")
        return
    
    # Запускаем веб-сервер параллельно
    print("🌐 Starting web server...")
    server_task = asyncio.create_task(start_web_server())
    
    # Проверяем доступность Telegram API
    try:
        print("🔄 Testing Telegram API connection...")
        # Пробуем получить информацию о боте
        me = await bot.get_me()
        print(f"✅ Bot connected: @{me.username}")
        print(f"✅ Bot ID: {me.id}")
        
        if not scheduler.running:
            scheduler.start()
        
        print("🤖 Starting bot polling...")
        # Запускаем бота в режиме polling
        await dp.start_polling(bot, handle_signals=False)
        
    except Exception as e:
        print(f"❌ Cannot connect to Telegram API: {e}")
        print("🔄 Running in demo mode...")
        
        # Демонстрационный режим
        if not scheduler.running:
            scheduler.start()
            
        print("📊 Bot is running in demo mode.")
        print("🔧 To enable full functionality:")
        print("   1. Ensure TELEGRAM_TOKEN is set in HF Space secrets")
        print("   2. Check if Telegram API is accessible from HF environment")
        print("   3. Verify bot token is valid")
        print("⏳ Keeping application alive...")
        
        # Бесконечный цикл для поддержания работы приложения
        while True:
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
