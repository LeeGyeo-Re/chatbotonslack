from flask import Flask,  request,  make_response
from slackclient import SlackClient
from pymongo import MongoClient
import json
import datetime

import smtplib
import time
import imaplib
import email

import re

app = Flask(__name__)

connection = MongoClient("localhost", 27017)
db = connection.BBB
collection = db.testCollection

slack_token = 'xoxb-502651382259-507358690916-jFPcxXUi9xIODzyTIeec3HNA'
slack_client_id = '502651382259.508927935334'
slack_client_secret = '52b455af33c4e2037f8347fb9a3a1685'
slack_verification = 'Tvkpj2jipEyFxJMclomhM99e'
sc = SlackClient(slack_token)


def read_email_from_gmail(smtp_server, email, pwd):
    mail = imaplib.IMAP4_SSL(smtp_server)
    mail.login(email, pwd)
    mail.select('inbox')

    type, data = mail.search(None, 'ALL')
    mail_ids = data[0]

    id_list = mail_ids.split()
    first_email_id = int(id_list[0])
    latest_email_id = int(id_list[-1])

    for i in range(latest_email_id, first_email_id, -1):
        typ, data = mail.fetch(str(i).encode(), '(RFC822)')
        str_email = []
        for response_part in data:
            if isinstance(response_part, tuple):
                msg = email.message_from_string(response_part[1])
                email_subject = msg['subject']
                email_from = msg['from']

                print('From : ' + email_from + '\n')
                print('Subject : ' + email_subject + '\n')
                str_email.append('From'+email_from+'Subject'+email_subject)
    return str_email



# stolen liberally from somewhere on the net

def add_to_do(user, text, month, date):
    collection.insert({
        "id": user,
        "content": text,
        "month": month,
        "date": date
    })
    print("insert Success!")

def view_your_today(user, date):
    print(date)
    todo = collection.find({"id" : user, "date":date.replace("일","")},{"content":1})
    result = [document["content"].replace("<@UEXAJLASY>  ","") for document in todo]

    return result




# 이벤트 핸들하는 함수

def _event_handler(event_type, slack_event):
    print(slack_event["event"])
    now = datetime.datetime.now()
    now_date = now.strftime('%d')
    now_month = now.strftime("%m")

    if event_type == "app_mention":

        user = slack_event["event"]["user"]
        channel = slack_event["event"]["channel"]
        text = slack_event["event"]["text"]

        if "/추가" in text:
            p = re.compile('(\d+)/(\d+)/(\d+)')
            match = p.search(text)
            if match:
                date = match.group(3)
                month = match.group(2)
                add_to_do(user, text.replace("/추가", "").replace(match.group(), ""), month, date)
            else :
                add_to_do(user, text.replace("/추가", ""), now_month, now_date)

            sc.api_call(
                "chat.postMessage",
                channel=channel,
                text=user + "님의 일정이 입력되었습니다."
            )

        elif "/읽기" in text:
            temp = read_email_from_gmail('smtp.gmail.com','lgr6952','rufp6952!!')
            sum = ""
            for i in temp:
                sum+=i
            print(sum)
            sc.api_call(
                "chat.postMessage",
                channel=channel,
                text=sum
            )



        elif "/도움말" in text:
            sc.api_call(
                "chat.postMessage",
                channel=channel,
                text="(ex) @elice_bot2 /추가 오늘은 ssafy에서 공부를 합니다 \n\n/추가 : 일정추가\n/조회 : 일정조회\n /등록 id 띄고 pass (ex)lee1234 1234567\n"
            )

        elif "/조회" in text:
            # p1 = re.compile('(\d+)월(\d+)일')
            p2 = re.compile('(\d+)일')
            match = p2.search(text)
            if match:

                output = ""
                temp = []
                temp = view_your_today(user, match.group())
                i = 1
                for x in temp:
                    output += str(i) + "번째 : " + str(x) + "\n"
                    i += 1
                sc.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text=output
                )

            else:

                output = ""
                temp = []
                temp = view_your_today(user, now_date)
                i = 1
                for x in temp:
                    output +=str(i)+"번째 : " + str(x)+"\n"
                    i+=1
                print(output)
                sc.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text=output
                )

        else:
            sc.api_call(
                "chat.postMessage",
                channel=channel,
                text="(ex) @elice_bot2 /추가 오늘은 ssafy에서 공부를 합니다 \n\n/추가 : 일정추가\n/조회 : 일정조회\n /등록 id 띄고 pass (ex)lee1234 1234567\n"
            )

    return make_response("App mention message has been sent", 200, )

    # ============= Event Type Not Found! ============= #
    # If the event_type does not have a handler
    message = "You have not added an event handler for the %s" % event_type
    # Return a helpful error message
    return make_response(message, 200, {"X-Slack-No-Retry": 1})

@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route("/listening", methods=["GET", "POST"])
def hears():
    print("handling success!")
    slack_event = json.loads(request.data)

    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type":
                                                                 "application/json"
                                                             })

    if slack_verification != slack_event.get("token"):
        message = "Invalid Slack verification token: %s" % (slack_event["token"])
        make_response(message, 403, {"X-Slack-No-Retry": 1})

    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return _event_handler(event_type, slack_event)

    # If our bot hears things that are not events we've subscribed to,
    # send a quirky but helpful error response
    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids\
                         you're looking for.", 404, {"X-Slack-No-Retry": 1})

# @app.route('/update', methods=['POST','GET'])
# def update():
#     if request.method == 'POST':
#         collection.save({
#           "_id": ObjectId(request.form["_id"]),
#           "title": request.form["title"],
#           "content": request.form["content"]
#         })
#         return redirect('/success')
#     else: #GET
#         _id = request.args.get('_id', '')
#         post = collection.find_one({"_id": ObjectId(_id)})
#         return redirect('/fail')
#
# @app.route('/delete/<_id>',methods=['POST','GET'])
# def delete(_id):
#     if request.method == 'POST':
#         collection.remove({"_id":ObjectId(_id)})
#         return redirect('/success')
#     else:
#         post = collection.find_one({"_id": ObjectId(_id)})
#         return render_template('delete-check.html', post = post)

@app.route('/success')
def success():
    return 'success'

@app.route('/fail')
def fail():
    return 'fail'

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000)
