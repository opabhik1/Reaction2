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

# Allowed channels list
ALLOWED_CHANNELS = [
    -1002384076132,
    -1001739880237,
    -1002482648816,
    -1002404556710,
    -1002343690606,
    -1002813557041,
-1002351702866,
-1002464855998,
-1002526136224,
-1002784634586,
    -1001954466164,
    -1002417488873,
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
            # Check if message is from an allowed channel
            chat_id = event.chat_id
            if chat_id not in ALLOWED_CHANNELS:
                print(f"⚠️ Ignoring message from non-allowed channel: {chat_id}")
                return

            # Ignore messages older than 5 mins
            if (event.message.date.replace(tzinfo=None) - datetime.utcnow()).total_seconds() < -300:
                return

            await asyncio.sleep(random.randint(1, 30))
            peer = await event.get_input_chat()
            emoji = random.choice(REACTION_EMOJIS)
            
            # Send reaction
            await client(SendReactionRequest(
                peer=peer,
                msg_id=event.message.id,
                reaction=[ReactionEmoji(emoticon=emoji)]
            ))
            
            # Increase views if it's a channel
            if isinstance(event.chat, Channel):
                try:
                    await client(GetMessagesViewsRequest(
                        peer=peer,
                        id=[event.message.id],
                        increment=True
                    ))
                    print(f"👁️ Viewed and ⚡ Reacted with {emoji} in allowed channel: {event.chat_id}")
                except Exception as ve:
                    print(f"⚠️ View increase failed: {ve}")
            else:
                print(f"⚡ Reacted with {emoji} in allowed chat: {event.chat_id}")
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
    print("🤖 BLAST MODE ACTIVATED! Reacting to messages in allowed channels only...")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(main())
