#!/usr/bin/env python3

import requests
import re
import os
import hashlib
import json
import difflib
import jsbeautifier

TELEGRAM_TOKEN = 'CHANGEME'
TELEGRAM_CHAT_ID = 'CHANGEME'
files_to_skip = ['.gitignore', '.DS_Store']


def is_valid_endpoint(endpoint):
    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    # check if valid url
    return re.match(regex, endpoint) is not None

def get_endpoint_list(endpointdir):
    endpoints = []
    filenames = []
    for (dp, dirnames, files) in os.walk(endpointdir):
        filenames.extend(files)
    
    for file in filenames:
        if file not in files_to_skip:
            with open("{}/{}".format(endpointdir,file), "r") as f:
                endpoints.extend(f.readlines())
        

    # Load all endpoints from a dir into a list
    return list(map(lambda x: x.strip(), endpoints))

def get_endpoint(endpoint):
    # get an endpoint, return its content
    r = requests.get(endpoint)
    return r.text

def get_hash(string):
    # Hash a string
    return hashlib.md5(string.encode("utf8")).hexdigest()[:10]

def save_endpoint(endpoint, ephash, eptext):
    # save endpoint content to file
    # add it to  list of 
    with open("jsmon.json", "r") as jsm:
        jsmd = json.load(jsm)
        if endpoint in jsmd.keys():
            jsmd[endpoint].append(ephash)
        else:
            jsmd[endpoint] = [ephash]

    with open("jsmon.json", "w") as jsm:
        json.dump(jsmd,jsm)

    with open("downloads/{}".format(ephash), "w") as epw:
        epw.write(eptext)

     
def get_previous_endpoint_hash(endpoint):
    # get previous endpoint version
    # or None if doesnt exist
    with open("jsmon.json", "r") as jsm:
        jsmd = json.load(jsm)
        if endpoint in jsmd.keys():
            return jsmd[endpoint][-1]
        else:
            return None
        

def get_file_stats(fhash):
    return os.stat("downloads/{}".format(fhash))

def get_diff(old,new):
    opt = {
        "indent_with_tabs": 1,
        "keep_function_indentation": 0,
           }
    oldlines = open("downloads/{}".format(old), "r").readlines()
    newlines = open("downloads/{}".format(new), "r").readlines()
    oldbeautified = jsbeautifier.beautify("".join(oldlines), opt).splitlines()
    newbeautified = jsbeautifier.beautify("".join(newlines), opt).splitlines()
    # print(oldbeautified)
    # print(newbeautified)

    differ = difflib.HtmlDiff()
    html = differ.make_file(oldbeautified,newbeautified)
    #open("test.html", "w").write(html)
    return html

def notify(endpoint,prev, new):
    diff = get_diff(prev,new)
    print("[!!!] Endpoint [ {} ] has changed from {} to {}".format(endpoint, prev, new))

    prevsize = get_file_stats(prev).st_size
    newsize = get_file_stats(new).st_size
    log_entry = "{} has been updated from <code>{}</code>(<b>{}</b>Bytes) to <code>{}</code>(<b>{}</b>Bytes)".format(endpoint, prev,prevsize, new,newsize)
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': log_entry,
        'parse_mode': 'HTML'
    }
    fpayload = {
        'document': ('diff.html', diff)
    }

    sendfile = requests.post("https://api.telegram.org/bot{token}/sendDocument".format(token=TELEGRAM_TOKEN),
                             files=fpayload, data=payload)
    #print(sendfile.content)
    return sendfile
    #test2 = requests.post("https://api.telegram.org/bot{token}/sendMessage".format(token=TELEGRAM_TOKEN),
    #                         data=payload).content


def main():
    print("JSMon - Web File Monitor")
    if TELEGRAM_TOKEN == "CHANGEME" or TELEGRAM_CHAT_ID == "CHANGEME":
        print("Please Set Up your Telegram Token And Chat ID!!!")
        exit(1)
        
    allendpoints = get_endpoint_list('targets')
    # print(allendpoints)

    for ep in allendpoints:
        prev_hash = get_previous_endpoint_hash(ep)
        ep_text = get_endpoint(ep)
        ep_hash = get_hash(ep_text)
        if ep_hash == prev_hash:
            continue
        else:
            save_endpoint(ep, ep_hash, ep_text)
            if prev_hash is not None:
                notify(ep,prev_hash, ep_hash)
            else:
                print("New Endpoint enrolled: {}".format(ep))
main()        

