#!/usr/bin/env python3

import requests
import re
import os
import hashlib
import json
import difflib
import jsbeautifier
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
from decouple import config

# Disable warnings about expired/invalid certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Environment variables (do not put your real keys here!)
TELEGRAM_TOKEN = config("JSMON_TELEGRAM_TOKEN", default="CHANGEME")
TELEGRAM_CHAT_ID = config("JSMON_TELEGRAM_CHAT_ID", default="CHANGEME")
SLACK_TOKEN = config("JSMON_SLACK_TOKEN", default="CHANGEME")
SLACK_CHANNEL_ID = config("JSMON_SLACK_CHANNEL_ID", default="CHANGEME")
NOTIFY_SLACK = config("JSMON_NOTIFY_SLACK", default=False, cast=bool)
NOTIFY_TELEGRAM = config("JSMON_NOTIFY_TELEGRAM", default=False, cast=bool)

if NOTIFY_SLACK:
    from slack import WebClient
    from slack.errors import SlackApiError
    if SLACK_TOKEN == "CHANGEME":
        print("ERROR SLACK TOKEN NOT FOUND!")
        exit(1)
    client = WebClient(token=SLACK_TOKEN)


def is_valid_endpoint(endpoint):
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, endpoint) is not None


def get_endpoint_list(endpointdir):
    endpoints = []
    filenames = []
    for (dp, dirnames, files) in os.walk(endpointdir):
        filenames.extend(files)
    filenames = list(filter(lambda x: x[0] != ".", filenames))
    for file in filenames:
        with open(f"{endpointdir}/{file}", "r") as f:
            endpoints.extend(f.readlines())

    return list(map(lambda x: x.strip(), endpoints))


def get_endpoint(endpoint):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Connection": "keep-alive",
    }

    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        response = session.get(endpoint, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        return response.text
    except requests.exceptions.SSLError as ssl_err:
        print(f"[SSL ERROR] SSL failure when accessing {endpoint}: {ssl_err}")
        return ""
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to access {endpoint}: {e}")
        return ""


def get_hash(string):
    return hashlib.md5(string.encode("utf8")).hexdigest()[:10]


def save_endpoint(endpoint, ephash, eptext):
    with open("jsmon.json", "r") as jsm:
        jsmd = json.load(jsm)
        if endpoint in jsmd.keys():
            jsmd[endpoint].append(ephash)
        else:
            jsmd[endpoint] = [ephash]

    with open("jsmon.json", "w") as jsm:
        json.dump(jsmd, jsm)

    with open(f"downloads/{ephash}", "w") as epw:
        epw.write(eptext)


def get_previous_endpoint_hash(endpoint):
    with open("jsmon.json", "r") as jsm:
        jsmd = json.load(jsm)
        if endpoint in jsmd.keys():
            return jsmd[endpoint][-1]
        else:
            return None


def get_file_stats(fhash):
    return os.stat(f"downloads/{fhash}")


def get_diff(old, new):
    opt = {
        "indent_with_tabs": 1,
        "keep_function_indentation": 0,
    }
    try:
        oldlines = open(f"downloads/{old}", "r").readlines()
    except FileNotFoundError:
        oldlines = []

    try:
        newlines = open(f"downloads/{new}", "r").readlines()
    except FileNotFoundError:
        newlines = []

    if not oldlines or not newlines:
        return ""

    oldbeautified = jsbeautifier.beautify("".join(oldlines), opt).splitlines()
    newbeautified = jsbeautifier.beautify("".join(newlines), opt).splitlines()

    differ = difflib.HtmlDiff()
    html = differ.make_file(oldbeautified, newbeautified)
    return html


def notify_telegram(endpoint, prev, new, diff, prevsize, newsize):
    print(f"[!!!] Endpoint [ {endpoint} ] has changed from {prev} to {new}")
    log_entry = (f"{endpoint} has been updated from <code>{prev}</code>(<b>{prevsize}</b> Bytes) "
                 f"to <code>{new}</code>(<b>{newsize}</b> Bytes)")
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': log_entry,
        'parse_mode': 'HTML'
    }
    fpayload = {
        'document': ('diff.html', diff)
    }

    sendfile = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument",
                             files=fpayload, data=payload)
    return sendfile


def notify_slack(endpoint, prev, new, diff, prevsize, newsize):
    try:
        response = client.files_upload(
            initial_comment=f"[JSmon] {endpoint} has been updated! Download the diff HTML file below to check changes.",
            channels=SLACK_CHANNEL_ID,
            content=diff,
            channel=SLACK_CHANNEL_ID,
            filetype="html",
            filename="diff.html",
            title="Diff changes"
        )
        return response
    except SlackApiError as e:
        assert e.response["ok"] is False
        print(f"Got an error: {e.response['error']}")


def notify(endpoint, prev, new):
    diff = get_diff(prev, new)
    if not diff:
        print(f"[!] Unable to generate diff for {endpoint} (file missing)")
        return

    try:
        prevsize = get_file_stats(prev).st_size
    except FileNotFoundError:
        prevsize = 0

    try:
        newsize = get_file_stats(new).st_size
    except FileNotFoundError:
        newsize = 0

    if NOTIFY_TELEGRAM:
        notify_telegram(endpoint, prev, new, diff, prevsize, newsize)

    if NOTIFY_SLACK:
        notify_slack(endpoint, prev, new, diff, prevsize, newsize)


def main():
    print("JSMon - Web File Monitor")

    if not (NOTIFY_SLACK or NOTIFY_TELEGRAM):
        print("You need to set up Slack or Telegram notifications for JSMon to work!")
        exit(1)
    if NOTIFY_TELEGRAM and "CHANGEME" in [TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]:
        print("Please set up your Telegram Token and Chat ID!")
    if NOTIFY_SLACK and "CHANGEME" in [SLACK_TOKEN, SLACK_CHANNEL_ID]:
        print("Please set up your Slack Token and Channel ID!")

    allendpoints = get_endpoint_list('targets')

    for ep in allendpoints:
        prev_hash = get_previous_endpoint_hash(ep)
        ep_text = get_endpoint(ep)
        ep_hash = get_hash(ep_text)
        if ep_hash == prev_hash:
            continue
        else:
            save_endpoint(ep, ep_hash, ep_text)
            if prev_hash is not None:
                notify(ep, prev_hash, ep_hash)
            else:
                print(f"New endpoint enrolled: {ep}")


if __name__ == "__main__":
    main()
