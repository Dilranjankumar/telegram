from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import httpx
import json
import os
from datetime import datetime

# Environment variables se lenge (secure)
TOKEN = os.getenv("TELEGRAM_TOKEN")
GROK_API_KEY = os.getenv("GROK_API_KEY")

MEMORY_FILE = "memory.json"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Bhai mai tera personal AI assistant hu!\n\n"
        "Kuch bhi puch, kuch bhi bol - main yaad rakhunga sab.\n"
        "Hindi, English, Hinglish - sab chalega! 😎"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    message = update.message.text
    
    # Typing indicator dikhao
    await update.message.chat.send_action("typing")

    # Memory load
    memory = load_memory(user_id)
    
    # Context bana
    context_messages = [
        {"role": "system", "content": f"""
Tu {user_name} ka personal AI assistant hai naam hai Dil Ranjan.
Tu friendly, helpful aur thoda funny hai.
Tu Hinglish me naturally baat karta hai.
Tu user ki history yaad rakhta hai aur personalized help deta hai.
Aaj ki date: {datetime.now().strftime('%d %B %Y, %A')}

User ke baare me jo tu jaanta hai:
{memory.get('personal_info', 'Abhi zyada pata nahi')}
"""},
        *memory.get('history', [])[-10:],
        {"role": "user", "content": message}
    ]

    try:
        # Grok API call (best option abhi)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-beta",  # grok-3 abhi limited hai, beta use karo
                    "messages": context_messages,
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                timeout=30
            )

        if response.status_code == 200:
            reply = response.json()['choices'][0]['message']['content']
            
            # Memory update
            memory.setdefault('history', []).append({"role": "user", "content": message})
            memory.setdefault('history', []).append({"role": "assistant", "content": reply})
            
            # Last 30 hi rakho
            if len(memory['history']) > 30:
                memory['history'] = memory['history'][-30:]
            
            save_memory(user_id, memory)
            
            await update.message.reply_text(reply)
        else:
            await update.message.reply_text(
                f"Bhai kuch gadbad ho gayi 😅\n"
                f"Error: {response.status_code}\n"
                f"Thodi der me try kar!"
            )
    except Exception as e:
        await update.message.reply_text(
            f"Oops! Server pe load zyada hai 😓\n"
            f"1-2 second me dobara try kar"
        )
        print(f"Error: {e}")

def load_memory(user_id):
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(str(user_id), {"history": [], "personal_info": ""})
    except:
        pass
    return {"history": [], "personal_info": ""}

def save_memory(user_id, memory):
    try:
        data = {}
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
    except:
        data = {}
    
    data[str(user_id)] = memory
    
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_memory(user_id, {"history": [], "personal_info": ""})
    await update.message.reply_text("Memory clear ho gayi bhai! Fresh start 🔄")

def main():
    if not TOKEN:
        print("❌ TELEGRAM_TOKEN environment variable set nahi hai!")
        return
    
    if not GROK_API_KEY:
        print("⚠️ GROK_API_KEY nahi hai! Free mode me chalega (limited)")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_memory))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot successfully chal raha hai!")
    print("🤖 Bot username: @dilranjan_bot")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
