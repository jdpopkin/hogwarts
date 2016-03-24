import points_util
import cup_image
from consts import HOUSES, SLACK_TOKEN, PREFECTS, ANNOUNCERS, CHANNEL, POINTS_FILE

from collections import Counter
import os
import re
import pickle
from slackclient import SlackClient
import time
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import httplib
from threading import Thread
import psycopg2
import urlparse

nth = {
    1: "first",
    2: "second",
    3: "third",
    4: "fourth"
}

class PointCounter(object):
    def __init__(self, prefects=PREFECTS,
                 announcers=ANNOUNCERS, points_file=POINTS_FILE):
        urlparse.uses_netloc.append("postgres")
        url = urlparse.urlparse(os.environ["DATABASE_URL"])
        self.conn = psycopg2.connect(
                database=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port
        )
        self.points = self.load_all_points()
        self.prefects = prefects
        self.announcers = announcers

    def load_all_points(self):
        points = {}
        for house in HOUSES:
            points[house] = self.load_points_for(house)
        return points

    def load_points_for(self, house_name):
        cur = self.conn.cursor()
        cur.execute(
                """SELECT coalesce(sum(value), 0) FROM awardings WHERE house = %s;""",
                (house_name,)
        )
        result = cur.fetchone()[0]

        self.conn.commit()
        cur.close()
        return result

    def get_points_from(self, message, awarder):
        amount = points_util.detect_points(message)
        # only prefects can award over one point at a time
        if awarder not in self.prefects:
            amount = max(min(amount, 1), -1)
        return amount

    @staticmethod
    def message_for(house, points):
        if points > 0:
            return "%s gets %s" % (
                house, points_util.pluralized_points(points))
        return "%s loses %s" % (
            house, points_util.pluralized_points(abs(points)))

    def award_points(self, message, awarder):
        points = self.get_points_from(message, awarder)
        houses = points_util.get_houses_from(message)
        messages = []
        if points and houses:
            for house in houses:
                self.points[house] += points
                self.record_point_change(house, points)
                messages.append(self.message_for(house, points))
        return messages

    def record_point_change(self, house, points):
        cur = self.conn.cursor()
        cur.execute(
                """INSERT INTO awardings (house, value) VALUES (%s,%s);""",
                (house, points)
        )
        self.conn.commit()
        cur.close()

    def print_status(self):
        for place, (house, points) in enumerate(sorted(self.points.items(), key=lambda x: x[-1])):
            yield "In %s place, %s with %d points" % (
                nth[len(HOUSES) - place], house, points)


def is_hogwarts_related(message):
    return (
        message["type"] == "message" and
        message["channel"] == CHANNEL and
        "text" in message and
        "user" in message and
        "point" in message["text"] and
        points_util.get_houses_from(message["text"]))

def run_chatbot():
    print("Testing how logging works")
    port = int(os.environ.get("PORT", 80))
    print("Should be bound to port %s" % port)
    sc = SlackClient(SLACK_TOKEN, None, http_proxy_port=port)
    p = PointCounter()
    if sc.rtm_connect():
        while True:
            messages = sc.rtm_read()
            for message in messages:
                if is_hogwarts_related(message):
                    print 'is_hogwarts_related'
                    for m in p.award_points(message['text'], message['user']):
                        sc.api_call(
                            "chat.postMessage", channel=CHANNEL, text=m)
                    os.system(
                        "curl -F file=@%s -F title=%s -F channels=%s -F token=%s https://slack.com/api/files.upload"
                         % (cup_image.image_for_scores(p.points), '"House Points"', CHANNEL, SLACK_TOKEN))


                time.sleep(1)
    else:
        print "Connection Failed, invalid token?"

def start_server():
    port = int(os.environ.get("PORT", 80))
    server = HTTPServer(('', port), BaseHTTPRequestHandler)
    server.serve_forever()

def ping_server():
    while True:
        print "Pinging server."
        conn = httplib.HTTPSConnection(os.environ.get("URL"))
        conn.request("GET", "/")
        r1 = conn.getresponse()
        time.sleep(60 * 29)

def main():
    server_thread = Thread(target = start_server)
    server_thread.start()
    ping_thread = Thread(target = ping_server)
    ping_thread.start()

    run_chatbot()

if __name__ == "__main__":
    main()
