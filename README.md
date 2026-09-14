# 🤖 KeyAuth Discord Bot Setup Guide

Yeh ek feature-packed Discord Bot hai jo **KeyAuth Seller API** ko Discord Server se direct control karne ke liye banaya gaya hai.

---

## ✨ Features & Slash Commands

| Command | Description | Admin Only |
|---|---|:---:|
| `/genkey` | Custom expiry, amount, mask & level ke sath new license key(s) generate karta hai. | ✅ |
| `/keyinfo` | Specific license key ki information dekhta hai. | ✅ |
| `/delkey` | KeyAuth system se key delete karta hai. | ✅ |
| `/resethwid` | KeyAuth user ka Hardware ID (HWID) reset karta hai. | ✅ |
| `/userinfo` | Registered user ki subscription, HWID, aur IP details dekhta hai. | ✅ |
| `/banuser` | User ko KeyAuth app me ban karta hai. | ✅ |
| `/unbanuser` | Banned user ko unban karta hai. | ✅ |
| `/stats` | Application ki overall statistics (Total Keys, Active Users) dikhata hai. | ✅ |
| `/ping` | Bot ki latency aur response time test karta hai. | ❌ |

---

## 🚀 Setup & Installation Instructions

### Step 1: Requirements Install Karein

Terminal / Command Prompt kholein aur project directory me command chalayein:

```bash
pip install -r requirements.txt
```

---

### Step 2: KeyAuth Seller Key & Discord Bot Token Add Karein

1. `.env` file ko text editor (e.g. VS Code, Notepad) me open karein.
2. **`DISCORD_TOKEN`**:
   - [Discord Developer Portal](https://discord.com/developers/applications) par jayein.
   - New Application create karein -> **Bot** tab par jayein -> **Reset Token** karke Token copy karein.
   - `.env` me paste karein: `DISCORD_TOKEN=your_token_here`
3. **`KEYAUTH_SELLER_KEY`**:
   - [KeyAuth Dashboard](https://keyauth.win/app/) par login karein.
   - Apni App ki **Seller Settings** me jayein aur **Seller Key** copy karein.
   - `.env` me paste karein: `KEYAUTH_SELLER_KEY=your_seller_key_here`
4. **`GUILD_ID` (Optional)**:
   - Apne Discord Server par Right-Click karke **Copy Server ID** karein aur `.env` me fill karein (is-se slash commands instanly update ho jati hain).

---

### Step 3: Bot Privileged Intents Enable Karein

Discord Developer Portal me apni Bot application khol kar:
1. **Bot** section par jayein.
2. Scroll down to **Privileged Gateway Intents**.
3. **Message Content Intent** ko **ENABLE** (ON) karein.
4. Save Changes par click karein.

---

### Step 4: Bot Ko Discord Server Me Invite Karein

1. Developer Portal me **OAuth2** -> **URL Generator** par jayein.
2. Scopes me select karein: `bot` aur `applications.commands`.
3. Bot Permissions me select karein: `Administrator` (ya `Send Messages`, `Embed Links`, `Use Application Commands`).
4. Bottom par bane link ko browser me open karke apne Discord Server me add karein.

---

### Step 5: Bot Run Karein

Bot ko start karne ke liye terminal me command chalayein:

```bash
python bot.py
```

jab bot connect ho jaye, Discord me `/` type karke KeyAuth slash commands access karein! 🎉
