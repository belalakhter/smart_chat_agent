import os
import threading
from datetime import datetime
from collections import defaultdict
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

class AlertRunner:
    def __init__(self):
        self.slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        self.active_alerts = {}
        self.message_tracker = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        self.lock = threading.Lock()

    def add_alert(self, user_id, channel, user_name):
        with self.lock:
            start_time = datetime.now()
            self.active_alerts[user_id] = {
                'channel': channel,
                'start_time': start_time,
                'user_name': user_name
            }

            print(f"Added alert for {user_name} in channel {channel}")

            timer = threading.Timer(300, self.send_report, args=[user_id])
            timer.daemon = True
            timer.start()

    def track_message(self, channel, sender_user_id):
        with self.lock:
            for alert_user_id, alert in self.active_alerts.items():
                if alert['channel'] == channel:
                    self.message_tracker[alert_user_id][channel][sender_user_id] += 1

                    total_count = sum(self.message_tracker[alert_user_id][channel].values())
                    print(f"Tracked message from {sender_user_id} for alert of {alert_user_id} in #{channel}. "
                          f"Total: {total_count}")


    def send_report(self, requesting_user_id):
        try:
            with self.lock:
                if requesting_user_id not in self.active_alerts:
                    return

                alert_info = self.active_alerts[requesting_user_id]
                channel = alert_info['channel']
                user_name = alert_info['user_name']
                message_counts = self.message_tracker.get(requesting_user_id, {}).get(channel, {})
                if not message_counts:
                    report_text = f"Activity Report for #{channel}\n\nNo messages were tracked."
                else:
                    sorted_users = sorted(message_counts.items(), key=lambda x: x[1], reverse=True)

                    report_lines = [f"12-Hour Activity Report for #{channel}\n"]

                    for user_id, count in sorted_users:
                        display_name = user_id
                        report_lines.append(f"• {display_name}: {count} messages")

                    total_messages = sum(message_counts.values())
                    total_users = len(message_counts)
                    report_lines.append(f"\nTotal: {total_messages} messages from {total_users} users")

                    report_text = "\n".join(report_lines)

                self.slack_client.chat_postMessage(
                    channel=requesting_user_id,
                    text=report_text
                )
                print(f"Sent report to {user_name} ({requesting_user_id})")
                if requesting_user_id in self.message_tracker:
                    del self.message_tracker[requesting_user_id]
                if channel in self.message_tracker:
                    del self.message_tracker[channel]

        except SlackApiError as e:
            print(f"Error sending report: {e}")
        except Exception as e:
            print(f"Unexpected error in send_report: {e}")

    def get_active_alerts(self):
        with self.lock:
            return dict(self.active_alerts)

    def cancel_alert(self, user_id):
        with self.lock:
            alert_info = self.active_alerts.get(user_id)
            if alert_info:
                channel = alert_info.get('channel')
                del self.active_alerts[user_id]
                if channel and channel in self.message_tracker:
                    del self.message_tracker[channel]
                return True
            return False

alert_runner = AlertRunner()

def get_alert_runner():
    return alert_runner
