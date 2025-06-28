import telebot
import time
import threading
import json
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Récupère le token via une variable d'environnement
API_TOKEN = os.getenv("7274471123:AAFI91a9GvSthhbsLGgSkKUvSN66NC4fHv4")
bot = telebot.TeleBot(API_TOKEN)

DATA_FILE = 'users.json'
COOLDOWN = 12 * 3600  # 12h
ADMIN_ID = 6656672923

users = {}
referrals = {}
reward_steps = {1: 3, 3: 5, 5: 20, 10: 50, 20: 150}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(users, f)

def load_data():
    global users
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            users = json.load(f)

def get_keyboard(uid):
    lang = users.get(uid, {}).get("lang", "fr")
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🎁 Claim 10 SOLI"))
    markup.row(
        KeyboardButton("💼 Mon profil" if lang == "fr" else "💼 Profile"),
        KeyboardButton("🎯 Tasks")
    )
    markup.row(
        KeyboardButton("👥 Inviter des amis" if lang == "fr" else "👥 Invite friends"),
        KeyboardButton("📥 Submit wallet")
    )
    markup.row(
        KeyboardButton("ℹ️ À propos" if lang == "fr" else "ℹ️ About")
    )
    return markup

@bot.message_handler(commands=['start'])
def start_handler(msg):
    uid = str(msg.from_user.id)
    if uid not in users:
        users[uid] = {
            'balance': 0,
            'lastClaim': 0,
            'lang': msg.from_user.language_code if msg.from_user.language_code in ['fr', 'en'] else 'fr',
            'wallet': '',
            'invited': 0,
            'bonusSteps': [],
            'ref': '',
            'clicks': 0
        }

        if ' ' in msg.text:
            ref_id = msg.text.split(' ')[1]
            if ref_id != uid and users[uid]['ref'] == '':
                users[uid]['ref'] = ref_id
                if ref_id not in referrals:
                    referrals[ref_id] = []
                if uid not in referrals[ref_id]:
                    referrals[ref_id].append(uid)
                    users[ref_id]['balance'] += 10
                    users[ref_id]['invited'] += 1
                    current = users[ref_id]['invited']
                    if current in reward_steps and current not in users[ref_id]['bonusSteps']:
                        bonus = reward_steps[current]
                        users[ref_id]['balance'] += bonus
                        users[ref_id]['bonusSteps'].append(current)
                        bot.send_message(int(ref_id), f"🎉 Bonus de {bonus} SOLI reçu pour avoir atteint {current} filleuls !")
                    bot.send_message(int(ref_id), "👥 Nouveau filleul ajouté : +10 SOLI !")

    bot.send_message(msg.chat.id, "👋 Bienvenue sur SoliCoin !", reply_markup=get_keyboard(uid))
    save_data()

@bot.message_handler(commands=['users'])
def list_users(msg):
    if msg.from_user.id == ADMIN_ID:
        text = f"👥 Total utilisateurs : {len(users)}\n\n"
        for uid, u in users.items():
            text += f"🆔 ID: {uid}\n💰 SOLI: {u['balance']}\n💼 Wallet: {u.get('wallet', 'Non renseigné')}\n---\n"
        bot.send_message(msg.chat.id, text)

@bot.message_handler(commands=['broadcast'])
def broadcast(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    sent = bot.send_message(msg.chat.id, "✉️ Envoie-moi le message à diffuser à tous les utilisateurs :")
    bot.register_next_step_handler(sent, send_broadcast)

def send_broadcast(msg):
    total = 0
    for uid in users:
        try:
            bot.send_message(int(uid), f"📢 MESSAGE GLOBAL :\n\n{msg.text}")
            total += 1
        except:
            continue
    bot.send_message(msg.chat.id, f"✅ Message envoyé à {total} utilisateurs.")

@bot.message_handler(commands=['stats'])
def show_stats(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    total_users = len(users)
    total_clicks = sum(u.get('clicks', 0) for u in users.values())
    total_invited = sum(u.get('invited', 0) for u in users.values())
    total_balance = sum(u.get('balance', 0) for u in users.values())

    bot.send_message(msg.chat.id,
        f"📊 Statistiques globales :\n\n"
        f"👥 Utilisateurs : {total_users}\n"
        f"👣 Clics sur liens : {total_clicks}\n"
        f"🎁 Parrainages confirmés : {total_invited}\n"
        f"💰 SOLI totaux à distribuer : {total_balance} SOLI"
    )

@bot.message_handler(func=lambda m: True)
def handle_all(msg):
    uid = str(msg.from_user.id)
    if uid not in users:
        return

    txt = msg.text

    if txt == "🎁 Claim 10 SOLI":
        now = time.time()
        if now - users[uid]['lastClaim'] >= COOLDOWN:
            users[uid]['balance'] += 10
            users[uid]['lastClaim'] = now
            bot.send_message(msg.chat.id, "✅ 10 SOLI ajoutés à ton solde !", reply_markup=get_keyboard(uid))
        else:
            left = int(COOLDOWN - (now - users[uid]['lastClaim']))
            h, m = divmod(left // 60, 60)
            bot.send_message(msg.chat.id, f"⏳ Prochain claim dans {h}h {m}min.")
        save_data()

    elif txt in ["💼 Mon profil", "💼 Profile"]:
        u = users[uid]
        bot.send_message(msg.chat.id,
                         f"👤 Ton ID : {uid}\n💰 Solde total : {u['balance']} SOLI\n👥 Parrainages : {u['invited']}",
                         reply_markup=get_keyboard(uid))

    elif txt == "📥 Submit wallet":
        bot.send_message(msg.chat.id, "✍️ Entre ton adresse de wallet SOLANA maintenant :")
        bot.register_next_step_handler(msg, save_wallet)

    elif txt in ["👥 Inviter des amis", "👥 Invite friends"]:
        users[uid]['clicks'] += 1
        bot.send_message(msg.chat.id,
            f"👥 Partage ce lien avec tes amis pour recevoir 10 SOLI par parrainage :\n\n"
            f"https://t.me/Solicoinsbot?start={uid}",
            reply_markup=get_keyboard(uid))

    elif txt == "🎯 Tasks":
        bot.send_message(msg.chat.id,
                         "🎯 Tâches disponibles :\n\n✅ Claim 10 SOLI toutes les 12h\n✅ Invite tes amis : +10 SOLI chacun\n🎉 Paliers bonus :\n- 1 invité : 3 SOLI\n- 3 invités : 5 SOLI\n- 5 invités : 20 SOLI\n- 10 invités : 50 SOLI\n- 20 invités : 150 SOLI",
                         reply_markup=get_keyboard(uid))

    elif txt in ["ℹ️ À propos", "ℹ️ About"]:
        bot.send_message(msg.chat.id,
                         "SoliCoin (SOLI) est un jeton communautaire sur Solana.\n🔗 Rejoins notre canal : https://t.me/solicoin100M",
                         reply_markup=get_keyboard(uid))

    elif txt.startswith("9") or txt.startswith("5"):
        users[uid]['wallet'] = txt.strip()
        bot.send_message(msg.chat.id, "✅ Adresse wallet enregistrée !", reply_markup=get_keyboard(uid))
        save_data()

def save_wallet(msg):
    uid = str(msg.from_user.id)
    users[uid]['wallet'] = msg.text.strip()
    bot.send_message(msg.chat.id, "✅ Adresse wallet enregistrée avec succès !", reply_markup=get_keyboard(uid))
    save_data()

def claim_loop():
    while True:
        now = time.time()
        for uid, u in users.items():
            if now - u['lastClaim'] >= COOLDOWN:
                try:
                    bot.send_message(int(uid), "⏰ Tu peux maintenant réclamer 10 SOLI !")
                except:
                    pass
        time.sleep(600)

load_data()
threading.Thread(target=claim_loop).start()
bot.infinity_polling()
