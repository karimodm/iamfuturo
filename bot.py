from telegram import Update, ChatAction, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
from datetime import datetime
import re

import quotes
import utils

pick_data = None

def ping(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f'pong {update.effective_user.first_name}')

def overview(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Fetching data...')
    data = quotes.get_future_data()
    index_deribit = data['Deribit'][0]['index']
    for source in data.keys():
        msg = f"--- {source} ---\n"
        for obj in sorted(data[source], key = lambda e: e['expir']):
            index = obj['index'] or index_deribit
            base_p = round(float(obj['mark'] - index) / index * 100, 2)
            apr_p = round(base_p / (obj['expir'] - datetime.today()).days * 365, 2)
            msg = msg + f"*{obj['symbol']}*\tB {base_p}%\tAPR {apr_p}%\n"
        update.message.reply_markdown(msg)

def pick(update: Update, context: CallbackContext) -> None:
    global pick_data
    update.message.reply_text('Fetching data...')
    pick_data = quotes.get_future_data()
    data = pick_data
    button_list = [ InlineKeyboardButton(source, callback_data = source) for source in data.keys() ]
    reply_markup = InlineKeyboardMarkup(utils.build_menu(button_list, n_cols = 1))
    update.message.reply_text("Choose from the source below:", reply_markup = reply_markup)

def sourcehandler(update: Update, context: CallbackContext) -> None:
    global pick_data
    data = pick_data

    source = update.callback_query.data
    button_list = [ InlineKeyboardButton(e['symbol'], callback_data = f"{source}_{e['symbol']}") for e in data[source] ]
    reply_markup = InlineKeyboardMarkup(utils.build_menu(button_list, n_cols = 2))
    update._effective_message.reply_text(f"Pick future from {source}:", reply_markup = reply_markup)

def futurehandler(update: Update, context: CallbackContext) -> None:
    global pick_data
    import ipdb
    ipdb.set_trace()
    source_future = update.callback_query.data
    source = re.match('^([^_]+)_.+', source_future)[1]
    button_list = [ 
        InlineKeyboardButton("Mark Price Alert", callback_data = f"{source_future}_MARK"),
        InlineKeyboardButton("Base Alert", callback_data = f"{source_future}_BASE")
    ]
    reply_markup = InlineKeyboardMarkup(utils.build_menu(button_list, n_cols = 2))
    update._effective_message.reply_text("What do you want to do?", reply_markup = reply_markup)

def markalerthandler(update: Update, context: CallbackContext) -> None:
    import ipdb
    ipdb.set_trace()
    match = re.match('^([^_]+)_(.+)_MARK$', source_future)
    source = match[1]
    symbol = match[2]
    update._effective_message.reply_text("Gimme the price (use '.' for decimals)")

def basealerthandler(update: Update, context: CallbackContext) -> None:
    import ipdb
    ipdb.set_trace()
    match = re.match('^([^_]+)_(.+)_BASE$', source_future)
    source = match[1]
    symbol = match[2]

def myalerts(update: Update, context: CallbackContext) -> None:
    pass

updater = Updater('1873243906:AAE4cP-fGRozRFQqcXBk8UMZ8lm_NWHNins')

updater.dispatcher.add_handler(CommandHandler('ping', ping))
updater.dispatcher.add_handler(CommandHandler('overview', overview))
updater.dispatcher.add_handler(CommandHandler('myalerts', myalerts))
updater.dispatcher.add_handler(CommandHandler('pick', pick))
updater.dispatcher.add_handler(CallbackQueryHandler(markalerthandler, pattern = '\w+_\w+_MARK'))
updater.dispatcher.add_handler(CallbackQueryHandler(basealerthandler, pattern = '\w+_\w+_BASE'))
updater.dispatcher.add_handler(CallbackQueryHandler(futurehandler, pattern = '\w+_\w+'))
updater.dispatcher.add_handler(CallbackQueryHandler(sourcehandler))

updater.start_polling()
updater.idle()
