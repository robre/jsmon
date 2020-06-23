# jsmon
JavaScript Change Monitor for BugBounty

## Installation

`git clone https://github.com/robre/jsmon.git & cd jsmon & TODO`


## Features

- Keep Track of endpoints - check them in a configurable interval 
- when endpoints change - send a notification via slack/telegram/mail?



## Structure

- Provide Endpoints via files in $ENDPOINTS directory (line seperated endpoints)
- Per Endpoint
- Download Endpoints and save whole or hash? (save as its own hash.js)
- Everyday request huge number of js files..
- have a file that tracks hash - endpoint relations. Simple JSON


## Usage

jsmon is designed to keep track of javascript files on websites - but it can be used for any filetype
To add endpoints 
