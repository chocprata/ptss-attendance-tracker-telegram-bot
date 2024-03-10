from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
import gspread
import logging
from supabase import create_client
from datetime import datetime
import ast
import os
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
current_date = datetime.now().strftime('%d/%m/%Y').lstrip('0').replace('/0', '/')


# SUPABASE
supabase_client= create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# GOOGLE SHEETS INFO
sa = gspread.service_account(filename='service_account.json')
sh = sa.open(" Learner Parade State - Mar")

# TELEGRAM BOT INFO
TOKEN: Final = os.getenv('TOKEN')
BOT_USERNAME: Final = os.getenv('BOT_USERNAME')
MY_TELEGRAM_CHAT_ID = os.getenv('MY_TELEGRAM_CHAT_ID')


# CONVERSATIONS
CHOOSE_CLASS, CONFIRM_CLASS, AUTHENTICATION, CHOOSE_AMPM, CONFIRM_AMPM, INPUT_ATTENDANCE, FEEDBACK = range(7)

# PASSWORDS
CLASS_PASSWORDS = ast.literal_eval(os.getenv('CLASS_PASSWORDS'))


# COMMANDS
# START FUNCTION
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Good Day! Welcome to PTSS Learner Bot! Type /attendance to input your attendance!")


# START OF ATTENDANCE FUNCTION
async def attendance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['chat_id'] = str(update.message.chat_id)
    chat_id = context.user_data['chat_id']

    response = supabase_client.table('ICs').select('*').execute()
    data = response.data

    if data:  # Check if data is not empty
        for row in data:
            if str(row.get('telegram_id')) == str(chat_id):
                chosen_class = row.get('chosen_class')
                if chosen_class:
                    context.user_data['chosen_class'] = chosen_class
                    keyboard = [
                        [InlineKeyboardButton("AM", callback_data='AM')],
                        [InlineKeyboardButton("PM", callback_data='PM')],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text(f"Welcome back!\nYou have previously chosen class {chosen_class}.\nPlease choose AM or PM!", reply_markup=reply_markup)
                    return CHOOSE_AMPM
    for worksheet in sh.worksheets():
        dates_row = worksheet.row_values(4)

        for index, date in enumerate(dates_row):
            try:
                worksheet_date = datetime.strptime(date, "%d/%m/%Y").date()
                current_date_obj = datetime.strptime(current_date, "%d/%m/%Y").date()

                if worksheet_date == current_date_obj:
                    class_column = worksheet.col_values(1)
                    class_index = class_column.index("CLASS") if "CLASS" in class_column else -1

                    if class_index != -1:
                        class_names = []

                        for class_name in class_column[class_index + 1:]:
                            if class_name == 'STATUS':
                                break
                            class_names.append(class_name)

                        keyboard = [
                            [InlineKeyboardButton(class_name, callback_data=class_name)]
                            for class_name in class_names
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await update.message.reply_text('Good Day! Welcome to PTSS! Please select your class!', reply_markup=reply_markup)
                        return CHOOSE_CLASS
                        break  
            except ValueError:
                continue  
        else:
            print("Chosen date not found in worksheet:", worksheet.title)


# CHOOSE_CLASS FUNCTION
async def choose_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chosen_class = query.data
    context.user_data['chosen_class'] = chosen_class

    keyboard = [
        [InlineKeyboardButton("Confirm", callback_data='confirm')],
        [InlineKeyboardButton("Back", callback_data='back')],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(f"You've chosen {chosen_class}, Is this correct?", reply_markup=reply_markup)
    return CONFIRM_CLASS


# CONFIRM_CLASS FUNCTION
async def confirm_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_response = query.data.lower()

    if user_response == "confirm":

        chosen_class = context.user_data['chosen_class']
        
        await query.edit_message_text(f"Great! You've chosen {chosen_class}. Please enter the password:")
        return AUTHENTICATION
    
    elif user_response == 'back':
        # Same as attendance
        for worksheet in sh.worksheets():
            dates_row = worksheet.row_values(4)

            for index, date in enumerate(dates_row):
                try:
                    worksheet_date = datetime.strptime(date, "%d/%m/%Y").date()
                    current_date_obj = datetime.strptime(current_date, "%d/%m/%Y").date()

                    if worksheet_date == current_date_obj:
                        class_column = worksheet.col_values(1)
                        class_index = class_column.index("CLASS") if "CLASS" in class_column else -1

                        if class_index != -1:
                            class_names = []

                            for class_name in class_column[class_index + 1:]:
                                if class_name == 'STATUS':
                                    break
                                class_names.append(class_name)

                            keyboard = [
                                [InlineKeyboardButton(class_name, callback_data=class_name)]
                                for class_name in class_names
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            await query.edit_message_text('Good Day! Welcome to PTSS! Please select your class!', reply_markup=reply_markup)
                            return CHOOSE_CLASS
                            break  
                except ValueError:
                    continue  
            else:
                print("Chosen date not found in worksheet:", worksheet.title)
    
    return CONFIRM_CLASS


# AUTHENTICATION FUNCTION
async def authentication(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_password = update.message.text
    chosen_class = context.user_data['chosen_class']
    correct_password = CLASS_PASSWORDS.get(chosen_class)

    if update.message.text == '/cancel':
        context.user_data.clear()
        await update.message.reply_text("Operation canceled. Type /attendance to start again.")
        return ConversationHandler.END
    
    if user_password == correct_password:

        keyboard = [
            [InlineKeyboardButton("AM", callback_data='AM')],
            [InlineKeyboardButton("PM", callback_data='PM')],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Password accepted! Please choose AM or PM!", reply_markup=reply_markup)
        return CHOOSE_AMPM
    
    else:
        await update.message.reply_text("Incorrect password. Please try again or type /cancel to cancel.")
        return AUTHENTICATION


# CHOOSE_AMPM FUNCTION
async def choose_AMPM(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chosen_AMPM = query.data
    context.user_data['chosen_AMPM'] = chosen_AMPM

    keyboard = [
        [InlineKeyboardButton("Confirm", callback_data='confirm')],
        [InlineKeyboardButton("Back", callback_data='back')],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(f"You've chosen {chosen_AMPM}, Is this correct?", reply_markup=reply_markup)
    return CONFIRM_AMPM


# CONFIRM_AMPM FUNCTION
async def confirm_AMPM(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_response = query.data.lower()

    if user_response == "confirm":
        
        chosen_AMPM = context.user_data['chosen_AMPM']
        chosen_class = context.user_data['chosen_class']

        await query.edit_message_text(
            f"Great! You've chosen {chosen_class} and {chosen_AMPM}. Please input your attendance in 2 lines, first line for Present, second line for Status.\n\nFor e.g.\n3\n0(1x LD, 1x Rest In Bunk)"
            )
        return INPUT_ATTENDANCE
    
    elif user_response == 'back':
        # Same as authentication
        keyboard = [
            [InlineKeyboardButton("AM", callback_data='AM')],
            [InlineKeyboardButton("PM", callback_data='PM')],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text("Please choose AM or PM!", reply_markup=reply_markup)
        return CHOOSE_AMPM
    
    return CONFIRM_AMPM
       

# INPUT_ATTENDANCE FUNCTION
async def input_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_list = update.message.text.strip().splitlines()

    if update.message.text == '/cancel':
        context.user_data.clear()
        await update.message.reply_text("Operation canceled. Type /attendance to start again.")
        return ConversationHandler.END

    if len(input_list) != 2:
        await update.message.reply_text("Invalid input. Please enter exactly two lines of data.")
        return INPUT_ATTENDANCE
    
    numeric_input = input_list[0]
    alphanumeric_input = input_list[1]

    if numeric_input.isnumeric() and alphanumeric_input:
        chat_id = context.user_data["chat_id"]
        chosen_class = context.user_data['chosen_class']
        chosen_AMPM = context.user_data['chosen_AMPM']
        response = supabase_client.table('ICs').select('*').execute()
        data = response.data
    
        match_found = any(row.get('telegram_id') == chat_id for row in data)

        

        if match_found:
            for worksheet in sh.worksheets():
                # Get all dates from the current worksheet
                dates_row = worksheet.row_values(4)
                # Iterate over the dates and find the matching one
                for index, date in enumerate(dates_row):
                    try:
                        # Convert both dates to datetime objects for comparison
                        worksheet_date = datetime.strptime(date, "%d/%m/%Y").date()
                        current_date_obj = datetime.strptime(current_date, "%d/%m/%Y").date()
                        # Check if the dates match
                        if worksheet_date == current_date_obj:
                            # Retrieve all values from column A
                            class_column = worksheet.col_values(1)
                            # Find the index where "CLASS" appears
                            class_index = class_column.index("CLASS") if "CLASS" in class_column else -1
                            if class_index != -1:
                                # Extract class names until 'STATUS' is encountered
                                class_names = []
                                for class_name in class_column[class_index + 1:]:
                                    if class_name == 'STATUS':
                                        break
                                    class_names.append(class_name)
                            # Find the corresponding AM/PM label for the chosen date
                            ampm_labels = worksheet.row_values(8)
                            ampm_label = ampm_labels[index]
                            
                            # Find the column index corresponding to the chosen class
                            class_column = worksheet.col_values(1)
                            class_row = class_column.index(chosen_class) + 1  # Add 1 to adjust for 0-based indexing

                            if class_row != -1:
                                # Calculate the cell coordinates (row, column) for the attendance
                                present_input_row = class_row
                                status_input_row = present_input_row + len(class_names) + 1
                                if chosen_AMPM == 'AM':
                                    cell_column = index + 1  # Add 1 to adjust for 0-based indexing
                                else:  # chosen_AMPM == 'PM'
                                    cell_column = index + 2  # Add 2 to adjust for 0-based indexing

                                # Write the present_input value to the calculated cell
                                worksheet.update_cell(present_input_row, cell_column, numeric_input)

                                # Write the status_input to the calculated cell
                                worksheet.update_cell(status_input_row, cell_column, alphanumeric_input)

                                # No need to search further since the date and class were found
                                # assessment_result = f"Chat ID: {chat_id}\nDate: {current_date}\nChosen Class: {chosen_class}\nChosen AM or PM: {chosen_AMPM}\nPresent(Numeric Input): {numeric_input}\nStatus(Alphanumeric Input): {alphanumeric_input}"
                                # await update.message.reply_text(f"Assessment Result:\n{assessment_result}")
                                message = "You have successfully inputted your attendance!"
                                await update.message.reply_text(message)
                                return ConversationHandler.END
                    except ValueError:
                        continue  # Ignore non-date values

        
        else:
            supabase_client.table("ICs").insert({"telegram_id":chat_id, "chosen_class":chosen_class}).execute()
            for worksheet in sh.worksheets():
                print("Processing worksheet:", worksheet.title)
                # Get all dates from the current worksheet
                dates_row = worksheet.row_values(4)
                # Iterate over the dates and find the matching one
                for index, date in enumerate(dates_row):
                    try:
                        # Convert both dates to datetime objects for comparison
                        worksheet_date = datetime.strptime(date, "%d/%m/%Y").date()
                        current_date_obj = datetime.strptime(current_date, "%d/%m/%Y").date()
                        # Check if the dates match
                        if worksheet_date == current_date_obj:
                            # Retrieve all values from column A
                            class_column = worksheet.col_values(1)
                            # Find the index where "CLASS" appears
                            class_index = class_column.index("CLASS") if "CLASS" in class_column else -1
                            if class_index != -1:
                                # Extract class names until 'STATUS' is encountered
                                class_names = []
                                for class_name in class_column[class_index + 1:]:
                                    if class_name == 'STATUS':
                                        break
                                    class_names.append(class_name)
                            # Find the corresponding AM/PM label for the chosen date
                            ampm_labels = worksheet.row_values(8)
                            ampm_label = ampm_labels[index]
                            
                            # Find the column index corresponding to the chosen class
                            class_column = worksheet.col_values(1)
                            class_row = class_column.index(chosen_class) + 1  # Add 1 to adjust for 0-based indexing

                            if class_row != -1:
                                # Calculate the cell coordinates (row, column) for the attendance
                                present_input_row = class_row
                                status_input_row = present_input_row + len(class_names) + 1
                                if chosen_AMPM == 'AM':
                                    cell_column = index + 1  # Add 1 to adjust for 0-based indexing
                                else:  # chosen_AMPM == 'PM'
                                    cell_column = index + 2  # Add 2 to adjust for 0-based indexing

                                # Write the present_input value to the calculated cell
                                worksheet.update_cell(present_input_row, cell_column, numeric_input)

                                # Write the status_input to the calculated cell
                                worksheet.update_cell(status_input_row, cell_column, alphanumeric_input)

                                # No need to search further since the date and class were found
                                # assessment_result = f"Chat ID: {chat_id}\nDate: {current_date}\nChosen Class: {chosen_class}\nChosen AM or PM: {chosen_AMPM}\nPresent(Numeric Input): {numeric_input}\nStatus(Alphanumeric Input): {alphanumeric_input}"
                                # await update.message.reply_text(f"Assessment Result:\n{assessment_result}")
                                message = "You have successfully inputted your attendance!"
                                await update.message.reply_text(message)
                                return ConversationHandler.END
                    except ValueError:
                        continue  # Ignore non-date values
    else:
        await update.message.reply_text("Invalid input. Please enter numeric data followed by alphanumeric data.")
        return INPUT_ATTENDANCE


# FEEDBACK_COMMAND FUNCTION
async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Please reply with your feedback. I will relay the message to my developer')
    context.user_data['expecting_feedback'] = True


# HANDLE_FEEDBACK FUNCTION
async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'expecting_feedback' in context.user_data and context.user_data['expecting_feedback']:
        feedback_text = update.message.text
        sender_username = update.message.from_user.username
        message = f"New feedback from @{sender_username}:\n\n{feedback_text}"
        await context.bot.send_message(chat_id=MY_TELEGRAM_CHAT_ID, text=message)
        await update.message.reply_text('Thank you for your feedback! It has been sent to the developer.')
        # Reset the state
        context.user_data['expecting_feedback'] = False
    else:
        await update.message.reply_text('I was not expecting any feedback at this moment.')


# CANCEL_COMMAND FUNCTION
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'chosen_class' in context.user_data:
        del context.user_data['chosen_class']  # Clear the user data
    
    context.user_data.clear()  # Clear all user data
    await update.message.reply_text("Operation canceled. Type /attendance to start again.")
    return ConversationHandler.END


# HELP_COMMAND FUNCTION
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Good Day! You can use the following commands:\n"
        "/attendance - Start the attendance process\n"
        "/cancel - Cancel the current operation\n"
        "/about - Get help\n"
        "\n"
        "Enjoy using PTSS Learnet Bot? Please give us some feedback! /feedback"
    )


# ABOUT_COMMAND FUNCTION
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "This bot was developed by PTSS, with the aims of digitalising exisiting training processes.\n"
        "\n"
        "Developer: 3SG Amadeus Alexander"
    )


# ERROR FUNCTION
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")


# TO RUN THE BOT
if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()

    # CONVERSATION HANDLER
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('attendance', attendance_command)],
        states={
            CHOOSE_CLASS: [CallbackQueryHandler(choose_class)],
            CONFIRM_CLASS: [CallbackQueryHandler(confirm_class)],
            AUTHENTICATION: [MessageHandler(filters.TEXT, authentication)],
            CHOOSE_AMPM: [CallbackQueryHandler(choose_AMPM)],
            CONFIRM_AMPM: [CallbackQueryHandler(confirm_AMPM)],
            INPUT_ATTENDANCE: [MessageHandler(filters.TEXT, input_attendance)],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )

    
    # COMMANDS
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('about', about_command))
    app.add_handler(CommandHandler('feedback', feedback_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback))
    app.add_handler(CommandHandler('cancel', cancel_command))

    # ERRORS
    app.add_error_handler(error)


    # BOT POLLING
    app.run_polling(poll_interval=3)