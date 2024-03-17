const axios = require('axios');
const cron = require('node-cron');
const { createClient } = require('@supabase/supabase-js');

require('dotenv').config()

const supabaseURL = process.env.SUPABASE_URL
const supabaseKEY = process.env.SUPABASE_KEY
const supabase = createClient(supabaseURL, supabaseKEY);

const sendMessageAM = async (chatId) => {
    const TOKEN = process.env.TOKEN
    const apiUrl = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
  
    const messageData = {
        chat_id: chatId,
        text: 'Please input your attendance for the AM Session!\n/attendance',
    };

    try {
        const response = await axios.post(apiUrl, messageData, {
            headers: {
                'Content-Type': 'application/json',
            },
        });
        console.log('Message sent successfully:', response.data);
    } catch (error) {
        console.error('Error sending message:', error.message);
    }
};


const sendMessagePM = async (chatId) => {
    const TOKEN = process.env.TOKEN
    const apiUrl = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
  
    const messageData = {
        chat_id: chatId,
        text: 'Please input your attendance for the PM Session!\n/attendance',
    };

    try {
        const response = await axios.post(apiUrl, messageData, {
            headers: {
                'Content-Type': 'application/json',
            },
        });
        console.log('Message sent successfully:', response.data);
    } catch (error) {
        console.error('Error sending message:', error.message);
    }
};


const sendMessagesToTelegramIDsAM = async () => {
    try {
        const { data: ICs, error } = await supabase.from('ICs').select('telegram_id');

        if (error) {
            throw error;
        }
        console.log(ICs)

        if (ICs && ICs.length > 0) {
            // Create an array of promises for sending messages to each Telegram ID
            const messagePromises = ICs.map(async (ic) => {
                const chatId = ic.telegram_id;
                if (chatId) {
                    return sendMessageAM(chatId);
                } else {
                    console.error('Telegram ID is missing or incorrect for ICs:', ic);
                    return Promise.reject(new Error('Telegram ID is missing or incorrect'));
                }
            });

            // Wait for all promises to resolve or reject
            await Promise.all(messagePromises);
        } else {
            console.log('No Users found in the database.');
        }
    } catch (error) {
        console.error('Error sending messages to Telegram IDs:', error.message);
        throw error; // Reject the main promise if an error occurs
    }
};

const sendMessagesToTelegramIDsPM = async () => {
    try {
        const { data: ICs, error } = await supabase.from('ICs').select('telegram_id');

        if (error) {
            throw error;
        }
        console.log(ICs)

        if (ICs && ICs.length > 0) {
            // Create an array of promises for sending messages to each Telegram ID
            const messagePromises = ICs.map(async (ic) => {
                const chatId = ic.telegram_id;
                if (chatId) {
                    return sendMessagePM(chatId);
                } else {
                    console.error('Telegram ID is missing or incorrect for ICs:', ic);
                    return Promise.reject(new Error('Telegram ID is missing or incorrect'));
                }
            });

            // Wait for all promises to resolve or reject
            await Promise.all(messagePromises);
        } else {
            console.log('No Users found in the database.');
        }
    } catch (error) {
        console.error('Error sending messages to Telegram IDs:', error.message);
        throw error; // Reject the main promise if an error occurs
    }
};


cron.schedule('30 6 * * 1-5', sendMessagesToTelegramIDsAM, {
    timezone: 'Asia/Singapore'
  });

cron.schedule('30 12 * * 1-5', sendMessagesToTelegramIDsPM, {
    timezone: 'Asia/Singapore'
  });



