#!/usr/bin/env python3

import requests
import re
import os
import hashlib
import json
import difflib
import jsbeautifier
from slack import WebClient
from slack.errors import SlackApiError

SLACK_TOKEN = "SLACK_OAUTH2_TOKEN" #e.g: xoxp-5XXX...
files_to_skip = ['.gitignore', '.DS_Store']
client = WebClient(token=SLACK_TOKEN)

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

    differ = difflib.HtmlDiff()
    html = differ.make_file(oldbeautified,newbeautified)
    return html

def notify(endpoint,prev, new):
    diff = get_diff(prev,new)
    prevsize = get_file_stats(prev).st_size
    newsize = get_file_stats(new).st_size
    try:
        response = client.files_upload(
            initial_comment = "[JSmon] {} has been updated! Download below diff HTML file to check changes.".format(endpoint),
            channels = "CF112CRPX",
            content = diff,
            channel = "CF112CRPX",
            filetype = "html",
            filename = "diff.html",
            title = "Diff changes"
            )
    except SlackApiError as e:
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")

def main():
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
                notify(ep,prev_hash, ep_hash)
            else:
                print("[!] New Endpoint enrolled: {}".format(ep))
main()
