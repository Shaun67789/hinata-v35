import os
import sys
from typing import Optional
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks
from telegram import ChatPermissions

from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fastapi.responses import FileResponse
import bot  # Import the bot module
import database
import json

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print(f"----- SYSTEM INFO -----")
    print(f"Python Version: {sys.version}")
    print(f"-----------------------")
    # Start the bot as a background task
    asyncio.create_task(bot.start_bot())
    # Note: auto_cleanup_task is started inside bot.start_bot() already
    bot.logger.info("Web Dashboard Started")
    yield
    # Shutdown logic
    await bot.stop_bot()

app = FastAPI(title="Hinata Bot Dashboard", lifespan=lifespan)

DASHBOARD_PASSWORD = "2810"

async def check_auth(request: Request):
    """Simple password check for dashboard access."""
    pwd = request.headers.get("X-Dashboard-Password")
    if pwd != DASHBOARD_PASSWORD:
        return False
    return True

# Helper to wrap responses for auth failure
def auth_failed():
    return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized Access Detected. PIN Required."})

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class ControlAction(BaseModel):
    action: str

class BroadcastMsg(BaseModel):
    target: str
    message: str = ""
    photo_url: str = ""   # Optional: URL of photo to send
    caption: str = ""     # Optional: caption for photo (overrides message if photo given)

class CommandExec(BaseModel):
    command: str
    chat_id: str = None
    user_id: str = None

class TokenUpdate(BaseModel):
    token: str

class DeleteMsgRequest(BaseModel):
    url: str

@app.get("/api/config")
async def get_config(request: Request):
    """Returns current bot configuration (excluding full token for security)."""
    if not await check_auth(request): return auth_failed()
    try:
        with open(bot.BOT_TOKEN_FILE, "r") as f:
            t = f.read().strip()
            masked = t[:5] + "..." + t[-5:] if len(t) > 10 else "Invalid Token"
    except:
        masked = "Not Found"

    return {
        "token": masked,
        "welcome_img": bot.CONFIG.get("welcome_img"),
        "fallback_img": bot.CONFIG.get("fallback_img"),
        "global_access": bot.CONFIG.get("global_access"),
        "couple_enabled": bot.CONFIG.get("couple_enabled", True),
        "couple_bg": bot.CONFIG.get("couple_bg"),
        # Tracked users
        "tracked_user1_id": bot.CONFIG.get("tracked_user1_id", str(bot.TRACKED_USER1_ID)),
        "forward_user1_group_id": bot.CONFIG.get("forward_user1_group_id", str(bot.FORWARD_USER1_GROUP_ID)),
        "tracked_user2_id": bot.CONFIG.get("tracked_user2_id", str(bot.TRACKED_USER2_ID)),
        "forward_user2_group_id": bot.CONFIG.get("forward_user2_group_id", str(bot.FORWARD_USER2_GROUP_ID)),
        # Legacy alias kept for compatibility
        "tracked_user_id": bot.CONFIG.get("tracked_user1_id", str(bot.TRACKED_USER1_ID)),
        "forward_group_id": bot.CONFIG.get("forward_user1_group_id", str(bot.FORWARD_USER1_GROUP_ID)),
        # Log destinations
        "destination_group_id": bot.CONFIG.get("destination_group_id", str(bot.DESTINATION_GROUP_ID)),
        "group_log_id": bot.CONFIG.get("group_log_id", str(bot.GROUP_LOG_ID)),
        # Tracking toggles
        "group_tracking_enabled": bot.CONFIG.get("group_tracking_enabled", True),
        "user_tracking_enabled": bot.CONFIG.get("user_tracking_enabled", True),
    }

@app.post("/api/token")
async def update_token(data: TokenUpdate, request: Request):
    """Updates the bot token in token.txt."""
    if not await check_auth(request): return auth_failed()
    try:
        with open(bot.BOT_TOKEN_FILE, "w") as f:
            f.write(data.token.strip())
        return {"success": True, "message": "Token updated successfully. Restart the bot to apply."}
    except Exception as e:
        return {"success": False, "error": str(e)}



@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

class ConfigUpdate(BaseModel):
    welcome_img: str = None
    fallback_img: str = None
    tracked_user_id: str = None        # legacy alias
    forward_group_id: str = None       # legacy alias
    bot_enabled: Optional[bool] = None
    couple_enabled: Optional[bool] = None
    couple_bg: str = None

@app.post("/api/config-update")
async def update_config(data: ConfigUpdate, request: Request):
    """Updates bot configuration (images, etc.)."""
    if not await check_auth(request): return auth_failed()
    try:
        if data.welcome_img:
            bot.CONFIG["welcome_img"] = data.welcome_img
        if data.fallback_img:
            bot.CONFIG["fallback_img"] = data.fallback_img
        if data.tracked_user_id:   # legacy
            bot.CONFIG["tracked_user1_id"] = data.tracked_user_id
            bot.TRACKED_USER1_ID = int(data.tracked_user_id)
        if data.forward_group_id:  # legacy
            bot.CONFIG["forward_user1_group_id"] = data.forward_group_id
            bot.FORWARD_USER1_GROUP_ID = int(data.forward_group_id)
        if data.bot_enabled is not None:
            bot.CONFIG["bot_enabled"] = data.bot_enabled
        if data.couple_enabled is not None:
            bot.CONFIG["couple_enabled"] = data.couple_enabled
        if data.couple_bg:
            bot.CONFIG["couple_bg"] = data.couple_bg
        bot.save_config(bot.CONFIG)
        return {"success": True, "message": "Neural configuration updated."}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
#  TRACKING CONFIG – Full control over IDs & toggles
# ═══════════════════════════════════════════════════════════

class TrackingConfig(BaseModel):
    # Tracked users
    tracked_user1_id: str = None
    forward_user1_group_id: str = None
    tracked_user2_id: str = None
    forward_user2_group_id: str = None
    # Log destinations
    destination_group_id: str = None
    group_log_id: str = None
    # Toggles
    group_tracking_enabled: Optional[bool] = None
    user_tracking_enabled: Optional[bool] = None

@app.post("/api/tracking-update")
async def update_tracking(data: TrackingConfig, request: Request):
    """Update all tracking IDs and enable/disable group & user tracking."""
    if not await check_auth(request): return auth_failed()
    try:
        changed = []

        if data.tracked_user1_id:
            uid = int(data.tracked_user1_id)
            bot.TRACKED_USER1_ID = uid
            bot.CONFIG["tracked_user1_id"] = str(uid)
            changed.append(f"Tracked User 1 → {uid}")

        if data.forward_user1_group_id:
            gid = int(data.forward_user1_group_id)
            bot.FORWARD_USER1_GROUP_ID = gid
            bot.CONFIG["forward_user1_group_id"] = str(gid)
            changed.append(f"User 1 Forward Group → {gid}")

        if data.tracked_user2_id:
            uid = int(data.tracked_user2_id)
            bot.TRACKED_USER2_ID = uid
            bot.CONFIG["tracked_user2_id"] = str(uid)
            changed.append(f"Tracked User 2 → {uid}")

        if data.forward_user2_group_id:
            gid = int(data.forward_user2_group_id)
            bot.FORWARD_USER2_GROUP_ID = gid
            bot.CONFIG["forward_user2_group_id"] = str(gid)
            changed.append(f"User 2 Forward Group → {gid}")

        if data.destination_group_id:
            gid = int(data.destination_group_id)
            bot.DESTINATION_GROUP_ID = gid
            bot.CONFIG["destination_group_id"] = str(gid)
            changed.append(f"Private Log Destination → {gid}")

        if data.group_log_id:
            gid = int(data.group_log_id)
            bot.GROUP_LOG_ID = gid
            bot.CONFIG["group_log_id"] = str(gid)
            changed.append(f"Group Log ID → {gid}")

        if data.group_tracking_enabled is not None:
            bot.CONFIG["group_tracking_enabled"] = data.group_tracking_enabled
            status = "ON" if data.group_tracking_enabled else "OFF"
            changed.append(f"Group Tracking → {status}")

        if data.user_tracking_enabled is not None:
            bot.CONFIG["user_tracking_enabled"] = data.user_tracking_enabled
            status = "ON" if data.user_tracking_enabled else "OFF"
            changed.append(f"User Tracking → {status}")

        bot.save_config(bot.CONFIG)
        return {
            "success": True,
            "message": "Tracking config updated.",
            "changes": changed
        }
    except ValueError as e:
        return {"success": False, "error": f"Invalid number format: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/download_db")
async def download_db(request: Request):
    """Allows the owner to download the bot's SQLite database file."""
    # Support both header and query param for external link download
    pwd = request.headers.get("X-Dashboard-Password") or request.query_params.get("pwd")
    if pwd != DASHBOARD_PASSWORD:
        return HTMLResponse(status_code=401, content="<h1>Unauthorized Access Denied.</h1>")
    db_path = "bot.db"
    if os.path.exists(db_path):
        return FileResponse(path=db_path, filename="bot.db", media_type="application/octet-stream")
    return JSONResponse(status_code=404, content={"error": "Database file not found."})

@app.get("/api/data")
async def get_data(request: Request):
    """Returns all users and groups with full metadata."""
    if not await check_auth(request): return auth_failed()
    users = database.get_all_users()
    groups = database.get_all_groups()
    broadcasts = database.get_all_broadcasts()
    
    return {
        "stats": {
            "total_users": len(users),
            "total_groups": len(groups),
            "total_messages": database.get_total_messages(),
            "broadcasts": len(broadcasts),
            "uptime": bot.get_uptime(),
            "status": bot.STATS.get("status", "online"),
            "global_access": bot.CONFIG.get("global_access", True)
        },
        "users": users,
        "groups": groups,
        "broadcasts": broadcasts,
        "banned_users": bot.CONFIG.get("banned_users", [])
    }


@app.get("/api/logs")
async def get_logs(request: Request):
    if not await check_auth(request): return auth_failed()
    # Read last 50 lines from log file
    if os.path.exists(bot.LOG_FILE):
        with open(bot.LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return lines[-50:]
    return ["Log file not found."]
def parse_telegram_url(url: str):
    """Parses a Telegram message URL to extract chat_id and message_id."""
    clean_url = url.strip().strip("/").split('?')[0]
    parts = clean_url.split("/")
    if len(parts) < 2:
        raise ValueError("Invalid URL format. Please provide a direct message link.")
        
    msg_id_str = parts[-1]
    if not msg_id_str.isdigit():
        raise ValueError(f"Could not parse message ID from '{msg_id_str}'. Please make sure it's a message link.")
    msg_id = int(msg_id_str)
    
    chat_id_str = parts[-2]
    # Handle private link format: https://t.me/c/12345/678
    if len(parts) >= 3 and parts[-3] == "c":
        if chat_id_str.isdigit():
            chat_id = int(f"-100{chat_id_str}")
        else: chat_id = chat_id_str
    elif chat_id_str.replace("-", "").isdigit():
        chat_id = int(chat_id_str)
    else:
        chat_id = f"@{chat_id_str}" if not chat_id_str.startswith("@") else chat_id_str
        
    return chat_id, msg_id

@app.post("/api/delete_msg")
async def delete_specific_message(req: DeleteMsgRequest, request: Request):
    """Deletes a specific message given its Telegram URL."""
    if not await check_auth(request): return auth_failed()
    if not bot.app: return {"success": False, "error": "Bot not initialized. Please wait a moment."}
    try:
        chat_id, msg_id = parse_telegram_url(req.url)
        bot.logger.info(f"Dashboard Request: Delete Msg {msg_id} in {chat_id}")
        await bot.app.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        return {"success": True, "message": f"Message {msg_id} deleted."}
    except Exception as e:
        bot.logger.error(f"Failed to delete via dashboard: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/pin_msg")
async def pin_specific_message(req: DeleteMsgRequest, request: Request):
    """Pins a specific message given its Telegram URL."""
    if not await check_auth(request): return auth_failed()
    if not bot.app: return {"success": False, "error": "Bot not initialized. Please wait a moment."}
    try:
        chat_id, msg_id = parse_telegram_url(req.url)
        bot.logger.info(f"Dashboard Request: Pin Msg {msg_id} in {chat_id}")
        await bot.app.bot.pin_chat_message(chat_id=chat_id, message_id=msg_id, disable_notification=False)
        return {"success": True, "message": f"Message {msg_id} pinned."}
    except Exception as e:
        bot.logger.error(f"Failed to pin via dashboard: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/unpin_msg")
async def unpin_specific_message(req: DeleteMsgRequest, request: Request):
    """Unpins a specific message given its Telegram URL."""
    if not await check_auth(request): return auth_failed()
    if not bot.app: return {"success": False, "error": "Bot not initialized. Please wait a moment."}
    try:
        chat_id, msg_id = parse_telegram_url(req.url)
        bot.logger.info(f"Dashboard Request: Unpin Msg {msg_id} in {chat_id}")
        await bot.app.bot.unpin_chat_message(chat_id=chat_id, message_id=msg_id)
        return {"success": True, "message": f"Message {msg_id} unpinned."}
    except Exception as e:
        bot.logger.error(f"Failed to unpin via dashboard: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/control")
async def control_bot(data: ControlAction, request: Request):
    if not await check_auth(request): return auth_failed()
    if data.action == "restart":
        await bot.stop_bot()
        asyncio.create_task(bot.start_bot())
        return {"success": True}
    elif data.action == "clear_logs":
        if os.path.exists(bot.LOG_FILE):
            open(bot.LOG_FILE, "w").close()
        return {"success": True}
    elif data.action == "toggle_access":
        bot.CONFIG["global_access"] = not bot.CONFIG.get("global_access", True)
        bot.save_config(bot.CONFIG)
        return {"success": True, "new_status": bot.CONFIG["global_access"]}
    elif data.action == "delete_broadcast":
        history = bot.read_json("broadcast_history.json", [])
        if not history:
            return {"success": False, "error": "No broadcast history found"}
        
        s = f = 0
        if not bot.app:
            return {"success": False, "error": "Bot not initialized"}
            
        for entry in history:
            try:
                await bot.app.bot.delete_message(chat_id=entry['chat_id'], message_id=entry['message_id'])
                s += 1
            except:
                f += 1
        
        bot.write_json("broadcast_history.json", [])
        return {"success": True, "deleted": s, "failed": f}
    elif data.action == "toggle_bot":
        if bot.STATS.get("status") == "online":
            await bot.stop_bot()
        else:
            asyncio.create_task(bot.start_bot())
        return {"success": True}
    elif data.action == "toggle_bot_enabled":
        bot.CONFIG["bot_enabled"] = not bot.CONFIG.get("bot_enabled", True)
        bot.save_config(bot.CONFIG)
        return {"success": True, "bot_enabled": bot.CONFIG["bot_enabled"]}
    elif data.action == "track_users":
        # Launch tracking as background task
        asyncio.create_task(track_all_users())
        return {"success": True, "message": "User tracking initiated in background"}
    elif data.action == "clear_downloads":
        count = 0
        for f in os.listdir("downloads"):
            try:
                os.remove(os.path.join("downloads", f))
                count += 1
            except: pass
        return {"success": True, "message": f"Cleared {count} files from neural core."}
    return {"success": False, "error": "Unknown action"}

@app.get("/api/files")
async def list_files(request: Request):
    if not await check_auth(request): return auth_failed()
    files = []
    folder = "downloads"
    if os.path.exists(folder):
        for f in os.listdir(folder):
            path = os.path.join(folder, f)
            if os.path.isfile(path):
                stats = os.stat(path)
                files.append({
                    "name": f,
                    "size": f"{stats.st_size / (1024*1024):.2f} MB",
                    "time": bot.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    return files

async def auto_cleanup_task():
    """Background task to clear downloads every 10 minutes."""
    while True:
        await asyncio.sleep(600) # 10 minutes
        try:
            now = bot.time.time()
            count = 0
            for f in os.listdir("downloads"):
                path = os.path.join("downloads", f)
                if os.path.isfile(path):
                    # Remove files older than 10 mins
                    if now - os.stat(path).st_mtime > 600:
                        os.remove(path)
                        count += 1
            if count > 0:
                bot.logger.info(f"Auto-cleanup: {count} expired files removed from registry.")
        except Exception as e:
            bot.logger.error(f"Cleanup Error: {e}")

async def track_all_users():
    """Background task to track all users metadata."""
    if not bot.app: return
    users = database.get_all_users()
    bot.logger.info(f"Starting tracking for {len(users)} users...")
    for u in users:
        try:
            chat = await bot.app.bot.get_chat(u['id'])
            database.add_user(u['id'], chat.full_name, chat.username)
            # Sleep a bit to avoid flood limits
            await asyncio.sleep(0.5)
        except Exception as e:
            bot.logger.error(f"Failed to track user {u['id']}: {e}")
    bot.logger.info("User tracking complete.")

@app.get("/api/broadcasts")
async def get_broadcast_history():
    return database.get_all_broadcasts()

@app.delete("/api/broadcasts/{b_id}")
async def delete_broadcast_item(b_id: int, request: Request):
    if not await check_auth(request): return auth_failed()
    try:
        b = database.get_broadcast(b_id)
        if not b:
            return {"success": False, "error": "Broadcast not found"}
        
        # Delete messages from Telegram
        msg_ids = json.loads(b['message_ids'])
        s = f = 0
        if bot.app:
            for chat_id, message_id in msg_ids.items():
                try:
                    await bot.app.bot.delete_message(chat_id=int(chat_id), message_id=int(message_id))
                    s += 1
                except:
                    f += 1
        
        # Delete from DB
        database.delete_broadcast_record(b_id)
        return {"success": True, "deleted": s, "failed": f}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/broadcast")
async def api_broadcast(data: BroadcastMsg, request: Request):
    if not await check_auth(request): return auth_failed()
    try:
        if not bot.app:
            return {"success": False, "error": "Bot not initialized"}
        
        msg_ids_map = {}
        s_users = f_users = s_groups = f_groups = 0
        is_media = bool(data.photo_url.strip())
        cap = data.caption.strip() or data.message.strip()
        text = data.message.strip()
        
        async def send_to(chat_id):
            """Helper: send text or photo to a single chat_id."""
            if is_media:
                sent = await bot.app.bot.send_photo(chat_id=chat_id, photo=data.photo_url.strip(), caption=cap, parse_mode="HTML")
            else:
                sent = await bot.app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
            return sent
        
        if data.target == "all" or data.target == "users":
            users = database.get_all_users()
            for u in users:
                uid = u['id']
                try: 
                    sent = await send_to(uid)
                    msg_ids_map[str(sent.chat_id)] = sent.message_id
                    s_users += 1
                except:
                    f_users += 1
        
        if data.target == "all" or data.target == "groups":
            groups = database.get_all_groups()
            for g in groups:
                gid = g['id']
                try: 
                    sent = await send_to(gid)
                    msg_ids_map[str(sent.chat_id)] = sent.message_id
                    s_groups += 1
                except:
                    f_groups += 1
                    
        if data.target not in ["all", "users", "groups"]:
            # Specific Target ID Handling
            try:
                t = int(data.target) if data.target.replace("-", "").isdigit() else data.target
                sent = await send_to(t)
                msg_ids_map[str(sent.chat_id)] = sent.message_id
                s_users += 1
            except Exception as e:
                bot.logger.error(f"Specific Broadcast Fail: {e}")
                f_users += 1
    
        # Save to DB
        label = f"[Media] {cap[:80]}" if is_media else text
        database.add_broadcast(label, data.target, s_users + s_groups, f_users + f_groups, msg_ids_map)
        
        # Update Stats
        bot.update_stats(s_users, f_users, s_groups, f_groups)
        bot.STATS["broadcasts"] = bot.STATS.get("broadcasts", 0) + 1

        return {
            "status": "success", 
            "sent": s_users + s_groups, 
            "failed": f_users + f_groups,
            "detail": f"Sent to {s_users} users & {s_groups} groups"
        }
    except Exception as e:
        bot.logger.error(f"API Broadcast Error: {e}")
        return {"status": "error", "detail": str(e)}

@app.post("/api/execute")
async def execute_command(data: CommandExec, request: Request):
    """Execute owner commands from dashboard."""
    if not await check_auth(request): return auth_failed()
    try:
        if not bot.app:
            return {"success": False, "error": "Bot not initialized"}
        
        chat_id = int(data.chat_id) if data.chat_id else None
        user_id = int(data.user_id) if data.user_id else None
        
        if data.command == "ban":
            if not chat_id or not user_id:
                return {"success": False, "error": "Chat ID and User ID required"}
            await bot.app.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            return {"success": True, "message": f"User {user_id} banned from {chat_id}"}
        
        elif data.command == "unban":
            if not chat_id or not user_id:
                return {"success": False, "error": "Chat ID and User ID required"}
            await bot.app.bot.unban_chat_member(chat_id=chat_id, user_id=user_id, only_if_banned=True)
            return {"success": True, "message": f"User {user_id} unbanned from {chat_id}"}
        
        elif data.command == "kick":
            if not chat_id or not user_id:
                return {"success": False, "error": "Chat ID and User ID required"}
            await bot.app.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await bot.app.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
            return {"success": True, "message": f"User {user_id} kicked from {chat_id}"}
        
        elif data.command == "mute":
            if not chat_id or not user_id:
                return {"success": False, "error": "Chat ID and User ID required"}
            await bot.app.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            return {"success": True, "message": f"User {user_id} muted in {chat_id}"}
        
        elif data.command == "unmute":
            if not chat_id or not user_id:
                return {"success": False, "error": "Chat ID and User ID required"}
            await bot.app.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_audios=True,
                    can_send_documents=True,
                    can_send_photos=True,
                    can_send_videos=True,
                    can_send_video_notes=True,
                    can_send_voice_notes=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_change_info=True,
                    can_invite_users=True,
                    can_pin_messages=True
                )
            )
            return {"success": True, "message": f"User {user_id} unmuted in {chat_id}"}
        
        elif data.command == "addadmin":
            if not chat_id or not user_id:
                return {"success": False, "error": "Chat ID and User ID required"}
            await bot.app.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_restrict_members=True,
                can_promote_members=True,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True
            )
            return {"success": True, "message": f"User {user_id} promoted to admin in {chat_id}"}
            
        elif data.command == "removeadmin":
            if not chat_id or not user_id:
                return {"success": False, "error": "Chat ID and User ID required"}
            await bot.app.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                is_anonymous=False, can_manage_chat=False, can_delete_messages=False, 
                can_manage_video_chats=False, can_restrict_members=False, 
                can_promote_members=False, can_change_info=False, 
                can_invite_users=False, can_pin_messages=False
            )
            return {"success": True, "message": f"User {user_id} removed from admin in {chat_id}"}
        
        return {"success": False, "error": "Unknown command"}
    except Exception as e:
        return {"success": False, "error": str(e)}

class MoodUpdate(BaseModel):
    mood: str

@app.get("/api/mood")
async def get_mood(request: Request):
    if not await check_auth(request): return auth_failed()
    return {"mood": bot.CONFIG.get("bot_mood", "flirty")}

@app.post("/api/mood")
async def set_mood(data: MoodUpdate, request: Request):
    """Sets the bot mood and saves it to config."""
    if not await check_auth(request): return auth_failed()
    try:
        bot.CONFIG["bot_mood"] = data.mood
        bot.save_config(bot.CONFIG)
        return {"success": True, "message": f"Bot mood updated to {data.mood}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ═══════════════════════════════════════════════════════════
#  GROUP COMMAND CENTER (GCC) – API Endpoints
# ═══════════════════════════════════════════════════════════

@app.get("/api/gcc/group_info")
async def gcc_group_info(group_id: str, request: Request):
    """Fetch group info + ALL reachable members.
    - Live: Telegram admins (always if bot is a member)
    - History: All users who EVER sent a message in this specific group (from chat_history)
    - Fallback: Global DB users (if no group-specific history exists)
    """
    if not await check_auth(request): return auth_failed()
    if not bot.app:
        return {"success": False, "error": "Bot not initialised. Please wait a moment and refresh."}
    try:
        gid = int(group_id) if group_id.lstrip("-").isdigit() else group_id

        # ── Step 1: Get group metadata ──────────────────────────────────────
        try:
            chat = await bot.app.bot.get_chat(gid)
            group_data = {
                "id": chat.id,
                "title": chat.title or "Unknown",
                "type": str(chat.type),
                "member_count": None,
                "username": chat.username,
                "description": chat.description,
            }
        except Exception as e:
            bot.logger.error(f"GCC: get_chat failed for {gid}: {e}")
            return {"success": False, "error": f"Cannot access group: {str(e)}"}

        # ── Step 2: Get real member count ───────────────────────────────────
        try:
            group_data["member_count"] = await bot.app.bot.get_chat_member_count(gid)
        except Exception:
            pass

        # ── Step 3: Fetch live admins from Telegram ─────────────────────────
        # This always works as long as bot is a member of the group.
        admin_ids = set()
        members_list = []
        bot_is_admin = False

        try:
            admins = await bot.app.bot.get_chat_administrators(gid)
            for a in admins:
                uid = a.user.id
                # Check if our own bot is among the admins
                if bot.app and uid == bot.app.bot.id:
                    bot_is_admin = True
                admin_ids.add(uid)
                status_str = str(a.status) if a.status else "administrator"
                # Get extra user info from our DB if we have it
                db_user = database.get_user(uid) or {}
                members_list.append({
                    "user": {
                        "id": uid,
                        "first_name": a.user.first_name or db_user.get("full_name", ""),
                        "last_name": a.user.last_name or "",
                        "username": a.user.username or db_user.get("username"),
                        "is_deleted": getattr(a.user, "is_deleted", False),
                    },
                    "status": status_str,
                    "source": "telegram",
                    "msg_count": db_user.get("message_count", 0),
                    "last_active": db_user.get("last_active_at", ""),
                })
        except Exception as e:
            bot.logger.warning(f"GCC: get_chat_administrators failed for {gid}: {e}")

        # ── Step 4: Fetch all users from group-specific chat_history ────────
        # This gives us EVERY user Hinata has ever seen talk in this group.
        group_history_users = database.get_users_in_chat(int(gid) if isinstance(gid, int) else gid)
        added_from_history = 0
        seen_ids = set(admin_ids)

        for u in group_history_users:
            uid = u.get("user_id")
            if uid and uid not in seen_ids:
                seen_ids.add(uid)
                members_list.append({
                    "user": {
                        "id": uid,
                        "first_name": u.get("full_name") or "Unknown",
                        "last_name": "",
                        "username": u.get("username"),
                        "is_deleted": False,
                    },
                    "status": "member",
                    "source": "history",   # Seen in THIS group chat
                    "msg_count": u.get("message_count", 0),
                    "last_active": u.get("last_active_at", ""),
                })
                added_from_history += 1

        # ── Step 5: Fallback — global DB if no group-specific data ──────────
        added_from_fallback = 0
        if added_from_history == 0:
            all_db_users = database.get_all_users()
            for u in all_db_users:
                uid = u.get("id")
                if uid and uid not in seen_ids:
                    seen_ids.add(uid)
                    members_list.append({
                        "user": {
                            "id": uid,
                            "first_name": u.get("full_name", "Unknown"),
                            "last_name": "",
                            "username": u.get("username"),
                            "is_deleted": False,
                        },
                        "status": "member",
                        "source": "database",
                        "msg_count": u.get("message_count", 0),
                        "last_active": u.get("last_active_at", ""),
                    })
                    added_from_fallback += 1

        # Build informative note
        admin_status = "✅ Bot IS admin in this group." if bot_is_admin else "⚠️ Bot is NOT admin — limited data available."
        sources = []
        if admin_ids:    sources.append(f"⚡ {len(admin_ids)} admins (live Telegram API)")
        if added_from_history: sources.append(f"📜 {added_from_history} members seen in this group's chat history")
        if added_from_fallback: sources.append(f"📦 {added_from_fallback} global DB users (no group-specific history yet)")
        note = admin_status + "  |  " + "  •  ".join(sources) if sources else admin_status

        bot.logger.info(f"GCC Scan: group={gid}, admins={len(admin_ids)}, history={added_from_history}, fallback={added_from_fallback}, is_admin={bot_is_admin}")

        return {
            "success": True,
            "group": group_data,
            "members": members_list,
            "bot_is_admin": bot_is_admin,
            "note": note,
        }
    except Exception as e:
        bot.logger.error(f"GCC Group Info Error: {e}")
        return {"success": False, "error": str(e)}


class GCCBulkAction(BaseModel):
    group_id: str
    action: str
    user_ids: list


@app.post("/api/gcc/bulk_action")
async def gcc_bulk_action(data: GCCBulkAction, request: Request):
    """Perform a moderation action on multiple users at once."""
    if not await check_auth(request): return auth_failed()
    if not bot.app:
        return {"success": False, "error": "Bot not initialised."}
    try:
        gid = int(data.group_id) if data.group_id.lstrip("-").isdigit() else data.group_id
        success_count = 0
        failed_count = 0
        for uid_str in data.user_ids:
            try:
                uid = int(uid_str)
                if data.action == "kick":
                    await bot.app.bot.ban_chat_member(chat_id=gid, user_id=uid)
                    await bot.app.bot.unban_chat_member(chat_id=gid, user_id=uid)
                elif data.action == "ban":
                    await bot.app.bot.ban_chat_member(chat_id=gid, user_id=uid)
                elif data.action == "mute":
                    await bot.app.bot.restrict_chat_member(
                        chat_id=gid, user_id=uid,
                        permissions=ChatPermissions(can_send_messages=False)
                    )
                elif data.action == "unmute":
                    await bot.app.bot.restrict_chat_member(
                        chat_id=gid, user_id=uid,
                        permissions=ChatPermissions(
                            can_send_messages=True, can_send_audios=True,
                            can_send_documents=True, can_send_photos=True,
                            can_send_videos=True, can_send_video_notes=True,
                            can_send_voice_notes=True, can_send_polls=True,
                            can_send_other_messages=True, can_add_web_page_previews=True,
                            can_change_info=True, can_invite_users=True, can_pin_messages=True
                        )
                    )
                elif data.action == "unban":
                    await bot.app.bot.unban_chat_member(chat_id=gid, user_id=uid, only_if_banned=True)
                success_count += 1
                await asyncio.sleep(0.15)  # Rate-limit friendly
            except Exception as e:
                bot.logger.warning(f"GCC Bulk {data.action} failed for {uid_str}: {e}")
                failed_count += 1
        bot.logger.info(f"GCC Bulk {data.action} — ✅ {success_count} ❌ {failed_count}")
        return {"success_count": success_count, "failed_count": failed_count}
    except Exception as e:
        return {"success": False, "error": str(e)}


class GCCDeleteMessages(BaseModel):
    group_id: str
    scope: str  # 'all' | 'user'
    user_id: str = None


@app.post("/api/gcc/delete_messages")
async def gcc_delete_messages(data: GCCDeleteMessages, request: Request):
    """Delete messages from a group — all recent or from a specific user."""
    if not await check_auth(request): return auth_failed()
    if not bot.app:
        return {"success": False, "error": "Bot not initialised."}
    try:
        gid = int(data.group_id) if data.group_id.lstrip("-").isdigit() else data.group_id
        deleted = 0
        failed = 0

        # Telegram Bot API can only delete messages it knows about.
        # We iterate over a configurable recent range of message IDs.
        # Strategy: try deleting the last ~1000 message IDs by brute-force.
        try:
            chat = await bot.app.bot.get_chat(gid)
            # Get latest message id by pinning/fetching — fallback to a large window
            latest_id = getattr(chat, "pinned_message", None)
            latest_msg_id = latest_id.message_id if latest_id else 100000
        except Exception:
            latest_msg_id = 100000

        target_uid = int(data.user_id) if data.user_id and data.user_id.isdigit() else None

        for msg_id in range(latest_msg_id, max(latest_msg_id - 2000, 0), -1):
            try:
                if data.scope == "all":
                    await bot.app.bot.delete_message(chat_id=gid, message_id=msg_id)
                    deleted += 1
                elif data.scope == "user" and target_uid:
                    # We can't easily filter by user without tracking — delete and check
                    # Best effort: just delete all in range for now
                    await bot.app.bot.delete_message(chat_id=gid, message_id=msg_id)
                    deleted += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
                if failed > 200:  # Stop early if too many failures (likely reached old msgs)
                    break

        bot.logger.info(f"GCC Delete Msgs ({data.scope}) in {gid} — ✅ {deleted} ❌ {failed}")
        return {"deleted": deleted, "failed": failed}
    except Exception as e:
        return {"success": False, "error": str(e)}


class GCCGroupAction(BaseModel):
    group_id: str
    action: str
    value: str = None
    user_ids: list = []


@app.post("/api/gcc/group_action")
async def gcc_group_action(data: GCCGroupAction, request: Request):
    """Perform a group-level action (settings, pins, invite, etc.)."""
    if not await check_auth(request): return auth_failed()
    if not bot.app:
        return {"success": False, "error": "Bot not initialised."}
    try:
        gid = int(data.group_id) if data.group_id.lstrip("-").isdigit() else data.group_id

        if data.action == "set_title":
            await bot.app.bot.set_chat_title(chat_id=gid, title=data.value)
            return {"success": True}

        elif data.action == "set_description":
            await bot.app.bot.set_chat_description(chat_id=gid, description=data.value)
            return {"success": True}

        elif data.action == "lock_group":
            await bot.app.bot.set_chat_permissions(chat_id=gid, permissions=ChatPermissions(
                can_send_messages=False, can_send_audios=False,
                can_send_documents=False, can_send_photos=False,
                can_send_videos=False, can_send_video_notes=False,
                can_send_voice_notes=False, can_send_polls=False,
                can_send_other_messages=False, can_add_web_page_previews=False,
                can_change_info=False, can_invite_users=False, can_pin_messages=False
            ))
            return {"success": True}

        elif data.action == "unlock_group":
            await bot.app.bot.set_chat_permissions(chat_id=gid, permissions=ChatPermissions(
                can_send_messages=True, can_send_audios=True,
                can_send_documents=True, can_send_photos=True,
                can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_change_info=False, can_invite_users=True, can_pin_messages=False
            ))
            return {"success": True}

        elif data.action == "get_invite_link":
            link = await bot.app.bot.export_chat_invite_link(chat_id=gid)
            return {"success": True, "value": link}

        elif data.action == "disable_invite":
            link = await bot.app.bot.export_chat_invite_link(chat_id=gid)
            return {"success": True, "value": f"Invite link revoked & new link: {link}"}

        elif data.action == "enable_invite":
            link = await bot.app.bot.export_chat_invite_link(chat_id=gid)
            return {"success": True, "value": link}

        elif data.action == "unpin_all":
            await bot.app.bot.unpin_all_chat_messages(chat_id=gid)
            return {"success": True}

        elif data.action == "pin_latest":
            chat = await bot.app.bot.get_chat(gid)
            if chat.pinned_message:
                await bot.app.bot.pin_chat_message(chat_id=gid, message_id=chat.pinned_message.message_id, disable_notification=True)
                return {"success": True, "value": f"Message {chat.pinned_message.message_id} pinned"}
            return {"success": False, "error": "No pinned message found to re-pin"}

        elif data.action == "promote_all_admins":
            s = f = 0
            for uid_str in data.user_ids:
                try:
                    uid = int(uid_str)
                    await bot.app.bot.promote_chat_member(
                        chat_id=gid, user_id=uid,
                        can_manage_chat=True, can_delete_messages=True,
                        can_manage_video_chats=True, can_restrict_members=True,
                        can_change_info=True, can_invite_users=True, can_pin_messages=True
                    )
                    s += 1
                    await asyncio.sleep(0.2)
                except Exception as e:
                    f += 1
            return {"success": True, "value": f"Promoted {s}, failed {f}"}

        elif data.action == "demote_all_admins":
            admins = await bot.app.bot.get_chat_administrators(gid)
            s = f = 0
            for a in admins:
                if a.status == "creator":
                    continue
                try:
                    await bot.app.bot.promote_chat_member(
                        chat_id=gid, user_id=a.user.id,
                        is_anonymous=False, can_manage_chat=False, can_delete_messages=False,
                        can_manage_video_chats=False, can_restrict_members=False,
                        can_promote_members=False, can_change_info=False,
                        can_invite_users=False, can_pin_messages=False
                    )
                    s += 1
                    await asyncio.sleep(0.2)
                except Exception:
                    f += 1
            return {"success": True, "value": f"Demoted {s} admins, failed {f}"}

        elif data.action == "set_admin_custom_title":
            if not data.user_ids:
                return {"success": False, "error": "No user ID specified"}
            uid = int(data.user_ids[0])
            await bot.app.bot.set_chat_administrator_custom_title(
                chat_id=gid, 
                user_id=uid, 
                custom_title=data.value or ""
            )
            return {"success": True}

        elif data.action == "leave_group":
            await bot.app.bot.leave_chat(chat_id=gid)
            return {"success": True}

        return {"success": False, "error": "Unknown action"}
    except Exception as e:
        bot.logger.error(f"GCC Group Action '{data.action}' Error: {e}")
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
#  MANUAL DATABASE ENTRY – Add Group / Add User
# ═══════════════════════════════════════════════════════════

class ManualAddGroup(BaseModel):
    group_id: str
    title: str
    group_type: str = "supergroup"

class ManualAddUser(BaseModel):
    user_id: str
    full_name: str
    username: str = ""


@app.post("/api/add_group")
async def api_add_group(data: ManualAddGroup, request: Request):
    """Manually add a group to the database."""
    if not await check_auth(request): return auth_failed()
    try:
        gid = int(data.group_id) if data.group_id.lstrip("-").isdigit() else None
        if gid is None:
            return {"success": False, "error": "Invalid group ID — must be a number"}
        if not data.title.strip():
            return {"success": False, "error": "Title cannot be empty"}
        database.add_group(gid, data.title.strip(), data.group_type.strip() or "supergroup")

        # If bot is running, also verify via Telegram and fetch real title
        real_title = data.title.strip()
        if bot.app:
            try:
                chat = await bot.app.bot.get_chat(gid)
                real_title = chat.title or real_title
                database.add_group(gid, real_title, str(chat.type))
            except Exception:
                pass  # Use manual data if bot can't reach it

        bot.logger.info(f"Manual DB add group: {gid} — {real_title}")
        return {"success": True, "message": f"Group '{real_title}' ({gid}) added to database."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/add_user")
async def api_add_user(data: ManualAddUser, request: Request):
    """Manually add a user to the database."""
    if not await check_auth(request): return auth_failed()
    try:
        uid = int(data.user_id) if data.user_id.strip().lstrip("-").isdigit() else None
        if uid is None:
            return {"success": False, "error": "Invalid user ID — must be a number"}
        if not data.full_name.strip():
            return {"success": False, "error": "Full name cannot be empty"}

        uname = (data.username or "").strip().lstrip("@")
        is_new = database.add_user(uid, data.full_name.strip(), uname)

        # Optionally try to get Telegram info
        real_name = data.full_name.strip()
        if bot.app:
            try:
                tg_user = await bot.app.bot.get_chat(uid)
                real_name = ((tg_user.first_name or "") + " " + (tg_user.last_name or "")).strip() or real_name
                database.add_user(uid, real_name, tg_user.username or uname)
            except Exception:
                pass

        action = "added" if is_new else "updated"
        bot.logger.info(f"Manual DB {action} user: {uid} — {real_name}")
        return {"success": True, "message": f"User '{real_name}' ({uid}) {action} in database.", "is_new": is_new}
    except Exception as e:
        return {"success": False, "error": str(e)}



# ═══════════════════════════════════════════════════════════
#  KEYWORD MANAGER API
# ═══════════════════════════════════════════════════════════

KEYWORD_FILE = "keyword.txt"

@app.get("/api/keywords")
async def get_keywords(request: Request):
    """Return all current keywords."""
    if not await check_auth(request): return auth_failed()
    try:
        if os.path.exists(KEYWORD_FILE):
            with open(KEYWORD_FILE, "r", encoding="utf-8") as f:
                kws = [k.strip() for k in f.read().splitlines() if k.strip()]
        else:
            kws = []
        return {"keywords": kws}
    except Exception as e:
        return {"success": False, "error": str(e)}

class KeywordAction(BaseModel):
    keyword: str

@app.post("/api/keywords/add")
async def add_keyword(data: KeywordAction, request: Request):
    """Add a new keyword to the keyword file."""
    if not await check_auth(request): return auth_failed()
    try:
        kw = data.keyword.strip().lower()
        if not kw:
            return {"success": False, "error": "Keyword cannot be empty"}
        existing = []
        if os.path.exists(KEYWORD_FILE):
            with open(KEYWORD_FILE, "r", encoding="utf-8") as f:
                existing = [k.strip() for k in f.read().splitlines() if k.strip()]
        if kw in existing:
            return {"success": False, "error": "Keyword already exists"}
        existing.append(kw)
        with open(KEYWORD_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(existing))
        return {"success": True, "message": f"Keyword '{kw}' added.", "keywords": existing}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/keywords/remove")
async def remove_keyword(data: KeywordAction, request: Request):
    """Remove a keyword from the keyword file."""
    if not await check_auth(request): return auth_failed()
    try:
        kw = data.keyword.strip().lower()
        if os.path.exists(KEYWORD_FILE):
            with open(KEYWORD_FILE, "r", encoding="utf-8") as f:
                existing = [k.strip() for k in f.read().splitlines() if k.strip()]
        else:
            existing = []
        if kw not in existing:
            return {"success": False, "error": "Keyword not found"}
        existing.remove(kw)
        with open(KEYWORD_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(existing))
        return {"success": True, "message": f"Keyword '{kw}' removed.", "keywords": existing}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ═══════════════════════════════════════════════════════════
#  USER / GROUP PROFILE LOOKUP
# ═══════════════════════════════════════════════════════════

@app.get("/api/lookup")
async def lookup_entity(entity_id: str, request: Request):
    """Look up a user or group on Telegram by ID."""
    if not await check_auth(request): return auth_failed()
    if not bot.app:
        return {"success": False, "error": "Bot not initialised"}
    try:
        eid = int(entity_id) if entity_id.lstrip("-").isdigit() else entity_id
        chat = await bot.app.bot.get_chat(eid)
        result = {
            "id": chat.id,
            "type": str(chat.type),
            "title": getattr(chat, "title", None),
            "first_name": getattr(chat, "first_name", None),
            "last_name": getattr(chat, "last_name", None),
            "username": getattr(chat, "username", None),
            "bio": getattr(chat, "bio", None),
            "description": getattr(chat, "description", None),
            "member_count": None,
        }
        try:
            result["member_count"] = await bot.app.bot.get_chat_member_count(eid)
        except Exception:
            pass
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ═══════════════════════════════════════════════════════════
#  QUICK MESSAGE SEND
# ═══════════════════════════════════════════════════════════

class QuickMessage(BaseModel):
    target_id: str
    message: str
    parse_mode: str = "HTML"

@app.post("/api/send_message")
async def send_quick_message(data: QuickMessage, request: Request):
    """Send a quick message to any user or group."""
    if not await check_auth(request): return auth_failed()
    if not bot.app:
        return {"success": False, "error": "Bot not initialised"}
    try:
        tid = int(data.target_id) if data.target_id.lstrip("-").isdigit() else data.target_id
        pm = data.parse_mode if data.parse_mode in ["HTML", "Markdown", "MarkdownV2"] else "HTML"
        sent = await bot.app.bot.send_message(chat_id=tid, text=data.message, parse_mode=pm)
        return {"success": True, "message_id": sent.message_id, "chat_id": sent.chat_id}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ═══════════════════════════════════════════════════════════
#  BOT INFO PANEL
# ═══════════════════════════════════════════════════════════

@app.get("/api/bot_info")
async def get_bot_info(request: Request):
    """Return live bot info from Telegram."""
    if not await check_auth(request): return auth_failed()
    if not bot.app:
        return {"success": False, "error": "Bot not initialised"}
    try:
        me = await bot.app.bot.get_me()
        return {
            "success": True,
            "id": me.id,
            "first_name": me.first_name,
            "username": me.username,
            "can_join_groups": me.can_join_groups,
            "can_read_all_group_messages": me.can_read_all_group_messages,
            "supports_inline_queries": me.supports_inline_queries,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ═══════════════════════════════════════════════════════════
#  DESTINATION GROUP CONFIG
# ═══════════════════════════════════════════════════════════

class DestConfig(BaseModel):
    destination_group_id: str

@app.post("/api/update_destination")
async def update_destination(data: DestConfig, request: Request):
    """Update the DESTINATION_GROUP_ID in bot config."""
    if not await check_auth(request): return auth_failed()
    try:
        new_id = int(data.destination_group_id.strip())
        bot.DESTINATION_GROUP_ID = new_id
        bot.CONFIG["destination_group_id"] = new_id
        bot.save_config(bot.CONFIG)
        return {"success": True, "message": f"Destination group updated to {new_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ═══════════════════════════════════════════════════════════
#  TOP ACTIVE USERS LEADERBOARD
# ═══════════════════════════════════════════════════════════

@app.get("/api/top_users")
async def get_top_users(request: Request, limit: int = 10):
    """Return top N users by message count."""
    if not await check_auth(request): return auth_failed()
    try:
        users = database.get_all_users()
        sorted_users = sorted(users, key=lambda u: u.get("message_count", 0), reverse=True)
        return {"success": True, "users": sorted_users[:limit]}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ═══════════════════════════════════════════════════════════
#  CSV EXPORT
# ═══════════════════════════════════════════════════════════
import csv
import io
from fastapi.responses import StreamingResponse

@app.get("/api/export/users")
async def export_users_csv(request: Request):
    """Export all users as a CSV file."""
    pwd = request.headers.get("X-Dashboard-Password") or request.query_params.get("pwd")
    if pwd != DASHBOARD_PASSWORD:
        return HTMLResponse(status_code=401, content="<h1>Unauthorized.</h1>")
    users = database.get_all_users()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Full Name", "Username", "Message Count", "Joined At"])
    for u in users:
        writer.writerow([
            u.get("id", ""),
            u.get("full_name", ""),
            u.get("username", ""),
            u.get("message_count", 0),
            u.get("joined_at", "")
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hinata_users.csv"}
    )

@app.get("/api/export/groups")
async def export_groups_csv(request: Request):
    """Export all groups as a CSV file."""
    pwd = request.headers.get("X-Dashboard-Password") or request.query_params.get("pwd")
    if pwd != DASHBOARD_PASSWORD:
        return HTMLResponse(status_code=401, content="<h1>Unauthorized.</h1>")
    groups = database.get_all_groups()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Type", "Added At"])
    for g in groups:
        writer.writerow([
            g.get("id", ""),
            g.get("title", ""),
            g.get("type", ""),
            g.get("added_at", "")
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hinata_groups.csv"}
    )

# ═══════════════════════════════════════════════════════════
#  PING / STATUS CHECK
# ═══════════════════════════════════════════════════════════

@app.get("/api/ping")
async def api_ping():
    """Simple health-check endpoint, no auth needed."""
    return {"status": "ok", "bot_running": bot.app is not None, "uptime": bot.get_uptime()}


if __name__ == "__main__":
    import uvicorn
    # Use environment variables for port (Render uses PORT env)
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
