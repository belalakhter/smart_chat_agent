import os

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from ..alert.tracker import get_alert_runner
from ..note.notes import get_note_runner
import requests
from ..summarizer.summarize import summarize_pdf
import re
from io import BytesIO
from ..summarizer.pinecone import init_pinecone,process_message
from ..summarizer.llm import contextual_prompt

app = App(token=os.environ["SLACK_BOT_TOKEN"])
alert_runner = get_alert_runner()
note_runner = get_note_runner()
pinecone_index = init_pinecone()

@app.message( re.compile(".*"))
def messages(message, client):
    message_text = message.get("text", "")
    user_id = message.get("user")
    channel_id = message.get("channel")
    try:
        user_info = client.users_info(user=user_id)
        user_name = user_info['user']['real_name']
        process_message(user_name,message_text,pinecone_index)
    except:
        user_name = user_id
    try:
        channel_info = client.conversations_info(channel=channel_id)
        channel_name = channel_info['channel']['name']
    except:
        channel_name = channel_id
    if not user_name or user_name == "None":
        print("Ignoring bot message.")
    else:
        alert_runner.track_message(channel_name, user_name)



@app.command("/accept-alerts")
def handle_accept_alerts(ack, respond, command, client):
    ack()
    try:
        user_id = command["user_id"]
        channel_id = command["channel_id"]
        try:
            user_info = client.users_info(user=user_id)
            user_name = user_info['user']['real_name']
        except:
            user_name = user_id

        try:
            channel_info = client.conversations_info(channel=channel_id)
            channel_name = channel_info['channel']['name']
        except:
            channel_name = channel_id

        alert_runner.add_alert(user_id, channel_name, user_name)


        respond({
            "response_type": "in_channel",
            "text": f" Accepted alert from {user_name}."
        })
        client.chat_postMessage(
            channel=user_id,
            text=f" Alert activated! I'm now tracking activity in {channel_name}."
        )

    except Exception as e:
        respond({
            "response_type": "ephemeral",
            "text": f"❌ Error setting up alert: {str(e)}"
        })


@app.command("/summarize")
def handle_summarize(ack, respond, command, client):
    ack()
    result = client.files_list(user=command["user_id"], count=1)
    files = result.get("files", [])
    if not files:
        respond("No recent file found to summarize.")
        return
    file = files[0]
    if file["filetype"] != "pdf":
        respond(f"Latest file is not a PDF: `{file['filetype']}`.")
        return
    download_url = file["url_private"]
    headers = {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}
    response = requests.get(download_url, headers=headers)
    print(response.headers.get("Content-Type", ""))
    pdf_bytes = BytesIO(response.content)

    temp_path = "/tmp/latest.pdf"
    with open(temp_path, "wb") as f:
        f.write(pdf_bytes.read())

    summary = summarize_pdf(temp_path)
    respond({
        "response_type": "in_channel",
        "text": f"Summary:\n{summary}"
    })



@app.command("/note")
def add_note(ack, respond, command, client):
    ack()
    user_id = command["user_id"]
    try:
        user_info = client.users_info(user=user_id)
        user_name = user_info['user']['real_name']
    except:
        user_name = user_id
    note_text = command.get("text", "").strip()
    note_runner.add_note(user_id, note_text)
    respond({
            "response_type": "in_channel",
            "text": f" Note added by {user_name}."
        })

@app.command("/ask")
def ask_history(ack, respond, command, client):
    ack()
    query = command.get("text", "").strip()
    respond({
            "response_type": "in_channel",
            "text": f"Processing your query: `{query}`…"
        })
    answer = contextual_prompt(query,pinecone_index)
    client.chat_postMessage(
            channel=command['channel_id'],
            text=answer
        )




@app.command("/get-notes")
def get_notes(ack, respond, command, client):
    ack()
    user_id = command["user_id"]
    try:
        user_info = client.users_info(user=user_id)
        user_name = user_info['user']['real_name']
    except:
        user_name = user_id
    notes = note_runner.get_notes(user_id)
    if not notes:
        message = "You don't have any saved notes yet."
    else:
        message_lines = [f"Your Notes, {user_name}:"]
        for i, note in enumerate(notes, 1):
            message_lines.append(f"{i}. {note}")
        message = "\n".join(message_lines)
    client.chat_postMessage(
        channel=user_id,
        text=message
    )



@app.command("/cancel-alert")
def handle_cancel_alert(ack, respond, command,client):
    ack()
    user_id = command["user_id"]
    try:
        user_info = client.users_info(user=user_id)
        user_name = user_info['user']['real_name']
    except:
        user_name = user_id
    try:
        if alert_runner.cancel_alert(user_id):
            respond({
                "response_type": "ephemeral",
                "text": f" Alert cancelled for {user_name}."
            })
        else:
            respond({
                "response_type": "ephemeral",
                "text": f" No active alert found for {user_name}."
            })

    except Exception as e:
        respond({
            "response_type": "ephemeral",
            "text": f" Error cancelling alert: {str(e)}"
        })

@app.command("/list-alerts")
def handle_list_alerts(ack, respond, command):
    ack()
    try:
        user_id = command["user_id"]
        active_alerts = alert_runner.get_active_alerts()

        if not active_alerts:
            respond({
                "response_type": "ephemeral",
                "text": "No active alerts are currently running."
            })
        else:
            user_alerts = [alert for uid, alert in active_alerts.items() if uid == user_id]
            alert_count = len(user_alerts)
            alert_text = "alert" if alert_count == 1 else "alerts"
            respond({
                "response_type": "ephemeral",
                "text": f"You have {alert_count} active {alert_text}."
            })
    except Exception as e:
        respond({
            "response_type": "ephemeral",
            "text": f"Error listing alerts: {str(e)}"
        })





def start_socket_client():
    try:
        handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        handler.start()
    except Exception as e:
        print(f"Error starting Socket Mode client: {e}")
    except KeyboardInterrupt:
            print("Stopped by user. Exiting cleanly.")
