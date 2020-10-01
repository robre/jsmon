# JSMon
JSMon - JavaScript Change Monitor for BugBounty

This is a fork of JSMon by robre modified to support Slack instead of Telegram with some minor fixes. You'll need to create a Slack OAuth app then assign it `files:write` and   `files:write:user` permissions the replace `SLACK_TOKEN` in the source code with your own.

And don't forget to install Slack library as follows

```
pip3 install slackclient
```

You can create Slack App in: https://api.slack.com/apps

Token and permissions in: https://api.slack.com/apps/[APP_ID]/oauth?
