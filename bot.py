import random
import asyncio
import threading
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from telethon import TelegramClient, events
from telethon.tl.functions.messages import (
    SendReactionRequest,
    GetMessagesViewsRequest,
    ImportChatInviteRequest
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import ReactionEmoji, Channel
from telethon.errors import (
    UserAlreadyParticipantError,
    InviteHashExpiredError,
    InviteRequestSentError,
    ChannelPrivateError,
    UsernameNotOccupiedError,
    FloodWaitError
)
from pymongo import MongoClient
from datetime import datetime, timedelta

# MongoDB Configuration
MONGO_URI = "mongodb+srv://opabhik1:opabhik1@cluster0.8t59c.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "telegram_bot"
COLLECTION_NAME = "reaction_tracker"

# Telegram Configuration
ALLOWED_CHANNELS = [
    -1002384076132,
    -1002351702866,
    -1002277213847,
    -1002089720900,
    -1002681191277,
    -1002151078203,
    -1002648138630,
]

REACTION_EMOJIS = [
    '🎉', '😍', '❤️', '🔥',
    '🍾', '👍', '🏆'
]

ACCOUNTS = [
    {"session": "t26.session", "api_id": 24364568, "api_hash": "49549ab1ed8872ebf945c9be1ed9cf6d"},
    {"session": "t27.session", "api_id": 27444429, "api_hash": "f055109f97ecac42e24017d2b5810f33"},
    {"session": "t28.session", "api_id": 27731245, "api_hash": "cad2f72d1c0d1b6e90ec90d339bda5e6"},
    {"session": "t29.session", "api_id": 3116753,  "api_hash": "d202ee3096c95594933c198368f1822f"},
    {"session": "t30.session", "api_id": 22324699, "api_hash": "65fdfbab09e238d65bc84b66d15f5a1d"},
    {"session": "t31.session", "api_id": 27709064, "api_hash": "20d611e4bae044da8b796f494d680f26"},
    {"session": "t32.session", "api_id": 3366952,  "api_hash": "6987311f94c86e0e6cdf52ca5c924f1a"},
    {"session": "t33.session", "api_id": 29356922, "api_hash": "dd1bbca313b4cc59e1f12be10068e0c6"},
    {"session": "t34.session", "api_id": 28954312, "api_hash": "5779767c588d4e43dad89ff99b87109d"},
    {"session": "t35.session", "api_id": 3504778,  "api_hash": "db622c4b3f354d6474597fe194ce7a91"},
    {"session": "t36.session", "api_id": 22294480, "api_hash": "d673762d798c56948372abbeb32843d3"},
    {"session": "t37.session", "api_id": 4565506,  "api_hash": "2c25ee573527aa2f7f43fa1a32d2f074"},
    {"session": "t38.session", "api_id": 20158764, "api_hash": "66ba8a8baee954716c15d0991f0fedf1"},
    {"session": "t39.session", "api_id": 3195551,  "api_hash": "340e245fcca681d5696c6bb253cf0dcd"},
    {"session": "t40.session", "api_id": 24242797, "api_hash": "39c5cf71d815d5ec0b07f3291671b863"},
    {"session": "t41.session", "api_id": 3833563,  "api_hash": "6fc316958ff24ccdc0006ce455daa0c6"},
    {"session": "t42.session", "api_id": 24364568, "api_hash": "49549ab1ed8872ebf945c9be1ed9cf6d"},
    {"session": "t43.session", "api_id": 27709064, "api_hash": "20d611e4bae044da8b796f494d680f26"},
    {"session": "t44.session", "api_id": 4565506,  "api_hash": "2c25ee573527aa2f7f43fa1a32d2f074"},
    {"session": "t45.session", "api_id": 27444429, "api_hash": "f055109f97ecac42e24017d2b5810f33"},
    {"session": "t46.session", "api_id": 24364568, "api_hash": "49549ab1ed8872ebf945c9be1ed9cf6d"},
    {"session": "t47.session", "api_id": 22324699, "api_hash": "65fdfbab09e238d65bc84b66d15f5a1d"},
    {"session": "t48.session", "api_id": 22294480, "api_hash": "d673762d798c56948372abbeb32843d3"},
    {"session": "t49.session", "api_id": 28954312, "api_hash": "5779767c588d4e43dad89ff99b87109d"},
    {"session": "t50.session", "api_id": 27709064, "api_hash": "20d611e4bae044da8b796f494d680f26"}
]
ADMIN_IDS = [7175947484]

clients = []

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_dummy_server():
    server = HTTPServer(("0.0.0.0", 8000), HealthCheckHandler)
    print("🩺 Health check server running on port 8000")
    server.serve_forever()

# MongoDB Functions
def get_mongo_collection():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]

async def update_reaction_tracker(chat_id, msg_id, session_name):
    collection = get_mongo_collection()
    key = f"{chat_id}_{msg_id}"
    
    update_result = collection.update_one(
        {"_id": key},
        {
            "$setOnInsert": {
                "chat_id": chat_id,
                "msg_id": msg_id,
                "timestamp": datetime.utcnow()
            },
            "$addToSet": {"sessions": session_name}
        },
        upsert=True
    )
    return update_result.modified_count or update_result.upserted_id

async def get_missing_sessions(chat_id, msg_id):
    collection = get_mongo_collection()
    key = f"{chat_id}_{msg_id}"
    
    record = collection.find_one({"_id": key})
    if not record:
        return []
    
    active_sessions = [c.session.filename.replace('.session', '') for c in clients]
    return list(set(active_sessions) - set(record.get("sessions", [])))

async def join_channel_from_link(client, link):
    try:
        print(f"Joining link: {link}")
        if 't.me/joinchat/' in link or re.search(r'https://t\.me/\+[a-zA-Z0-9_-]+', link):
            hash_part = link.split('/')[-1].replace('+', '')
            await client(ImportChatInviteRequest(hash_part))
        elif re.match(r'(https://)?t\.me/[\w\d_]+', link):
            username = link.split('/')[-1]
            await client(JoinChannelRequest(username))
        else:
            return False, "Invalid link format"
        return True, None
    except UserAlreadyParticipantError:
        return True, "Already joined"
    except (InviteHashExpiredError, InviteRequestSentError, ChannelPrivateError, UsernameNotOccupiedError) as e:
        return False, f"❌ Invite error: {str(e)}"
    except Exception as e:
        return False, str(e)

async def leave_channel(client, channel_id):
    try:
        channel_id = int(channel_id)
        entity = await client.get_entity(channel_id)
        await client.delete_dialog(entity)
        return True, None
    except ValueError:
        return False, "Invalid channel ID format"
    except Exception as e:
        return False, str(e)

async def safe_send_reaction(client, peer, msg_id, emoji):
    try:
        await client(SendReactionRequest(
            peer=peer,
            msg_id=msg_id,
            reaction=[ReactionEmoji(emoticon=emoji)]
        ))
        return True
    except FloodWaitError as e:
        print(f"⏳ Flood wait for {e.seconds} seconds")
        await asyncio.sleep(e.seconds + 5)
        return await safe_send_reaction(client, peer, msg_id, emoji)
    except Exception as e:
        print(f"💥 Reaction failed: {e}")
        return False

async def check_missing_reactions():
    while True:
        try:
            collection = get_mongo_collection()
            time_threshold = datetime.utcnow() - timedelta(hours=24)
            
            records = collection.find({
                "timestamp": {"$gte": time_threshold}
            })
            
            for record in records:
                missing_sessions = await get_missing_sessions(record["chat_id"], record["msg_id"])
                
                if missing_sessions:
                    print(f"🔍 Found {len(missing_sessions)} missing reactions for {record['_id']}")
                    
                    for session_name in missing_sessions:
                        client = next((c for c in clients 
                                    if c.session.filename.replace('.session', '') == session_name), None)
                        
                        if client:
                            try:
                                peer = await client.get_input_entity(record["chat_id"])
                                emoji = random.choice(REACTION_EMOJIS)
                                
                                success = await safe_send_reaction(
                                    client, peer, record["msg_id"], emoji
                                )
                                
                                if success:
                                    await update_reaction_tracker(
                                        record["chat_id"], 
                                        record["msg_id"], 
                                        session_name
                                    )
                                    print(f"➕ Added missing reaction from {session_name}")
                                
                                await asyncio.sleep(random.randint(5, 15))
                                
                            except Exception as e:
                                print(f"❌ Failed to add missing reaction from {session_name}: {e}")
            
            await asyncio.sleep(1800)  # Check every 30 minutes
            
        except Exception as e:
            print(f"❌ Error in missing reaction checker: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retrying after error

async def react_to_message(event):
    try:
        chat_id = event.chat_id
        if chat_id not in ALLOWED_CHANNELS:
            return

        msg_id = event.message.id
        session_name = client.session.filename.replace('.session', '')
        
        missing_sessions = await get_missing_sessions(chat_id, msg_id)
        if session_name not in missing_sessions:
            return
        
        await asyncio.sleep(random.randint(1, 30))
        
        peer = await event.get_input_chat()
        emoji = random.choice(REACTION_EMOJIS)
        
        success = await safe_send_reaction(client, peer, msg_id, emoji)
        
        if success:
            await update_reaction_tracker(chat_id, msg_id, session_name)
            print(f"✅ {session_name} reacted to {chat_id}/{msg_id}")
            
            if isinstance(event.chat, Channel):
                try:
                    await client(GetMessagesViewsRequest(
                        peer=peer,
                        id=[msg_id],
                        increment=True
                    ))
                    print(f"👁️ Viewed message {msg_id}")
                except Exception as ve:
                    print(f"⚠️ View increase failed: {ve}")
                    
    except Exception as e:
        print(f"❌ Reaction failed for {session_name}: {e}")

async def create_client(session_file, api_id, api_hash):
    client = TelegramClient(session_file, api_id, api_hash)
    message_queue = asyncio.Queue()

    async def worker():
        while True:
            event = await message_queue.get()
            await react_to_message(event)
            message_queue.task_done()

    for _ in range(5):
        asyncio.create_task(worker())

    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        await message_queue.put(event)

    @client.on(events.NewMessage(pattern=r'^/join (.+?)(?:\s+([\w\s,]+))?$'))
    async def join_handler(event):
        sender = await event.get_sender()
        if sender.id not in ADMIN_IDS:
            return

        link = event.pattern_match.group(1).strip()
        sessions_input = event.pattern_match.group(2)
        
        target_clients = clients
        if sessions_input:
            session_names = [s.strip() for s in sessions_input.split(',')]
            target_clients = [
                c for c in clients 
                if any(c.session.filename.replace('.session', '') in name for name in session_names)
            ]
            if not target_clients:
                await event.reply("❌ No matching sessions found!")
                return

        msg = await event.reply(f"⏳ Processing join request for {len(target_clients)} accounts...")

        joined = 0
        failed = 0
        details = []

        for c in target_clients:
            try:
                delay = random.randint(1, 120)
                print(f"⏱️ Waiting {delay}s before joining with {await c.get_me()}")
                await asyncio.sleep(delay)

                success, err = await join_channel_from_link(c, link)
                if success:
                    joined += 1
                    details.append(f"✅ {c.session.filename}: Success")
                else:
                    failed += 1
                    details.append(f"❌ {c.session.filename}: {err}")
                    print(f"{await c.get_me()}: failed - {err}")

                await msg.edit(
                    f"⏳ Joining...\n"
                    f"✅ Joined: {joined}\n"
                    f"❌ Failed: {failed}\n\n"
                    f"Last update: {c.session.filename}"
                )
            except Exception as e:
                failed += 1
                details.append(f"❌ {c.session.filename}: Error - {str(e)}")
                await msg.edit(
                    f"⏳ Joining...\n"
                    f"✅ Joined: {joined}\n"
                    f"❌ Failed: {failed}\n\n"
                    f"Last error: {str(e)}"
                )

        report = (
            f"✅ Join process completed!\n\n"
            f"📊 Stats:\n"
            f"✅ Joined: {joined}\n"
            f"❌ Failed: {failed}\n\n"
            f"🔍 Details:\n"
        )
        detail_chunks = [details[i:i+10] for i in range(0, len(details), 10)]
        
        await msg.edit(report + "\n".join(detail_chunks[0]))
        for chunk in detail_chunks[1:]:
            await event.reply("\n".join(chunk))

    @client.on(events.NewMessage(pattern=r'^/leave (-?\d+)'))
    async def leave_handler(event):
        sender = await event.get_sender()
        if sender.id not in ADMIN_IDS:
            return
        channel_id = event.pattern_match.group(1).strip()
        msg = await event.reply("⏳ Processing leave request...")
        left = 0
        failed = 0
        for c in clients:
            try:
                await asyncio.sleep(random.randint(1, 10))
                success, err = await leave_channel(c, channel_id)
                if success:
                    left += 1
                else:
                    failed += 1
                await msg.edit(f"⏳ Leaving...\n✅ Left: {left}\n❌ Failed: {failed}")
            except Exception as e:
                failed += 1
                await msg.edit(f"⏳ Leaving...\n✅ Left: {left}\n❌ Failed: {failed} (Error: {e})")
        await msg.edit(f"✅ Leave process completed!\n\n✅ Left: {left}\n❌ Failed: {failed}")

    return client

async def start_client_and_run(acc):
    try:
        client = await create_client(acc["session"], acc["api_id"], acc["api_hash"])
        await client.start()
        me = await client.get_me()
        await client.send_message('me', f"✅ Restarted successfully as {me.first_name}")
        print(f"🚀 {acc['session']} logged in and ready!")
        return client
    except Exception as e:
        print(f"❌ Failed to login with {acc['session']}: {e}")
        return None

async def main():
    global clients
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    tasks = [asyncio.create_task(start_client_and_run(acc)) for acc in ACCOUNTS]
    results = await asyncio.gather(*tasks)
    clients = [client for client in results if client is not None]
    
    if not clients:
        print("⚠️ No clients were successfully logged in. Exiting.")
        return
    
    asyncio.create_task(check_missing_reactions())
    
    print("🤖 BOT STARTED WITH MONGODB TRACKING!")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == "__main__":
    asyncio.run(main())
