import os
import asyncio
from bot import bot, dp
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def main():
    print("Starting bot in polling mode for Hugging Face Spaces...")
    
    if not scheduler.running:
        scheduler.start()
    
    # Запускаем бота в режиме polling для HF Spaces
    await dp.start_polling(bot, handle_signals=False)

if __name__ == "__main__":
    asyncio.run(main())
