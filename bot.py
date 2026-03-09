# لا تنسى ذكر الله 🤍
# ELITE HOST BOT v5.0 — ULTRA EDITION

import telebot, os, json, subprocess, sys, psutil, shutil, logging, threading, time, re, hashlib, socket, random, string, zipfile, urllib.request
from telebot import types
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from collections import defaultdict

# ── تسريع فائق — uvloop (إذا متاح) ─────────────────────────
try:
    import asyncio

except ImportError:
    pass

# ── تسريع Python GC ─────────────────────────────────────────
import gc
gc.set_threshold(50000, 500, 100)


# ══════════════════════════════════════════════════════════════
#  السجل
# ══════════════════════════════════════════════════════════════
os.makedirs("LOGS", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("LOGS/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("ELITE")

# ══════════════════════════════════════════════════════════════
#  الإعدادات
# ══════════════════════════════════════════════════════════════
TOKEN     = os.environ.get("TOKEN",     "8652433036:AAErkpPSRx7A4sz_-kWdahxEXizpvV47YsI")
ADMIN_ID  = int(os.environ.get("ADMIN_ID",  "8665373093"))
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "8665373093,8206539702").split(",")]

# ── التحقق من صحة التوكن قبل البدء ──────────────────────────
if not TOKEN or ":" not in TOKEN:
    log.critical("❌ التوكن غير صحيح! تحقق من متغير TOKEN")
    sys.exit(1)

bot      = telebot.TeleBot(
    TOKEN,
    threaded      = True,
    num_threads   = 200,           # ↑ زيادة عدد الـ threads
    skip_pending  = True,          # تخطي الرسائل القديمة عند البدء
)
executor = ThreadPoolExecutor(
    max_workers  = 200,
    thread_name_prefix = "elite_worker"
)

BOT_START_TIME = time.time()

# ══════════════════════════════════════════════════════════════
#  🤖 نظام الذكاء الاصطناعي — DeepSeek
# ══════════════════════════════════════════════════════════════
AI_KEY     = os.environ.get("AI_KEY", "DarkAI-DeepAI-EFF939A9130A0ABAE3A7414D")
AI_URL     = "https://sii3.top/api/deepseek/api.php"
AI_SYSTEM  = (
    "أنت مساعد ذكي اسمه ELITE AI داخل بوت تليجرام اسمه ELITE HOST. "
    "بتساعد المستخدمين في البرمجة واستضافة الملفات والأسئلة العامة. "
    "ردودك بالعربي وواضحة ومختصرة. لو فيه كود اكتبه في code block."
)
ai_sessions = {}  # uid -> list of previous messages (context)

def ai_ask(prompt: str, uid: str = None) -> str:
    """إرسال سؤال لـ DeepSeek مع retry تلقائي"""
    context = ""
    if uid and uid in ai_sessions:
        for msg in ai_sessions[uid][-4:]:
            context += f"User: {msg['q']}\nAI: {msg['a']}\n\n"

    full_prompt = AI_SYSTEM + "\n\n" + context + "User: " + prompt

    import urllib.request, urllib.parse
    data = urllib.parse.urlencode({"key": AI_KEY, "v3": full_prompt}).encode()

    for attempt in range(3):  # 3 محاولات
        try:
            req = urllib.request.Request(AI_URL, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode()
            try:
                result = json.loads(raw)
                reply  = result.get("response", "").strip()
            except:
                reply = raw.strip()

            if not reply:
                raise Exception("رد فارغ")

            if uid:
                if uid not in ai_sessions: ai_sessions[uid] = []
                ai_sessions[uid].append({"q": prompt, "a": reply})
                if len(ai_sessions[uid]) > 10:
                    ai_sessions[uid] = ai_sessions[uid][-10:]
            return reply

        except Exception as e:
            log.warning(f"AI attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(2)

    return "⚠️ السيرفر مشغول حالياً، حاول تاني بعد ثواني 🔄"

def ai_stream_reply(chat_id: int, text: str, reply_to_id: int = None):
    """إرسال الرد بشكل تدريجي"""
    try:
        if reply_to_id:
            msg = safe_send(chat_id, "🤖 جارٍ التفكير...", reply_to_message_id=reply_to_id)
        else:
            msg = safe_send(chat_id, "🤖 جارٍ التفكير...")
        mid  = msg.message_id
        words = text.split()
        out  = ""
        for i, w in enumerate(words):
            out += w + " "
            # تحديث كل 6 كلمات أو في النهاية
            if (i+1) % 6 == 0 or i == len(words)-1:
                try:
                    bot.edit_message_text(out.strip(), chat_id, mid)
                except: pass
                time.sleep(0.04)
    except Exception as e:
        log.error(f"AI stream error: {e}")
        try: safe_send(chat_id, text)
        except: pass

for d in ["ELITE_HOST","GHOST_VOLUMES","SYSTEM_CORES","LOGS","QUARANTINE","BACKUPS"]:
    os.makedirs(d, exist_ok=True)

# ══════════════════════════════════════════════════════════════
#  نظام الأمان المتقدم
# ══════════════════════════════════════════════════════════════

# ── Rate Limiting متعدد المستويات ──────────────────────────
spam_counter   = defaultdict(list)
upload_counter = defaultdict(list)
spam_blocked   = {}
failed_cmds    = defaultdict(int)
suspicious     = set()

SPAM_LIMIT        = 8
SPAM_WINDOW       = 10
SPAM_BAN_TIME     = 60
UPLOAD_LIMIT      = 5
UPLOAD_WINDOW     = 60
MAX_FAILED_CMDS   = 10

# ── Cache فائق السرعة لتسريع الاستجابة ──────────────────────
_response_cache: dict = {}          # cache للردود المتكررة
_cache_ttl:      dict = {}          # وقت انتهاء الـ cache
CACHE_SECONDS         = 30          # كل 30 ثانية يتجدد الـ cache

def _cache_get(key: str):
    if key in _response_cache:
        if time.time() < _cache_ttl.get(key, 0):
            return _response_cache[key]
        del _response_cache[key]
    return None

def _cache_set(key: str, val, ttl: int = CACHE_SECONDS):
    _response_cache[key] = val
    _cache_ttl[key]      = time.time() + ttl

# ── Lock خفيف للعمليات المتزامنة ────────────────────────────
_db_lock = threading.RLock()



# ══ نظام الأمان المتقدم ══════════════════════════
SECURITY_LOG     = []
download_counter = defaultdict(list)
FILE_ACCESS_LOG  = defaultdict(list)
INTRUSION_SCORE  = defaultdict(int)
MAX_INTRUSION    = 15
PROTECTED_FILES  = {
    "bot.py","elite_db.json","config.json",".env",
    "requirements.txt","nixpacks.toml","data.json"
}

def sec_log(uid: str, action: str, level: str = "warn", fname: str = ""):
    entry = {
        "time":   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "uid":    uid,
        "name":   db["users"].get(uid,{}).get("name","؟") if 'db' in dir() else "؟",
        "action": action,
        "level":  level,
        "file":   fname,
    }
    SECURITY_LOG.append(entry)
    if len(SECURITY_LOG) > 500: SECURITY_LOG.pop(0)
    log.warning(f"[SEC/{level.upper()}] uid={uid} | {action} | file={fname}")

def add_intrusion(uid: str, score: int, reason: str):
    INTRUSION_SCORE[uid] += score
    sec_log(uid, reason, "warn")
    total = INTRUSION_SCORE[uid]
    if total >= 8 and (total - score) < 8:
        try:
            mk = types.InlineKeyboardMarkup()
            mk.add(types.InlineKeyboardButton("👤 ملف المستخدم", callback_data=f"uview_{uid}"))
            safe_send(ADMIN_ID,
                f"⚠️ مستخدم مشبوه!\n"
                f"👤 {db['users'].get(uid,{}).get('name','؟')} | `{uid}`\n"
                f"🎯 نقاط الخطورة: {total}/{MAX_INTRUSION}\n"
                f"⚡ السبب: {reason}", reply_markup=mk)
        except: pass
    if total >= MAX_INTRUSION:
        if uid not in db.get("blacklist",[]):
            add_to_blacklist(uid)
            if uid in db["users"]: db["users"][uid]["role"] = "banned"
            save()
            sec_log(uid, f"حظر تلقائي — نقاط: {total}", "critical")
            mk2 = types.InlineKeyboardMarkup(row_width=2)
            mk2.add(
                types.InlineKeyboardButton("✅ رفع الحظر", callback_data=f"uact_{uid}_unban"),
                types.InlineKeyboardButton("👤 ملف المستخدم", callback_data=f"uview_{uid}"),
            )
            try:
                safe_send(ADMIN_ID,
                    f"🚨 *حظر تلقائي*\n"
                    f"👤 {db['users'].get(uid,{}).get('name','؟')} | `{uid}`\n"
                    f"🎯 نقاط الخطورة: {total}\n"
                    f"📋 السبب: {reason}", reply_markup=mk2)
            except: pass

def is_protected_file(fname: str) -> bool:
    if fname in PROTECTED_FILES: return True
    fname_lower = fname.lower()
    for s in ["token","secret","password","api_key","_db","database","backup","elite","config"]:
        if s in fname_lower: return True
    return False

def watermark_file(content: bytes, uid: str) -> bytes:
    """علامة مائية مخفية في الملفات النصية"""
    try:
        text = content.decode("utf-8")
        name = db["users"].get(uid,{}).get("name","؟").replace(" ","_")
        ts   = datetime.now().strftime('%Y%m%d%H%M%S')
        mark = f"\n# __WM__{uid}_{ts}_{name}__WM__\n"
        return (text + mark).encode("utf-8")
    except:
        return content

def check_download_flood(uid: str) -> bool:
    now = time.time()
    download_counter[uid] = [t for t in download_counter[uid] if now - t < 60]
    download_counter[uid].append(now)
    if len(download_counter[uid]) > 3:
        add_intrusion(uid, 3, "تحميل سريع — أكتر من 3 ملفات في دقيقة")
        return True
    return False

def is_spam(uid:str) -> bool:
    if uid in spam_blocked:
        if time.time() < spam_blocked[uid]: return True
        else: del spam_blocked[uid]
    now = time.time()
    spam_counter[uid] = [t for t in spam_counter[uid] if now-t < SPAM_WINDOW]
    spam_counter[uid].append(now)
    if len(spam_counter[uid]) > SPAM_LIMIT:
        spam_blocked[uid] = now + SPAM_BAN_TIME
        log.warning(f"SPAM blocked: {uid}")
        # أبلغ الأدمن لو تكرر
        failed_cmds[uid] += 1
        if failed_cmds[uid] >= 3:
            suspicious.add(uid)
            try: safe_send(ADMIN_ID, f"🚨 مستخدم مشبوه: {uid} — spam متكرر")
            except: pass
        return True
    return False

def is_upload_spam(uid:str) -> bool:
    now = time.time()
    upload_counter[uid] = [t for t in upload_counter[uid] if now-t < UPLOAD_WINDOW]
    upload_counter[uid].append(now)
    return len(upload_counter[uid]) > UPLOAD_LIMIT

def check_suspicious(uid:str, action:str=""):
    """تتبع المحاولات المشبوهة"""
    failed_cmds[uid] += 1
    if failed_cmds[uid] >= MAX_FAILED_CMDS:
        suspicious.add(uid)
        add_to_blacklist(uid)
        try: safe_send(ADMIN_ID,
            f"🔴 حظر تلقائي: `{uid}`\n"
            f"سبب: {MAX_FAILED_CMDS} محاولة مشبوهة\n"
            f"آخر فعل: {action}")
        except: pass

def validate_file(raw:bytes, fname:str, uid:str) -> tuple:
    """التحقق من الملف قبل الرفع — يرجع (ok, reason)"""
    # فحص الحجم
    max_kb = db["settings"].get("max_file_size_kb", 500)
    if len(raw) > max_kb * 1024:
        return False, f"الملف كبير ({len(raw)//1024}KB) — الحد {max_kb}KB"

    # فحص عدد الملفات للمستخدم العادي
    role = get_role(uid)
    if role == ROLE_USER:
        user_files = sum(1 for v in db["files"].values() if v.get("owner")==uid)
        max_files  = db["settings"].get("max_files_per_user", 5)
        if user_files >= max_files:
            return False, f"وصلت للحد الأقصى ({max_files} ملفات)"

    # فحص rate limit للرفع
    if is_upload_spam(uid):
        return False, f"كتير رفعات — انتظر دقيقة"

    # فحص امتداد الملف
    allowed = [".py", ".js", ".sh", ".json", ".txt", ".env", ".toml", ".yaml", ".yml"]
    ext = os.path.splitext(fname)[1].lower()
    if ext not in allowed:
        return False, f"امتداد {ext} مش مدعوم"

    return True, "ok"

# ── فاحص محتوى URL في الرسائل ─────────────────────────────
PHISHING_PATTERNS = [
    r"bit\.ly|tinyurl|t\.co",         # روابط مختصرة
    r"free.*hack|hack.*free",          # مواقع هكر
    r"win.*prize|claim.*reward",       # نصب
]

def contains_suspicious_url(text:str) -> bool:
    for p in PHISHING_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

# ══════════════════════════════════════════════════════════════
#  معالج الأخطاء العام
# ══════════════════════════════════════════════════════════════
def handle_error(e: Exception, context: str = ""):
    log.error(f"ERROR [{context}]: {e}")
    try:
        safe_send(ADMIN_ID,
            f"🔴 خطأ في البوت\n"
            f"📍 {context}\n"
            f"❌ {str(e)[:300]}")
    except: pass

# ══════════════════════════════════════════════════════════════
#  مراقبة الصحة التلقائية
# ══════════════════════════════════════════════════════════════
HEALTH_LOG = []   # آخر 50 قراءة

CPU_ALERT_SENT   = False
CPU_KILLED_ONCE  = False

def health_monitor():
    global CPU_ALERT_SENT, CPU_KILLED_ONCE
    while True:
        time.sleep(30)  # كل 30 ثانية بدل 60
        try:
            cpu  = psutil.cpu_percent(interval=1)
            mem  = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            HEALTH_LOG.append({
                "time": datetime.now().strftime('%H:%M'),
                "cpu": cpu, "mem": mem, "disk": disk
            })
            if len(HEALTH_LOG) > 100: HEALTH_LOG.pop(0)

            # ── CPU عالي جداً — إيقاف تلقائي ─────────
            if cpu > 95 and not CPU_KILLED_ONCE:
                CPU_KILLED_ONCE = True
                killed = []
                for name in list(running_procs.keys()):
                    stop_file(name)
                    killed.append(name)
                mk = types.InlineKeyboardMarkup(row_width=2)
                mk.add(
                    types.InlineKeyboardButton("🔃 إعادة تشغيل الكل", callback_data="run_all"),
                    types.InlineKeyboardButton("📊 الموارد",           callback_data="ap_res"),
                )
                safe_send(ADMIN_ID,
                    f"🚨 CPU وصل {cpu:.1f}% — تم إيقاف {len(killed)} ملف تلقائياً!\n"
                    f"الملفات: {', '.join(killed) or 'لا يوجد'}\n"
                    f"RAM: {mem:.1f}% | Disk: {disk:.1f}%",
                    reply_markup=mk)
                CPU_ALERT_SENT = True

            elif cpu > 85 and not CPU_ALERT_SENT:
                CPU_ALERT_SENT = True
                mk = types.InlineKeyboardMarkup(row_width=2)
                mk.add(
                    types.InlineKeyboardButton("💀 إيقاف الكل",  callback_data="killall"),
                    types.InlineKeyboardButton("📊 الموارد",      callback_data="ap_res"),
                )
                safe_send(ADMIN_ID,
                    f"🔥 تحذير: CPU وصل {cpu:.1f}%!\n"
                    f"RAM: {mem:.1f}% | Disk: {disk:.1f}%\n"
                    f"⚡ ملفات شغالة: {len(running_procs)}",
                    reply_markup=mk)

            elif cpu < 70:
                CPU_ALERT_SENT  = False
                CPU_KILLED_ONCE = False

            # ── RAM عالية ─────────────────────────────
            if mem > 90:
                safe_send(ADMIN_ID,
                    f"🔥 RAM وصلت {mem:.1f}%!\nCPU: {cpu:.1f}% | Disk: {disk:.1f}%")
            if disk > 90:
                safe_send(ADMIN_ID, f"💾 Disk امتلأ {disk:.1f}%!")

            # ── ملفات وقفت ────────────────────────────
            for name, info in list(running_procs.items()):
                if info["proc"].poll() is not None:
                    if name in db["files"] and not db["files"][name].get("auto_restart"):
                        db["files"][name]["active"] = False
                        running_procs.pop(name, None)
                        save()
                        safe_send(ADMIN_ID,
                            f"⚠️ توقف: `{name}`")
        except Exception as e:
            log.error(f"Health monitor: {e}")

threading.Thread(target=health_monitor, daemon=True).start()

# ══════════════════════════════════════════════════════════════
#  باك أب تلقائي
# ══════════════════════════════════════════════════════════════
def auto_backup():
    while True:
        time.sleep(3600 * int(os.environ.get("BACKUP_HOURS","6")))
        try:
            if not os.path.exists(DB_FILE): continue
            ts  = datetime.now().strftime('%Y%m%d_%H%M')
            dst = f"BACKUPS/elite_db_{ts}.json"
            shutil.copy2(DB_FILE, dst)
            # احتفظ بآخر 10 باك أب بس
            backups = sorted([f for f in os.listdir("BACKUPS") if f.endswith(".json")])
            for old in backups[:-10]:
                os.remove(f"BACKUPS/{old}")
            with open(dst,'rb') as f:
                bot.send_document(ADMIN_ID, f,
                    caption=f"💾 باك أب تلقائي\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            log.info(f"Auto backup: {dst}")
        except Exception as e:
            log.error(f"Auto backup: {e}")

threading.Thread(target=auto_backup, daemon=True).start()

# ══════════════════════════════════════════════════════════════
#  قاعدة البيانات
# ══════════════════════════════════════════════════════════════
DB_FILE = "elite_db.json"

# ══════════════════════════════════════════════════════════════
#  🛡 دوال الإرسال الآمن — تمنع أخطاء Markdown تلقائياً
# ══════════════════════════════════════════════════════════════

def esc(text) -> str:
    """تنظيف النص من أحرف Markdown الخطيرة"""
    if text is None: return ""
    s = str(text)
    # أحرف تكسر MarkdownV1
    for ch in ['_', '*', '`', '[']:
        s = s.replace(ch, '\\' + ch)
    return s

def safe_send(chat_id, text: str, **kwargs):
    """إرسال رسالة آمن — لو فشل Markdown يرسل بدونه"""
    try:
        return safe_send(chat_id, text, **kwargs)
    except Exception as e:
        if "can't parse entities" in str(e) or "Bad Request" in str(e):
            kwargs.pop("parse_mode", None)
            try:
                return safe_send(chat_id, text, **kwargs)
            except Exception as e2:
                log.error(f"safe_send fallback failed: {e2}")
        else:
            log.error(f"safe_send: {e}")

def safe_reply(m, text: str, **kwargs):
    """رد آمن — لو فشل Markdown يرسل بدونه"""
    try:
        return safe_reply(m, text, **kwargs)
    except Exception as e:
        if "can't parse entities" in str(e) or "Bad Request" in str(e):
            kwargs.pop("parse_mode", None)
            try:
                return safe_reply(m, text, **kwargs)
            except Exception as e2:
                log.error(f"safe_reply fallback failed: {e2}")
        else:
            log.error(f"safe_reply: {e}")

def safe_edit(chat_id, msg_id, text: str, **kwargs):
    """تعديل رسالة آمن"""
    try:
        return bot.edit_message_text(text, chat_id, msg_id, **kwargs)
    except Exception as e:
        if "can't parse entities" in str(e) or "Bad Request" in str(e):
            kwargs.pop("parse_mode", None)
            try:
                return bot.edit_message_text(text, chat_id, msg_id, **kwargs)
            except: pass
        elif "message is not modified" not in str(e):
            log.error(f"safe_edit: {e}")


def load_db():
    default = {
        "users":     {},
        "files":     {},
        "envs":      {},
        "scheduled": [],
        "quarantine":[],
        "tickets":   {},
        "blacklist": [],
        "alerts":    [],
        "file_versions": {},
        "stats": {
            "uploads": 0, "commands": 0, "restarts": 0,
            "blocked": 0, "kills": 0, "tickets_opened": 0,
        },
        "settings":  {
            "max_files_per_user":   5,
            "max_file_size_kb":     500,
            "maintenance":          False,
            "auto_vip":             True,
            "notify_on_crash":      True,
            "notify_on_new_user":   True,
            "max_crashes_before_disable": 5,
        },
        "notes":     [],
        "locked":    False,
        "daily_report_time": "08:00",
    }
    if not os.path.exists(DB_FILE): return default
    try:
        with open(DB_FILE,'r',encoding='utf-8') as f: data=json.load(f)
        for k,v in default.items():
            if k not in data: data[k]=v
        if "settings" not in data: data["settings"] = default["settings"]
        for k,v in default["settings"].items():
            if k not in data["settings"]: data["settings"][k] = v
        # تأكد من وجود stats دائماً
        if "stats" not in data: data["stats"] = default["stats"]
        for k,v in default["stats"].items():
            if k not in data["stats"]: data["stats"][k] = v
        return data
    except: return default

db = load_db()

def save():
    with open(DB_FILE,'w',encoding='utf-8') as f:
        json.dump(db,f,ensure_ascii=False,indent=2)

save()

# ══════════════════════════════════════════════════════════════
#  الصلاحيات
# ══════════════════════════════════════════════════════════════
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_VIP   = "vip"
ROLE_USER  = "user"

def get_role(uid:str) -> str:
    if int(uid) == ADMIN_ID:           return ROLE_OWNER
    if int(uid) in ADMIN_IDS:          return ROLE_ADMIN
    u = db["users"].get(uid,{})
    return u.get("role", ROLE_USER)

def is_staff(uid:str) -> bool:
    return get_role(uid) in [ROLE_OWNER, ROLE_ADMIN]

def reg_user(m):
    uid  = str(m.from_user.id)
    name = m.from_user.first_name or "مستخدم"
    if uid not in db["users"]:
        db["users"][uid] = {
            "name":    name,
            "joined":  __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M'),
            "role":    ROLE_USER,
            "uploads": 0,
        }
        save()
        try:
            safe_send(ADMIN_ID,
                f"👤 مستخدم جديد: {name} ({uid})")
        except: pass
    else:
        db["users"][uid]["name"] = name
    return uid

# ══════════════════════════════════════════════════════════════
#  فاحص الملفات
# ══════════════════════════════════════════════════════════════
# ── أنماط الخطر الحقيقي فقط (مش كل حاجة) ──

# ══════════════════════════════════════════════════════════════
#  🛡 ELITE SECURITY ENGINE v3.0 — محرك الفحص الأمني المتقدم
# ══════════════════════════════════════════════════════════════

# ── نظام التحذيرات والحظر التلقائي ─────────────────────────
# warning_count[uid] = تحذيرات متبقية  (يبدأ من MAX_WARNINGS وينزل لـ 0 → حظر)
warning_count: dict  = {}
MAX_WARNINGS         = 3   # يبدأ من 3 وينزل — لما يوصل 0 حظر فوري

# ── تصنيفات مستوى الخطورة ────────────────────────────────────
SEV_CRITICAL = "CRITICAL"   # حظر فوري بدون تحذير
SEV_HIGH     = "HIGH"       # تحذير + قد يؤدي للحظر
SEV_MEDIUM   = "MEDIUM"     # تحذير فقط

# ── قائمة الأنماط الخطيرة الشاملة ────────────────────────────
# كل عنصر: (regex, وصف, مستوى_الخطورة)
DANGER_PATTERNS = [

    # ════ CRITICAL — حظر فوري ════════════════════════════════

    # Reverse/Bind Shell
    (r"reverse.?shell|bind.?shell|bash\s+-i\s+>&",
     "reverse shell / bind shell", SEV_CRITICAL),
    (r"socket\.connect.*(?:4444|1337|31337|9001|6666)",
     "اتصال بمنفذ Hacker مشهور", SEV_CRITICAL),
    (r"\/bin\/sh|\/bin\/bash.*-[ic]|cmd\.exe.*\/c",
     "تنفيذ shell مباشر", SEV_CRITICAL),
    (r"pty\.spawn|os\.execve.*sh|subprocess.*shell\s*=\s*True.*(?:rm|del|format|mkfs)",
     "shell=True مع أوامر خطيرة", SEV_CRITICAL),

    # Ransomware
    (r"Fernet.*(?:encrypt|key).*os\.walk",
     "تشفير ملفات (Ransomware)", SEV_CRITICAL),
    (r"AES.*encrypt.*os\.(?:listdir|walk)",
     "تشفير ملفات بـ AES (Ransomware)", SEV_CRITICAL),
    (r"\.enc\b.*open.*wb.*for.*os\.walk",
     "تشفير وحفظ ملفات (Ransomware)", SEV_CRITICAL),

    # Fork Bomb
    (r"os\.fork\s*\(\s*\).*os\.fork\s*\(\s*\)",
     "Fork Bomb مزدوج", SEV_CRITICAL),
    (r"while\s+(?:True|1)\s*:.*os\.fork",
     "Fork Bomb في حلقة لا نهائية", SEV_CRITICAL),

    # حذف نظام
    (r"os\.system\s*\(['\"]?\s*rm\s+-rf\s+/",
     "حذف root النظام بـ rm -rf /", SEV_CRITICAL),
    (r"shutil\.rmtree\s*\(['\"]?\s*/(?:etc|var|usr|home|root)",
     "حذف مجلدات حيوية بـ shutil", SEV_CRITICAL),
    (r"format\s+[cCdD]:|del\s+/[fFsS]\s+/[qQ]\s+[cCdD]:",
     "تهيئة أو حذف القرص (Windows)", SEV_CRITICAL),

    # Token Stealer
    (r"(?:discord|telegram|slack).*token.*(?:requests|urllib|http)",
     "سرقة توكنات (Token Stealer)", SEV_CRITICAL),
    (r"(?:localStorage|sessionStorage).*token.*(?:fetch|XMLHttpRequest)",
     "سرقة بيانات المتصفح", SEV_CRITICAL),
    (r"re\.findall.*[A-Za-z0-9_-]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}",
     "استخراج Discord Token بـ regex", SEV_CRITICAL),

    # Crypto Miner
    (r"xmrig|minerd|stratum\+(?:tcp|ssl)://",
     "تعدين عملات مشفرة (XMRig)", SEV_CRITICAL),
    (r"cryptominer|nicehash|pool\.minexmr",
     "برنامج تعدين", SEV_CRITICAL),
    (r"hashlib\.sha256.*nonce.*target.*difficulty",
     "خوارزمية Proof-of-Work للتعدين", SEV_CRITICAL),

    # Self-Replication / Worm
    (r"shutil\.copy.*__file__.*(?:startup|autorun|AppData)",
     "نسخ نفسه للـ Startup (Worm)", SEV_CRITICAL),
    (r"glob\.glob.*\.py.*open.*write.*open.*read.*__file__",
     "تكاثر ذاتي في ملفات Python", SEV_CRITICAL),

    # ════ HIGH — تحذير شديد ══════════════════════════════════

    # Keylogger
    (r"pynput.*(?:Listener|keyboard|mouse)",
     "Keylogger بـ pynput", SEV_HIGH),
    (r"GetAsyncKeyState|SetWindowsHookEx|WH_KEYBOARD",
     "Keylogger بـ WinAPI", SEV_HIGH),
    (r"keylog|keystroke|key_press.*log",
     "تسجيل ضغطات لوحة المفاتيح", SEV_HIGH),

    # Stealer — سرقة بيانات
    (r"(?:os\.path\.join|glob).*(?:\.ssh|id_rsa|known_hosts)",
     "قراءة مفاتيح SSH الخاصة", SEV_HIGH),
    (r"(?:os\.path\.join|glob).*(?:cookies\.sqlite|Login\s*Data|wallet\.dat)",
     "سرقة كوكيز أو بيانات تسجيل دخول", SEV_HIGH),
    (r"HKEY_CURRENT_USER.*(?:Software\\Google|Software\\Discord)",
     "قراءة Registry لسرقة بيانات", SEV_HIGH),
    (r"win32crypt\.CryptUnprotectData",
     "فك تشفير كلمات مرور Chrome/Edge", SEV_HIGH),
    (r"sqlite3.*(?:Login\s*Data|Cookies|Web\s*Data)",
     "استخراج بيانات المتصفح من SQLite", SEV_HIGH),

    # Backdoor
    (r"exec\s*\(\s*(?:requests|urllib).*\.(?:get|post|read)\s*\(",
     "تنفيذ كود مُحمَّل من الإنترنت (Backdoor)", SEV_HIGH),
    (r"eval\s*\(\s*(?:base64\.b64decode|zlib\.decompress)",
     "تنفيذ كود مشفر أو مضغوط (Obfuscated)", SEV_HIGH),
    (r"exec\s*\(\s*base64|exec\s*\(\s*__import__",
     "تنفيذ كود مشفر Base64", SEV_HIGH),
    (r"compile\s*\(.*exec\s*\(",
     "تجميع وتنفيذ كود ديناميكي", SEV_HIGH),

    # Remote Access / C2
    (r"(?:paramiko|fabric).*(?:exec_command|run).*(?:rm|del|format|wget|curl)",
     "أوامر خطيرة عبر SSH", SEV_HIGH),
    (r"socket\.socket.*SOCK_(?:STREAM|RAW).*(?:bind|listen|connect).*(?:while|loop)",
     "Server/Listener مشبوه", SEV_HIGH),
    (r"(?:ftplib|smtplib).*(?:sendmail|storbinary).*(?:os\.environ|passwd|token)",
     "إرسال بيانات حساسة عبر FTP/SMTP", SEV_HIGH),

    # Privilege Escalation
    (r"ctypes.*(?:windll|cdll).*(?:ShellExecute|CreateProcess).*runas",
     "رفع الصلاحيات (UAC Bypass)", SEV_HIGH),
    (r"subprocess.*(?:sudo|runas|pkexec).*(?:chmod|chown|passwd)",
     "محاولة رفع صلاحيات (sudo/runas)", SEV_HIGH),

    # Process Injection
    (r"ctypes\.windll\.kernel32\.(?:WriteProcessMemory|CreateRemoteThread|VirtualAllocEx)",
     "Process Injection بـ WinAPI", SEV_HIGH),
    (r"OpenProcess.*PROCESS_ALL_ACCESS",
     "فتح عملية بكل الصلاحيات", SEV_HIGH),

    # Webcam / Microphone
    (r"cv2\.VideoCapture\s*\(\s*0\s*\).*while",
     "تسجيل فيديو من الكاميرا سراً", SEV_HIGH),
    (r"pyaudio.*stream.*read.*open.*wb",
     "تسجيل صوت من الميكروفون سراً", SEV_HIGH),
    (r"sounddevice\.rec|soundfile\.write.*rec",
     "تسجيل صوت مشبوه", SEV_HIGH),

    # Screenshot Loop
    (r"(?:mss|PIL\.ImageGrab|pyautogui).*(?:grab|screenshot).*(?:while|sleep\()",
     "لقطات شاشة متكررة", SEV_HIGH),

    # Obfuscation
    (r"zlib\.decompress\s*\(\s*base64\.b64decode",
     "كود مشفر ومضغوط (Obfuscation)", SEV_HIGH),
    (r"marshal\.loads|pickle\.loads.*base64",
     "كود متحول خطير (Marshal/Pickle)", SEV_HIGH),
    (r"(?:chr\(\d+\)\s*\+\s*){10,}",
     "كود مبعثر بـ chr() (Obfuscation)", SEV_HIGH),
    (r"\\x[0-9a-fA-F]{2}(?:\\x[0-9a-fA-F]{2}){15,}",
     "كود hex مشفر طويل", SEV_HIGH),

    # Hidden Import
    (r"__import__\s*\(['\"](?:os|subprocess|socket|ctypes)['\"]",
     "استيراد مخفي لمكتبة خطيرة", SEV_HIGH),
    (r"importlib\.import_module\s*\(['\"](?:os|subprocess|socket)['\"]",
     "استيراد ديناميكي لمكتبة خطيرة", SEV_HIGH),

    # System Files
    (r"(?:open|read).*(?:/etc/(?:passwd|shadow|sudoers)|/root/\.(?:ssh|bash_history))",
     "قراءة ملفات نظام حساسة", SEV_HIGH),
    (r"(?:/proc/self/mem|/dev/mem|/dev/kmem)",
     "وصول مباشر لذاكرة النظام", SEV_HIGH),

    # ════ MEDIUM — تحذير ════════════════════════════════════

    # shell=True عام (بدون أوامر خطيرة)
    (r"subprocess\.[A-Za-z_]+\s*\(.*shell\s*=\s*True",
     "shell=True — خطر تنفيذ أوامر", SEV_MEDIUM),

    # Database Destruction
    (r"DROP\s+(?:TABLE|DATABASE|SCHEMA)\s+",
     "حذف قاعدة بيانات", SEV_MEDIUM),
    (r"DELETE\s+FROM\s+\w+\s+WHERE\s+1\s*=\s*1",
     "حذف كل البيانات من جدول", SEV_MEDIUM),
    (r"TRUNCATE\s+TABLE",
     "تفريغ جدول قاعدة بيانات", SEV_MEDIUM),

    # Suspicious Network
    (r"(?:requests|urllib|httpx)\.(?:get|post)\s*\(.*(?:password|token|secret|key)=",
     "إرسال بيانات حساسة عبر HTTP", SEV_MEDIUM),
    (r"(?:pastebin\.com|hastebin\.com|dpaste\.com)",
     "إرسال بيانات لـ Pastebin", SEV_MEDIUM),
    (r"(?:ngrok|serveo|localhost\.run)",
     "tunnel مشبوه (ngrok/serveo)", SEV_MEDIUM),

    # Env Stealing
    (r"os\.environ.*(?:TOKEN|PASSWORD|SECRET|API_KEY|PRIVATE)",
     "قراءة متغيرات بيئة حساسة لإرسالها", SEV_MEDIUM),

    # Autostart
    (r"(?:HKEY_CURRENT_USER|HKLM).*(?:Run|RunOnce).*(?:reg\s+add|winreg)",
     "إضافة للـ Autostart في Registry", SEV_MEDIUM),
    (r"(?:crontab|/etc/rc\.local|systemd.*enable)",
     "تسجيل تشغيل تلقائي", SEV_MEDIUM),
]

# ── فحص AST (Abstract Syntax Tree) ─────────────────────────
def _ast_deep_scan(content: str) -> list:
    """فحص بنية الكود بـ AST — يكشف الأنماط المخفية"""
    issues = []
    try:
        import ast as _ast
        tree = _ast.parse(content)
        for node in _ast.walk(tree):
            # exec/eval بأي شكل
            if isinstance(node, _ast.Call):
                func_name = ""
                if isinstance(node.func, _ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, _ast.Attribute):
                    func_name = node.func.attr
                if func_name in ("exec", "eval", "compile"):
                    # تحقق لو الـ argument مش string مباشر
                    if node.args and not isinstance(node.args[0], _ast.Constant):
                        issues.append((f"{func_name}() بمتغير ديناميكي — تنفيذ كود مجهول", SEV_HIGH))
            # os.system بأي شكل
            if isinstance(node, _ast.Call):
                if (isinstance(node.func, _ast.Attribute) and
                    node.func.attr in ("system","popen","execv","execve","spawnl")):
                    issues.append((f"استدعاء {node.func.attr}() — تنفيذ أوامر نظام", SEV_MEDIUM))
    except SyntaxError:
        issues.append(("خطأ Syntax في الملف — قد يكون مشفراً", SEV_MEDIUM))
    except Exception:
        pass
    return issues

# ── فحص الـ Hash ضد قاعدة بيانات Malware معروفة ────────────
KNOWN_MALWARE_HASHES = {
    # MD5 hashes لملفات ضارة معروفة (نماذج — يمكن توسيعها)
    "44d88612fea8a8f36de82e1278abb02f",  # EICAR test
    "69630e4574ec6798239b091cda43dca0",  # EICAR variant
}

def _hash_check(raw: bytes) -> tuple:
    """فحص الـ MD5 ضد قاعدة بيانات Malware"""
    import hashlib
    md5  = hashlib.md5(raw).hexdigest()
    sha1 = hashlib.sha1(raw).hexdigest()
    if md5 in KNOWN_MALWARE_HASHES:
        return True, f"MD5 مطابق لـ Malware معروف: {md5}"
    return False, md5

# ── فحص الـ Entropy (كشف التشفير/التعبئة) ──────────────────
def _entropy_check(content: str) -> float:
    """Shannon Entropy — قيمة عالية = كود مشفر/مضغوط"""
    import math
    if not content:
        return 0.0
    freq = {}
    for c in content:
        freq[c] = freq.get(c, 0) + 1
    length = len(content)
    entropy = -sum((f/length)*math.log2(f/length) for f in freq.values())
    return round(entropy, 2)

# ── الفحص الشامل الرئيسي ────────────────────────────────────
def deep_scan_file(path: str, raw: bytes = None) -> dict:
    """
    🛡 ELITE DEEP SCAN — فحص شامل متعدد الطبقات
    يرجع dict فيه:
      verdict:   SAFE | WARNING | DANGER | CRITICAL
      dangers:   [(وصف, مستوى)]
      warnings:  [وصف]
      entropy:   float
      hash_md5:  str
      imports:   [str]
      to_install:[str]
      score:     int  (0=آمن, كلما ارتفع كلما زاد الخطر)
    """
    result = {
        "verdict":    "SAFE",
        "dangers":    [],
        "warnings":   [],
        "entropy":    0.0,
        "hash_md5":   "",
        "imports":    [],
        "to_install": [],
        "score":      0,
        "layers":     [],  # طبقات الفحص اللي اتنفذت
    }

    try:
        if raw is None:
            with open(path, "rb") as f:
                raw = f.read()

        content = raw.decode("utf-8", errors="replace")
        ext = os.path.splitext(path)[1].lower()

        # ── طبقة 1: فحص Hash ─────────────────────────────────
        result["layers"].append("Hash Check")
        is_known, hash_val = _hash_check(raw)
        result["hash_md5"] = hash_val
        if is_known:
            result["dangers"].append((hash_val, SEV_CRITICAL))
            result["score"] += 100

        # ── طبقة 2: Shannon Entropy ──────────────────────────
        result["layers"].append("Entropy Analysis")
        entropy = _entropy_check(content)
        result["entropy"] = entropy
        if entropy > 6.5:
            result["warnings"].append(f"Entropy عالي ({entropy}) — كود مشفر/مضغوط محتمل")
            result["score"] += 15
        if entropy > 7.2:
            result["dangers"].append((f"Entropy خطير ({entropy}) — Packed/Obfuscated", SEV_HIGH))
            result["score"] += 25

        # ── طبقة 3: Regex Pattern Matching ───────────────────
        result["layers"].append("Pattern Matching (YARA-style)")
        for pattern, desc, severity in DANGER_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                result["dangers"].append((desc, severity))
                result["score"] += {"CRITICAL": 50, "HIGH": 25, "MEDIUM": 10}.get(severity, 5)

        # ── طبقة 4: AST Analysis (Python فقط) ────────────────
        if ext == ".py":
            result["layers"].append("AST Deep Analysis")
            ast_issues = _ast_deep_scan(content)
            for desc, severity in ast_issues:
                result["dangers"].append((desc, severity))
                result["score"] += {"CRITICAL": 50, "HIGH": 25, "MEDIUM": 10}.get(severity, 5)

        # ── طبقة 5: فحص الـ Imports ──────────────────────────
        result["layers"].append("Import Scanner")
        imports = set()
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            m = re.match(r'^import\s+([\w]+)', stripped)
            if m: imports.add(m.group(1))
            m = re.match(r'^from\s+([\w]+)', stripped)
            if m: imports.add(m.group(1))

        result["imports"] = sorted(imports - BUILTIN)

        # مكاتب خطيرة بذاتها
        DANGEROUS_IMPORTS = {
            "pynput":    ("Keylogger library", SEV_HIGH),
            "pyHook":    ("Keylogger library", SEV_HIGH),
            "win32api":  ("Windows API مشبوه", SEV_MEDIUM),
            "win32con":  ("Windows API مشبوه", SEV_MEDIUM),
            "ctypes":    ("مكتبة ctypes — قد تُستخدم لـ Injection", SEV_MEDIUM),
            "mss":       ("لقطات شاشة", SEV_MEDIUM),
        }
        for imp in imports:
            if imp in DANGEROUS_IMPORTS:
                desc, sev = DANGEROUS_IMPORTS[imp]
                result["dangers"].append((f"استيراد {imp}: {desc}", sev))
                result["score"] += {"CRITICAL": 50, "HIGH": 25, "MEDIUM": 10}.get(sev, 5)

        # مكاتب محتاجة تثبيت
        to_install = []
        for imp in imports:
            if imp in BUILTIN: continue
            if imp in IMPORT_MAP:
                for p in IMPORT_MAP[imp].split():
                    if not _is_installed(p): to_install.append(p)
            else:
                if not _is_installed(imp): to_install.append(imp)
        result["to_install"] = list(dict.fromkeys(to_install))

        # ── طبقة 6: فحص الـ URLs المشبوهة ────────────────────
        result["layers"].append("URL Scanner")
        urls = re.findall(r'https?://[^\s\'"]+', content)
        SUSPICIOUS_DOMAINS = ["pastebin.com","hastebin","ngrok","serveo","raw.githubusercontent.com/suspicious"]
        for url in urls:
            for d in SUSPICIOUS_DOMAINS:
                if d in url:
                    result["warnings"].append(f"URL مشبوه: {url[:60]}")
                    result["score"] += 8
                    break

        # ── تحديد الحكم النهائي ───────────────────────────────
        critical_found = any(s == SEV_CRITICAL for _, s in result["dangers"])
        high_found     = any(s == SEV_HIGH     for _, s in result["dangers"])

        if critical_found or result["score"] >= 50:
            result["verdict"] = "CRITICAL"
        elif high_found or result["score"] >= 25:
            result["verdict"] = "DANGER"
        elif result["warnings"] or result["score"] >= 10:
            result["verdict"] = "WARNING"
        else:
            result["verdict"] = "SAFE"

    except Exception as e:
        result["warnings"].append(f"خطأ في الفحص: {e}")
        result["verdict"] = "WARNING"

    return result


# ── نظام التحذيرات والحظر التلقائي ─────────────────────────
def handle_security_violation(uid: str, fname: str, result: dict, chat_id: int) -> bool:
    """
    يعالج الملف الخطير:
    - CRITICAL → حظر فوري
    - DANGER   → تحذير، بعد MAX_WARNINGS حظر
    يرجع True لو تم الحظر أو الرفض، False لو تجاوز
    """
    verdict  = result["verdict"]
    dangers  = result["dangers"]
    score    = result["score"]
    name     = db["users"].get(uid, {}).get("name", "؟")
    role_e   = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤"}.get(get_role(uid),"👤")

    # ── بناء قائمة الأنماط الخطيرة ──────────────────────────
    danger_lines = ""
    for desc, sev in dangers[:8]:
        icon = "🔴" if sev == SEV_CRITICAL else "🟠" if sev == SEV_HIGH else "🟡"
        danger_lines += f"  {icon} {desc}\n"

    # ── إشعار الأدمن دائماً ──────────────────────────────────
    mk_admin = types.InlineKeyboardMarkup(row_width=2)
    mk_admin.add(
        types.InlineKeyboardButton("✅ موافقة استثنائية", callback_data=f"qapprove_{fname}"),
        types.InlineKeyboardButton("🗑 حذف فوري",         callback_data=f"qdelete_{fname}"),
        types.InlineKeyboardButton("🚫 حظر المستخدم",    callback_data=f"uact_{uid}_ban"),
        types.InlineKeyboardButton("👤 ملف المستخدم",    callback_data=f"uview_{uid}"),
    )
    sev_icon = "🚨" if verdict == "CRITICAL" else "⚠️"
    safe_send(ADMIN_ID,
        f"{sev_icon} *تهديد أمني — {verdict}*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📄 الملف: `{fname}`\n"
        f"{role_e} المستخدم: *{name}* | 🆔 `{uid}`\n"
        f"🎯 نقاط الخطر: `{score}`\n"
        f"🔬 طبقات الفحص: `{len(result['layers'])}`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⛔ *الأنماط الخطيرة:*\n{danger_lines}", reply_markup=mk_admin)

    # ── CRITICAL → حظر فوري ─────────────────────────────────
    if verdict == "CRITICAL":
        add_to_blacklist(uid)
        if uid in db["users"]: db["users"][uid]["role"] = "banned"
        save()
        sec_log(uid, f"حظر فوري — ملف CRITICAL: {fname}", "critical", fname)
        INTRUSION_SCORE[uid] = MAX_INTRUSION + 1

        safe_send(chat_id,
            f"🚫 *رُفض — حظر فوري*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⛔ *أنماط خطيرة جداً:*\n{danger_lines}\n"
            f"📄 الملف: `{fname}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔒 تم حظرك تلقائياً بسبب رفع ملف خطير للغاية.")
        return True

    # ── DANGER → نظام التحذيرات (1 → 2 → 3 → حظر فوري) ────────
    if uid not in warning_count:
        warning_count[uid] = 0

    warning_count[uid] += 1
    current = warning_count[uid]

    if current >= MAX_WARNINGS:
        # وصل الحد → حظر فوري على الفور
        warning_count.pop(uid, None)
        add_to_blacklist(uid)
        if uid in db["users"]: db["users"][uid]["role"] = "banned"
        save()
        sec_log(uid, f"حظر تلقائي — استنفد {MAX_WARNINGS} تحذيرات", "critical", fname)
        INTRUSION_SCORE[uid] = MAX_INTRUSION + 1

        safe_send(chat_id,
            f"🚫 *رُفض — حظر فوري*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⛔ *الأنماط الخطيرة:*\n{danger_lines}\n"
            f"📄 الملف: `{fname}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔴 تحذير {current}/{MAX_WARNINGS} — استنفدت كل تحذيراتك.\n"
            f"🔒 *تم حظرك نهائياً من البوت.*")
        try:
            safe_send(ADMIN_ID,
                f"🔒 *حظر تلقائي فوري*\n"
                f"{role_e} *{name}* | 🆔 `{uid}`\n"
                f"📄 آخر ملف: `{fname}`\n"
                f"🎯 استنفد {MAX_WARNINGS} تحذيرات")
        except: pass
        return True

    else:
        # تحذير مع عداد تصاعدي واضح
        filled  = "🟥" * current
        empty   = "⬜" * (MAX_WARNINGS - current)
        bar     = filled + empty
        left    = MAX_WARNINGS - current
        left_txt = f"تحذير{'ات' if left > 1 else ''} واحدة أخرى ستُحظر فوراً!" if left == 1 else f"بعد {left} تحذيرات ستُحظر فوراً"

        safe_send(chat_id,
            f"🚫 *رُفض — حظر فوري*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⛔ *أنماط خطيرة:*\n{danger_lines}\n"
            f"📄 الملف: `{fname}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *تحذير {current}/{MAX_WARNINGS}* {bar}\n"
            f"{'⚡ آخر تحذير! ' if left == 1 else ''}{left_txt}")
        return True

    return False


# ── الاحتفاظ بـ scan_file القديمة للتوافق ──────────────────
def scan_file(path: str) -> dict:
    """wrapper للتوافق مع الكود القديم"""
    result = deep_scan_file(path)
    # تحويل للصيغة القديمة
    old_format = {
        "safe":       result["verdict"] == "SAFE",
        "warnings":   result["warnings"],
        "danger":     [d for d, _ in result["dangers"]],
        "imports":    result["imports"],
        "to_install": result["to_install"],
    }
    return old_format



# ── خريطة شاملة للمكاتب مع الإصدارات الصحيحة ──
IMPORT_MAP = {
    # تليجرام
    "telegram":       "python-telegram-bot==21.3",
    "telebot":        "pyTelegramBotAPI",
    "aiogram":        "aiogram==3.7.0",
    "telethon":       "telethon",
    "pyrogram":       "pyrogram tgcrypto",
    # HTTP
    "requests":       "requests",
    "aiohttp":        "aiohttp",
    "httpx":          "httpx==0.27.2",
    "urllib3":        "urllib3",
    "httplib2":       "httplib2",
    "websocket":      "websocket-client",
    "websockets":     "websockets",
    # ويب
    "flask":          "flask",
    "fastapi":        "fastapi uvicorn",
    "django":         "django",
    "starlette":      "starlette",
    "tornado":        "tornado",
    "quart":          "quart",
    "sanic":          "sanic",
    # قواعد بيانات
    "sqlalchemy":     "sqlalchemy",
    "aiosqlite":      "aiosqlite",
    "pymongo":        "pymongo",
    "motor":          "motor",
    "redis":          "redis",
    "aioredis":       "aioredis",
    "peewee":         "peewee",
    "tortoise":       "tortoise-orm",
    "databases":      "databases",
    # بيانات
    "numpy":          "numpy",
    "pandas":         "pandas",
    "scipy":          "scipy",
    "sklearn":        "scikit-learn",
    "matplotlib":     "matplotlib",
    "seaborn":        "seaborn",
    "plotly":         "plotly",
    # صور
    "PIL":            "Pillow",
    "cv2":            "opencv-python",
    "skimage":        "scikit-image",
    "imageio":        "imageio",
    # أدوات
    "dotenv":         "python-dotenv",
    "apscheduler":    "apscheduler",
    "bs4":            "beautifulsoup4",
    "lxml":           "lxml",
    "html5lib":       "html5lib",
    "loguru":         "loguru",
    "colorama":       "colorama",
    "psutil":         "psutil",
    "cryptography":   "cryptography",
    "nacl":           "PyNaCl",
    "jwt":            "PyJWT",
    "yaml":           "pyyaml",
    "toml":           "toml",
    "qrcode":         "qrcode",
    "barcode":        "python-barcode",
    "gtts":           "gTTS",
    "pydub":          "pydub",
    "schedule":       "schedule",
    "pytz":           "pytz",
    "dateutil":       "python-dateutil",
    "tqdm":           "tqdm",
    "rich":           "rich",
    "click":          "click",
    "typer":          "typer",
    "pydantic":       "pydantic",
    "attrs":          "attrs",
    "cachetools":     "cachetools",
    "aiofiles":       "aiofiles",
    "anyio":          "anyio",
    "trio":           "trio",
    "uvloop":         "uvloop",
    "paramiko":       "paramiko",
    "fabric":         "fabric",
    "boto3":          "boto3",
    "google":         "google-api-python-client",
    "tweepy":         "tweepy",
    "discord":        "discord.py",
    "slack_sdk":      "slack-sdk",
    "stripe":         "stripe",
    "paypalrestsdk":  "paypalrestsdk",
    "jwt":            "PyJWT",
    "passlib":        "passlib",
    "bcrypt":         "bcrypt",
    "arrow":          "arrow",
    "humanize":       "humanize",
    "emoji":          "emoji",
    "translate":      "translate",
    "deep_translator":"deep-translator",
    "googletrans":    "googletrans==4.0.0rc1",
    "openai":         "openai",
    "anthropic":      "anthropic",
    "groq":           "groq",
    "cohere":         "cohere",
    "transformers":   "transformers",
    "torch":          "torch",
    "tensorflow":     "tensorflow",
    "keras":          "keras",
    "celery":         "celery",
    "kombu":          "kombu",
    "pika":           "pika",
    "kafka":          "kafka-python",
    "nats":           "nats-py",
    "socketio":       "python-socketio",
    "pyserial":       "pyserial",
    "serial":         "pyserial",
    "RPi":            "RPi.GPIO",
}

BUILTIN = {
    "os","sys","re","json","time","math","random","string","hashlib","logging",
    "sqlite3","threading","traceback","io","datetime","collections","functools",
    "typing","pathlib","shutil","subprocess","asyncio","abc","copy","enum","gc",
    "glob","gzip","inspect","itertools","operator","pickle","platform","queue",
    "signal","socket","struct","tempfile","textwrap","urllib","uuid","warnings",
    "weakref","zipfile","base64","csv","html","http","email","concurrent",
    "contextlib","dataclasses","decimal","difflib","fractions","heapq","hmac",
    "ipaddress","keyword","locale","mimetypes","numbers","pprint","secrets",
    "stat","statistics","tarfile","types","builtins","__future__","argparse",
    "configparser","getpass","getopt","optparse","unittest","doctest","pdb",
    "profile","timeit","cProfile","dis","ast","tokenize","token","compileall",
    "py_compile","importlib","pkgutil","zipimport","site","code","codeop",
    "pprint","reprlib","textwrap","unicodedata","stringprep","readline","rlcompleter",
    "struct","codecs","io","abc","numbers","cmath","decimal","fractions","random",
    "statistics","array","queue","types","copy","pprint","enum","graphlib",
}

def _is_installed(pkg:str) -> bool:
    """تحقق هل المكتبة متثبتة أصلاً"""
    import importlib.util
    name = pkg.split("==")[0].split(">=")[0].split("<=")[0]
    # تحويل اسم pip لاسم import
    pip_to_import = {
        "pyTelegramBotAPI":"telebot", "python-telegram-bot":"telegram",
        "Pillow":"PIL", "beautifulsoup4":"bs4", "python-dotenv":"dotenv",
        "scikit-learn":"sklearn", "opencv-python":"cv2", "PyJWT":"jwt",
        "pyyaml":"yaml", "gTTS":"gtts", "python-dateutil":"dateutil",
        "aioredis":"aioredis",
    }
    import_name = pip_to_import.get(name, name.replace("-","_"))
    try:
        return importlib.util.find_spec(import_name) is not None
    except: return False

def scan_file(path:str) -> dict:
    """فحص ذكي للملف — يكتشف المكاتب ويتحقق من الأمان"""
    result = {"safe":True, "warnings":[], "danger":[], "imports":[], "to_install":[]}
    try:
        with open(path,'r',encoding='utf-8',errors='replace') as f:
            content = f.read()

        # ── فحص الأمان (أنماط الخطر الحقيقي فقط) ──
        for pattern, desc in DANGER_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE|re.DOTALL):
                result["danger"].append(desc)
                result["safe"] = False

        # ── استخراج المكاتب بطريقة أذكى ──
        imports = set()
        for line in content.splitlines():
            stripped = line.strip()
            # تجاهل التعليقات
            if stripped.startswith("#"): continue
            # import x / import x.y
            m = re.match(r'^import\s+([\w]+)', stripped)
            if m: imports.add(m.group(1))
            # from x import y
            m = re.match(r'^from\s+([\w]+)', stripped)
            if m: imports.add(m.group(1))

        result["imports"] = sorted(imports - BUILTIN)

        # ── تحديد اللي محتاج تثبيت ──
        to_install = []
        for imp in imports:
            if imp in BUILTIN: continue
            if imp in IMPORT_MAP:
                pkgs = IMPORT_MAP[imp].split()
                for p in pkgs:
                    if not _is_installed(p):
                        to_install.append(p)
            else:
                # اسم غير معروف → جرّب بنفس الاسم لو مش متثبت
                if not _is_installed(imp):
                    to_install.append(imp)

        result["to_install"] = list(dict.fromkeys(to_install))  # بدون تكرار

    except Exception as e:
        result["warnings"].append(f"خطأ في الفحص: {e}")
    return result

def check_bot_config(path:str) -> dict:
    """فحص وجود التوكن والأدمن ID في ملف البوت"""
    result = {
        "has_token":   False,
        "has_admin":   False,
        "token_val":   None,
        "admin_val":   None,
        "token_type":  None,  # hardcoded / env
        "admin_type":  None,
        "warnings":    [],
        "suggestions": [],
    }
    try:
        with open(path,'r',encoding='utf-8',errors='replace') as f:
            content = f.read()

        # ── فحص التوكن ──────────────────────────────
        # Hardcoded token مثل "123456:ABC..."
        tok_match = re.search(r'["\'](\d{8,10}:[A-Za-z0-9_-]{35,})["\']', content)
        if tok_match:
            result["has_token"]  = True
            result["token_type"] = "hardcoded"
            result["token_val"]  = tok_match.group(1)[:20] + "..."
        # env مثل os.environ.get("BOT_TOKEN") أو os.getenv("TOKEN")
        elif re.search(r'(os\.environ|os\.getenv|environ\.get).*["\'][A-Z_]*TOKEN[A-Z_]*["\']', content, re.IGNORECASE):
            result["has_token"]  = True
            result["token_type"] = "env"
            result["token_val"]  = "من متغيرات البيئة"
        else:
            result["warnings"].append("❌ مفيش توكن — ابحث عن TOKEN في الكود وحطه")
            result["suggestions"].append("TOKEN = 'توكنك من @BotFather'")

        # ── فحص الأدمن ID ────────────────────────────
        admin_match = re.search(r'(ADMIN|OWNER|MASTER|admin_id|owner_id)\s*=\s*["\']?(\d{5,12})["\']?', content, re.IGNORECASE)
        if admin_match:
            result["has_admin"]  = True
            result["admin_type"] = "hardcoded"
            result["admin_val"]  = admin_match.group(2)
        elif re.search(r'(os\.environ|os\.getenv|environ\.get).*["\'][A-Z_]*(?:ADMIN|OWNER|MASTER)[A-Z_]*["\']', content, re.IGNORECASE):
            result["has_admin"]  = True
            result["admin_type"] = "env"
            result["admin_val"]  = "من متغيرات البيئة"
        else:
            result["warnings"].append("❌ مفيش ADMIN_ID — حط ID الأدمن في الكود")
            result["suggestions"].append("ADMIN_ID = رقمك (اكتب /id للبوت تعرفه)")

        # ── تحقق من صحة التوكن شكلاً ─────────────────
        if result["token_type"] == "hardcoded" and tok_match:
            tok = tok_match.group(1)
            if not re.match(r'^\d{8,10}:[A-Za-z0-9_-]{35,}$', tok):
                result["warnings"].append("⚠️ التوكن شكله غلط — تأكد منه من @BotFather")

    except Exception as e:
        result["warnings"].append(f"خطأ في الفحص: {e}")
    return result

# ══════════════════════════════════════════════════════════════
#  تثبيت المكاتب
# ══════════════════════════════════════════════════════════════
def install_pkgs(pkgs:list, chat_id:int=None) -> bool:
    if not pkgs: return True
    try:
        pkgs_txt = " ".join(pkgs)
        if chat_id: safe_send(chat_id, f"📦 جارٍ تثبيت {len(pkgs)} مكتبة...")
        r = subprocess.run([sys.executable,"-m","pip","install"]+pkgs+["--quiet"],
                           capture_output=True, text=True, timeout=300)
        if r.returncode == 0:
            if chat_id: safe_send(chat_id, f"✅ تم تثبيت {len(pkgs)} مكتبة بنجاح!")
            return True
        else:
            # استخراج المكاتب اللي فشلت فقط
            out = (r.stdout+r.stderr).strip()
            failed = re.findall(r"Failed building wheel for ([\w\-]+)", out)
            failed_txt = " | ".join(failed) if failed else "بعض المكاتب"
            if chat_id:
                safe_send(chat_id,
                    f"⚠️ فشل تثبيت: {failed_txt}\n"
                    f"السبب: محتاج C compiler غير متاح على السيرفر.\n"
                    f"الباقي اتثبّت بنجاح ✅")
            return False
    except subprocess.TimeoutExpired:
        if chat_id: safe_send(chat_id, "⏱ انتهى وقت التثبيت (5 دقايق)")
        return False
    except Exception as e:
        if chat_id: safe_send(chat_id, f"❌ خطأ: {e}")
        return False

def install_req_file(path:str, chat_id:int=None) -> bool:
    try:
        if chat_id: safe_send(chat_id, "📦 جارٍ تثبيت المكاتب من الملف...")
        r = subprocess.run([sys.executable,"-m","pip","install","-r",path,"--quiet"],
                           capture_output=True, text=True, timeout=180)
        if r.returncode == 0:
            if chat_id: safe_send(chat_id, "✅ تم التثبيت!")
            return True
        else:
            out = (r.stdout+r.stderr).strip()
            if chat_id: safe_send(chat_id, f"⚠️ خطأ:\n\n{out[-1500:]}\n")
            return False
    except: return False

# ══════════════════════════════════════════════════════════════
#  تشغيل الملفات
# ══════════════════════════════════════════════════════════════
running_procs   = {}
restart_threads = {}

def launch(path:str, name:str=None):
    try:
        ext     = os.path.splitext(path)[1].lower()
        log_out = open(f"LOGS/{os.path.basename(path)}.log","w",encoding="utf-8")
        env     = os.environ.copy()
        env["PATH"] = "/opt/node/bin:" + env.get("PATH","")
        if name and name in db.get("envs",{}): env.update(db["envs"][name])
        # نسخ data.json لنفس مجلد الملف لو موجود
        file_dir = os.path.dirname(os.path.abspath(path))
        for extra in ["data.json","config.json",".env"]:
            for loc in [".", "ELITE_HOST"]:
                src = os.path.join(loc, extra)
                dst = os.path.join(file_dir, extra)
                if os.path.exists(src) and src != dst:
                    try: shutil.copy2(src, dst)
                    except: pass
        # اكتشاف node تلقائياً
        node_bin = "/opt/node/bin/node"
        if not os.path.exists(node_bin):
            node_bin = shutil.which("node") or "node"
        cmds    = {".py":[sys.executable,path], ".js":[node_bin,path], ".sh":["bash",path]}
        if ext not in cmds: return None
        if ext == ".sh": os.chmod(path, 0o755)
        proc = subprocess.Popen(cmds[ext], start_new_session=True,
                                stdout=log_out, stderr=subprocess.STDOUT, env=env)
        info = {"proc":proc, "pid":proc.pid, "started":time.time()}
        if name:
            running_procs[name] = info
            if name in db["files"]:
                db["files"][name]["active"] = True; save()
                # إشعار صاحب الملف
                owner = db["files"][name].get("owner","")
                if owner and owner != str(ADMIN_ID):
                    try:
                        bot.send_message(int(owner),
                            f"▶️ ملفك `{name}` بدأ التشغيل ✅\n"
                            f"🕐 {datetime.now().strftime('%H:%M:%S')}")
                    except: pass
        log.info(f"Launch: {path} PID:{proc.pid}")
        return proc
    except Exception as e:
        log.error(f"Launch error: {e}"); return None

def stop_file(name:str):
    info = running_procs.pop(name, None)
    if info:
        pid = info.get("pid")
        try:
            import signal
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except:
            try: os.kill(pid, 9)
            except:
                try: info["proc"].kill()
                except: pass
        # تأكد إن العملية ماتت فعلاً
        try:
            import psutil as _ps
            p = _ps.Process(pid)
            p.wait(timeout=3)
        except: pass
    if name in db["files"]:
        db["files"][name]["active"] = False
        save()
        # إشعار صاحب الملف
        owner = db["files"][name].get("owner","")
        if owner and owner != str(ADMIN_ID):
            try:
                bot.send_message(int(owner),
                    f"⏹ ملفك `{name}` توقف\n"
                    f"🕐 {datetime.now().strftime('%H:%M:%S')}")
            except: pass

def kill_all_procs():
    """إيقاف كل العمليات بالقوة"""
    import signal
    killed = 0
    # من القائمة المعروفة
    for name in list(running_procs.keys()):
        stop_file(name)
        killed += 1
    # فحص أي عملية من ELITE_HOST مش في القائمة
    try:
        for proc in psutil.process_iter(['pid','cmdline']):
            try:
                cmd = " ".join(proc.info['cmdline'] or [])
                if "ELITE_HOST" in cmd and proc.pid != os.getpid():
                    os.kill(proc.pid, signal.SIGKILL)
                    killed += 1
            except: pass
    except: pass
    return killed

def auto_restart_watcher(name:str, path:str):
    while True:
        time.sleep(5)
        if name not in db["files"]: break
        if not db["files"][name].get("auto_restart"): break
        if not db["files"][name].get("active"): break
        info = running_procs.get(name)
        if info and info["proc"].poll() is not None:
            db["stats"]["restarts"] = db["stats"].get("restarts",0)+1; save()
            launch(path, name)
            try: safe_send(ADMIN_ID, f"🔁 إعادة تشغيل تلقائية: {name}")
            except: pass

def enable_ar(name:str, path:str):
    if name in restart_threads and restart_threads[name].is_alive(): return
    t = threading.Thread(target=auto_restart_watcher, args=(name,path), daemon=True)
    t.start(); restart_threads[name] = t

# ══════════════════════════════════════════════════════════════
#  المجدول
# ══════════════════════════════════════════════════════════════
def scheduler():
    while True:
        time.sleep(30)
        for task in list(db.get("scheduled",[])):
            try:
                if not task.get("done") and datetime.now() >= datetime.strptime(task["run_at"],"%Y-%m-%d %H:%M"):
                    if task["name"] in db["files"]:
                        launch(db["files"][task["name"]]["path"], task["name"])
                        task["done"] = True; save()
                        safe_send(ADMIN_ID, f"⏰ نُفِّذت: {task['name']}")
            except: pass

threading.Thread(target=scheduler, daemon=True).start()

# ── باك أب تلقائي كل 6 ساعات ────────────────────────────────
def auto_backup():
    while True:
        time.sleep(6 * 3600)
        try:
            if os.path.exists(DB_FILE):
                with open(DB_FILE,'rb') as f:
                    bot.send_document(ADMIN_ID, f,
                        caption=f"💾 *باك أب تلقائي*\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        except: pass

threading.Thread(target=auto_backup, daemon=True).start()

# ── تقرير يومي ────────────────────────────────────────────────
def daily_report():
    while True:
        time.sleep(60)
        try:
            now = datetime.now().strftime('%H:%M')
            if now == db.get("daily_report_time","08:00"):
                s = db["stats"]
                roles = {}
                for u,info in db["users"].items():
                    roles[info.get("role","user")] = roles.get(info.get("role","user"),0)+1
                mem  = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                report = (
                    f"📊 *التقرير اليومي — {datetime.now().strftime('%Y-%m-%d')}*\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"👥 المستخدمون: `{len(db['users'])}`\n"
                    f"  ├ ⭐ VIP: `{roles.get('vip',0)}`\n"
                    f"  └ 👤 عادي: `{roles.get('user',0)}`\n\n"
                    f"📂 الملفات: `{len(db['files'])}` | ⚡ شغّالة: `{len(running_procs)}`\n"
                    f"📤 رفعات: `{s.get('uploads',0)}` | 🔁 إعادات: `{s.get('restarts',0)}`\n\n"
                    f"💻 CPU: `{psutil.cpu_percent()}%` | RAM: `{mem.percent}%` | Disk: `{disk.percent}%`"
                )
                for admin in ADMIN_IDS:
                    try: safe_send(admin, report)
                    except: pass
                time.sleep(61)
        except Exception as e:
            log.error(f"Daily report: {e}")

threading.Thread(target=daily_report, daemon=True).start()

# ── مراقب الكراشات ────────────────────────────────────────────
def crash_watcher():
    notified = set()
    while True:
        time.sleep(10)
        try:
            for name, info in list(running_procs.items()):
                if info["proc"].poll() is not None and name not in notified:
                    notified.add(name)
                    owner = db["files"].get(name,{}).get("owner")
                    if name in db["files"]:
                        db["files"][name]["crashes"] = db["files"][name].get("crashes",0)+1
                        db["files"][name]["active"]  = False
                        save()
                    for admin in ADMIN_IDS:
                        try: safe_send(admin, f"💥 توقف: {name}")
                        except: pass
                    if owner and owner not in [str(a) for a in ADMIN_IDS]:
                        try:
                            bot.send_message(int(owner),
                                f"⚠️ ملفك توقف: {name}\n"
                                f"اضغط ▶️ تشغيل ملف لإعادة تشغيله")
                        except: pass
            notified &= set(running_procs.keys())
        except Exception as e:
            log.error(f"Crash watcher: {e}")

threading.Thread(target=crash_watcher, daemon=True).start()

# ══════════════════════════════════════════════════════════════
#  نظام الإشعارات المتقدم
# ══════════════════════════════════════════════════════════════
def notify_all(msg:str, role_filter:str=None):
    """إرسال إشعار لكل المستخدمين أو فئة معينة"""
    count = 0
    for u, info in list(db["users"].items()):
        if role_filter and info.get("role") != role_filter: continue
        try:
            bot.send_message(int(u), msg)
            count += 1; time.sleep(0.05)
        except: pass
    return count

def send_alert(uid:str, msg:str, level:str="info"):
    icons = {"info":"ℹ️","warn":"⚠️","error":"🔴","success":"✅"}
    try: safe_send(int(uid), f"{icons.get(level,'ℹ️')} {msg}")
    except: pass

# ══════════════════════════════════════════════════════════════
#  نظام تذاكر الدعم
# ══════════════════════════════════════════════════════════════
def open_ticket(uid:str, msg:str) -> str:
    tid = "T" + str(int(time.time()))[-8:]
    db["tickets"][tid] = {
        "uid":     uid,
        "msg":     msg,
        "status":  "open",
        "replies": [],
        "created": datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    db["stats"]["tickets_opened"] = db["stats"].get("tickets_opened",0)+1
    save()
    name      = db["users"].get(uid,{}).get("name","؟")
    role      = get_role(uid)
    role_e    = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤"}.get(role,"👤")
    # عدد تذاكر المستخدم
    user_tix  = sum(1 for t in db["tickets"].values() if t.get("uid")==uid)
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton(f"📩 رد", callback_data=f"treply_{tid}"),
        types.InlineKeyboardButton(f"✅ إغلاق", callback_data=f"tclose_{tid}"),
        types.InlineKeyboardButton(f"👤 ملف المستخدم", callback_data=f"uview_{uid}"),
    )
    for admin in ADMIN_IDS:
        try:
            safe_send(admin,
                f"🎫 تذكرة جديدة — #{tid}\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"{role_e} {name} | ID: {uid}\n"
                f"📊 تذاكره السابقة: {user_tix}\n"
                f"🕐 {db['tickets'][tid]['created']}\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"📝 {msg[:500]}",
                reply_markup=mk)
        except: pass
    return tid

# ══════════════════════════════════════════════════════════════
#  نظام إصدارات الملفات
# ══════════════════════════════════════════════════════════════
def save_file_version(fname:str, path:str):
    """احتفظ بنسخة قديمة من الملف قبل الاستبدال"""
    if not os.path.exists(path): return
    os.makedirs("BACKUPS/versions", exist_ok=True)
    ts  = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = f"BACKUPS/versions/{fname}_{ts}"
    try:
        shutil.copy2(path, dst)
        versions = db["file_versions"].setdefault(fname, [])
        versions.append({"path":dst,"time":ts})
        if len(versions) > 5: # احتفظ بآخر 5 نسخ بس
            old = versions.pop(0)
            try: os.remove(old["path"])
            except: pass
        save()
    except: pass

# ══════════════════════════════════════════════════════════════
#  Blacklist
# ══════════════════════════════════════════════════════════════
def is_blacklisted(uid:str) -> bool:
    return uid in db.get("blacklist",[])

def add_to_blacklist(uid:str):
    bl = db.setdefault("blacklist",[])
    if uid not in bl: bl.append(uid); save()

def remove_from_blacklist(uid:str):
    bl = db.get("blacklist",[])
    if uid in bl: bl.remove(uid); save()
    while True:
        time.sleep(60)
        dead = []
        for name, info in list(running_procs.items()):
            try:
                p = psutil.Process(info["pid"])
                # لو العملية أكلت أكتر من 90% RAM → تحذير
                if p.memory_percent() > 90:
                    safe_send(ADMIN_ID,
                        f"⚠️ *تحذير RAM!*\n`{name}` بيستخدم `{p.memory_percent():.1f}%` من الذاكرة!")
            except psutil.NoSuchProcess:
                dead.append(name)
        for name in dead:
            if name in running_procs:
                running_procs.pop(name)
                if name in db["files"]:
                    db["files"][name]["active"] = False; save()

threading.Thread(target=health_monitor, daemon=True).start()

# ══════════════════════════════════════════════════════════════
#  لوحات المفاتيح
# ══════════════════════════════════════════════════════════════
def kb_owner():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    m.add(
        # ─── قسم الرفع والاستضافة ───────────
        "📦 قسم الرفع",
        # ─── قسم الأدمن ──────────────────────
        "👑 قسم الأدمن",
        # ─── قسم السيرفر ─────────────────────
        "🖥 قسم السيرفر",
        # ─── قسم المستخدمين ──────────────────
        "👥 قسم المستخدمين",
        # ─── قسم التواصل ─────────────────────
        "💬 قسم التواصل",
        # ─── قسم الأدوات ─────────────────────
        "🔧 قسم الأدوات",
    )
    return m

def kb_admin():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    m.add(
        "📦 قسم الرفع",
        "🖥 قسم السيرفر",
        "👥 قسم المستخدمين",
        "💬 قسم التواصل",
        "🔧 قسم الأدوات",
    )
    return m

def kb_vip():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        "📂 ملفاتي",         "📊 إحصائياتي",
        "▶️ تشغيل ملف",      "⏹ إيقاف ملف",
        "🔎 فحص ملف",        "📋 لوج ملفاتي",
        "🤖 ذكاء اصطناعي",   "🎫 تذكرة دعم",
        "💬 تواصل مع الأدمن", "⭐ مميزات VIP",
        "🔑 توليد كلمة سر",  "ℹ️ مساعدة",
    )
    return m

def kb_user():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        "📂 ملفاتي",         "📊 إحصائياتي",
        "▶️ تشغيل ملف",      "⏹ إيقاف ملف",
        "🔎 فحص ملف",        "📋 لوج ملفاتي",
        "🤖 ذكاء اصطناعي",   "🎫 تذكرة دعم",
        "💬 تواصل مع الأدمن", "🔑 توليد كلمة سر",
        "ℹ️ مساعدة",
    )
    return m

# ─── لوحات الأقسام ──────────────────────────────────────────

def kb_section_upload():
    """📦 قسم الرفع والاستضافة"""
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    m.add(
        "🖥 الاستضافة",       "⚙️ الحاويات",       "📁 الملفات",
        "▶️ تشغيل ملف",       "⏹ إيقاف ملف",      "🔄 إعادة تشغيل ملف",
        "🔎 فحص ملف",         "📦 تثبيت مكاتب",    "📜 إصدارات الملفات",
        "🚨 الحجر الصحي",     "⏰ المجدولة",        "🔃 إعادة تشغيل الكل",
        "💀 إيقاف الكل",      "🧹 تطهير",
        "🔙 الرئيسية",
    )
    return m

def kb_section_admin():
    """👑 قسم الأدمن"""
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    m.add(
        "🔐 لوحة الأدمن",     "⚙️ الإعدادات",      "🔒 قفل البوت",
        "🔄 تحديث البوت",     "💾 باك أب",          "📌 تثبيت رسالة",
        "🛡 لوحة الأمان",     "🚫 القائمة السوداء", "📡 المشبوهون",
        "🛡 أمان الملفات",    "🎫 التذاكر",         "📢 بث رسالة",
        "📣 إشعار عام",       "⚡ تسريع",
        "🔙 الرئيسية",
    )
    return m

def kb_section_server():
    """🖥 قسم السيرفر"""
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    m.add(
        "📡 موارد السيرفر",   "🔍 مراقبة العمليات", "📊 الإحصائيات",
        "📋 السجلات",          "🌡 درجة CPU",        "🕐 وقت التشغيل",
        "📋 نسخ السجل",       "🗑 مسح السجلات",     "📈 تقرير فوري",
        "🌐 فحص IP",          "🤖 ذكاء اصطناعي",
        "🔙 الرئيسية",
    )
    return m

def kb_section_users():
    """👥 قسم المستخدمين"""
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    m.add(
        "👥 المستخدمون",      "🔎 بحث مستخدم",     "🏆 المتصدرون",
        "📜 إصدارات الملفات", "📝 ملاحظات",         "📊 إحصائيات المستخدمين",
        "🔙 الرئيسية",
    )
    return m

def kb_section_chat():
    """💬 قسم التواصل"""
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        "📬 صندوق الرسائل",           "💬 محادثة مستخدم",
        "🔕 المحظورون من التواصل",    "🎫 التذاكر",
        "📢 بث رسالة",                "📣 إشعار عام",
        "🔙 الرئيسية",
    )
    return m

def kb_section_tools():
    """🔧 قسم الأدوات"""
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    m.add(
        "🖥️ Shell",           "🔑 توليد كلمة سر",  "📝 ملاحظات",
        "🌐 فحص IP",          "⚡ تسريع",           "🕐 وقت التشغيل",
        "🔑 توليد كلمة سر",  "📌 تثبيت رسالة",    "🤖 ذكاء اصطناعي",
        "ℹ️ مساعدة",
        "🔙 الرئيسية",
    )
    return m

def get_kb(uid:str):
    r = get_role(uid)
    if r == ROLE_OWNER: return kb_owner()
    if r == ROLE_ADMIN: return kb_admin()
    if r == ROLE_VIP:   return kb_vip()
    return kb_user()



def kb_file(fname):
    m = types.InlineKeyboardMarkup(row_width=3)
    active  = db["files"].get(fname,{}).get("active",False)
    ar      = db["files"].get(fname,{}).get("auto_restart",False)
    pinned  = db["files"].get(fname,{}).get("pinned",False)
    m.add(
        types.InlineKeyboardButton("⏹ إيقاف" if active else "▶️ تشغيل", callback_data=f"tog_{fname}"),
        types.InlineKeyboardButton("🔄 إعادة",   callback_data=f"rst_{fname}"),
        types.InlineKeyboardButton("🗑 حذف",     callback_data=f"del_{fname}"),
    )
    m.add(
        types.InlineKeyboardButton("📋 لوج",     callback_data=f"log_{fname}"),
        types.InlineKeyboardButton("📥 تحميل",   callback_data=f"dwn_{fname}"),
        types.InlineKeyboardButton("🔁 Auto" if not ar else "⏹ Auto", callback_data=f"ar_{fname}"),
    )
    m.add(
        types.InlineKeyboardButton("🌍 ENV",     callback_data=f"env_{fname}"),
        types.InlineKeyboardButton("📊 موارد",   callback_data=f"res_{fname}"),
        types.InlineKeyboardButton("📦 مكاتب",   callback_data=f"pip_{fname}"),
    )
    m.add(
        types.InlineKeyboardButton("⏰ جدولة",   callback_data=f"sched_{fname}"),
        types.InlineKeyboardButton("📌 تثبيت" if not pinned else "📌 إلغاء", callback_data=f"pin_{fname}"),
        types.InlineKeyboardButton("🔎 فحص",     callback_data=f"chk_{fname}"),
    )
    m.add(
        types.InlineKeyboardButton("✏️ إعادة تسمية", callback_data=f"ren_{fname}"),
        types.InlineKeyboardButton("📋 نسخ مسار",    callback_data=f"pth_{fname}"),
    )
    return m


def kb_file_upload(fname: str, uid: str, config: dict):
    """
    لوحة تظهر بعد رفع الملف مباشرة — للأدمن
    تحتوي على: تشغيل، تعديل التوكن، تعديل الـ ID، رسالة للكل، وكل أزرار الإدارة
    """
    active = db["files"].get(fname, {}).get("active", False)
    ext    = os.path.splitext(fname)[1].lower()
    is_py  = ext == ".py"

    m = types.InlineKeyboardMarkup(row_width=2)

    # ─── صف 1: تشغيل / حذف ─────────────────
    m.add(
        types.InlineKeyboardButton("▶️ تشغيل الآن",  callback_data=f"tog_{fname}"),
        types.InlineKeyboardButton("🗑 حذف",          callback_data=f"del_{fname}"),
    )

    # ─── صف 2: تعديل التوكن والـ ID (للـ .py فقط) ──
    if is_py:
        tok_icon = "✅ توكن" if config.get("has_token") else "❌ تعديل التوكن"
        id_icon  = "✅ ID"   if config.get("has_admin") else "❌ تعديل الـ ID"
        m.add(
            types.InlineKeyboardButton(f"🔑 {tok_icon}",  callback_data=f"edit_token_{fname}"),
            types.InlineKeyboardButton(f"👤 {id_icon}",   callback_data=f"edit_id_{fname}"),
        )
        m.add(
            types.InlineKeyboardButton("✏️ تعديل توكن + ID", callback_data=f"edit_both_{fname}"),
        )

    # ─── صف 3: رسائل ─────────────────────────
    m.add(
        types.InlineKeyboardButton("📢 رسالة لكل المستخدمين", callback_data=f"bcast_file_{fname}"),
    )

    # ─── صف 4: إدارة ─────────────────────────
    m.add(
        types.InlineKeyboardButton("📋 لوج",    callback_data=f"log_{fname}"),
        types.InlineKeyboardButton("📥 تحميل",  callback_data=f"dwn_{fname}"),
        types.InlineKeyboardButton("🔎 فحص",    callback_data=f"chk_{fname}"),
    )
    m.add(
        types.InlineKeyboardButton("🌍 ENV",    callback_data=f"env_{fname}"),
        types.InlineKeyboardButton("🔁 Auto",   callback_data=f"ar_{fname}"),
        types.InlineKeyboardButton("📦 مكاتب",  callback_data=f"pip_{fname}"),
    )
    return m


def kb_file_user_upload(fname: str):
    """لوحة تظهر للمستخدم العادي بعد رفع الملف"""
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("▶️ تشغيل",       callback_data=f"utog_{fname}"),
        types.InlineKeyboardButton("📋 لوج",          callback_data=f"log_{fname}"),
        types.InlineKeyboardButton("🗑 حذف",          callback_data=f"del_{fname}"),
        types.InlineKeyboardButton("📂 ملفاتي كلها",  callback_data=f"uview_files"),
    )
    return m



def kb_admin_panel():
    """لوحة إدارة المستخدمين الكبيرة"""
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("👑 تعيين أدمن",       callback_data="ap_set_admin"),
        types.InlineKeyboardButton("⭐ تعيين VIP",         callback_data="ap_set_vip"),
        types.InlineKeyboardButton("👤 تخفيض لـ User",    callback_data="ap_set_user"),
        types.InlineKeyboardButton("🚫 حظر",              callback_data="ap_ban"),
        types.InlineKeyboardButton("✅ رفع حظر",           callback_data="ap_unban"),
        types.InlineKeyboardButton("📜 كل المستخدمين",    callback_data="ap_list_all"),
        types.InlineKeyboardButton("👑 الأدمنز",           callback_data="ap_list_admins"),
        types.InlineKeyboardButton("⭐ VIP قائمة",         callback_data="ap_list_vip"),
        types.InlineKeyboardButton("🚫 المحظورون",         callback_data="ap_list_banned"),
        types.InlineKeyboardButton("📊 إحصائيات Users",    callback_data="ap_stats"),
        types.InlineKeyboardButton("📢 رسالة جماعية",      callback_data="ap_broadcast"),
        types.InlineKeyboardButton("🗑 حذف مستخدم",        callback_data="ap_delete_user"),
    )
    return m

def kb_user_actions(target_uid:str, role:str):
    m = types.InlineKeyboardMarkup(row_width=2)
    if role != ROLE_ADMIN:
        m.add(types.InlineKeyboardButton("👑 أدمن",  callback_data=f"usr_admin_{target_uid}"))
    if role != ROLE_VIP:
        m.add(types.InlineKeyboardButton("⭐ VIP",   callback_data=f"usr_vip_{target_uid}"))
    if role != ROLE_USER:
        m.add(types.InlineKeyboardButton("👤 User",  callback_data=f"usr_user_{target_uid}"))
    m.add(
        types.InlineKeyboardButton("🚫 حظر",         callback_data=f"usr_ban_{target_uid}"),
        types.InlineKeyboardButton("✅ رفع حظر",      callback_data=f"usr_unban_{target_uid}"),
    )
    return m

# ══════════════════════════════════════════════════════════════
#  حالات المستخدم
# ══════════════════════════════════════════════════════════════
user_states = {}
shell_mode  = set()

# ══════════════════════════════════════════════════════════════
#  نظام المحادثة المباشرة بين الأدمن والمستخدمين
# ══════════════════════════════════════════════════════════════
# admin_chat_with[admin_uid] = target_uid  → الأدمن بيكلم مين دلوقتي
# user_chat_open[user_uid]   = True        → المستخدم في وضع التواصل
admin_chat_with: dict = {}
user_chat_open:  set  = set()

def _send_to_admin(from_uid: str, text: str = None, msg=None):
    """إرسال رسالة من مستخدم للأدمن الرئيسي مع زر رد"""
    name   = db["users"].get(from_uid, {}).get("name", "؟")
    role   = get_role(from_uid)
    role_e = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤"}.get(role,"👤")

    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("💬 رد عليه",    callback_data=f"chat_reply_{from_uid}"),
        types.InlineKeyboardButton("👤 ملفه",        callback_data=f"uview_{from_uid}"),
        types.InlineKeyboardButton("🚫 تجاهل",       callback_data=f"chat_ignore_{from_uid}"),
        types.InlineKeyboardButton("🔕 حظر التواصل", callback_data=f"chat_block_{from_uid}"),
    )
    header = (
        f"💬 *رسالة من مستخدم*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{role_e} *{name}* | 🆔 `{from_uid}`\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
    )
    try:
        if msg and msg.document:
            # إعادة إرسال الملف للأدمن
            bot.send_document(
                ADMIN_ID,
                msg.document.file_id,
                caption=header + f"📎 أرسل ملف: `{msg.document.file_name}`",
                reply_markup=mk
            )
        elif msg and msg.photo:
            bot.send_photo(
                ADMIN_ID,
                msg.photo[-1].file_id,
                caption=header + (msg.caption or ""),
                reply_markup=mk
            )
        elif msg and msg.voice:
            bot.send_voice(
                ADMIN_ID,
                msg.voice.file_id,
                caption=header + "🎙 رسالة صوتية",
                reply_markup=mk
            )
        else:
            bot.send_message(
                ADMIN_ID,
                header + (text or ""),
                reply_markup=mk
            )
    except Exception as e:
        log.error(f"_send_to_admin: {e}")

def _send_to_user(target_uid: str, text: str = None, msg=None, from_name: str = "الأدمن"):
    """إرسال رسالة من الأدمن لمستخدم"""
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("💬 رد على الأدمن", callback_data="open_chat"))
    header = (
        f"📩 *رسالة من {from_name}:*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
    )
    try:
        if msg and msg.document:
            bot.send_document(
                int(target_uid),
                msg.document.file_id,
                caption=header + f"📎 `{msg.document.file_name}`",
                reply_markup=mk
            )
        elif msg and msg.photo:
            bot.send_photo(
                int(target_uid),
                msg.photo[-1].file_id,
                caption=header + (msg.caption or ""),
                reply_markup=mk
            )
        elif msg and msg.voice:
            bot.send_voice(
                int(target_uid),
                msg.voice.file_id,
                caption=header + "🎙 رسالة صوتية من الأدمن",
                reply_markup=mk
            )
        else:
            bot.send_message(
                int(target_uid),
                header + (text or ""),
                reply_markup=mk
            )
        return True
    except Exception as e:
        log.error(f"_send_to_user {target_uid}: {e}")
        return False



# ══════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(m):
    uid  = reg_user(m)
    name = m.from_user.first_name or "مستخدم"
    role = get_role(uid)
    role_emoji = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤"}.get(role,"👤")

    uid_files = [f for f,v in db["files"].items() if v.get("owner")==uid]
    active_f  = sum(1 for f in uid_files if db["files"][f].get("active"))
    badges = []
    if role == ROLE_VIP:   badges.append("⭐ VIP")
    if role == ROLE_ADMIN: badges.append("👑 أدمن")
    if role == ROLE_OWNER: badges.append("🔱 مالك")
    if db["users"][uid].get("uploads",0) >= 10: badges.append("📤 محترف")
    badge_str = " ".join(badges) if badges else ""

    welcome = (
        f"{role_emoji} *أهلاً {name}!* {badge_str}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📊 الصلاحية: `{role.upper()}`\n"
        f"📂 ملفاتك: `{len(uid_files)}` | ⚡ شغّالة: `{active_f}`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💡 /help مساعدة"
    )
    safe_send(m.chat.id, welcome, reply_markup=get_kb(uid))

@bot.message_handler(commands=['myfiles'])
def cmd_myfiles(m):
    _show_files(m)

@bot.message_handler(commands=['id'])
def cmd_id(m):
    safe_reply(m, f"🆔 ID بتاعك: {m.from_user.id}")

@bot.message_handler(commands=['stats'])
def cmd_stats(m):
    _server_stats(m)

@bot.message_handler(commands=['stop'])
def cmd_stop(m):
    uid = reg_user(m)
    if not is_staff(uid): return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        safe_reply(m, "الاستخدام: /stop اسم_الملف"); return
    fname = parts[1].strip()
    if fname in db["files"]:
        stop_file(fname)
        safe_reply(m, f"⏹ تم إيقاف {fname}")
    else:
        safe_reply(m, f"❌ الملف غير موجود")

@bot.message_handler(commands=['run'])
def cmd_run(m):
    uid = reg_user(m)
    if not is_staff(uid): return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        safe_reply(m, "الاستخدام: /run اسم_الملف"); return
    fname = parts[1].strip()
    if fname in db["files"]:
        launch(db["files"][fname]["path"], fname)
        safe_reply(m, f"🚀 تم تشغيل {fname}")
    else:
        safe_reply(m, f"❌ الملف غير موجود")

@bot.message_handler(commands=['health'])
def cmd_health(m):
    uid = reg_user(m)
    if not is_staff(uid): return
    if not HEALTH_LOG:
        safe_reply(m, "⏳ لسه ما في بيانات، انتظر دقيقة."); return
    last = HEALTH_LOG[-1]
    avg_cpu = sum(h["cpu"] for h in HEALTH_LOG) / len(HEALTH_LOG)
    avg_mem = sum(h["mem"] for h in HEALTH_LOG) / len(HEALTH_LOG)
    safe_reply(m,
        f"🏥 *تقرير الصحة*\n━━━━━━━━━━━━━━━━━\n"
        f"📊 آخر قراءة ({last['time']}):\n"
        f"  CPU: `{last['cpu']}%` | RAM: `{last['mem']}%` | Disk: `{last['disk']}%`\n\n"
        f"📈 المتوسط ({len(HEALTH_LOG)} قراءة):\n"
        f"  CPU: `{avg_cpu:.1f}%` | RAM: `{avg_mem:.1f}%`")

@bot.message_handler(commands=['backup'])
def cmd_backup(m):
    uid = reg_user(m)
    if not is_staff(uid): return
    if os.path.exists(DB_FILE):
        with open(DB_FILE,'rb') as f:
            bot.send_document(m.chat.id, f, caption=f"💾 باك أب يدوي — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

@bot.message_handler(commands=['mytickets'])
def cmd_mytickets(m):
    uid  = reg_user(m)
    tix  = [(tid,t) for tid,t in db["tickets"].items() if t.get("uid")==uid]
    if not tix:
        safe_reply(m, "🎫 مفيش تذاكر سابقة.\nاضغط 🎫 تذكرة دعم لفتح تذكرة جديدة."); return
    txt = "🎫 *تذاكرك:*\n━━━━━━━━━━━━━━━━━\n"
    for tid, t in sorted(tix, key=lambda x: x[0], reverse=True)[:5]:
        st  = "🟢 مفتوحة" if t.get("status")=="open" else "🔴 مغلقة"
        rds = len(t.get("replies",[]))
        txt += f"{st} #{tid} | ردود: {rds}\n📝 {t.get('msg','')[:60]}...\n🕐 {t.get('created','')}\n\n"
    safe_reply(m, txt)

@bot.message_handler(commands=['status'])
def cmd_status(m):
    uid  = reg_user(m)
    cpu  = psutil.cpu_percent(interval=0.5)
    mem  = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    up   = int(time.time() - BOT_START_TIME)
    h,r  = divmod(up,3600); mins,_ = divmod(r,60)
    cpu_bar  = "█"*int(cpu/10) + "░"*(10-int(cpu/10))
    mem_bar  = "█"*int(mem/10) + "░"*(10-int(mem/10))
    safe_reply(m,
        f"📡 *حالة السيرفر*\n━━━━━━━━━━━━━━━━━\n"
        f"CPU: `{cpu_bar}` {cpu:.1f}%\n"
        f"RAM: `{mem_bar}` {mem:.1f}%\n"
        f"💾 Disk: {disk:.1f}%\n"
        f"⏱ وقت التشغيل: {h}س {mins}د\n"
        f"⚡ شغّالة: {len(running_procs)} ملف")

@bot.message_handler(commands=['help'])
def cmd_help(m):
    uid = reg_user(m)
    role = get_role(uid)
    cmds = (
        "📖 *الأوامر المتاحة:*\n━━━━━━━━━━━━━━━━━\n"
        "/start — الرئيسية\n"
        "/id — ID بتاعك\n"
        "/myfiles — ملفاتك\n"
        "/stats — موارد السيرفر\n"
        "/help — المساعدة\n"
    )
    if is_staff(uid):
        cmds += (
            "\n*للأدمن:*\n"
            "/run اسم — تشغيل ملف\n"
            "/stop اسم — إيقاف ملف\n"
            "/health — تقرير الصحة\n"
            "/backup — باك أب فوري\n"
        )
    cmds += f"\n🆔 ID: `{m.from_user.id}`"
    safe_reply(m, cmds)

# ══════════════════════════════════════════════════════════════
#  رفع الملفات
# ══════════════════════════════════════════════════════════════
def _send_scan_report(m, fname: str, deep: dict, config: dict, fsize: int,
                      scan_only: bool = False, admin_only: bool = False):
    """إرسال تقرير الفحص — plain text بدون Markdown"""
    verdict  = deep.get("verdict", "SAFE")
    score    = deep.get("score", 0)
    entropy  = deep.get("entropy", 0.0)
    hash_md5 = deep.get("hash_md5", "")
    layers   = deep.get("layers", [])
    dangers  = deep.get("dangers", [])
    warnings = deep.get("warnings", [])
    uid      = str(m.from_user.id)

    # اسم الملف بدون أحرف خاصة
    fname_safe = str(fname).replace('`','').replace('*','').replace('_',' ')

    verdict_icon = {
        "SAFE":    "✅ آمن تماماً",
        "WARNING": "🟡 تحذيرات طفيفة",
        "DANGER":  "🟠 خطر متوسط",
        "CRITICAL":"🔴 خطر حرج",
    }.get(verdict, "✅ آمن")

    danger_lines = ""
    for desc, sev in dangers[:6]:
        icon = "🔴" if sev == "CRITICAL" else "🟠" if sev == "HIGH" else "🟡"
        danger_lines += f"  {icon} {str(desc)}\n"

    warn_lines = ""
    for w in warnings[:3]:
        warn_lines += f"  ⚠️ {str(w)}\n"

    bot_info = ""
    if config:
        tok_icon = "✅" if config.get("has_token") else "❌"
        adm_icon = "✅" if config.get("has_admin") else "❌"
        tok_val  = str(config.get("token_val") or "غير موجود")[:30]
        adm_val  = str(config.get("admin_val") or "غير موجود")
        bot_info = (
            f"\n🤖 إعدادات البوت:\n"
            f"  {tok_icon} التوكن: {tok_val}\n"
            f"  {adm_icon} الأدمن ID: {adm_val}\n"
        )
        if config.get("suggestions"):
            bot_info += "  💡 " + " | ".join(str(s) for s in config["suggestions"][:3]) + "\n"

    libs_txt = ""
    if deep.get("to_install"):
        libs_txt = f"\n📦 مكاتب للتثبيت: {', '.join(deep['to_install'][:5])}\n"

    hash_short = hash_md5[:16] + "..." if len(hash_md5) > 16 else hash_md5
    prefix = "🔎 تقرير الفحص" if scan_only else "✅ تم الرفع"

    text = (
        f"{prefix}: {fname_safe}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📦 الحجم: {fsize//1024} KB | 🔬 طبقات: {len(layers)}\n"
        f"🔐 MD5: {hash_short}\n"
        f"📊 Entropy: {entropy} | 🎯 نقاط الخطر: {score}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🛡 الحكم: {verdict_icon}\n"
        f"{danger_lines}"
        f"{warn_lines}"
        f"{bot_info}"
        f"{libs_txt}"
    )

    if admin_only:
        try:
            safe_send(ADMIN_ID, "⚠️ " + text)
        except: pass
        return

    config_safe = config if config else {}
    markup = kb_file_upload(fname, uid, config_safe) if is_staff(uid) else kb_file_user_upload(fname)
    safe_reply(m, text, reply_markup=markup)




@bot.message_handler(content_types=['document'])
def handle_upload(m):
    uid  = reg_user(m)
    role = get_role(uid)

    # ➤ لو المستخدم في وضع التواصل → الملف يروح للأدمن
    if uid in user_chat_open and not is_staff(uid):
        if uid not in db.get("chat_blocked", []):
            _send_to_admin(uid, None, m)
            safe_reply(m, "📨 الملف وصل للأدمن ✅")
        else:
            safe_reply(m, "🔕 تواصلك محظور حالياً.")
        return

    # ➤ لو الأدمن في محادثة → الملف يروح للمستخدم
    if is_staff(uid) and uid in admin_chat_with:
        target = admin_chat_with[uid]
        name = db["users"].get(target, {}).get("name", "؟")
        ok = _send_to_user(target, None, m)
        safe_reply(m, f"✅ الملف وصل لـ {name}" if ok else f"❌ فشل الإرسال لـ {target}")
        return

    # لو البوت مقفول والمستخدم مش أدمن
    if db.get("locked") and not is_staff(uid):
        safe_reply(m, "🔒 البوت مقفول حالياً. جرّب بعدين."); return

    def deploy():
        try:
            fname = m.document.file_name or "file"
            ext   = os.path.splitext(fname)[1].lower()
            fname_safe = fname.replace('`','').replace('*','').replace('_',' ')

            # تحميل الملف
            raw = None
            for attempt in range(3):
                try:
                    raw = bot.download_file(bot.get_file(m.document.file_id).file_path)
                    break
                except Exception as dl_err:
                    if attempt == 2:
                        safe_reply(m, f"\u274c فشل تحميل الملف: {str(dl_err)[:80]}")
                        return
                    time.sleep(2)
            if not raw: return

            # ملفات محمية
            if is_protected_file(fname) and not is_staff(uid):
                safe_reply(m, f"\U0001f6ab الملف {fname_safe} محمي!")
                return

            # فحص الحجم والامتداد
            ok, reason = validate_file(raw, fname, uid)
            if not ok:
                safe_reply(m, f"\u274c {reason}")
                return

            state = user_states.get(uid, {})

            # تحديث البوت
            if state.get("action") == "update_bot" and fname == "bot.py":
                user_states.pop(uid, None)
                with open("bot.py", "wb") as f2: f2.write(raw)
                safe_reply(m, "\U0001f504 تم استلام التحديث! جارٍ إعادة التشغيل...")
                time.sleep(1)
                os.execv(sys.executable, [sys.executable, "bot.py"])
                return

            # requirements.txt
            if fname == "requirements.txt":
                path = f"ELITE_HOST/{fname}"
                with open(path, "wb") as f2: f2.write(raw)
                safe_reply(m, "\U0001f4e6 تم استلام requirements.txt - جارٍ التثبيت...")
                install_req_file(path, m.chat.id)
                return

            # الفحص الامني للملفات القابلة للتنفيذ
            if ext in [".py", ".js", ".sh"] and not is_staff(uid):
                safe_reply(m, f"\U0001f52c جارٍ فحص {fname_safe}...")
                tmp_path = f"/tmp/prescan_{uid}_{fname}"
                with open(tmp_path, "wb") as f2: f2.write(raw)
                deep = deep_scan_file(tmp_path, raw)
                try: os.remove(tmp_path)
                except: pass
                if deep["verdict"] in ("CRITICAL", "DANGER"):
                    db["quarantine"].append({
                        "fname": fname, "uid": uid,
                        "dangers": [d for d, _ in deep["dangers"]],
                        "verdict": deep["verdict"],
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    db["stats"]["blocked"] = db["stats"].get("blocked", 0) + 1
                    save()
                    handle_security_violation(uid, fname, deep, m.chat.id)
                    return

            # حفظ الملف
            path = f"ELITE_HOST/{fname}"
            if os.path.exists(path):
                save_file_version(fname, path)
            with open(path, "wb") as f2: f2.write(raw)
            db["files"][fname] = {
                "owner": uid, "active": False, "path": path,
                "size": len(raw), "auto_restart": False,
                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "ext": ext
            }
            db["stats"]["uploads"] = db["stats"].get("uploads", 0) + 1
            if uid in db["users"]:
                db["users"][uid]["uploads"] = db["users"][uid].get("uploads", 0) + 1
            save()

            # رسالة النجاح
            if ext == ".py":
                config = check_bot_config(path)
                tok_icon = "\u2705" if config.get("has_token") else "\u274c"
                adm_icon = "\u2705" if config.get("has_admin") else "\u274c"
                tok_val  = str(config.get("token_val") or "غير موجود")[:25]
                adm_val  = str(config.get("admin_val") or "غير موجود")
                scan     = scan_file(path)
                libs_txt = "\nمكاتب: " + ", ".join(scan["to_install"][:5]) if scan.get("to_install") else ""
                msg = (
                    f"\u2705 تم الرفع: {fname_safe}\n"
                    f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
                    f"\U0001f4e6 {len(raw)//1024} KB\n"
                    f"{tok_icon} التوكن: {tok_val}\n"
                    f"{adm_icon} الادمن: {adm_val}\n"
                    f"\U0001f50d الامان: {'آمن' if scan.get('safe') else 'مشاكل'}"
                    f"{libs_txt}"
                )
                markup = kb_file_upload(fname, uid, config) if is_staff(uid) else kb_file_user_upload(fname)
                safe_reply(m, msg, reply_markup=markup)
                def install_and_run(scan=scan, path=path, fname=fname, chat_id=m.chat.id):
                    if scan.get("to_install"):
                        ok2 = install_pkgs(scan["to_install"], None)
                        safe_send(chat_id, "\u2705 تم تثبيت المكاتب!" if ok2 else "\u26a0\ufe0f بعض المكاتب فشلت")
                    launch(path, fname)
                    safe_send(chat_id, f"\U0001f680 تم تشغيل {fname_safe}")
                executor.submit(install_and_run)
            else:
                markup = kb_file_upload(fname, uid, {}) if is_staff(uid) else kb_file_user_upload(fname)
                safe_reply(m, f"\u2705 تم الرفع: {fname_safe}\n\U0001f4e6 {len(raw)//1024} KB", reply_markup=markup)
                if ext in [".js", ".sh"]:
                    launch(path, fname)
                    safe_send(m.chat.id, f"\U0001f680 تم تشغيل {fname_safe}")

            try: _notify_admin_upload(uid, fname, len(raw), ext, m.chat.id)
            except: pass

        except Exception as e:
            log.error(f"Upload error: {e}")
            safe_reply(m, f"\u274c خطأ: {str(e)[:150]}")

    executor.submit(deploy)
# ══════════════════════════════════════════════════════════════
#  Callbacks
# ══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid   = str(call.from_user.id)
    role  = get_role(uid)
    data  = call.data

    # استخراج act و tgt بشكل صحيح
    # الأوامر المعروفة متعددة الكلمات
    KNOWN_ACTS = [
        "verget","treply","tclose","qapprove","qdelete","ustop","utog",
        "uview","uact","unban","usr","tog","run","stop","log","dl","env","sched","scan","upd",
        "cfg","ver","bl","notif","ap","pth","ren","pgkill","autorst",
        "ai_mode","ai"
    ]
    act = ""
    tgt = ""
    for known in sorted(KNOWN_ACTS, key=len, reverse=True):
        if data.startswith(known + "_"):
            act = known
            tgt = data[len(known)+1:]
            break
        elif data == known:
            act = known
            tgt = ""
            break
    if not act:
        parts = data.split("_",1)
        act   = parts[0]
        tgt   = parts[1] if len(parts)>1 else ""

    def only_staff():
        if not is_staff(uid):
            bot.answer_callback_query(call.id,"❌ لا صلاحية"); return True
        return False

    def only_owner():
        if role != ROLE_OWNER:
            bot.answer_callback_query(call.id,"❌ للمالك فقط"); return True
        return False

    # ══ ملفات ══════════════════════════════
    if act == "tog":
        if only_staff(): return
        if tgt in db["files"]:
            if db["files"][tgt].get("active"):
                stop_file(tgt); bot.answer_callback_query(call.id,"⏹ متوقف")
            else:
                launch(db["files"][tgt]["path"], tgt)
                bot.answer_callback_query(call.id,"▶️ يعمل")
            try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb_file(tgt))
            except: pass

    elif act == "rst":
        if only_staff(): return
        if tgt in db["files"]:
            stop_file(tgt); time.sleep(0.3)
            launch(db["files"][tgt]["path"], tgt)
            bot.answer_callback_query(call.id,"🔄 تمت الإعادة")

    elif act == "del":
        if only_staff(): return
        if tgt in db["files"]:
            path = db["files"][tgt].get("path","")
            stop_file(tgt)
            try:
                if os.path.exists(path): os.remove(path)
            except: pass
            del db["files"][tgt]
            db.get("envs",{}).pop(tgt,None); save()
            bot.answer_callback_query(call.id,"🗑 حُذف")
            try: bot.edit_message_text(f"🗑 حُذف `{tgt}`", call.message.chat.id, call.message.message_id)
            except: pass

    elif act == "log":
        bot.answer_callback_query(call.id)
        lp = f"LOGS/{tgt}.log"
        if os.path.exists(lp):
            with open(lp,'r',encoding='utf-8',errors='replace') as f:
                lines = f.readlines()[-30:]
            out = "".join(lines).strip() or "(فارغ)"
            if len(out)>3500: out="..."+out[-3500:]
            safe_send(call.message.chat.id, f"📋 {tgt}\n\n{out}\n")
        else:
            safe_send(call.message.chat.id,"📋 لا يوجد لوج.")

    elif act == "dwn":
        bot.answer_callback_query(call.id)
        fname = tgt
        # ── حماية الملفات المحمية ──────────
        if is_protected_file(fname):
            add_intrusion(uid, 10, f"محاولة تحميل ملف محمي: {fname}")
            safe_send(call.message.chat.id,
                f"🚫 *ممنوع!* الملف `{fname}` محمي ولا يمكن تحميله.\n"
                f"تم تسجيل هذه المحاولة.")
            return
        # ── فحص flood ──────────────────────
        if role == ROLE_USER and check_download_flood(uid):
            safe_send(call.message.chat.id,
                "⏳ تحميل سريع جداً — انتظر دقيقة."); return
        # ── صلاحية — فقط صاحب الملف أو staff ──
        if fname in db["files"]:
            owner = db["files"][fname].get("owner","")
            if owner != uid and not is_staff(uid):
                add_intrusion(uid, 5, f"محاولة تحميل ملف شخص آخر: {fname}")
                safe_send(call.message.chat.id,
                    "🚫 هذا الملف مش ملفك!"); return
            p = db["files"][fname].get("path","")
            if os.path.exists(p):
                FILE_ACCESS_LOG[uid].append((datetime.now().strftime('%H:%M:%S'), fname, "download"))
                sec_log(uid, f"تحميل ملف: {fname}", "info", fname)
                with open(p,'rb') as f:
                    raw = f.read()
                # علامة مائية للمستخدمين العاديين
                if role == ROLE_USER:
                    raw = watermark_file(raw, uid)
                import io
                bot.send_document(call.message.chat.id,
                    io.BytesIO(raw),
                    visible_file_name=fname,
                    caption=f"📥 `{fname}`\n🔒 هذا الملف مرتبط بحسابك")

    elif act == "ar":
        if only_staff(): return
        if tgt in db["files"]:
            cur = db["files"][tgt].get("auto_restart",False)
            db["files"][tgt]["auto_restart"] = not cur; save()
            if not cur: enable_ar(tgt, db["files"][tgt]["path"])
            bot.answer_callback_query(call.id, "🔁 مفعّل" if not cur else "⏹ متوقف")
            try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb_file(tgt))
            except: pass

    elif act == "res":
        bot.answer_callback_query(call.id)
        info = running_procs.get(tgt)
        if not info:
            safe_send(call.message.chat.id, f"❌ {tgt} غير مشغّل."); return
        try:
            p = psutil.Process(info["pid"])
            up = int(time.time()-info["started"])
            h,r=divmod(up,3600); mn,s=divmod(r,60)
            safe_send(call.message.chat.id,
                f"📊 *{tgt}*\nPID:`{info['pid']}` CPU:`{p.cpu_percent(0.5)}%` RAM:`{p.memory_info().rss//1024//1024}MB` ⏱`{h:02d}:{mn:02d}:{s:02d}`")
        except psutil.NoSuchProcess:
            safe_send(call.message.chat.id,"⚠️ انتهت.")

    elif act == "pip":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        user_states[uid] = {"action":"pip_install","file":tgt}
        safe_send(call.message.chat.id,
            f"📦 اكتب المكاتب:\nمثال: `requests flask aiohttp`")

    elif act == "env":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        envs = db.get("envs",{}).get(tgt,{})
        text = "\n".join([f"`{k}`=`{v}`" for k,v in envs.items()]) or "لا توجد."
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("➕ إضافة",    callback_data=f"envadd_{tgt}"),
            types.InlineKeyboardButton("🗑 مسح",      callback_data=f"envclear_{tgt}")
        )
        safe_send(call.message.chat.id, f"🌍 ENV: {tgt}\n{text}", reply_markup=mk)

    elif act == "envadd":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        user_states[uid] = {"action":"add_env","file":tgt}
        safe_send(call.message.chat.id, "🌍 أرسل: KEY=VALUE")

    elif act == "envclear":
        if only_staff(): return
        db.setdefault("envs",{})[tgt]={}; save()
        bot.answer_callback_query(call.id,"🗑 تم")

    elif act == "sched":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        user_states[uid] = {"action":"schedule","file":tgt}
        safe_send(call.message.chat.id, f"⏰ أرسل الوقت:\nYYYY-MM-DD HH:MM")

    elif act == "runnow":
        if only_staff(): return
        user_states.pop(uid,None)
        if tgt in db["files"]:
            launch(db["files"][tgt]["path"], tgt)
            bot.answer_callback_query(call.id,"🚀 يشتغل")

    # ══ الحجر الصحي ═══════════════════════
    elif act == "qapprove":
        if only_owner(): return
        entry = next((e for e in db["quarantine"] if e["fname"]==tgt), None)
        if entry:
            db["quarantine"].remove(entry); save()
            launch(entry["path"], tgt)
            bot.answer_callback_query(call.id,"✅ موافقة")
            try: bot.edit_message_text(f"✅ وافقت على `{tgt}` وتم تشغيله.", call.message.chat.id, call.message.message_id)
            except: pass

    elif act == "qdelete":
        if only_owner(): return
        entry = next((e for e in db["quarantine"] if e["fname"]==tgt), None)
        if entry:
            db["quarantine"].remove(entry)
            if tgt in db["files"]: del db["files"][tgt]
            try:
                if os.path.exists(entry["path"]): os.remove(entry["path"])
            except: pass
            save()
            bot.answer_callback_query(call.id,"🗑 حُذف")
            try: bot.edit_message_text(f"🗑 تم حذف `{tgt}` من الحجر.", call.message.chat.id, call.message.message_id)
            except: pass

    elif act == "qdelete":
        if only_owner(): return
        entry = next((e for e in db["quarantine"] if e["fname"]==tgt), None)
        if entry:
            db["quarantine"].remove(entry)
            if tgt in db["files"]: del db["files"][tgt]
            try:
                if os.path.exists(entry["path"]): os.remove(entry["path"])
            except: pass
            save()
            bot.answer_callback_query(call.id,"🗑 حُذف")
            try: bot.edit_message_text(f"🗑 تم حذف `{tgt}` من الحجر.", call.message.chat.id, call.message.message_id)
            except: pass

    # ── تثبيت الملف (pin) ────────────────────
    elif act == "pin":
        if only_staff(): return
        if tgt in db["files"]:
            cur = db["files"][tgt].get("pinned", False)
            db["files"][tgt]["pinned"] = not cur; save()
            bot.answer_callback_query(call.id, "📌 تم التثبيت" if not cur else "📌 إلغاء التثبيت")
            try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb_file(tgt))
            except: pass

    # ── فحص الملف (chk) ──────────────────────
    elif act == "chk":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        if tgt in db["files"]:
            path = db["files"][tgt].get("path","")
            if os.path.exists(path):
                scan   = scan_file(path)
                config = check_bot_config(path)
                tok    = f"{'✅' if config['has_token'] else '❌'} التوكن: `{config['token_val'] or 'غير موجود'}`"
                adm    = f"{'✅' if config['has_admin'] else '❌'} الأدمن: `{config['admin_val'] or 'غير موجود'}`"
                libs   = f"📦 `{', '.join(scan['to_install'])}`" if scan["to_install"] else "📦 لا تحتاج مكاتب"
                danger = ("\n🔴 " + "\n🔴 ".join(scan["danger"])) if scan["danger"] else "\n✅ آمن"
                safe_send(call.message.chat.id,
                    f"🔎 *فحص: {tgt}*\n━━━━━━━━━━━━━━━━━\n{tok}\n{adm}\n{libs}{danger}")

    # ── إعادة تسمية (ren) ────────────────────
    elif act == "ren":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        user_states[uid] = {"action":"rename_file","file":tgt}
        safe_send(call.message.chat.id,
            f"✏️ اكتب الاسم الجديد لـ `{tgt}`:")

    # ── مسار الملف (pth) ─────────────────────
    elif act == "pth":
        bot.answer_callback_query(call.id)
        if tgt in db["files"]:
            path = db["files"][tgt].get("path","")
            safe_send(call.message.chat.id,
                f"📋 *مسار الملف:*\n`{path}`")

    # ── لوحة الأدمن (ap) ─────────────────────
    elif act == "ap":
        if only_owner(): return
        bot.answer_callback_query(call.id)
        sub = tgt

        if sub == "list_all":
            users = list(db["users"].items())
            mk = types.InlineKeyboardMarkup(row_width=2)
            for u, info in users[:20]:
                e = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤","banned":"🚫"}.get(info.get("role","user"),"👤")
                mk.add(types.InlineKeyboardButton(
                    f"{e} {info.get('name','؟')}",
                    callback_data=f"uview_{u}"
                ))
            safe_send(call.message.chat.id,
                f"📜 كل المستخدمين ({len(db['users'])}) — اضغط على أي مستخدم:",
                reply_markup=mk)

        elif sub == "list_admins":
            mk = types.InlineKeyboardMarkup(row_width=2)
            admins = [(u,info) for u,info in db["users"].items() if info.get("role")==ROLE_ADMIN]
            for u, info in admins:
                mk.add(types.InlineKeyboardButton(f"👑 {info.get('name','؟')}", callback_data=f"uview_{u}"))
            mk.add(types.InlineKeyboardButton(f"🔱 المالك", callback_data=f"uview_{ADMIN_ID}"))
            safe_send(call.message.chat.id,
                f"👑 الأدمنز ({len(admins)+1}):", reply_markup=mk)

        elif sub == "list_vip":
            vips = [(u,info) for u,info in db["users"].items() if info.get("role")==ROLE_VIP]
            if not vips:
                safe_send(call.message.chat.id, "لا يوجد VIP."); return
            mk = types.InlineKeyboardMarkup(row_width=2)
            for u, info in vips[:20]:
                mk.add(types.InlineKeyboardButton(f"⭐ {info.get('name','؟')}", callback_data=f"uview_{u}"))
            safe_send(call.message.chat.id, f"⭐ VIP ({len(vips)}):", reply_markup=mk)

        elif sub == "list_banned":
            banned = [(u,info) for u,info in db["users"].items() if info.get("role")=="banned"]
            if not banned:
                safe_send(call.message.chat.id, "✅ لا يوجد محظورون."); return
            mk = types.InlineKeyboardMarkup(row_width=2)
            for u, info in banned[:20]:
                mk.add(types.InlineKeyboardButton(f"🚫 {info.get('name','؟')}", callback_data=f"uview_{u}"))
            safe_send(call.message.chat.id,
                f"🚫 المحظورون ({len(banned)}) — اضغط لإدارة:", reply_markup=mk)

        elif sub == "stats":
            roles = {}
            for u,info in db["users"].items():
                r = info.get("role","user")
                roles[r] = roles.get(r,0)+1
            safe_send(call.message.chat.id,
                f"📊 *إحصائيات المستخدمين*\n━━━━━━━━━━━━━━━━━\n"
                f"👥 الكل: `{len(db['users'])}`\n"
                f"🔱 مالك: `{roles.get('owner',1)}`\n"
                f"👑 أدمن: `{roles.get('admin',0)}`\n"
                f"⭐ VIP: `{roles.get('vip',0)}`\n"
                f"👤 عادي: `{roles.get('user',0)}`\n"
                f"🚫 محظور: `{roles.get('banned',0)}`")

        elif sub in ["set_admin","set_vip","set_user","ban","unban","delete_user"]:
            action_map = {
                "set_admin":   "👑 تعيين أدمن",
                "set_vip":     "⭐ تعيين VIP",
                "set_user":    "👤 تخفيض لـ User",
                "ban":         "🚫 حظر مستخدم",
                "unban":       "✅ رفع حظر",
                "delete_user": "🗑 حذف مستخدم"
            }
            user_states[uid] = {"action": f"panel_{sub}"}
            safe_send(call.message.chat.id,
                f"*{action_map[sub]}*\nأرسل ID المستخدم:")

        elif sub == "broadcast":
            user_states[uid] = {"action": "broadcast"}
            safe_send(call.message.chat.id,
                "📢 اكتب الرسالة الجماعية:")

    # ══ الأمان ════════════════════════════
    elif act == "sec":
        if only_owner(): return
        bot.answer_callback_query(call.id)
        if tgt == "clear_sus":
            suspicious.clear(); failed_cmds.clear()
            INTRUSION_SCORE.clear()
            safe_send(call.message.chat.id, "✅ تم مسح قائمة المشبوهين ونقاط الخطورة")
        elif tgt == "ban_all_sus":
            count = 0
            for u in list(suspicious):
                add_to_blacklist(u)
                if u in db["users"]: db["users"][u]["role"] = "banned"
                count += 1
            suspicious.clear(); save()
            safe_send(call.message.chat.id, f"🚫 تم حظر {count} مستخدم")
        elif tgt == "log":
            if not SECURITY_LOG:
                safe_send(call.message.chat.id, "📋 سجل الأمان فارغ."); return
            lines = []
            for e in SECURITY_LOG[-15:][::-1]:
                lvl_e = {"critical":"🔴","warn":"🟡","info":"🟢"}.get(e["level"],"⚪")
                lines.append(f"{lvl_e} {e['time']} | {e['name']} | {e['action'][:40]}")
            safe_send(call.message.chat.id,
                f"📋 *سجل الأمان (آخر 15):*\n━━━━━━━━━━━━━━━━━\n" + "\n".join(lines))
        elif tgt == "scores":
            if not INTRUSION_SCORE:
                safe_send(call.message.chat.id, "✅ لا توجد نقاط خطورة."); return
            lines = []
            mk2 = types.InlineKeyboardMarkup(row_width=2)
            for u, sc in sorted(INTRUSION_SCORE.items(), key=lambda x: -x[1])[:10]:
                name = db["users"].get(u,{}).get("name","؟")
                bar  = "█" * min(10, sc//2) + "░" * (10 - min(10, sc//2))
                lines.append(f"🎯 {name} | `{u}`\n   `{bar}` {sc}/{MAX_INTRUSION}")
                mk2.add(types.InlineKeyboardButton(f"👤 {name[:12]}", callback_data=f"uview_{u}"))
            safe_send(call.message.chat.id,
                f"🎯 *نقاط الخطورة:*\n━━━━━━━━━━━━━━━━━\n" + "\n".join(lines), reply_markup=mk2)
        elif tgt == "clear_log":
            SECURITY_LOG.clear(); INTRUSION_SCORE.clear()
            safe_send(call.message.chat.id, "✅ تم مسح سجل الأمان")
        elif tgt == "reset":
            spam_blocked.clear(); spam_counter.clear()
            upload_counter.clear(); failed_cmds.clear()
            INTRUSION_SCORE.clear(); download_counter.clear()
            safe_send(call.message.chat.id, "🔐 تم إعادة تعيين كل الحماية ✅")
        elif tgt == "protected":
            lines = [f"🔒 `{f}`" for f in sorted(PROTECTED_FILES)]
            safe_send(call.message.chat.id,
                f"🔒 *الملفات المحمية ({len(PROTECTED_FILES)}):*\n━━━━━━━━━━━━━━━━━\n"
                + "\n".join(lines) +
                "\n━━━━━━━━━━━━━━━━━\n"
                "⛔ هذه الملفات لا يمكن رفعها أو تحميلها من المستخدمين العاديين")

    # ══ إعدادات البوت ════════════════════
    elif act == "cfg":
        if only_owner(): return
        bot.answer_callback_query(call.id)
        cfg_labels = {
            "max_files_per_user":   "حد الملفات لكل مستخدم",
            "max_file_size_kb":     "الحجم الأقصى للملف (KB)",
            "report_time":          "وقت التقرير اليومي (مثال: 08:00)",
        }
        if tgt == "toggle_lock":
            db["locked"] = not db.get("locked", False); save()
            state_txt = "🔒 مقفول" if db["locked"] else "🔓 مفتوح"
            safe_send(call.message.chat.id, f"البوت الآن: {state_txt}")
        elif tgt == "toggle_maintenance":
            db["settings"]["maintenance"] = not db["settings"].get("maintenance", False); save()
            state_txt = "🔧 صيانة مفعّلة" if db["settings"]["maintenance"] else "✅ صيانة إيقاف"
            safe_send(call.message.chat.id, f"{state_txt}")
        elif tgt in cfg_labels:
            user_states[uid] = {"action": f"cfg_set_{tgt}"}
            safe_send(call.message.chat.id,
                f"✏️ {cfg_labels[tgt]}\nالقيمة الحالية: {db['settings'].get(tgt, db.get('daily_report_time','08:00'))}\n\nابعت القيمة الجديدة:")
    elif act == "uview":
        if tgt == "files":
            # المستخدم العادي يشوف ملفاته
            bot.answer_callback_query(call.id)
            uid_files = [f for f, v in db["files"].items() if v.get("owner") == uid]
            if not uid_files:
                safe_send(call.message.chat.id, "📂 لا توجد ملفات."); return
            mk2 = types.InlineKeyboardMarkup(row_width=2)
            for f in uid_files[:10]:
                st = "✅" if db["files"][f].get("active") else "❌"
                mk2.add(types.InlineKeyboardButton(f"{st} {f}", callback_data=f"log_{f}"))
            safe_send(call.message.chat.id,
                f"📂 *ملفاتك ({len(uid_files)}):*", reply_markup=mk2)
            return
        if not is_staff(uid): return
        bot.answer_callback_query(call.id)
        target = tgt
        info   = db["users"].get(target, {})
        if not info:
            safe_send(call.message.chat.id, "❌ المستخدم مش موجود"); return

        role_e = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤","banned":"🚫"}.get(info.get("role","user"),"👤")
        trole  = info.get("role","user")

        # إحصائيات الملفات
        u_files  = [f for f,v in db["files"].items() if v.get("owner")==target]
        active_f = sum(1 for f in u_files if db["files"][f].get("active"))
        crashes  = sum(db["files"][f].get("crashes",0) for f in u_files)
        total_kb = sum(db["files"][f].get("size",0) for f in u_files) // 1024

        txt = (
            f"{role_e} *{info.get('name','؟')}*\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{target}`\n"
            f"📅 انضم: {info.get('joined','؟')}\n"
            f"👤 الدور: `{trole.upper()}`\n"
            f"📤 رفعات: `{info.get('uploads',0)}`\n"
            f"📂 ملفات: `{len(u_files)}` | ⚡ شغالة: `{active_f}`\n"
            f"💥 كراشات: `{crashes}` | 📦 حجم: `{total_kb} KB`"
        )

        # أزرار الإجراءات حسب الدور الحالي
        mk = types.InlineKeyboardMarkup(row_width=2)
        if trole == "banned":
            mk.add(
                types.InlineKeyboardButton("✅ رفع الحظر",     callback_data=f"uact_{target}_unban"),
                types.InlineKeyboardButton("🗑 حذف الحساب",   callback_data=f"uact_{target}_delete"),
            )
        elif trole == "user":
            mk.add(
                types.InlineKeyboardButton("⭐ ترقية VIP",     callback_data=f"uact_{target}_set_vip"),
                types.InlineKeyboardButton("👑 تعيين أدمن",    callback_data=f"uact_{target}_set_admin"),
                types.InlineKeyboardButton("🚫 حظر",           callback_data=f"uact_{target}_ban"),
            )
        elif trole == "vip":
            mk.add(
                types.InlineKeyboardButton("👤 تخفيض User",    callback_data=f"uact_{target}_set_user"),
                types.InlineKeyboardButton("👑 تعيين أدمن",    callback_data=f"uact_{target}_set_admin"),
                types.InlineKeyboardButton("🚫 حظر",           callback_data=f"uact_{target}_ban"),
            )
        elif trole == "admin":
            mk.add(
                types.InlineKeyboardButton("👤 تخفيض User",    callback_data=f"uact_{target}_set_user"),
                types.InlineKeyboardButton("🚫 حظر",           callback_data=f"uact_{target}_ban"),
            )
        mk.add(
            types.InlineKeyboardButton("📂 ملفاته",         callback_data=f"uact_{target}_files"),
            types.InlineKeyboardButton("📩 مراسلته",        callback_data=f"uact_{target}_msg"),
        )

        safe_send(call.message.chat.id, txt, reply_markup=mk)

    # ══ تنفيذ إجراء على مستخدم ════════════
    elif act == "uact":
        if not is_staff(uid): return
        parts2   = tgt.split("_", 1)
        target   = parts2[0]
        action   = parts2[1] if len(parts2) > 1 else ""
        info     = db["users"].get(target, {})
        if not info and action != "delete":
            bot.answer_callback_query(call.id, "❌ مستخدم غير موجود"); return

        if action == "unban":
            db["users"][target]["role"] = ROLE_USER
            if target in db.get("blacklist",[]): db["blacklist"].remove(target)
            save()
            bot.answer_callback_query(call.id, "✅ تم رفع الحظر")
            safe_send(call.message.chat.id, f"✅ تم رفع الحظر عن {info.get('name','؟')}")
            try: safe_send(int(target), "✅ تم رفع الحظر عنك! يمكنك استخدام البوت مجدداً.", reply_markup=get_kb(target))
            except: pass

        elif action == "ban":
            db["users"][target]["role"] = "banned"
            add_to_blacklist(target); save()
            bot.answer_callback_query(call.id, "🚫 تم الحظر")
            safe_send(call.message.chat.id, f"🚫 تم حظر {info.get('name','؟')}")
            try: safe_send(int(target), "🚫 تم حظرك من البوت.")
            except: pass

        elif action == "set_vip":
            db["users"][target]["role"] = ROLE_VIP; save()
            bot.answer_callback_query(call.id, "⭐ تم الترقية لـ VIP")
            safe_send(call.message.chat.id, f"⭐ تم ترقية {info.get('name','؟')} لـ VIP")
            try: safe_send(int(target), "⭐ تم ترقيتك لـ VIP! استمتع بالمميزات.", reply_markup=get_kb(target))
            except: pass

        elif action == "set_admin":
            if role != ROLE_OWNER: bot.answer_callback_query(call.id, "❌ للمالك فقط"); return
            db["users"][target]["role"] = ROLE_ADMIN; save()
            bot.answer_callback_query(call.id, "👑 تم التعيين أدمن")
            safe_send(call.message.chat.id, f"👑 تم تعيين {info.get('name','؟')} أدمن")
            try: safe_send(int(target), "👑 تم تعيينك أدمن!", reply_markup=get_kb(target))
            except: pass

        elif action == "set_user":
            db["users"][target]["role"] = ROLE_USER; save()
            bot.answer_callback_query(call.id, "👤 تم التخفيض")
            safe_send(call.message.chat.id, f"👤 تم تخفيض {info.get('name','؟')} لـ User")

        elif action == "delete":
            name = db["users"].pop(target, {}).get("name","؟"); save()
            bot.answer_callback_query(call.id, "🗑 تم الحذف")
            safe_send(call.message.chat.id, f"🗑 تم حذف حساب {name}")

        elif action == "files":
            u_files = [f for f,v in db["files"].items() if v.get("owner")==target]
            bot.answer_callback_query(call.id)
            if not u_files:
                safe_send(call.message.chat.id, "📂 مفيش ملفات."); return
            mk2 = types.InlineKeyboardMarkup(row_width=2)
            for f in u_files[:10]:
                st = "✅" if db["files"][f].get("active") else "❌"
                mk2.add(types.InlineKeyboardButton(f"{st} {f}", callback_data=f"pth_{f}"))
            safe_send(call.message.chat.id,
                f"📂 ملفات {info.get('name','؟')} ({len(u_files)}):", reply_markup=mk2)

        elif action == "msg":
            user_states[uid] = {"action": f"msg_user_{target}"}
            bot.answer_callback_query(call.id)
            safe_send(call.message.chat.id,
                f"📩 اكتب الرسالة اللي عايز تبعتها لـ {info.get('name','؟')}:")
        if only_owner(): return
        bot.answer_callback_query(call.id)
        role_map = {"all":None,"vip":ROLE_VIP,"user":ROLE_USER}
        user_states[uid] = {"action":"send_notif","filter":role_map.get(tgt)}
        labels = {"all":"الكل","vip":"VIP فقط","user":"عادي فقط"}
        safe_send(call.message.chat.id,
            f"📣 إشعار لـ {labels.get(tgt,'الكل')}\nاكتب نص الإشعار:")

    # ══ تذاكر الدعم ══════════════════════
        if not is_staff(uid): return
        bot.answer_callback_query(call.id)
        user_states[uid] = {"action":"ticket_reply","ticket_id":tgt}
        safe_send(call.message.chat.id, f"📩 اكتب ردك على التذكرة #{tgt}:")

    elif act == "tclose":
        if not is_staff(uid): return
        bot.answer_callback_query(call.id, "✅ تم إغلاق التذكرة")
        if tgt in db["tickets"]:
            db["tickets"][tgt]["status"] = "closed"; save()
            ticket_uid = db["tickets"][tgt]["uid"]
            try:
                bot.send_message(int(ticket_uid),
                    f"🎫 تذكرتك #{tgt} تم إغلاقها من الأدمن ✅")
            except: pass

    # ══ Blacklist ════════════════════════
    elif act == "bl":
        if only_owner(): return
        bot.answer_callback_query(call.id)
        if tgt == "add":
            user_states[uid] = {"action":"bl_add"}
            safe_send(call.message.chat.id, "ابعت ID المستخدم اللي عايز تحظره:")

    # ══ إصدارات الملفات ══════════════════
    elif act == "ver":
        if not is_staff(uid): return
        bot.answer_callback_query(call.id)
        versions = db.get("file_versions",{}).get(tgt,[])
        if not versions:
            safe_send(call.message.chat.id, "لا توجد إصدارات محفوظة."); return
        mk = types.InlineKeyboardMarkup(row_width=1)
        for v in versions[-5:]:
            mk.add(types.InlineKeyboardButton(
                f"📥 {v['time']}", callback_data=f"verget_{tgt}|{v['time']}"))
        safe_send(call.message.chat.id,
            f"📜 إصدارات {tgt}:", reply_markup=mk)

    elif act == "verget":
        if not is_staff(uid): return
        parts = tgt.split("|",1)
        fname = parts[0]; ts = parts[1] if len(parts)>1 else ""
        versions = db.get("file_versions",{}).get(fname,[])
        ver = next((v for v in versions if v["time"]==ts), None)
        if ver and os.path.exists(ver["path"]):
            bot.answer_callback_query(call.id, "📥 جارٍ الإرسال...")
            with open(ver["path"],'rb') as f:
                bot.send_document(call.message.chat.id, f,
                    caption=f"📜 إصدار قديم من {fname}\n🕐 {ts}")
        else:
            bot.answer_callback_query(call.id, "❌ الملف غير موجود")
    elif act == "utog":
        fname = tgt
        if fname not in db["files"] or db["files"][fname].get("owner") != uid:
            bot.answer_callback_query(call.id, "❌ مش ملفك"); return
        bot.answer_callback_query(call.id, f"▶️ جارٍ تشغيل {fname}")
        launch(db["files"][fname]["path"], fname)
        safe_send(call.message.chat.id, f"🚀 تم تشغيل {fname}")

    elif act == "ustop":
        fname = tgt
        if fname not in db["files"] or db["files"][fname].get("owner") != uid:
            bot.answer_callback_query(call.id, "❌ مش ملفك"); return
        bot.answer_callback_query(call.id, f"⏹ جارٍ إيقاف {fname}")
        stop_file(fname)
        safe_send(call.message.chat.id, f"⏹ تم إيقاف {fname}")

    # ══ إجراءات على مستخدم مباشرة ══════════
    elif act == "usr":
        if only_owner(): return
        sub_parts = tgt.split("_",1)
        sub_act   = sub_parts[0]
        target_uid = sub_parts[1] if len(sub_parts)>1 else ""
        _apply_user_action(call, uid, sub_act, target_uid)

    # ══ ذكاء اصطناعي ══════════════════════
    elif act == "ai":
        bot.answer_callback_query(call.id)
        if tgt == "continue":
            safe_send(call.message.chat.id, "💬 ابعت سؤالك:")
        elif tgt == "clear":
            ai_sessions.pop(uid, None)
            safe_send(call.message.chat.id, "🗑 تم مسح المحادثة ✅")
        elif tgt == "end":
            user_states.pop(uid, None)
            ai_sessions.pop(uid, None)
            safe_send(call.message.chat.id, "👋 تم إنهاء الجلسة", reply_markup=get_kb(uid))

    elif act == "ai_mode":
        bot.answer_callback_query(call.id)
        if tgt == "cancel":
            user_states.pop(uid, None)
            safe_send(call.message.chat.id, "❌ تم الإلغاء", reply_markup=get_kb(uid))
        elif tgt == "chat":
            user_states[uid] = {"action":"ai_chat","mode":"chat"}
            safe_send(call.message.chat.id, "💬 ابعت سؤالك:")
        elif tgt == "code":
            user_states[uid] = {"action":"ai_chat","mode":"code"}
            safe_send(call.message.chat.id, "🐍 ابعت الكود اللي عايز تحلله:")
        elif tgt == "prog":
            user_states[uid] = {"action":"ai_chat","mode":"prog"}
            safe_send(call.message.chat.id, "🔧 ابعت سؤال البرمجة:")

    # ══ تعديل التوكن والـ ID في الملف ══════
    elif act == "edit":
        if only_staff(): return
        bot.answer_callback_query(call.id)

        if tgt.startswith("token_"):
            fname = tgt[6:]
            user_states[uid] = {"action": "edit_token", "file": fname, "step": "token"}
            mk_cancel = types.InlineKeyboardMarkup()
            mk_cancel.add(types.InlineKeyboardButton("❌ إلغاء", callback_data=f"edit_cancel_{fname}"))
            safe_send(call.message.chat.id,
                f"🔑 *تعديل التوكن في* `{fname}`\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"أرسل التوكن الجديد:\n"
                f"مثال: `1234567890:AAFxxx...`", reply_markup=mk_cancel)

        elif tgt.startswith("id_"):
            fname = tgt[3:]
            user_states[uid] = {"action": "edit_admin_id", "file": fname}
            mk_cancel = types.InlineKeyboardMarkup()
            mk_cancel.add(types.InlineKeyboardButton("❌ إلغاء", callback_data=f"edit_cancel_{fname}"))
            safe_send(call.message.chat.id,
                f"👤 *تعديل الـ Admin ID في* `{fname}`\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"أرسل الـ ID الجديد:\n"
                f"مثال: `123456789`", reply_markup=mk_cancel)

        elif tgt.startswith("both_"):
            fname = tgt[5:]
            user_states[uid] = {"action": "edit_token", "file": fname, "step": "token", "then_id": True}
            mk_cancel = types.InlineKeyboardMarkup()
            mk_cancel.add(types.InlineKeyboardButton("❌ إلغاء", callback_data=f"edit_cancel_{fname}"))
            safe_send(call.message.chat.id,
                f"✏️ *تعديل التوكن والـ ID في* `{fname}`\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"*الخطوة 1/2:* أرسل التوكن الجديد:", reply_markup=mk_cancel)

        elif tgt.startswith("cancel_"):
            fname = tgt[7:]
            user_states.pop(uid, None)
            safe_send(call.message.chat.id,
                f"❌ تم إلغاء التعديل على `{fname}`.",
                reply_markup=kb_file(fname))

        elif tgt.startswith("skip_id_"):
            fname = tgt[8:]
            user_states.pop(uid, None)
            bot.answer_callback_query(call.id, "⏭ تم التخطي")
            _show_edit_done(call.message, fname, "✅ تم تعديل التوكن — تم تخطي الـ ID")

    # ══ رسالة لكل المستخدمين بعد رفع ملف ══
    elif act == "bcast":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        if tgt.startswith("file_"):
            fname = tgt[5:]
            mk = types.InlineKeyboardMarkup(row_width=3)
            mk.add(
                types.InlineKeyboardButton("👥 الكل",      callback_data=f"bcast_all_{fname}"),
                types.InlineKeyboardButton("⭐ VIP فقط",   callback_data=f"bcast_vip_{fname}"),
                types.InlineKeyboardButton("👤 عادي فقط",  callback_data=f"bcast_user_{fname}"),
                types.InlineKeyboardButton("❌ إلغاء",      callback_data=f"bcast_cancel_{fname}"),
            )
            safe_send(call.message.chat.id,
                f"📢 *رسالة بعد رفع* `{fname}`\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"لمن تريد إرسال الرسالة؟", reply_markup=mk)

        elif tgt.startswith("all_") or tgt.startswith("vip_") or tgt.startswith("user_"):
            parts    = tgt.split("_", 1)
            target   = parts[0]
            fname    = parts[1] if len(parts) > 1 else ""
            role_map = {"all": None, "vip": ROLE_VIP, "user": ROLE_USER}
            labels   = {"all": "الكل", "vip": "VIP فقط", "user": "عادي فقط"}
            user_states[uid] = {
                "action":      "bcast_with_file",
                "file":        fname,
                "role_filter": role_map.get(target),
                "label":       labels.get(target, "الكل"),
            }
            safe_send(call.message.chat.id,
                f"📢 رسالة لـ *{labels.get(target,'الكل')}* مع معلومات `{fname}`\n"
                f"اكتب نص الرسالة اللي هتتبعث:\n"
                f"_(هيتضاف تلقائياً اسم الملف وحالته)_")

        elif tgt.startswith("cancel_"):
            user_states.pop(uid, None)
            safe_send(call.message.chat.id, "❌ تم إلغاء الإرسال.")


        bot.answer_callback_query(call.id)

        if tgt.startswith("reply_"):
            target_uid = tgt[6:]
            if not is_staff(uid):
                bot.answer_callback_query(call.id, "❌ للأدمن فقط"); return
            admin_chat_with[uid] = target_uid
            name = db["users"].get(target_uid, {}).get("name", "؟")
            mk_cancel = types.InlineKeyboardMarkup()
            mk_cancel.add(types.InlineKeyboardButton("❌ إنهاء المحادثة", callback_data="chat_end"))
            safe_send(call.message.chat.id,
                f"💬 *أنت الآن تتحدث مع:*\n"
                f"👤 *{name}* | 🆔 `{target_uid}`\n\n"
                f"📝 اكتب رسالتك أو أرسل ملف/صورة/صوت وهيوصله مباشرة.\n"
                f"اضغط ❌ إنهاء المحادثة للخروج.",
                reply_markup=mk_cancel)
            # إشعار المستخدم إن الأدمن بدأ محادثة
            user_chat_open.add(target_uid)
            try:
                mk_user = types.InlineKeyboardMarkup()
                mk_user.add(types.InlineKeyboardButton("💬 رد", callback_data="open_chat"))
                safe_send(int(target_uid),
                    "📩 *الأدمن فتح معك محادثة مباشرة!*\n"
                    "اكتب ردك وهيوصله فوراً 🚀",
                    reply_markup=mk_user)
            except: pass

        elif tgt == "end":
            target = admin_chat_with.pop(uid, None)
            if target:
                user_chat_open.discard(target)
                name = db["users"].get(target, {}).get("name", "؟")
                safe_send(call.message.chat.id,
                    f"✅ انتهت المحادثة مع *{name}*.",
                    reply_markup=get_kb(uid))
                try:
                    safe_send(int(target),
                        "🔚 الأدمن أنهى المحادثة.\nلو عندك استفسار اضغط 🎫 تذكرة دعم.",
                        reply_markup=get_kb(target))
                except: pass
            else:
                safe_send(call.message.chat.id, "مفيش محادثة مفتوحة.", reply_markup=get_kb(uid))

        elif tgt.startswith("ignore_"):
            target_uid = tgt[7:]
            user_chat_open.discard(target_uid)
            safe_send(call.message.chat.id, f"🔕 تم تجاهل رسالة {target_uid}.")

        elif tgt.startswith("unblock_"):
            target_uid = tgt[8:]
            blocked = db.get("chat_blocked", [])
            if target_uid in blocked:
                blocked.remove(target_uid)
                save()
            name = db["users"].get(target_uid, {}).get("name", "؟")
            bot.answer_callback_query(call.id, f"✅ رُفع حظر {name}")
            safe_send(call.message.chat.id, f"✅ تم رفع حظر التواصل عن {name}.")

        elif tgt.startswith("block_"):
            target_uid = tgt[6:]
            user_chat_open.discard(target_uid)
            db.setdefault("chat_blocked", [])
            if target_uid not in db["chat_blocked"]:
                db["chat_blocked"].append(target_uid)
                save()
            name = db["users"].get(target_uid, {}).get("name", "؟")
            safe_send(call.message.chat.id,
                f"🔕 تم حظر التواصل من *{name}*.\nلن تصله رسائله بعد الآن.")



    elif act == "open":
        if tgt == "chat":
            bot.answer_callback_query(call.id)
            user_chat_open.add(uid)
            mk_cancel = types.InlineKeyboardMarkup()
            mk_cancel.add(types.InlineKeyboardButton("❌ إنهاء", callback_data="chat_end_user"))
            safe_send(call.message.chat.id,
                "💬 *وضع التواصل مع الأدمن مفعّل!*\n"
                "اكتب رسالتك وستصل للأدمن مباشرة.\n"
                "اضغط ❌ إنهاء للخروج.",
                reply_markup=mk_cancel)

        elif tgt == "chat_end_user":
            user_chat_open.discard(uid)
            safe_send(call.message.chat.id,
                "✅ تم إنهاء وضع التواصل.",
                reply_markup=get_kb(uid))


    """تطبيق إجراء على مستخدم"""
    if target_uid not in db["users"]:
        bot.answer_callback_query(call.id,"❌ مستخدم غير موجود"); return
    role_map = {"admin": ROLE_ADMIN, "vip": ROLE_VIP, "user": ROLE_USER, "ban": "banned"}
    notify_map = {
        "admin": "👑 تمت ترقيتك لـ أدمن!",
        "vip":   "⭐ تمت ترقيتك لـ VIP!",
        "user":  "👤 تم تغيير دورك لـ User.",
        "ban":   "🚫 تم حظرك.",
        "unban": "✅ رُفع الحظر عنك."
    }
    if action == "unban":
        db["users"][target_uid]["role"] = ROLE_USER
    elif action in role_map:
        db["users"][target_uid]["role"] = role_map[action]
    save()
    try: safe_send(int(target_uid), notify_map.get(action,""), reply_markup=get_kb(target_uid))
    except: pass
    bot.answer_callback_query(call.id, f"✅ تم")
    try:
        bot.edit_message_text(
            f"✅ تم تطبيق `{action}` على `{target_uid}`",
            call.message.chat.id, call.message.message_id)
    except: pass

# ══════════════════════════════════════════════════════════════
#  Shell
# ══════════════════════════════════════════════════════════════
def run_shell(chat_id, cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        out = (r.stdout+r.stderr).strip() or "(لا يوجد output)"
        db["stats"]["commands"] = db["stats"].get("commands",0)+1; save()
        if len(out)>3500: out=out[-3500:]+"\n...(مقطوع)"
        safe_send(chat_id, f"\n{out}\n")
    except subprocess.TimeoutExpired:
        safe_send(chat_id,"⏱ 30 ثانية انتهت")
    except Exception as e:
        safe_send(chat_id, f"❌ {e}")

# ══════════════════════════════════════════════════════════════
#  المعالج الرئيسي
# ══════════════════════════════════════════════════════════════
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    uid = reg_user(m)
    if uid in user_chat_open and not is_staff(uid):
        if uid not in db.get("chat_blocked", []):
            _send_to_admin(uid, m.caption, m)
            safe_reply(m, "📨 الصورة وصلت للأدمن ✅")
        else:
            safe_reply(m, "🔕 تواصلك محظور.")
        return
    if is_staff(uid) and uid in admin_chat_with:
        target = admin_chat_with[uid]
        name = db["users"].get(target, {}).get("name", "؟")
        ok = _send_to_user(target, None, m)
        safe_reply(m, f"✅ الصورة وصلت لـ {name}" if ok else f"❌ فشل")

@bot.message_handler(content_types=['voice'])
def handle_voice(m):
    uid = reg_user(m)
    if uid in user_chat_open and not is_staff(uid):
        if uid not in db.get("chat_blocked", []):
            _send_to_admin(uid, None, m)
            safe_reply(m, "📨 الرسالة الصوتية وصلت للأدمن ✅")
        else:
            safe_reply(m, "🔕 تواصلك محظور.")
        return
    if is_staff(uid) and uid in admin_chat_with:
        target = admin_chat_with[uid]
        name = db["users"].get(target, {}).get("name", "؟")
        ok = _send_to_user(target, None, m)
        safe_reply(m, f"✅ الصوت وصل لـ {name}" if ok else f"❌ فشل")

@bot.message_handler(func=lambda m: True)
def main_handler(m):
    uid  = reg_user(m)
    role = get_role(uid)
    text = m.text or ""

    # ══ وضع الصيانة ══════════════════════
    if db["settings"].get("maintenance") and role not in [ROLE_OWNER, ROLE_ADMIN]:
        safe_reply(m, "🔧 البوت في وضع الصيانة حالياً. حاول لاحقاً ✅"); return

    # ══ Blacklist ══════════════════════════
    if is_blacklisted(uid):
        safe_reply(m, "🚫 أنت محظور من استخدام البوت."); return

    # ══════════════════════════════════════════════════════
    #  📡 نظام المحادثة المباشرة — توجيه الرسائل
    # ══════════════════════════════════════════════════════

    # ➤ الأدمن في وضع المحادثة → أرسل للمستخدم
    if is_staff(uid) and uid in admin_chat_with:
        target = admin_chat_with[uid]
        # زر إنهاء المحادثة
        if text and text.strip() in ["❌ إنهاء المحادثة", "/end", "end"]:
            admin_chat_with.pop(uid, None)
            user_chat_open.discard(target)
            name = db["users"].get(target, {}).get("name", "؟")
            safe_reply(m, f"✅ انتهت المحادثة مع {name}.", reply_markup=get_kb(uid))
            try:
                safe_send(int(target),
                    "🔚 الأدمن أنهى المحادثة.\nلو عندك استفسار اضغط 🎫 تذكرة دعم.",
                    reply_markup=get_kb(target))
            except: pass
            return
        # إرسال الرسالة/الملف/الصورة/الصوت للمستخدم
        name = db["users"].get(target, {}).get("name", "؟")
        ok = _send_to_user(target, text, m)
        if ok:
            safe_reply(m, f"✅ وصلت لـ {name}")
        else:
            safe_reply(m, f"❌ فشل الإرسال لـ {target} — ربما حذف البوت")
            admin_chat_with.pop(uid, None)
        return

    # ➤ المستخدم في وضع التواصل → أرسل للأدمن
    if uid in user_chat_open and not is_staff(uid):
        if text and text.strip() in ["❌ إنهاء", "/end"]:
            user_chat_open.discard(uid)
            safe_reply(m, "✅ تم إنهاء وضع التواصل.", reply_markup=get_kb(uid))
            # إشعار الأدمن
            for a_uid, t_uid in list(admin_chat_with.items()):
                if t_uid == uid:
                    admin_chat_with.pop(a_uid, None)
                    name = db["users"].get(uid, {}).get("name", "؟")
                    try: safe_send(int(a_uid), f"🔚 {name} أنهى المحادثة.", reply_markup=get_kb(a_uid))
                    except: pass
            return
        # إرسال للأدمن
        if uid not in db.get("chat_blocked", []):
            _send_to_admin(uid, text, m)
            safe_reply(m, "📨 وصلت للأدمن ✅")
        else:
            safe_reply(m, "🔕 تواصلك محظور حالياً.")
        return



    # ══ فحص الروابط المشبوهة ══════════════
    if text and contains_suspicious_url(text) and role == ROLE_USER:
        check_suspicious(uid, f"رابط مشبوه: {text[:50]}")
        safe_reply(m, "⚠️ الرسالة دي فيها روابط مشبوهة."); return

    # ══ Anti-Spam ════════════════════════
    if role not in [ROLE_OWNER, ROLE_ADMIN]:
        if is_spam(uid):
            safe_reply(m, "⏳ كثير رسايل — انتظر دقيقة")
            return

    # ══ لو البوت مقفول ════════════════════
    if db.get("locked") and role == ROLE_USER:
        safe_reply(m, "🔒 البوت مقفول حالياً."); return

    # ══ AI Mode — يجي قبل States عشان ما يتحذفش ══
    # قائمة أزرار الكيبورد — AI ما يلتقطهاش
    KEYBOARD_BUTTONS = {
        "📂 ملفاتي","📊 إحصائياتي","▶️ تشغيل ملف","⏹ إيقاف ملف",
        "🔎 فحص ملف","📋 لوج ملفاتي","🤖 ذكاء اصطناعي","🎫 تذكرة دعم",
        "🔑 توليد كلمة سر","ℹ️ مساعدة","⭐ مميزات VIP","📡 السيرفر",
        "🕐 وقت التشغيل","❌ خروج Shell","🔒 قفل البوت","🛡 أمان الملفات",
        "🖥 الاستضافة","⚙️ الحاويات","👥 المستخدمون","📈 تقرير فوري",
        "💀 إيقاف الكل","🔄 تحديث البوت","💾 باك أب","🛡 لوحة الأمان",
        # أزرار الأقسام
        "📦 قسم الرفع","👑 قسم الأدمن","🖥 قسم السيرفر",
        "👥 قسم المستخدمين","💬 قسم التواصل","🔧 قسم الأدوات",
        "🔙 الرئيسية",
        # أزرار داخل الأقسام
        "🔄 إعادة تشغيل ملف","📊 إحصائيات المستخدمين",
        "📬 صندوق الرسائل","💬 محادثة مستخدم","🔕 المحظورون من التواصل",
        "💬 تواصل مع الأدمن",
    }
    if user_states.get(uid, {}).get("action") == "ai_chat":
        if text not in KEYBOARD_BUTTONS and not text.startswith("/"):
            bot.send_chat_action(m.chat.id, "typing")
            ai_mode = user_states[uid].get("mode", "chat")
            if ai_mode == "code":
                prompt = f"حلل الكود ده:\n1. إيه بيعمل\n2. أي مشاكل\n3. اقتراحات\n\n```\n{m.text}\n```"
                reply  = ai_ask(prompt)
            else:
                reply = ai_ask(m.text, uid)
            mk2 = types.InlineKeyboardMarkup(row_width=3)
            mk2.add(
                types.InlineKeyboardButton("🔄 استمرار", callback_data="ai_continue"),
                types.InlineKeyboardButton("🗑 مسح",     callback_data="ai_clear"),
                types.InlineKeyboardButton("❌ إنهاء",   callback_data="ai_end"),
            )
            def send_stream():
                ai_stream_reply(m.chat.id, reply, m.message_id)
                try: safe_send(m.chat.id, "─────────────", reply_markup=mk2)
                except: pass
            threading.Thread(target=send_stream, daemon=True).start()
            return
        # لو ضغط زرار كيبورد وهو في AI — اخرج من وضع AI تلقائياً
        if text in KEYBOARD_BUTTONS:
            user_states.pop(uid, None)
            ai_sessions.pop(uid, None)

    # ══ States ════════════════════════════
    # لو ضغط زرار — امسح الـ state وكمل
    if uid in user_states and (text in KEYBOARD_BUTTONS or text.startswith("/")):
        user_states.pop(uid, None)

    if uid in user_states:
        state = user_states.pop(uid)
        act   = state.get("action","")

        if act == "add_env":
            if "=" in text:
                k,v = text.split("=",1)
                db.setdefault("envs",{}).setdefault(state["file"],{})[k.strip()] = v.strip(); save()
                safe_reply(m, f"✅ {k.strip()}={v.strip()}")
            else:
                safe_reply(m,"❌ الصيغة: KEY=VALUE")

        elif act == "pip_install":
            def do_pip():
                install_pkgs(text.strip().split(), m.chat.id)
            executor.submit(do_pip)

        elif act == "schedule":
            try:
                datetime.strptime(text.strip(),"%Y-%m-%d %H:%M")
                db.setdefault("scheduled",[]).append({"name":state["file"],"run_at":text.strip(),"done":False}); save()
                safe_reply(m, f"⏰ جُدوِل {state['file']} في {text.strip()}")
            except:
                safe_reply(m,"❌ الصيغة: YYYY-MM-DD HH:MM")

        elif act == "broadcast":
            if not is_staff(uid): return
            count = 0
            for u in list(db["users"].keys()):
                try:
                    bot.send_message(int(u), f"📢 رسالة من الإدارة:\n{text}")
                    count += 1; time.sleep(0.05)
                except: pass
            safe_reply(m, f"📢 أُرسلت لـ {count} مستخدم.")

        elif act == "check_ip":
            def do_ip():
                try:
                    import urllib.request
                    target = text.strip()
                    url = f"http://ip-api.com/json/{target}?fields=status,country,regionName,city,isp,org,as,query,lat,lon,timezone"
                    with urllib.request.urlopen(url, timeout=10) as r:
                        data = json.loads(r.read())
                    if data.get("status") == "success":
                        safe_reply(m,
                            f"🌐 *فحص IP: {data.get('query')}*\n━━━━━━━━━━━━━━━━━\n"
                            f"🌍 الدولة: `{data.get('country')}`\n"
                            f"🏙 المدينة: `{data.get('city')}`\n"
                            f"📡 ISP: `{data.get('isp')}`\n"
                            f"🏢 المنظمة: `{data.get('org')}`\n"
                            f"🕐 التوقيت: `{data.get('timezone')}`\n"
                            f"📍 {data.get('lat')}, {data.get('lon')}")
                    else:
                        safe_reply(m, f"❌ مش قادر يفحص {target}")
                except Exception as e:
                    safe_reply(m, f"❌ خطأ: {str(e)[:200]}")
            executor.submit(do_ip)

        elif act == "add_note":
            if text != "/skip":
                db.setdefault("notes",[]).append(f"{text} — {datetime.now().strftime('%d/%m %H:%M')}"); save()
                safe_reply(m, "📝 تم حفظ الملاحظة ✅")

        elif act == "pin_msg":
            if role != ROLE_OWNER: return
            count = 0
            for u in list(db["users"].keys()):
                try:
                    bot.send_message(int(u), f"📌 رسالة مثبّتة:\n\n{text}")
                    count += 1; time.sleep(0.05)
                except: pass
            safe_reply(m, f"📌 تم الإرسال لـ {count} مستخدم")

            if not is_staff(uid): return
            try:
                amount = int(text.strip())
                if target not in db["users"]:
                    safe_reply(m, "❌ المستخدم مش موجود"); return
                safe_reply(m, f"✅ تم إرسال {amount} نقطة لـ {db['users'][target].get('name','؟')}")
            except:
                safe_reply(m, "❌ ابعت رقم صحيح")

        elif act.startswith("msg_user_"):
            if not is_staff(uid): return
            target = act.replace("msg_user_","")
            try:
                safe_send(int(target), f"📩 رسالة من الأدمن:\n\n{text}")
                safe_reply(m, "✅ تم إرسال الرسالة")
            except:
                safe_reply(m, "❌ فشل الإرسال")
            parts = text.strip().split(maxsplit=2)
            if len(parts) < 2:
                safe_reply(m, "❌ الصيغة: ID النقطة السبب"); return
            target_uid = parts[0]
            try:
                amount = int(parts[1])
                reason = parts[2] if len(parts)>2 else "من الأدمن 🎁"
            except:
                safe_reply(m, "❌ النقطة لازم يكون رقم"); return
            if target_uid not in db["users"]:
                safe_reply(m, "❌ المستخدم مش موجود"); return
            safe_reply(m, f"✅ تم إرسال {amount} نقطة لـ {target_uid}")

        elif act == "edit_token":
            fname   = state.get("file", "")
            then_id = state.get("then_id", False)
            new_tok = text.strip()
            # تحقق من شكل التوكن
            import re as _re
            if not _re.match(r'^\d{8,12}:[A-Za-z0-9_-]{35,}$', new_tok):
                safe_reply(m,
                    "❌ التوكن غير صحيح!\n"
                    "الشكل الصحيح: `1234567890:AAFxxx...`\n"
                    "أرسله مرة تانية أو احصل عليه من @BotFather")
                user_states[uid] = state  # أعد الـ state
                return
            # تعديل التوكن في الملف
            ok, msg_result = _edit_file_value(fname, "token", new_tok)
            if ok:
                if then_id:
                    # انتقل لخطوة الـ ID
                    user_states[uid] = {"action": "edit_admin_id", "file": fname, "from_both": True}
                    mk_skip = types.InlineKeyboardMarkup()
                    mk_skip.add(
                        types.InlineKeyboardButton("⏭ تخطي الـ ID", callback_data=f"edit_skip_id_{fname}"),
                        types.InlineKeyboardButton("❌ إلغاء",        callback_data=f"edit_cancel_{fname}"),
                    )
                    safe_reply(m,
                        f"✅ *تم تعديل التوكن!*\n\n"
                        f"*الخطوة 2/2:* أرسل الـ Admin ID الجديد:\n"
                        f"مثال: `123456789`\n\n"
                        f"_(يمكنك الضغط ⏭ تخطي إذا لا تريد تعديله)_", reply_markup=mk_skip)
                else:
                    # انتهى التعديل — اعرض أزرار الرفع
                    _show_edit_done(m, fname, "✅ تم تعديل التوكن بنجاح!")
            else:
                safe_reply(m, f"❌ فشل تعديل التوكن:\n{msg_result}")
                user_states[uid] = state

        elif act == "edit_admin_id":
            fname       = state.get("file", "")
            from_both   = state.get("from_both", False)
            new_id      = text.strip()
            if not new_id.isdigit() or len(new_id) < 5:
                safe_reply(m,
                    "❌ الـ ID غير صحيح! لازم يكون أرقام فقط.\n"
                    "مثال: `123456789`\n"
                    "استخدم /id عشان تعرف ID بتاعك")
                user_states[uid] = state
                return
            ok, msg_result = _edit_file_value(fname, "admin_id", new_id)
            if ok:
                label = "✅ تم تعديل التوكن والـ ID بنجاح!" if from_both else "✅ تم تعديل الـ ID بنجاح!"
                _show_edit_done(m, fname, label)
            else:
                safe_reply(m, f"❌ فشل تعديل الـ ID:\n{msg_result}")
                user_states[uid] = state

        elif act == "bcast_with_file":
            fname       = state.get("file", "")
            role_filter = state.get("role_filter")
            label       = state.get("label", "الكل")
            info        = db["files"].get(fname, {})
            active_txt  = "✅ شغّال" if info.get("active") else "⏸ متوقف"
            ext_icon    = {"py":"🐍","js":"⚡","sh":"🖥️"}.get(os.path.splitext(fname)[1].lstrip("."), "📄")
            full_msg    = (
                f"📢 *رسالة من الأدمن*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{text}\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{ext_icon} `{fname}` | {active_txt}"
            )
            count = notify_all(full_msg, role_filter)
            safe_reply(m,
                f"📢 *تم الإرسال لـ {count} مستخدم ({label})*\n"
                f"الرسالة:\n{text[:200]}")


            safe_reply(m,
                f"🎫 تم فتح تذكرة #{tid}\n"
                f"الأدمن هيرد عليك قريباً ✅")
            return

        elif act.startswith("cfg_set_"):
            if role != ROLE_OWNER: return
            key = act.replace("cfg_set_","")
            try:
                if key == "report_time":
                    db["daily_report_time"] = text.strip()
                    safe_reply(m, f"✅ وقت التقرير: {text.strip()}")
                else:
                    val = int(text.strip())
                    db["settings"][key] = val
                    safe_reply(m, f"✅ تم تغيير {key} إلى {val}")
                save()
            except:
                safe_reply(m, "❌ قيمة غير صحيحة")

        elif act == "search_user":
            if not is_staff(uid): return
            query = text.strip().lower()
            results = []
            for u, info in db["users"].items():
                if query in u or query in info.get("name","").lower():
                    r = info.get("role","user")
                    re_e = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤","banned":"🚫"}.get(r,"👤")
                    results.append(
                        f"{re_e} {info.get('name','؟')}\n"
                        f"   🆔 `{u}` | 📤{info.get('uploads',0)}\n"
                        f"   📅 {info.get('joined','؟')}"
                    )
            if not results:
                safe_reply(m, "❌ مفيش نتيجة.")
            else:
                safe_reply(m,
                    f"🔎 نتائج ({len(results)}):\n━━━━━━━━━━━━━━━━━\n" + "\n\n".join(results[:5]))

        elif act == "send_notif":
            if role != ROLE_OWNER: return
            role_filter = state.get("filter")
            count = notify_all(f"📣 إشعار من الأدمن:\n\n{text}", role_filter)
            safe_reply(m, f"✅ تم إرسال الإشعار لـ {count} مستخدم")
        elif act == "bl_add":
            if role != ROLE_OWNER: return
            target = text.strip()
            add_to_blacklist(target)
            # حظر من البوت كمان
            if target in db["users"]:
                db["users"][target]["role"] = "banned"; save()
            safe_reply(m, f"🚫 تم إضافة {target} للقائمة السوداء")

        elif act == "ticket_reply":
            tid = state.get("ticket_id")
            if tid and tid in db["tickets"]:
                db["tickets"][tid]["replies"].append({
                    "from": "admin", "msg": text,
                    "time": datetime.now().strftime('%H:%M')
                })
                ticket_uid = db["tickets"][tid]["uid"]
                save()
                try:
                    bot.send_message(int(ticket_uid),
                        f"📩 رد من الأدمن على تذكرتك #{tid}:\n\n{text}")
                except: pass
                safe_reply(m, f"✅ تم الرد على التذكرة #{tid}")

        elif act == "rename_file":
            old_name = state["file"]
            new_name = text.strip()
            if old_name in db["files"] and new_name:
                old_path = db["files"][old_name]["path"]
                new_path = f"ELITE_HOST/{new_name}"
                try:
                    os.rename(old_path, new_path)
                    db["files"][new_name] = db["files"].pop(old_name)
                    db["files"][new_name]["path"] = new_path
                    if old_name in running_procs:
                        running_procs[new_name] = running_procs.pop(old_name)
                    save()
                    safe_reply(m, f"✅ تم تغيير الاسم:\n{old_name} ← {new_name}")
                except Exception as e:
                    safe_reply(m, f"❌ {e}")

        elif act.startswith("panel_"):
            if not is_staff(uid): return
            sub = act.replace("panel_","")
            target_uid = text.strip()
            if target_uid not in db["users"]:
                safe_reply(m,"❌ ID غير موجود."); return
            target_role = db["users"][target_uid].get("role","user")
            mk = kb_user_actions(target_uid, target_role)
            name = db["users"][target_uid].get("name","؟")
            safe_reply(m,
                f"👤 *المستخدم:* {name}\n🆔 `{target_uid}`\nالدور: `{target_role}`", reply_markup=mk)
        return  # إنهاء أي state دايماً

    # ══ Shell Mode ════════════════════════
    if uid in shell_mode:
        if text == "❌ خروج Shell":
            shell_mode.discard(uid)
            safe_reply(m,"🔙 خرجت.", reply_markup=get_kb(uid))
        elif is_staff(uid):
            run_shell(m.chat.id, text)
        return

    # ══ أزرار الأقسام الرئيسية ════════════
    if text == "🔙 الرئيسية":
        safe_reply(m, "🏠 الرئيسية", reply_markup=get_kb(uid)); return

    if text == "📦 قسم الرفع":
        if not is_staff(uid): return
        safe_reply(m,
            "📦 *قسم الرفع والاستضافة*\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"📂 ملفات: `{len(db['files'])}` | ⚡ شغّالة: `{len(running_procs)}`\n"
            f"🚨 حجر: `{len(db.get('quarantine',[]))}`",
            reply_markup=kb_section_upload()); return

    if text == "👑 قسم الأدمن":
        if not is_staff(uid): return
        s = db["settings"]
        safe_reply(m,
            f"👑 *قسم الأدمن*\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"🔒 مقفول: {'✅' if db.get('locked') else '❌'} | "
            f"🔧 صيانة: {'✅' if s.get('maintenance') else '❌'}\n"
            f"🎫 تذاكر مفتوحة: `{sum(1 for t in db['tickets'].values() if t.get('status')=='open')}`",
            reply_markup=kb_section_admin()); return

    if text == "🖥 قسم السيرفر":
        if not is_staff(uid): return
        import psutil as _ps
        cpu  = _ps.cpu_percent(interval=0.5)
        mem  = _ps.virtual_memory().percent
        disk = _ps.disk_usage('/').percent
        safe_reply(m,
            f"🖥 *قسم السيرفر*\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"CPU: `{cpu}%` | RAM: `{mem}%` | Disk: `{disk}%`",
            reply_markup=kb_section_server()); return

    if text == "👥 قسم المستخدمين":
        if not is_staff(uid): return
        roles = {}
        for u, info in db["users"].items():
            r = info.get("role", "user")
            roles[r] = roles.get(r, 0) + 1
        safe_reply(m,
            f"👥 *قسم المستخدمين*\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"الكل: `{len(db['users'])}` | "
            f"⭐ VIP: `{roles.get('vip',0)}` | "
            f"🚫 محظور: `{roles.get('banned',0)}`",
            reply_markup=kb_section_users()); return

    if text == "💬 قسم التواصل":
        if not is_staff(uid): return
        active_chats = len(admin_chat_with)
        waiting      = len(user_chat_open)
        open_tix     = sum(1 for t in db["tickets"].values() if t.get("status") == "open")
        safe_reply(m,
            f"💬 *قسم التواصل*\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"📡 محادثات مفتوحة: `{active_chats}`\n"
            f"⏳ ينتظرون ردك: `{waiting}`\n"
            f"🎫 تذاكر مفتوحة: `{open_tix}`",
            reply_markup=kb_section_chat()); return

    if text == "🔧 قسم الأدوات":
        if not is_staff(uid): return
        safe_reply(m,
            "🔧 *قسم الأدوات*",
            reply_markup=kb_section_tools()); return

    if text == "🔄 إعادة تشغيل ملف":
        if not is_staff(uid): return
        running = [f for f in running_procs]
        if not running:
            safe_reply(m, "❌ مفيش ملفات شغالة حالياً."); return
        mk2 = types.InlineKeyboardMarkup(row_width=2)
        for f in running[:10]:
            mk2.add(types.InlineKeyboardButton(f"🔄 {f}", callback_data=f"rst_{f}"))
        safe_reply(m, "اختار الملف اللي عايز تعيد تشغيله:", reply_markup=mk2); return

    if text == "📊 إحصائيات المستخدمين":
        if not is_staff(uid): return
        roles = {}
        for u, info in db["users"].items():
            r = info.get("role", "user")
            roles[r] = roles.get(r, 0) + 1
        safe_reply(m,
            f"📊 *إحصائيات المستخدمين*\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"👥 الكل: `{len(db['users'])}`\n"
            f"🔱 مالك: `{roles.get('owner',1)}`\n"
            f"👑 أدمن: `{roles.get('admin',0)}`\n"
            f"⭐ VIP: `{roles.get('vip',0)}`\n"
            f"👤 عادي: `{roles.get('user',0)}`\n"
            f"🚫 محظور: `{roles.get('banned',0)}`"); return

    # ══ كل المستخدمين ════════════════════

    if text == "📂 ملفاتي" or text == "/myfiles":
        _show_files(m); return
    if text in ["ℹ️ مساعدة","ℹ️ المساعدة"]:
        _help(m); return
    if text in ["📡 السيرفر","📡 موارد السيرفر"]:
        _server_stats(m); return

        role    = get_role(uid)


    if text == "🤖 ذكاء اصطناعي":
        user_states[uid] = {"action": "ai_chat", "mode": "chat"}
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("💬 محادثة عامة",   callback_data="ai_mode_chat"),
            types.InlineKeyboardButton("🐍 تحليل كود",    callback_data="ai_mode_code"),
            types.InlineKeyboardButton("🔧 مساعدة برمجة", callback_data="ai_mode_prog"),
            types.InlineKeyboardButton("❌ إلغاء",         callback_data="ai_mode_cancel"),
        )
        safe_reply(m,
            "🤖 *الذكاء الاصطناعي — DeepSeek*\n━━━━━━━━━━━━━━━━━\n"
            "اختر النوع أو ابعت سؤالك مباشرة:", reply_markup=mk); return

    if text == "📊 إحصائياتي":
        uid_files = [f for f,v in db["files"].items() if v.get("owner")==uid]
        active    = sum(1 for f in uid_files if db["files"][f].get("active"))
        crashes   = sum(db["files"][f].get("crashes",0) for f in uid_files)
        total_kb  = sum(db["files"][f].get("size",0) for f in uid_files) // 1024
        uploads   = db["users"].get(uid,{}).get("uploads",0)
        safe_reply(m,
            f"📊 إحصائياتك\n━━━━━━━━━━━━━━━━━\n"
            f"📂 ملفاتك: {len(uid_files)} | ✅ شغالة: {active}\n"
            f"💥 كراشات: {crashes} | 📦 الحجم: {total_kb} KB\n"
            f"📤 رفعات: {uploads}\n"
            f"🆔 ID: {uid}"); return

    if text == "⭐ مميزات VIP":
        if role not in [ROLE_VIP, ROLE_ADMIN, ROLE_OWNER]:
            safe_reply(m,
                "⭐ مميزات VIP\n━━━━━━━━━━━━━━━━━\n"
                "🚀 تشغيل ملفات أكثر\n"
                "📡 إحصائيات السيرفر\n"
                "🕐 وقت التشغيل\n"
                "📋 لوج مباشر\n"
                "⚡ أولوية في الدعم"); return
        safe_reply(m,
            f"⭐ أنت {role.upper()} — تستمتع بكل المميزات!\n"
            "📂 ملفات غير محدودة\n"
            "📡 موارد السيرفر\n"
            "🕐 وقت التشغيل\n"
            "⚡ أولوية في الدعم"); return

    if text == "▶️ تشغيل ملف":
        uid_files = [f for f,v in db["files"].items() if v.get("owner")==uid and not v.get("active")]
        if not uid_files:
            safe_reply(m, "✅ كل ملفاتك شغالة أو مفيش ملفات."); return
        mk = types.InlineKeyboardMarkup(row_width=2)
        for f in uid_files[:10]:
            mk.add(types.InlineKeyboardButton(f"▶️ {f}", callback_data=f"utog_{f}"))
        safe_reply(m, "اختار الملف اللي عايز تشغّله:", reply_markup=mk); return

    if text == "⏹ إيقاف ملف":
        uid_files = [f for f,v in db["files"].items() if v.get("owner")==uid and v.get("active")]
        if not uid_files:
            safe_reply(m, "❌ مفيش ملفات شغالة."); return
        mk = types.InlineKeyboardMarkup(row_width=2)
        for f in uid_files[:10]:
            mk.add(types.InlineKeyboardButton(f"⏹ {f}", callback_data=f"ustop_{f}"))
        safe_reply(m, "اختار الملف اللي عايز توقفه:", reply_markup=mk); return

    if text == "📋 لوج ملفاتي":
        uid_files = [f for f,v in db["files"].items() if v.get("owner")==uid]
        if not uid_files:
            safe_reply(m, "📂 مفيش ملفات."); return
        mk = types.InlineKeyboardMarkup(row_width=2)
        for f in uid_files[:10]:
            mk.add(types.InlineKeyboardButton(f"📋 {f}", callback_data=f"log_{f}"))
        safe_reply(m, "اختار الملف اللي عايز تشوف لوجه:", reply_markup=mk); return

    if text == "💬 تواصل مع الأدمن":
        if is_staff(uid):
            safe_reply(m, "أنت أدمن — استخدم 💬 محادثة مستخدم لبدء محادثة."); return
        if uid in db.get("chat_blocked", []):
            safe_reply(m, "🔕 تواصلك مع الأدمن محظور حالياً."); return
        user_chat_open.add(uid)
        mk_cancel = types.InlineKeyboardMarkup()
        mk_cancel.add(types.InlineKeyboardButton("❌ إنهاء التواصل", callback_data="open_chat_end_user"))
        safe_reply(m,
            "💬 *وضع التواصل مع الأدمن مفعّل!*\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "✅ اكتب رسالتك أو أرسل ملف/صورة/صوت\n"
            "وستصل للأدمن مباشرة فوراً 🚀\n\n"
            "اضغط ❌ إنهاء التواصل للخروج.",
            reply_markup=mk_cancel)
        # إشعار الأدمن
        name = db["users"].get(uid, {}).get("name", "؟")
        mk_adm = types.InlineKeyboardMarkup()
        mk_adm.add(
            types.InlineKeyboardButton("💬 رد عليه", callback_data=f"chat_reply_{uid}"),
            types.InlineKeyboardButton("🔕 تجاهل",   callback_data=f"chat_ignore_{uid}"),
        )
        try:
            safe_send(ADMIN_ID,
                f"📡 *{name}* (`{uid}`) فتح وضع التواصل معك!", reply_markup=mk_adm)
        except: pass
        return

    # ══ للأدمن: صندوق الرسائل ════════════
    if text == "📬 صندوق الرسائل":
        if not is_staff(uid): return
        active_chats = list(admin_chat_with.items())
        open_users   = list(user_chat_open)
        lines = []
        if active_chats:
            lines.append("💬 *محادثات مفتوحة:*")
            for a, t in active_chats:
                aname = db["users"].get(a, {}).get("name", "؟")
                tname = db["users"].get(t, {}).get("name", "؟")
                lines.append(f"  👑 {aname} ↔️ 👤 {tname}")
        if open_users:
            lines.append("\n📡 *ينتظرون ردك:*")
            mk2 = types.InlineKeyboardMarkup(row_width=2)
            for u in open_users[:10]:
                name = db["users"].get(u, {}).get("name", "؟")
                lines.append(f"  👤 {name} (`{u}`)")
                mk2.add(types.InlineKeyboardButton(f"💬 {name[:15]}", callback_data=f"chat_reply_{u}"))
            if not lines:
                safe_reply(m, "📬 الصندوق فارغ — لا توجد محادثات مفتوحة."); return
            safe_reply(m,
                "📬 *صندوق الرسائل*\n━━━━━━━━━━━━━━━━━━━\n" + "\n".join(lines), reply_markup=mk2)
            return
        if not lines:
            safe_reply(m, "📬 الصندوق فارغ."); return
        safe_reply(m,
            "📬 *صندوق الرسائل*\n━━━━━━━━━━━━━━━━━━━\n" + "\n".join(lines))
        return

    if text == "💬 محادثة مستخدم":
        if not is_staff(uid): return
        # اختيار مستخدم للمحادثة
        users_list = [(u, info) for u, info in db["users"].items()
                      if int(u) != ADMIN_ID and u not in [str(a) for a in ADMIN_IDS]]
        if not users_list:
            safe_reply(m, "👥 لا يوجد مستخدمون بعد."); return
        mk2 = types.InlineKeyboardMarkup(row_width=2)
        for u, info in users_list[-20:]:
            role_e = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤"}.get(info.get("role","user"),"👤")
            mk2.add(types.InlineKeyboardButton(
                f"{role_e} {info.get('name','؟')[:15]}",
                callback_data=f"chat_reply_{u}"
            ))
        safe_reply(m, "💬 اختر المستخدم اللي عايز تكلمه:", reply_markup=mk2)
        return

    if text == "🔕 المحظورون من التواصل":
        if not is_staff(uid): return
        blocked = db.get("chat_blocked", [])
        if not blocked:
            safe_reply(m, "✅ لا يوجد محظورون من التواصل."); return
        mk2 = types.InlineKeyboardMarkup(row_width=2)
        lines = []
        for u in blocked:
            name = db["users"].get(u, {}).get("name", "؟")
            lines.append(f"🔕 `{u}` — {name}")
            mk2.add(types.InlineKeyboardButton(f"✅ رفع حظر {name[:12]}", callback_data=f"chat_unblock_{u}"))
        safe_reply(m,
            f"🔕 *محظورو التواصل ({len(blocked)}):*\n" + "\n".join(lines), reply_markup=mk2)
        return



    if text == "🖥 الاستضافة":
        total = sum(v.get("size",0) for v in db["files"].values())//1024
        safe_reply(m,
            f"⚡ *الاستضافة*\n━━━━━━━━━━━━━━━━━\n"
            f"📂 ملفات: `{len(db['files'])}` | 💾 `{total} KB`\n"
            f"🔄 نشط: `{len(running_procs)}`\n"
            f"🚨 حجر: `{len(db.get('quarantine',[]))}`")

    elif text == "⚙️ الحاويات":
        if not db["files"]:
            safe_reply(m,"📂 لا توجد ملفات."); return
        for fname,info in db["files"].items():
            st = "✅ يعمل" if info.get("active") else "❌ متوقف"
            ar = " 🔁" if info.get("auto_restart") else ""
            safe_send(m.chat.id,
                f"📄 *{fname}*{ar}\n{st} | 👤`{info.get('owner','؟')}` | 📦`{info.get('size',0)//1024}KB`", reply_markup=kb_file(fname))

    elif text == "💀 إيقاف الكل":
        c = kill_all_procs()
        db["stats"]["kills"] = db["stats"].get("kills",0)+1; save()
        safe_reply(m, f"💀 أُوقفت {c} عملية بالقوة.")

    elif text == "📡 موارد السيرفر":
        _server_stats(m)

    elif text == "📋 السجلات":
        p = "LOGS/bot.log"
        if os.path.exists(p):
            with open(p,'r',encoding='utf-8',errors='replace') as f:
                lines = f.readlines()[-25:]
            out = "".join(lines)
            if len(out)>3800: out=out[-3800:]
            safe_reply(m, f"\n{out}\n")

    elif text == "📊 الإحصائيات":
        s = db["stats"]
        safe_reply(m,
            f"📊 *الإحصائيات*\n━━━━━━━━━━━━━━━━━\n"
            f"📤 رفعات: `{s.get('uploads',0)}`\n"
            f"💀 إيقافات: `{s.get('kills',0)}`\n"
            f"🖥️ Shell: `{s.get('commands',0)}`\n"
            f"🔁 إعادات: `{s.get('restarts',0)}`\n"
            f"🚨 محجوز: `{s.get('blocked',0)}`\n"
            f"👥 مستخدمون: `{len(db['users'])}`")

    elif text == "👥 المستخدمون":
        lines = []
        for u,info in list(db["users"].items())[:15]:
            r = info.get("role","user")
            e = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤","banned":"🚫"}.get(r,"👤")
            lines.append(f"{e} `{u}` — {info.get('name','؟')}")
        safe_reply(m,
            f"👥 *المستخدمون ({len(db['users'])}):*\n" + "\n".join(lines))

    elif text == "🔐 لوحة الأدمن":
        if role != ROLE_OWNER:
            safe_reply(m,"❌ للمالك فقط."); return
        safe_reply(m,
            "🔐 *لوحة التحكم الكاملة*\n━━━━━━━━━━━━━━━━━\nاختر عملية:", reply_markup=kb_admin_panel())

    elif text == "🧹 تطهير":
        for n in list(running_procs.keys()): stop_file(n)
        try:
            shutil.rmtree("ELITE_HOST"); os.makedirs("ELITE_HOST",exist_ok=True)
            db["files"].clear(); save()
        except Exception as e: log.error(f"Clean: {e}")
        safe_reply(m,"🧹 تم التطهير.")

    elif text == "🖥️ Shell":
        mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
        mk.add("❌ خروج Shell")
        shell_mode.add(uid)
        safe_reply(m,"🖥️ Shell نشط — اكتب أي أمر Linux.", reply_markup=mk)

    elif text == "📁 الملفات":
        files = os.listdir("ELITE_HOST")
        if not files:
            safe_reply(m,"📁 فارغ."); return
        lines = [f"📄 `{f}` — {os.path.getsize(f'ELITE_HOST/{f}')//1024} KB" for f in files]
        mk = types.InlineKeyboardMarkup()
        for f in files[:8]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dwn_{f}"))
        safe_reply(m,"📁 ELITE\\_HOST:\n"+"\n".join(lines), reply_markup=mk)

    elif text == "⏰ المجدولة":
        tasks = [t for t in db.get("scheduled",[]) if not t.get("done")]
        lines = [f"📄 `{t['name']}` ← `{t['run_at']}`" for t in tasks] or ["لا توجد."]
        safe_reply(m,"⏰ المجدولة:\n"+"\n".join(lines))
        if db["files"]:
            mk = types.InlineKeyboardMarkup()
            for n in list(db["files"].keys())[:8]:
                mk.add(types.InlineKeyboardButton(f"⏰ {n}", callback_data=f"sched_{n}"))
            safe_send(m.chat.id,"اختر ملفاً:", reply_markup=mk)

    elif text == "🔍 مراقبة العمليات":
        if not running_procs:
            safe_reply(m,"🔍 لا توجد عمليات."); return
        lines = []
        for n,info in running_procs.items():
            up = int(time.time()-info.get("started",time.time()))
            h,r=divmod(up,3600); mn,s=divmod(r,60)
            try:
                p=psutil.Process(info["pid"])
                lines.append(f"📄`{n}` PID:`{info['pid']}` CPU:`{p.cpu_percent(0.1)}%` RAM:`{p.memory_info().rss//1024//1024}MB` ⏱`{h:02d}:{mn:02d}:{s:02d}`")
            except: lines.append(f"📄`{n}` ⚠️ انتهت")
        safe_reply(m,"🔍 العمليات:\n\n"+"\n\n".join(lines))

    elif text == "🚨 الحجر الصحي":
        q = db.get("quarantine",[])
        if not q:
            safe_reply(m,"✅ الحجر فارغ."); return
        for entry in q:
            mk = types.InlineKeyboardMarkup(row_width=2)
            mk.add(
                types.InlineKeyboardButton("✅ موافقة",  callback_data=f"qapprove_{entry['fname']}"),
                types.InlineKeyboardButton("🗑 حذف",     callback_data=f"qdelete_{entry['fname']}")
            )
            safe_send(m.chat.id,
                f"🚨 *{entry['fname']}*\n"
                f"👤 `{entry['uid']}` | 🕐 {entry['time']}\n"
                f"🔴 " + "\n🔴 ".join(entry.get("dangers",[])), reply_markup=mk)

    elif text == "💾 باك أب":
        if not is_staff(uid): return
        try:
            if os.path.exists(DB_FILE):
                with open(DB_FILE,'rb') as f:
                    bot.send_document(m.chat.id, f,
                        caption=f"💾 *باك أب قاعدة البيانات*\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            else:
                safe_reply(m,"❌ لا توجد قاعدة بيانات.")
        except Exception as e:
            safe_reply(m, f"❌ {e}")

    elif text == "📦 تثبيت مكاتب":
        if not is_staff(uid): return
        user_states[uid] = {"action":"pip_install","file":None}
        safe_reply(m,
            "📦 اكتب المكاتب اللي عايز تثبّتها:\nمثال: `requests flask aiohttp`")

    elif text == "🔎 فحص ملف":
        user_states[uid] = {"action":"scan_only"}
        safe_reply(m,
            "🔎 *ابعت الملف اللي عايز تفحصه*\n"
            "هيبعتلك:\n"
            "• ✅ آمن أو ⚠️ مشاكل\n"
            "• 🤖 وجود التوكن والأدمن ID\n"
            "• 📦 المكاتب المحتاجة\n"
            "بدون ما يتشغّل أو يترفع")

    elif text == "🔄 تحديث البوت":
        if role != ROLE_OWNER: return
        safe_reply(m,
            "🔄 *تحديث البوت*\n━━━━━━━━━━━━━━━━━\n"
            "ابعت الملف الجديد `bot.py` وهيتحدث تلقائياً.\n"
            "⚠️ البيانات مش هتتحذف.")
        user_states[uid] = {"action":"update_bot"}

    elif text == "📢 بث رسالة":
        if not is_staff(uid): return
        user_states[uid] = {"action":"broadcast"}
        safe_reply(m, "📢 اكتب الرسالة اللي عايز تبعتها لكل المستخدمين:")

    elif text == "🌐 فحص IP":
        if not is_staff(uid): return
        user_states[uid] = {"action":"check_ip"}
        safe_reply(m, "🌐 ابعت IP أو دومين عايز تفحصه:")

    elif text == "📝 ملاحظات":
        if role != ROLE_OWNER: return
        notes = db.get("notes", [])
        if not notes:
            safe_reply(m, "📝 لا توجد ملاحظات.")
        else:
            txt = "\n".join([f"• {n}" for n in notes[-10:]])
            safe_reply(m, f"📝 الملاحظات:\n{txt}")
        user_states[uid] = {"action":"add_note"}
        safe_send(m.chat.id, "اكتب ملاحظة جديدة أو /skip للتخطي:")

    elif text == "⚡ تسريع":
        if role != ROLE_OWNER: return
        import gc
        collected = gc.collect()
        safe_reply(m,
            f"⚡ *تم تنظيف الذاكرة*\n"
            f"🗑 محذوف: `{collected}` كائن\n"
            f"🔧 Threads: `{threading.active_count()}`\n"
            f"💾 RAM: `{psutil.virtual_memory().percent}%`")

    elif text == "🔒 قفل البوت":
        if role != ROLE_OWNER: return
        locked = db.get("locked", False)
        db["locked"] = not locked; save()
        state = "🔒 مقفول" if not locked else "🔓 مفتوح"
        safe_reply(m, f"البوت الآن: {state}\n{'المستخدمون الجدد لن يستطيعوا الرفع' if not locked else 'المستخدمون يستطيعون الرفع'}")

    elif text == "🗑 مسح السجلات":
        if role != ROLE_OWNER: return
        try:
            import glob as gl
            for f in gl.glob("LOGS/*.log"):
                open(f,'w').close()
            safe_reply(m, "🗑 تم مسح كل السجلات.")
        except Exception as e:
            safe_reply(m, f"❌ {e}")

    elif text == "🕐 وقت التشغيل":
        up = int(time.time() - BOT_START_TIME)
        d, r = divmod(up, 86400)
        h, r = divmod(r, 3600)
        mn, s = divmod(r, 60)
        safe_reply(m,
            f"🕐 *وقت التشغيل*\n━━━━━━━━━━━━━━━━━\n"
            f"⏱ `{d}` يوم `{h}` ساعة `{mn}` دقيقة `{s}` ثانية\n"
            f"🚀 بدأ: `{datetime.fromtimestamp(BOT_START_TIME).strftime('%Y-%m-%d %H:%M')}`\n"
            f"⚡ عمليات نشطة: `{len(running_procs)}`\n"
            f"🔧 Threads: `{threading.active_count()}`")

    elif text == "🔑 توليد كلمة سر":
        import secrets, string
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        pwd8  = ''.join(secrets.choice(chars) for _ in range(8))
        pwd16 = ''.join(secrets.choice(chars) for _ in range(16))
        pwd32 = ''.join(secrets.choice(chars) for _ in range(32))
        safe_reply(m,
            f"🔑 *كلمات سر عشوائية:*\n━━━━━━━━━━━━━━━━━\n"
            f"8 حروف: `{pwd8}`\n"
            f"16 حرف: `{pwd16}`\n"
            f"32 حرف: `{pwd32}`")

    elif text == "📌 تثبيت رسالة":
        if role != ROLE_OWNER: return
        user_states[uid] = {"action":"pin_msg"}
        safe_reply(m, "📌 اكتب الرسالة اللي عايز تثبّتها للكل:")

    elif text == "🌡 درجة CPU":
        try:
            temps = psutil.sensors_temperatures() if hasattr(psutil,'sensors_temperatures') else {}
            cpu_freq = psutil.cpu_freq()
            cpu_pct  = psutil.cpu_percent(interval=1, percpu=True)
            cores_txt = " | ".join([f"C{i}:`{p}%`" for i,p in enumerate(cpu_pct)])
            freq_txt  = f"`{cpu_freq.current:.0f}` MHz" if cpu_freq else "غير متاح"
            temp_txt  = "غير متاح"
            if temps:
                for k,v in temps.items():
                    if v: temp_txt = f"`{v[0].current}°C`"; break
            safe_reply(m,
                f"🌡 *مراقبة CPU*\n━━━━━━━━━━━━━━━━━\n"
                f"🔥 درجة الحرارة: {temp_txt}\n"
                f"⚡ التردد: {freq_txt}\n"
                f"📊 النوى: {cores_txt}")
        except Exception as e:
            safe_reply(m, f"❌ {e}")

    elif text == "📋 نسخ السجل":
        if not is_staff(uid): return
        p = "LOGS/bot.log"
        if os.path.exists(p):
            with open(p,'rb') as f:
                bot.send_document(m.chat.id, f, caption="📋 السجل الكامل")
        else:
            safe_reply(m, "❌ لا يوجد سجل.")

    elif text == "🔃 إعادة تشغيل الكل":
        if not is_staff(uid): return
        count = 0
        for fname, info in list(db["files"].items()):
            if info.get("active"):
                stop_file(fname)
                time.sleep(0.2)
                launch(info["path"], fname)
                count += 1
        safe_reply(m, f"🔃 تمت إعادة تشغيل {count} ملف")

    elif text == "🛡 أمان الملفات":
        if role != ROLE_OWNER: return
        protected = list(PROTECTED_FILES)
        threats   = [(u,sc) for u,sc in INTRUSION_SCORE.items() if sc >= 5]
        wm_files  = [f for f in db["files"] if db["files"][f].get("watermarked")]
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("📋 سجل الأمان",    callback_data="sec_log"),
            types.InlineKeyboardButton("🎯 نقاط الخطورة",  callback_data="sec_scores"),
            types.InlineKeyboardButton("🔒 ملفات محمية",   callback_data="sec_protected"),
            types.InlineKeyboardButton("🧹 مسح التهديدات", callback_data="sec_clear_sus"),
        )
        safe_reply(m,
            f"🛡 *أمان الملفات*\n━━━━━━━━━━━━━━━━━\n"
            f"🔒 ملفات محمية: {len(protected)}\n"
            f"⚠️ تهديدات نشطة: {len(threats)}\n"
            f"🔏 ملفات بعلامة مائية: {len(db['files'])}\n"
            f"📋 أحداث مسجلة: {len(SECURITY_LOG)}\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🚫 أي ملف محمي يتم رفضه تلقائياً\n"
            f"🔏 كل ملف بيتحمّل بيتوسم بـ ID صاحبه", reply_markup=mk)

    elif text == "📈 تقرير فوري":
        if not is_staff(uid): return
        s = db["stats"]
        roles = {}
        for u,info in db["users"].items():
            roles[info.get("role","user")] = roles.get(info.get("role","user"),0)+1
        mem  = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        up   = int(time.time()-BOT_START_TIME)
        h,r  = divmod(up,3600); mn,sc = divmod(r,60)
        safe_reply(m,
            f"📈 تقرير فوري\n━━━━━━━━━━━━━━━━━\n"
            f"🕐 تشغيل: {h}س {mn}د\n"
            f"👥 مستخدمون: {len(db['users'])} | ⭐ VIP: {roles.get('vip',0)}\n"
            f"📂 ملفات: {len(db['files'])} | ⚡ نشطة: {len(running_procs)}\n"
            f"📤 رفعات: {s.get('uploads',0)} | 🔁 إعادات: {s.get('restarts',0)}\n"
            f"CPU: {psutil.cpu_percent()}% | RAM: {mem.percent}% | Disk: {disk.percent}%")

    elif text == "🎫 التذاكر":
        if not is_staff(uid): return
        open_tickets = [(tid,t) for tid,t in db["tickets"].items() if t.get("status")=="open"]
        if not open_tickets:
            safe_reply(m, "✅ لا توجد تذاكر مفتوحة."); return
        for tid, t in open_tickets[:5]:
            name = db["users"].get(t["uid"],{}).get("name","؟")
            mk = types.InlineKeyboardMarkup()
            mk.add(
                types.InlineKeyboardButton("📩 رد", callback_data=f"treply_{tid}"),
                types.InlineKeyboardButton("✅ إغلاق", callback_data=f"tclose_{tid}")
            )
            safe_send(m.chat.id,
                f"🎫 #{tid}\n👤 {name} ({t['uid']})\n🕐 {t['created']}\n📝 {t['msg'][:200]}",
                reply_markup=mk)

    elif text == "🎫 تذكرة دعم":
        user_states[uid] = {"action":"open_ticket"}
        safe_reply(m,
            "🎫 اكتب مشكلتك أو سؤالك وهيوصل للأدمن فوراً:")

    elif text == "🚫 القائمة السوداء":
        if role != ROLE_OWNER: return
        bl = db.get("blacklist",[])
        if not bl:
            safe_reply(m, "✅ القائمة السوداء فارغة."); return
        lines = []
        for u in bl:
            name = db["users"].get(u,{}).get("name","؟")
            lines.append(f"🚫 `{u}` — {name}")
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("➕ حظر جديد", callback_data="bl_add"))
        safe_reply(m,
            f"🚫 القائمة السوداء ({len(bl)}):\n" + "\n".join(lines), reply_markup=mk)

    elif text == "🛡 لوحة الأمان":
        if role != ROLE_OWNER: return
        s       = db["settings"]
        threats = sum(1 for sc in INTRUSION_SCORE.values() if sc >= 5)
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("📋 سجل الأمان",      callback_data="sec_log"),
            types.InlineKeyboardButton("🎯 نقاط الخطورة",    callback_data="sec_scores"),
            types.InlineKeyboardButton("🧹 مسح السجل",       callback_data="sec_clear_log"),
            types.InlineKeyboardButton("🔐 تعيين الحماية",   callback_data="sec_reset"),
        )
        safe_reply(m,
            f"🛡 *لوحة الأمان المتقدمة*\n━━━━━━━━━━━━━━━━━\n"
            f"🚫 القائمة السوداء: {len(db.get('blacklist',[]))}\n"
            f"🚨 مشبوهون: {len(suspicious)}\n"
            f"🎯 تهديدات نشطة: {threats}\n"
            f"📋 أحداث مسجلة: {len(SECURITY_LOG)}\n"
            f"⏳ محظورون مؤقتاً: {len(spam_blocked)}\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📦 حجم أقصى: {s.get('max_file_size_kb',500)} KB\n"
            f"📂 ملفات/مستخدم: {s.get('max_files_per_user',5)}\n"
            f"📤 رفعات/دقيقة: {UPLOAD_LIMIT}\n"
            f"🔒 مقفول: {'✅' if db.get('locked') else '❌'}\n"
            f"🔧 صيانة: {'✅' if s.get('maintenance') else '❌'}", reply_markup=mk)

    elif text == "📡 المشبوهون":
        if role != ROLE_OWNER: return
        # دمج المشبوهين مع أصحاب نقاط الخطورة
        all_threats = {}
        for u in suspicious:
            all_threats[u] = all_threats.get(u, 0) + failed_cmds.get(u, 0)
        for u, sc in INTRUSION_SCORE.items():
            if sc >= 5:
                all_threats[u] = all_threats.get(u, 0) + sc
        if not all_threats:
            safe_reply(m, "✅ لا يوجد مستخدمون مشبوهون."); return
        mk = types.InlineKeyboardMarkup(row_width=2)
        lines = []
        for u, sc in sorted(all_threats.items(), key=lambda x: -x[1])[:10]:
            name = db["users"].get(u,{}).get("name","؟")
            role_e = "🚫" if db["users"].get(u,{}).get("role")=="banned" else "⚠️"
            lines.append(f"{role_e} `{u}` — {name}\n   نقاط الخطورة: {INTRUSION_SCORE.get(u,0)} | محاولات: {failed_cmds.get(u,0)}")
            mk.add(types.InlineKeyboardButton(f"👤 {name[:15]}", callback_data=f"uview_{u}"))
        mk.add(
            types.InlineKeyboardButton("🧹 مسح المشبوهين",  callback_data="sec_clear_sus"),
            types.InlineKeyboardButton("🚫 حظر الكل",       callback_data="sec_ban_all_sus"),
        )
        safe_reply(m,
            f"📡 *التهديدات ({len(all_threats)}):*\n━━━━━━━━━━━━━━━━━\n" + "\n".join(lines), reply_markup=mk)

    elif text == "🔐 إعادة تعيين حماية":
        if role != ROLE_OWNER: return
        spam_blocked.clear(); spam_counter.clear()
        upload_counter.clear(); failed_cmds.clear()
        INTRUSION_SCORE.clear(); download_counter.clear()
        safe_reply(m, "🔐 تم إعادة تعيين كل حدود الحماية ✅")
        if not is_staff(uid): return
        versions = db.get("file_versions",{})
        if not versions:
            safe_reply(m, "📜 لا توجد إصدارات محفوظة."); return
        lines = []
        for fname, vers in list(versions.items())[:10]:
            lines.append(f"📄 {fname} — {len(vers)} نسخة")
        mk = types.InlineKeyboardMarkup(row_width=1)
        for fname in list(versions.keys())[:5]:
            mk.add(types.InlineKeyboardButton(f"📄 {fname}", callback_data=f"ver_{fname}"))
        safe_reply(m,
            "📜 الملفات التي لها إصدارات محفوظة:\n" + "\n".join(lines),
            reply_markup=mk)

    elif text == "⚙️ الإعدادات":
        if role != ROLE_OWNER: return
        s = db["settings"]
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("📂 حد الملفات",    callback_data="cfg_max_files_per_user"),
            types.InlineKeyboardButton("📦 الحجم الأقصى",  callback_data="cfg_max_file_size_kb"),
            types.InlineKeyboardButton(
                "🔒 قفل البوت" if not db.get("locked") else "🔓 فتح البوت",
                callback_data="cfg_toggle_lock"),
            types.InlineKeyboardButton(
                "🔧 تفعيل الصيانة" if not s.get("maintenance") else "✅ إيقاف الصيانة",
                callback_data="cfg_toggle_maintenance"),
            types.InlineKeyboardButton("⏰ وقت التقرير",   callback_data="cfg_report_time"),
        )
        safe_reply(m,
            f"⚙️ إعدادات البوت\n━━━━━━━━━━━━━━━━━\n"
            f"📂 حد ملفات/مستخدم: {s.get('max_files_per_user',5)}\n"
            f"📦 حجم أقصى: {s.get('max_file_size_kb',500)} KB\n"
            f"🔒 مقفول: {'نعم' if db.get('locked') else 'لا'}\n"
            f"🔧 صيانة: {'نعم' if s.get('maintenance') else 'لا'}\n"
            f"⏰ وقت التقرير: {db.get('daily_report_time','08:00')}\n\n"
            f"اضغط على أي إعداد لتعديله:",
            reply_markup=mk)

    elif text == "🏆 المتصدرون":
        if not is_staff(uid): return
        sorted_users = sorted(db["users"].items(), key=lambda x: x[1].get("uploads",0), reverse=True)[:10]
        medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        lines = []
        for i,(u,info) in enumerate(sorted_users):
            re_e = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤"}.get(info.get("role","user"),"👤")
            lines.append(f"{medals[i]} {re_e} {info.get('name','؟')} — 📤{info.get('uploads',0)} رفعة")
        safe_reply(m, "🏆 أعلى 10 مستخدمين\n━━━━━━━━━━━━━━━━━\n" + "\n".join(lines))

    elif text == "🔎 بحث مستخدم":
        if not is_staff(uid): return
        user_states[uid] = {"action":"search_user"}
        safe_reply(m, "🔎 ابعت اسم أو ID المستخدم:")

    elif text == "📣 إشعار عام":
        if role != ROLE_OWNER: return
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("👥 الكل",     callback_data="notif_all"),
            types.InlineKeyboardButton("⭐ VIP فقط",  callback_data="notif_vip"),
            types.InlineKeyboardButton("👤 عادي فقط", callback_data="notif_user"),
        )
        safe_reply(m, "📣 لمن تريد الإشعار؟", reply_markup=mk)

# ══════════════════════════════════════════════════════════════
#  إشعار الأدمن عند رفع ملف — مع رسالة تأكيد للمستخدم
# ══════════════════════════════════════════════════════════════
def _edit_file_value(fname: str, field: str, new_val: str) -> tuple:
    """
    تعديل التوكن أو الـ Admin ID في ملف Python مباشرة
    field: 'token' | 'admin_id'
    يرجع (True, "ok") أو (False, "سبب الفشل")
    """
    import re as _re
    if fname not in db["files"]:
        return False, "الملف غير موجود في قاعدة البيانات"
    path = db["files"][fname].get("path", "")
    if not os.path.exists(path):
        return False, "الملف غير موجود على الديسك"
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        original = content

        if field == "token":
            # استبدال كل أشكال التوكن المعروفة
            patterns = [
                # TOKEN = "xxx" أو TOKEN = 'xxx'
                (r'(TOKEN\s*=\s*os\.environ\.get\(["\'][^"\']+["\'],\s*)["\'][^"\']+["\'](\))',
                 lambda m2: f'{m2.group(1)}"{new_val}"{m2.group(2)}'),
                (r'(TOKEN\s*=\s*)["\'][^"\']+["\']',
                 lambda m2: f'{m2.group(1)}"{new_val}"'),
                # TeleBot("xxx") أو bot = TeleBot('xxx')
                (r'(TeleBot\s*\(\s*)["\'][^"\']+["\']',
                 lambda m2: f'{m2.group(1)}"{new_val}"'),
                # token = "xxx"
                (r'(token\s*=\s*)["\'][^"\']+["\']',
                 lambda m2: f'{m2.group(1)}"{new_val}"'),
                # BOT_TOKEN = "xxx"
                (r'(BOT_TOKEN\s*=\s*os\.environ\.get\(["\'][^"\']+["\'],\s*)["\'][^"\']+["\'](\))',
                 lambda m2: f'{m2.group(1)}"{new_val}"{m2.group(2)}'),
                (r'(BOT_TOKEN\s*=\s*)["\'][^"\']+["\']',
                 lambda m2: f'{m2.group(1)}"{new_val}"'),
                # أي توكن بشكل رقم:حروف داخل quotes
                (r'["\'](\d{8,12}:[A-Za-z0-9_\-]{35,})["\']',
                 lambda m2: f'"{new_val}"'),
            ]

        elif field == "admin_id":
            patterns = [
                # ADMIN_ID = os.environ.get("...", "123")
                (r'(ADMIN_ID\s*=\s*int\(os\.environ\.get\(["\'][^"\']+["\'],\s*["\']?)\d+(["\']?\)\))',
                 lambda m2: f'{m2.group(1)}{new_val}{m2.group(2)}'),
                # ADMIN_ID = int("123") أو ADMIN_ID = 123
                (r'(ADMIN_ID\s*=\s*int\(\s*)["\']?\d+["\']?(\s*\))',
                 lambda m2: f'{m2.group(1)}"{new_val}"{m2.group(2)}'),
                (r'(ADMIN_ID\s*=\s*)\d+',
                 lambda m2: f'{m2.group(1)}{new_val}'),
                # ADMIN_IDS = [int(x) for x in os.environ.get("...", "123").split(",")]
                (r'(ADMIN_IDS\s*=\s*\[int\(x\) for x in os\.environ\.get\(["\'][^"\']+["\'],\s*["\'])\d+(["\'])',
                 lambda m2: f'{m2.group(1)}{new_val}{m2.group(2)}'),
                # owner_id = 123 / admin_id = 123
                (r'(owner_id\s*=\s*)\d+',
                 lambda m2: f'{m2.group(1)}{new_val}'),
                (r'(admin_id\s*=\s*)\d+',
                 lambda m2: f'{m2.group(1)}{new_val}'),
            ]
        else:
            return False, "نوع التعديل غير معروف"

        changed = False
        for pattern, replacer in patterns:
            new_content = _re.sub(pattern, replacer, content)
            if new_content != content:
                content = new_content
                changed = True
                break  # أول استبدال ناجح يكفي

        if not changed:
            return False, "لم يتم العثور على القيمة في الملف — تأكد من وجودها"

        # نسخة احتياطية
        save_file_version(fname, path)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        log.info(f"Edited {field} in {fname}")
        return True, "ok"

    except Exception as e:
        log.error(f"_edit_file_value: {e}")
        return False, str(e)


def _show_edit_done(m, fname: str, label: str):
    """عرض رسالة اكتمال التعديل مع أزرار الخيارات"""
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("🚀 رفع وتشغيل الآن",    callback_data=f"tog_{fname}"),
        types.InlineKeyboardButton("📤 تحميل الملف المعدّل", callback_data=f"dwn_{fname}"),
        types.InlineKeyboardButton("🔑 تعديل توكن تاني",     callback_data=f"edit_token_{fname}"),
        types.InlineKeyboardButton("👤 تعديل ID تاني",       callback_data=f"edit_id_{fname}"),
        types.InlineKeyboardButton("📋 لوج",                 callback_data=f"log_{fname}"),
        types.InlineKeyboardButton("🗑 حذف",                 callback_data=f"del_{fname}"),
    )
    safe_reply(m,
        f"{label}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📄 الملف: `{fname}`\n\n"
        f"اختر الخطوة التالية:",
        reply_markup=mk)



    """
    ✅ يرسل إشعار للأدمن الرئيسي عند رفع أي ملف من أي مستخدم
    ✅ يرسل رسالة تأكيد جميلة للمستخدم نفسه
    """
    name      = db["users"].get(uid, {}).get("name", "؟")
    role      = get_role(uid)
    role_e    = {"owner": "🔱", "admin": "👑", "vip": "⭐", "user": "👤"}.get(role, "👤")
    active_st = "✅ شغّال" if db["files"].get(fname, {}).get("active") else "⏸ متوقف"
    size_str  = f"{fsize // 1024} KB" if fsize >= 1024 else f"{fsize} B"
    total_files = len([f for f, v in db["files"].items() if v.get("owner") == uid])
    now_str   = datetime.now().strftime('%H:%M:%S')
    ext_icons = {".py": "🐍", ".js": "⚡", ".sh": "🖥️", ".json": "📋",
                 ".txt": "📄", ".env": "🔐", ".yaml": "📑", ".yml": "📑", ".toml": "⚙️"}
    ext_icon  = ext_icons.get(ext, "📄")

    # ─── رسالة الأدمن ───────────────────────────────────────
    admin_markup = types.InlineKeyboardMarkup(row_width=3)
    admin_markup.add(
        types.InlineKeyboardButton("▶️ تشغيل",    callback_data=f"tog_{fname}"),
        types.InlineKeyboardButton("📋 لوج",       callback_data=f"log_{fname}"),
        types.InlineKeyboardButton("🗑 حذف",       callback_data=f"del_{fname}"),
        types.InlineKeyboardButton("📥 تحميل",     callback_data=f"dwn_{fname}"),
        types.InlineKeyboardButton("🔎 فحص",       callback_data=f"chk_{fname}"),
        types.InlineKeyboardButton("👤 المستخدم",  callback_data=f"uview_{uid}"),
    )

    admin_text = (
        f"📤 *ملف جديد مرفوع!*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{ext_icon} الملف: `{fname}`\n"
        f"💾 الحجم: `{size_str}`\n"
        f"🕐 الوقت: `{now_str}`\n"
        f"📂 الحالة: {active_st}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{role_e} المستخدم: *{name}*\n"
        f"🆔 ID: `{uid}`\n"
        f"📊 ملفاته الكلية: `{total_files}`"
    )

    try:
        bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=admin_markup
        )
    except Exception as e:
        log.warning(f"Admin upload notify failed: {e}")

    # ─── إشعار بقية الأدمنز (غير الرئيسي) ──────────────────
    for admin in ADMIN_IDS:
        if admin == ADMIN_ID:
            continue
        try:
            bot.send_message(
                admin,
                f"📤 *ملف جديد*\n{ext_icon} `{fname}` | {role_e} {name} (`{uid}`) | `{size_str}`",
                reply_markup=admin_markup
            )
        except Exception as e:
            log.warning(f"Admin {admin} upload notify failed: {e}")

    # ─── رسالة تأكيد للمستخدم (لو مش أدمن) ─────────────────
    if not is_staff(uid):
        confirm_markup = types.InlineKeyboardMarkup(row_width=2)
        confirm_markup.add(
            types.InlineKeyboardButton("▶️ تشغيل",       callback_data=f"utog_{fname}"),
            types.InlineKeyboardButton("⏹ إيقاف",        callback_data=f"ustop_{fname}"),
            types.InlineKeyboardButton("📋 شوف اللوج",   callback_data=f"log_{fname}"),
            types.InlineKeyboardButton("📂 ملفاتي كلها", callback_data=f"uview_{uid}"),
        )
        try:
            bot.send_message(
                user_chat_id,
                f"✅ *تم رفع ملفك بنجاح!*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{ext_icon} الملف: `{fname}`\n"
                f"💾 الحجم: `{size_str}`\n"
                f"🕐 الوقت: `{now_str}`\n"
                f"📊 ملفاتك الكلية: `{total_files}`\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⏳ انتظر — الأدمن هيراجعه ويشغّله قريباً ✅",
                reply_markup=confirm_markup
            )
        except Exception as e:
            log.warning(f"User upload confirm failed: {e}")



    uid = reg_user(m); role = get_role(uid)
    files = [f for f,v in db["files"].items()
             if v.get("owner")==uid or is_staff(uid)]
    if not files:
        safe_send(m.chat.id,"📂 لا توجد ملفات."); return
    for fname in files:
        info = db["files"][fname]
        st = "✅" if info.get("active") else "❌"
        ar = " 🔁" if info.get("auto_restart") else ""
        safe_send(m.chat.id,
            f"📄 *{fname}*{ar} {st}\n📦`{info.get('size',0)//1024}KB` | 🕐{info.get('uploaded_at','؟')}",
            reply_markup=kb_file(fname) if is_staff(uid) else None)

def _server_stats(m):
    mem=psutil.virtual_memory(); disk=psutil.disk_usage('/'); net=psutil.net_io_counters()
    safe_reply(m,
        f"📊 *السيرفر*\n━━━━━━━━━━━━━━━━━\n"
        f"🖥️ CPU: `{psutil.cpu_percent(1)}%`\n"
        f"💾 RAM: `{mem.percent}%` ({mem.used//1024//1024}/{mem.total//1024//1024}MB)\n"
        f"💿 Disk: `{disk.percent}%` ({disk.used//1024//1024//1024}/{disk.total//1024//1024//1024}GB)\n"
        f"🌐 ↑`{net.bytes_sent//1024//1024}MB` ↓`{net.bytes_recv//1024//1024}MB`\n"
        f"⚡ عمليات: `{len(running_procs)}` | 🔧 Threads: `{threading.active_count()}`")

def _help(m):
    uid  = reg_user(m)
    role = get_role(uid)

    if role == ROLE_USER:
        safe_send(m.chat.id,
            f"👤 *دليل المستخدم*\n━━━━━━━━━━━━━━━━━\n"
            f"💎 نقاطك: `{pts}` | تكلفة رفع: `{cost}` | إحالة: `+{refs}`\n\n"
            f"🔗 *للرفع لازم نقاط:*\n"
            f"كل إحالة = `{refs}` نقاط\n"
            f"رفع ملف يكلف `{cost}` نقاط\n\n"
            f"📤 *رفع ملف:*\n"
            f"ابعت ملف `.py` `.js` `.sh` مباشرة\n\n"
            f"📋 *الأزرار:*\n"
            f"📂 ملفاتي — ملفاتك المرفوعة\n"
            f"▶️ تشغيل / ⏹ إيقاف — تحكم في ملفاتك\n"
            f"📋 لوج — شوف لوج أي ملف\n"
            f"🎫 تذكرة دعم — تواصل مع الأدمن\n\n"
            f"🆔 `{m.from_user.id}`")

    elif role == ROLE_VIP:
        safe_send(m.chat.id,
            f"⭐ *دليل VIP*\n━━━━━━━━━━━━━━━━━\n"
            f"💎 نقاطك: `{pts}`\n\n"
            f"📤 رفع ملفات بدون تكلفة نقاط\n"
            f"📡 إحصائيات السيرفر\n"
            f"🕐 وقت التشغيل\n"
            f"⭐ مميزات VIP — شوف كل مميزاتك\n"
            f"🎫 أولوية في الدعم\n\n"
            f"🆔 `{m.from_user.id}`")

    else:
        safe_reply(m,
            f"📖 *دليل الأدمن*\n━━━━━━━━━━━━━━━━━\n"
            f"/run اسم — تشغيل ملف\n"
            f"/stop اسم — إيقاف ملف\n"
            f"/health — صحة السيرفر\n"
            f"/backup — باك أب فوري\n"
            f"/stats — موارد السيرفر\n"
            f"🖥 لوحة التحكم:\n"
            f"👥 المستخدمون — إدارة كاملة\n"
            f"🔐 لوحة الأدمن — صلاحيات\n"
            f"⚙️ الإعدادات — تعديل كل شيء\n"
            f"📈 تقرير فوري — إحصائيات لحظية\n"
            f"🏆 المتصدرون — أعلى المستخدمين\n\n"
            f"🆔 {m.from_user.id}")


# ══════════════════════════════════════════════════════════════
#  التشغيل
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info("🚀 ELITE HOST BOT v5.0 ULTRA EDITION")

    # ── حذف أي webhook قديم وإنهاء sessions القديمة ──────────
    try:
        bot.delete_webhook(drop_pending_updates=True)
        time.sleep(2)
        log.info("✅ Webhook cleared")
    except Exception as e:
        log.warning(f"Webhook clear: {e}")

    try:
        bot.set_my_commands([
            types.BotCommand("/start",   "الرئيسية"),
            types.BotCommand("/id",      "معرفة ID"),
            types.BotCommand("/myfiles", "ملفاتي"),
            types.BotCommand("/stats",   "موارد السيرفر"),
            types.BotCommand("/health",  "تقرير الصحة"),
            types.BotCommand("/backup",  "باك أب فوري"),
            types.BotCommand("/run",     "تشغيل ملف"),
            types.BotCommand("/stop",    "إيقاف ملف"),
            types.BotCommand("/help",    "المساعدة"),
        ])
    except: pass

    startup_msg = (
        "🟢 ELITE HOST v5.0 ULTRA يعمل!\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"📂 ملفات: {len(db['files'])} | 👥 مستخدمون: {len(db['users'])}\n"
        "💎 نقطة | 🔗 دعوة | 💥 كراش واتشر | 📊 تقرير يومي"
    )
    for admin in ADMIN_IDS:
        try:
            safe_send(admin, startup_msg,
                reply_markup=kb_owner() if admin == ADMIN_ID else kb_admin())
        except Exception as e:
            log.warning(f"Startup notify {admin}: {e}")

    # ── polling مع معالجة خطأ 409 ─────────────────────────────
    while True:
        try:
            bot.infinity_polling(
                skip_pending         = True,
                timeout              = 60,
                long_polling_timeout = 60,
                allowed_updates      = ["message", "callback_query"],
                restart_on_change    = False,
                logger_level         = logging.WARNING,
            )
        except Exception as e:
            err = str(e)
            if "409" in err or "Conflict" in err:
                log.warning("⚠️ خطأ 409 — instance تاني شغال، انتظر 10 ثواني...")
                time.sleep(10)
                try:
                    bot.delete_webhook(drop_pending_updates=True)
                except: pass
                time.sleep(5)
            else:
                log.error(f"Polling error: {e}")
                time.sleep(3)

