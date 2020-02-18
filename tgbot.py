import requests
import json
import telebot
import sqlite3
import re
import datetime
import os
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta



def rm_db():
    if os.path.exists('rates.db'):
        os.remove('rates.db')

rm_db()

b_url = 'https://api.exchangeratesapi.io/latest?base=USD'
conn = sqlite3.connect('rates.db', check_same_thread=False)
lasttime = datetime.datetime.now()



def load_hist():
    sub_days = datetime.datetime.today() + relativedelta(days=-7)
    p_url = "https://api.exchangeratesapi.io/history?start_at=%s&end_at=%s&base=USD&symbols=CAD" % (
        sub_days.strftime('%Y-%m-%d'), lasttime.strftime('%Y-%m-%d'))
    return json.loads(requests.get(p_url).text)


def load_rates():
    return json.loads(requests.get(b_url).text)


def before_bot():
    raw_rates = load_rates()
    rates = {k: round(raw_rates["rates"][k], 2) for k in raw_rates["rates"]}
    c = conn.cursor()
    c.execute('''CREATE TABLE rates
                (currency text, course real)''')
    for i in rates.items():
        insert = "INSERT INTO rates (currency, course) \
            VALUES %s;" % (str(i).replace('{', '').replace('}', '').replace(':', ','))
        c.execute(insert)
        conn.commit()


before_bot()

# tg bot

bot = telebot.TeleBot('793393414:AAGnfD3QvR6U8EVTyq8VCTlPZDtVJpLhJL8')


def create_graph():
    raw_df = load_hist()
    x_axis = sorted(raw_df['rates'])
    y_axis = []
    for i in sorted(raw_df['rates'].items()):
        y_axis.append(float(str([*list(i[1].values())]).replace('[','').replace(']','')))
    plt.plot(x_axis, y_axis, color='green', linestyle='dashed', linewidth=3,
             marker='o', markerfacecolor='blue', markersize=10)
    plt.xlabel('x - date')
    plt.ylabel('y - rate')
    plt.title('USD-CAD')
    plt.savefig('hist.png')


def count_exchange(inp_str):
    x = re.search('\d+|$', inp_str).group()
    exch_curr = inp_str[-3:]
    c = conn.cursor()
    c.execute("SELECT * FROM rates")
    results = c.fetchall()
    qdict = dict(results)
    rounded = round(int(x) * qdict[exch_curr], 2)
    return '$' + str(rounded)


def list_output():
    c = conn.cursor()
    c.execute("SELECT * FROM rates")
    results = c.fetchall()
    qdict = dict(results)
    return '\n'.join('%s: %s' % k for k in qdict.items())


def update_rates():
    print('ok')
    raw_rates = load_rates()
    rates = {k: round(raw_rates["rates"][k], 2) for k in raw_rates["rates"]}
    c = conn.cursor()
    for i in rates.keys():
        update = "UPDATE rates set course = %s where currency = '%s'" % (rates[i], i)
        c.execute(update)
        conn.commit()


@bot.message_handler(commands=['list'])
def start_command(message):
    reqtime = datetime.datetime.now()
    delta = 10
    diffsec = (reqtime - lasttime).seconds
    difftime = diffsec / 60
    if difftime < delta:
        bot.send_message(
            message.chat.id,
            list_output()
        )
    else:
        update_rates()
        bot.send_message(
            message.chat.id,
            list_output()
        )


@bot.message_handler(commands=['history'])
def start_hist(message):
    create_graph()
    img = open('hist.png', 'rb')
    bot.send_photo(message.chat.id, img)
    img.close()
    os.remove('hist.png')



@bot.message_handler(commands=['exchange'])
def start_exchange(message):
    bot.send_message(message.from_user.id, "Write how much USD you want exchange and for which currency\n" +
                     "Example: 10 USD to CAD")
    bot.register_next_step_handler(message, get_exchange)


def get_exchange(message):
    usr_exch = message.text
    bot.send_message(message.from_user.id,
                     count_exchange(usr_exch))


def main():
    bot.polling(none_stop=True, interval=5)


if __name__ == '__main__':
    main()
