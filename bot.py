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
    UsernameNotOccupiedError
)

REACTION_EMOJIS = [
    '🎉', '😍', '❤️', '🔥',
    '🍾', '🗿', '👍', '👀', '🏆'
]

ACCOUNTS = [
    {"session": "t1.session", "api_id": 25205178, "api_hash": "9b363da33d28d0e136cc4e4a140eaaef"},
    {"session": "t2.session", "api_id": 24403499, "api_hash": "7f58376338498165c2c712300a3fa9b9"},
    {"session": "t3.session", "api_id": 25205178, "api_hash": "9b363da33d28d0e136cc4e4a140eaaef"},
    {"session": "t4.session", "api_id": 24403499, "api_hash": "7f58376338498165c2c712300a3fa9b9"},
    {"session": "t5.session", "api_id": 25205178, "api_hash": "9b363da33d28d0e136cc4e4a140eaaef"},
{"session": "t6.session", "api_id": 5269790, "api_hash": "672798adfbaba6d3a39bd655e781414a"},
    {"session": "t7.session", "api_id": 5269790, "api_hash": "672798adfbaba6d3a39bd655e781414a"},
    {"session": "t8.session", "api_id": 29361283, "api_hash": "64320b22d955e413c2d86e2a6d15ab31"},
  {"session": "t9.session", "api_id": 24575253, "api_hash": "e0b2960a618c89ce6eda997ff8976382"},

{"session": "t10.session", "api_id": 24403499, "api_hash": "7f58376338498165c2c712300a3fa9b9"},
 {"session": "t11.session", "api_id": 25205178, "api_hash": "9b363da33d28d0e136cc4e4a140eaaef"},
    {"session": "t12.session", "api_id": 24403499, "api_hash": "7f58376338498165c2c712300a3fa9b9"},
    {"session": "t13.session", "api_id": 25205178, "api_hash": "9b363da33d28d0e136cc4e4a140eaaef"},
    {"session": "t14.session", "api_id": 24403499, "api_hash": "7f58376338498165c2c712300a3fa9b9"},
    {"session": "t15.session", "api_id": 25205178, "api_hash": "9b363da33d28d0e136cc4e4a140eaaef"},
{"session": "t16.session", "api_id": 5269790, "api_hash": "672798adfbaba6d3a39bd655e781414a"},
    {"session": "t17.session", "api_id": 5269790, "api_hash": "672798adfbaba6d3a39bd655e781414a"},
    {"session": "t18.session", "api_id": 29361283, "api_hash": "64320b22d955e413c2d86e2a6d15ab31"},
  {"session": "t19.session", "api_id": 24575253, "api_hash": "e0b2960a618c89ce6eda997ff8976382"},
 {"session": "t20.session", "api_id": 26112879, "api_hash": "75583b9537ab1e1016c96e79ff822142"},
    {"session": "t21.session", "api_id": 22747517, "api_hash": "f2f8c7759124a4db306c8bad63ffe576"},
    {"session": "t22.session", "api_id": 26206909, "api_hash": "d61f271776edae5a1261edf4d3fb775f"},
    {"session": "t23.session", "api_id": 26112879, "api_hash": "75583b9537ab1e1016c96e79ff822142"},
    {"session": "t24.session", "api_id": 24820626, "api_hash": "3659d694699b512548bba42e3017e7a5"},
    {"session": "t25.session", "api_id": 22747517, "api_hash": "f2f8c7759124a4db306c8bad63ffe576"},

]
ADMIN_IDS = [7175947484]

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_dummy_server():
    server = HTTPServer(("0.0.0.0", 8000), HealthCheckHandler)
    print("🩺 Health check server running on port 8000")
    server.serve_forever()

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

async def create_client(session_file, api_id, api_hash):
    client = TelegramClient(session_file, api_id, api_hash)
    message_queue = asyncio.Queue()


    async def react_to_message(event):
        try:
            # Ignore messages older than 5 mins
            if (event.message.date.replace(tzinfo=None) - datetime.utcnow()).total_seconds() < -300:
                return

            await asyncio.sleep(random.randint(2, 60))
            peer = await event.get_input_chat()
            emoji = random.choice(REACTION_EMOJIS)
            await client(SendReactionRequest(
                peer=peer,
                msg_id=event.message.id,
                reaction=[ReactionEmoji(emoticon=emoji)]
            ))
            if isinstance(event.chat, Channel):
                try:
                    await client(GetMessagesViewsRequest(
                        peer=peer,
                        id=[event.message.id],
                        increment=True
                    ))
                    print(f"👁️ Viewed and ⚡ Reacted with {emoji} in channel: {event.chat_id}")
                except Exception as ve:
                    print(f"⚠️ View increase failed: {ve}")
            else:
                print(f"⚡ Reacted with {emoji} in chat: {event.chat_id}")
        except Exception as e:
            print(f"💥 Error while reacting: {e}")

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
        await client.send_message('me', f"✅ Restarted successfully as {me.first_name} (ID: {me.id})")
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
    print("🤖 BLAST MODE ACTIVATED! Reacting instantly to all messages...")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(main())
