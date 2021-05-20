from telegram import Update, ChatAction, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, PicklePersistence
from datetime import datetime
import os
import re
import uuid
from emoji import emojize
import logging

import quotes
import utils

pick_data = None

def markalert_runner(context: CallbackContext) -> None:
    alerts = context.bot_data['markalerts']
    future_data = quotes.get_future_data()
    flat_data = [i for s in list(future_data.values()) for i in s] # flatten data
    alert_emoji = emojize(':droplet:', use_aliases = True)
    def _match(alert):
        return lambda data: data['source'] == alert['source'] and data['symbol'] == alert['symbol']
    for alert in alerts:
        matching = filter(_match(alert), flat_data)
        for match in matching:
            if match['mark'] >= alert['price']:
                alert['user'].send_message(f"{alert_emoji} MARK ALERT:\n{alert['source']} -> {alert['symbol']}: {match['mark']} >= {alert['price']}")

def basealert_runner(context: CallbackContext) -> None:
    alerts = context.bot_data['basealerts']
    future_data = quotes.get_future_data()
    index_deribit = future_data['Deribit'][0]['index']
    flat_data = [i for s in list(future_data.values()) for i in s] # flatten data
    alert_emoji = emojize(':moneybag:', use_aliases = True)
    def _match(alert):
        return lambda data: data['source'] == alert['source'] and data['symbol'] == alert['symbol']
    for alert in alerts:
        matching = filter(_match(alert), flat_data)
        for match in matching:
            index = match['index'] or index_deribit
            base_p = round(float(match['mark'] - index) / index * 100, 2)
            if base_p < 0.5:
                alert['user'].send_message(f"{alert_emoji} BASE ALERT:\n{alert['source']} -> {alert['symbol']}: {base_p}%")

def ping(update: Update, context: CallbackContext) -> None:
    update.effective_chat.send_message(f'pong {update.effective_user.first_name}')

def apr(update: Update, context: CallbackContext) -> None:
    context.bot.send_chat_action(chat_id = update.effective_message.chat_id, action = ChatAction.TYPING)
    data = quotes.get_future_data()
    index_deribit = data['Deribit'][0]['index']
    for source in data.keys():
        msg = f"--- {source} ---\n"
        for obj in sorted(data[source], key = lambda e: e['expir']):
            index = obj['index'] or index_deribit
            base_p = round(float(obj['mark'] - index) / index * 100, 2)
            try:
                apr_p = round(base_p / (obj['expir'] - datetime.today()).days * 365, 2)
            except ZeroDivisionError:
                apr_p = float('inf')
            msg = msg + f"*{obj['symbol']}*\tM {obj['mark']}\tB {base_p}%\tAPR {apr_p}%\n"
        update.effective_chat.send_message(msg, parse_mode = ParseMode.MARKDOWN)

def markalert(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 3:
        update.message.reply_text(f"/markalert <source> <future_symbol> <price>")
        return

    alerts = context.bot_data['markalerts']

    id = str(uuid.uuid4())[:8]
    source = context.args[0]
    symbol = context.args[1]
    price =  float(context.args[2])

    alerts.append({ 'short_id': id, 'user': update.effective_user, 'source': source, 'symbol': symbol, 'price': price })
    update.message.reply_text(f"I'll alert you when mark of {symbol} on {source} >= {price}")

def basealert(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 2:
        update.message.reply_text(f"/basealert <source> <future_symbol>")
        return

    alerts = context.bot_data['basealerts']

    id = str(uuid.uuid4())[:8]
    source = context.args[0]
    symbol = context.args[1]

    alerts.append({ 'short_id': id, 'user': update.effective_user, 'source': source, 'symbol': symbol })
    update.message.reply_text(f"I'll alert you when base of {symbol} on {source} <= 0.5%")

def myalerts(update: Update, context: CallbackContext) -> None:
    mark_alerts = filter(lambda alert: alert['user'] == update.effective_user, context.bot_data['markalerts'])
    base_alerts = filter(lambda alert: alert['user'] == update.effective_user, context.bot_data['basealerts'])
    msg = "BASE ALERTS:\n"
    for alert in base_alerts:
        msg = msg + f"*{alert['short_id']}*: {alert['source']} {alert['symbol']}\n"
    msg = msg + "MARK ALERTS:\n"
    for alert in mark_alerts:
        msg = msg + f"*{alert['short_id']}*: {alert['source']} {alert['symbol']} {alert['price']}\n"
    msg = msg.replace('_', '\_')
    update.message.reply_markdown(msg)

def delalert(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 1:
        update.message.reply_text("/delalert <id>")
        return
    del_id = context.args[0]
    mark_alerts = context.bot_data['markalerts']
    base_alerts = context.bot_data['basealerts']
    context.bot_data['markalerts'] = list(filter(lambda alert: alert['short_id'] != del_id or alert['user'] != update.effective_user, mark_alerts))
    context.bot_data['basealerts'] = list(filter(lambda alert: alert['short_id'] != del_id or alert['user'] != update.effective_user, base_alerts))
    update.message.reply_markdown(f"Deleted alert *{del_id}*")

def usage(update: Update, context: CallbackContext) -> None:
    msg = "You can control me by sending these commands:\n\n"
    msg = msg + "/ping - check if I am alive!\n"
    msg = msg + "/apr - get a futures overview from all supported sources\n"
    msg = msg + "/markalert - set a mark price alert for a future\n"
    msg = msg + "/basealert - set a 0.5% base alert for a future\n"
    msg = msg + "/myalerts - show your configured alerts\n"
    msg = msg + "/delalert - delete an active alert\n"
    update.effective_chat.send_message(msg)


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

storage = PicklePersistence(filename = './data/bot')

updater = Updater(os.environ['TELEGRAM_TOKEN'], persistence = storage)

if not 'basealerts' in updater.dispatcher.bot_data:
    updater.dispatcher.bot_data['basealerts'] = []

if not 'markalerts' in updater.dispatcher.bot_data:
    updater.dispatcher.bot_data['markalerts'] = []

updater.dispatcher.add_handler(CommandHandler('ping', ping))
updater.dispatcher.add_handler(CommandHandler('apr', apr))
updater.dispatcher.add_handler(CommandHandler('markalert', markalert))
updater.dispatcher.add_handler(CommandHandler('basealert', basealert))
updater.dispatcher.add_handler(CommandHandler('myalerts', myalerts))
updater.dispatcher.add_handler(CommandHandler('delalert', delalert))
updater.dispatcher.add_handler(CommandHandler('help', usage))
updater.dispatcher.add_handler(CommandHandler('start', usage))

updater.job_queue.run_repeating(basealert_runner, 120)
updater.job_queue.run_repeating(markalert_runner, 120)

updater.start_polling()
updater.idle()
