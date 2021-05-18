from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from datetime import datetime

import quotes

def ping(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f'Hello {update.effective_user.first_name}')

def apr(update: Update, context: CallbackContext) -> None:
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

def markalert(update: Update, context: CallbackContext) -> None:
    pass

updater = Updater('1873243906:AAE4cP-fGRozRFQqcXBk8UMZ8lm_NWHNins')

updater.dispatcher.add_handler(CommandHandler('ping', ping))
updater.dispatcher.add_handler(CommandHandler('apr', apr))
updater.dispatcher.add_handler(CommandHandler('markalert', markalert))

updater.start_polling()
updater.idle()
