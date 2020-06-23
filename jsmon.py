#!/usr/bin/env python3

import requests
import re
import os
import hashlib
import json

gEndpoints = {} # global Endpoint List

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

def notify(endpoint,prev, new):
    print("[!!!] Endpoint [ {} ] has changed from {} to {}".format(endpoint, prev, new))
    TELEGRAM_TOKEN = '1216105549:AAHEfqRMGjenWQsFTp5ZXaE3ap-BK8BUBBE'
    TELEGRAM_CHAT_ID = '115041299'

    prevsize = get_file_stats(prev).st_size
    newsize = get_file_stats(new).st_size
    log_entry = "{} has been updated from {}({}) to {}({})".format(endpoint, prev,prevsize, new,newsize)
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': log_entry,
        'parse_mode': 'HTML'
    }
    return requests.post("https://api.telegram.org/bot{token}/sendMessage".format(token=TELEGRAM_TOKEN),
                             data=payload).content

def main():
    allendpoints = get_endpoint_list('targets')
    print(allendpoints)

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
