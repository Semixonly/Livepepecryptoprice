
import os
import time
import logging
import httpx

from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# Ayarlar
BOT_TOKEN = os.getenv("BOT_TOKEN")
CACHE_TIME = 600  # 10 dakika

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Kripto para listesi
COINS = {
    "btc": ("bitcoin", "Bitcoin"),
    "eth": ("ethereum", "Ethereum"),
    "ltc": ("litecoin", "Litecoin"),
    "bnb": ("binancecoin", "BNB"),
    "sol": ("solana", "Solana"),
    "xrp": ("ripple", "XRP"),
    "doge": ("dogecoin", "Dogecoin"),
    "ada": ("cardano", "Cardano"),
    "trx": ("tron", "TRON"),
    "shib": ("shiba-inu", "Shiba Inu"),
    "pepe": ("pepe", "Pepe"),
    "ton": ("the-open-network", "Toncoin"),
    "usdt": ("tether", "Tether"),
    "usdc": ("usd-coin", "USD Coin"),
    "avax": ("avalanche-2", "Avalanche"),
    "dot": ("polkadot", "Polkadot"),
    "link": ("chainlink", "Chainlink"),
}

CACHE = {}


async def get_price(coin, currency):
    key = (coin, currency)
    now = time.monotonic()

    # Önbellek kontrolü
    if key in CACHE:
        cached = CACHE[key]

        if now - cached["time"] < CACHE_TIME:
            return cached["data"], True

    coin_id, _ = COINS[coin]

    url = "https://api.coingecko.com/api/v3/simple/price"

    params = {
        "ids": coin_id,
        "vs_currencies": currency,
        "include_24hr_change": "true",
        "include_last_updated_at": "true"
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()

        result = response.json()

    if coin_id not in result or currency not in result[coin_id]:
        raise ValueError("Fiyat bilgisi bulunamadı.")

    data = result[coin_id]

    CACHE[key] = {
        "time": now,
        "data": data
    }

    return data, False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 CRYPTO LIVE PRICE BOT\n\n"
        "Kripto para fiyatlarını öğrenmek için:\n\n"
        "/ltc usd - Litecoin\n"
        "/btc usd - Bitcoin\n"
        "/eth usd - Ethereum\n"
        "/bnb usd - BNB\n"
        "/sol usd - Solana\n"
        "/pepe usd - Pepe\n\n"
        "Para birimleri: USD, TRY, EUR, GBP, BTC\n\n"
        "🔄 Fiyat önbelleği: 10 dakika"
    )


async def price_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    command = update.message.text.split()[0]
    coin = command.split("@")[0][1:].lower()

    if coin not in COINS:
        return

    if not context.args:
        await update.message.reply_text(
            f"❌ Kullanım: /{coin} usd\n"
            f"Örnek: /{coin} try"
        )
        return

    currency = context.args[0].lower()

    if currency not in ["usd", "try", "eur", "gbp", "btc"]:
        await update.message.reply_text(
            "❌ Desteklenen para birimleri:\n"
            "USD, TRY, EUR, GBP, BTC"
        )
        return

    try:
        data, from_cache = await get_price(coin, currency)

        coin_id, coin_name = COINS[coin]
        price = data[currency]

        change = data.get(f"{currency}_24h_change")
        updated = data.get("last_updated_at")

        formatted_price = f"{price:,.12g}"

        if change is not None:
            change_text = f"{change:+.2f}%"
            emoji = "🟢" if change >= 0 else "🔴"
        else:
            change_text = "Veri bulunamadı"
            emoji = "⚪"

        if updated:
            update_time = datetime.fromtimestamp(
                updated
            ).strftime("%d.%m.%Y %H:%M:%S")
        else:
            update_time = "Bilinmiyor"

        cache_status = (
            "Önbellekten alındı"
            if from_cache
            else "Yeni API verisi"
        )

        message = (
            f"🪙 {coin_name} ({coin.upper()})\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"💰 Fiyat: {formatted_price} {currency.upper()}\n"
            f"{emoji} 24 saatlik değişim: {change_text}\n\n"
            f"🕒 Veri zamanı: {update_time}\n"
            f"🔄 Durum: {cache_status}\n"
            f"⏱ Önbellek: 10 dakika\n\n"
            f"📊 Kaynak: CoinGecko"
        )

        await update.message.reply_text(message)

    except Exception:
        logging.exception("Fiyat sorgusu başarısız")
        await update.message.reply_text(
            "⚠️ Fiyat alınamadı.\n"
            "Lütfen biraz sonra tekrar dene."
        )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN ortam değişkeni ayarlanmamış!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    for coin in COINS:
        app.add_handler(
            CommandHandler(coin, price_command)
        )

    logging.info("Crypto Live Price Bot başlatılıyor...")

    app.run_polling()


if __name__ == "__main__":
    main()
