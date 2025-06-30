import time
import requests
import os

# === CONFIG ===

SOLANA_WALLETS = [
    "6v9RfGEXrb9TD2CVZQSo3rB5VAMkM2Ku8z6MFjZxnKnN",
    "38ESLHdJkqNvMbJmbgsHJGXjJPpsL4TkvSUgXegYgvpr",
    "FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiouN5",
    "HVh6wHNBAsG3pq1Bj5oCzRjoWKVogEDHwUHkRz3ekFgt",
    "9r4sWYfiETiGjhszFfFp6UZhkv3qUckrqcA37SXzUfAi",
    "ArmMNRgoeCQNLX6YNZMugNZhvtVb8kxnqsgXzCcVTy6A",
    "MJKqp326RZCHnAAbew9MDdui3iCKWco7fsK9sVuZTX2",
    "52C9T2T7JRojtxumYnYZhyUmrN7kqvCLc4Ksvjk7TxD",
    "8BseXT9EtoEhBTKFFYkwTnjKSUZwhtmdKY2rj8j45Rt",
    "GitYucwpNcg6Dx1Y15UQn8LZMX1uuqQNn8rXxEWNC",
    "9QgXqrgdbVU8KcpfskqPAXKzbaYQJecgMAruSWoXDkM"
]

BASE_WALLETS = [
    "4ABvR6sHF9M8Lp9G4xVuVXz3bZ6Mc9uA7e7sGtPjaF2Y",
    "2YmXnZkrLF6v56mpqkti7sXbAAmkz1RkXrCk9kXLfn4L",
    "7NenTu2DGA6HRjiFQ5azQ18FJ2vN9PtBWu8vL3yQKXBy",
    "9GwQxPHgTby3MQVAjNP5u8ERKXcvt6zXV1XJVNSFSdZh",
    "3T6k7XQzpj2Bi8f6H9Uy4qB2GktV4ByqkFWpX6LFY84Z"
]

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TOKEN_META_URL = f"https://api.helius.xyz/v0/tokens/metadata?api-key={HELIUS_API_KEY}"

DEX_PROGRAMS = [
    "9xQeWvG816bUx9EPXfnD8Z4t4d3ZCvK5dXA7CzA5kNtP",
    "RVKd61ztZW9CQbKzM3dTzQz3fBipEcXP2eaXfKenD5n",
    "5quB64YFxhYSgXyRRc1rLZNR5pczcxowhTQNJjTCvWvb",
    "4ckmDgGz5g9wnZ2gGdnCrpzo6q2ketskkvM5RDwQGy2T",
    "DVa7gZhU7mD94GLg1DZcJqWQUGzM9BXhCM3QxSK9V1bA"
]

last_sigs = {}
token_cache = {}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    })
    if r.status_code != 200:
        print("❌ Telegram error:", r.text)
    else:
        print("✅ Telegram alert sent.")

def get_token_name(mint):
    if mint in token_cache:
        return token_cache[mint]
    try:
        r = requests.post(TOKEN_META_URL, json={"mints": [mint]})
        data = r.json()[0]
        name = data.get("symbol") or data.get("name") or "Unknown"
        token_cache[mint] = name
        return name
    except:
        return "Unknown"

# === Solana ===
def get_sol_sig(wallet):
    url = f"https://api.helius.xyz/v0/addresses/{wallet}/transactions?api-key={HELIUS_API_KEY}&limit=1"
    res = requests.get(url).json()
    if res:
        return res[0]["signature"]
    return None

def check_sol_buy(wallet, sig):
    url = f"https://api.helius.xyz/v0/transactions/{sig}?api-key={HELIUS_API_KEY}"
    r = requests.get(url)
    tx = r.json()

    instructions = tx.get("events", {}).get("programs", []) + tx.get("instructions", [])
    involved_programs = [ix.get("programId") or ix.get("program") for ix in instructions if isinstance(ix, dict)]
    is_dex = any(prog in DEX_PROGRAMS for prog in involved_programs)

    sol_out = any(x["fromUserAccount"] == wallet and x["amount"] > 0 for x in tx.get("nativeTransfers", []))
    token_changes = [c for c in tx.get("tokenBalanceChanges", []) if c["owner"] == wallet and c["delta"] > 0]

    if is_dex and sol_out and token_changes:
        for change in token_changes:
            name = get_token_name(change["mint"])
            send_telegram(
                f"🔽 *REAL BUY on Solana!*\n"
                f"Wallet: `{wallet}`\n"
                f"Token: *${name}*\n"
                f"Mint: `{change['mint']}`\n"
                f"Amount: `{change['dblTokenAmount']}`"
            )

# === Base ===
def get_base_sig(wallet):
    url = f"https://api.helius.xyz/v0/addresses/{wallet}/transactions?api-key={HELIUS_API_KEY}&limit=1"
    res = requests.get(url).json()
    if res:
        return res[0]["signature"]
    return None

def check_base_transfer(wallet, sig):
    url = f"https://api.helius.xyz/v0/transactions/{sig}?api-key={HELIUS_API_KEY}"
    r = requests.get(url)
    tx = r.json()
    for change in tx.get("tokenBalanceChanges", []):
        if change["owner"] == wallet:
            direction = "🔽 BUY" if change["delta"] > 0 else "🔼 SELL"
            send_telegram(
                f"{direction} *Base Token Alert!*\n"
                f"Wallet: `{wallet}`\n"
                f"Token: `{change['mint']}`\n"
                f"Amount: `{abs(change['dblTokenAmount'])}`"
            )

# === MAIN ===
def main():
    print("🚀 Starting Multi-Chain Bot...")

    for wallet in SOLANA_WALLETS + BASE_WALLETS:
        sig = get_sol_sig(wallet) if wallet in SOLANA_WALLETS else get_base_sig(wallet)
        last_sigs[wallet] = sig
        print(f"Tracking {wallet} — latest sig: {sig}")

    while True:
        try:
            for wallet in SOLANA_WALLETS:
                sig = get_sol_sig(wallet)
                if sig and sig != last_sigs[wallet]:
                    check_sol_buy(wallet, sig)
                    last_sigs[wallet] = sig

            for wallet in BASE_WALLETS:
                sig = get_base_sig(wallet)
                if sig and sig != last_sigs[wallet]:
                    check_base_transfer(wallet, sig)
                    last_sigs[wallet] = sig

            time.sleep(10)
        except Exception as e:
            print("❌ Error:", e)
            time.sleep(20)

if __name__ == "__main__":
    main()
