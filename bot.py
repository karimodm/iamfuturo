from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext


def apr(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f'Hello {update.effective_user.first_name}')

def markalert(update: Update context CallbackContext) -> None:


updater = Updater('1873243906:AAE4cP-fGRozRFQqcXBk8UMZ8lm_NWHNins')

updater.dispatcher.add_handler(CommandHandler('apr', apr))
updater.dispatcher.add_handler(CommandHandler('markalert', markalert))

updater.start_polling()
updater.idle()
