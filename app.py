import os
import asyncio
from aiohttp import web
from bot import bot, dp
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def health_check(request):
    """Health check endpoint для Hugging Face"""
    return web.Response(text="Borderliner Bot is running!", status=200)

async def main():
    print("Starting Borderliner Bot for Hugging Face Spaces...")
    
    # Создаем веб-сервер для health check
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    # Запускаем веб-сервер в фоне
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 7860)
    await site.start()
    print("🌐 Health check server started on port 7860")
    
    # Проверяем доступность Telegram API
    try:
        # Пробуем получить информацию о боте
        me = await bot.get_me()
        print(f"✅ Bot connected: @{me.username}")
        
        if not scheduler.running:
            scheduler.start()
        
        # Запускаем бота в режиме polling
        await dp.start_polling(bot, handle_signals=False)
        
    except Exception as e:
        print(f"❌ Cannot connect to Telegram API: {e}")
        print("🔄 Running in demo mode...")
        
        # Демонстрационный режим
        if not scheduler.running:
            scheduler.start()
            
        print("📊 Bot is running in demo mode.")
        print("🔧 To enable full functionality, ensure Telegram API access is available.")
        print("⏳ Keeping application alive...")
        
        # Бесконечный цикл для поддержания работы приложения
        while True:
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
