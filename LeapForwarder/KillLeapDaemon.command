#/bin/bash

# See http://lists.apple.com/archives/remote-desktop/2006/Sep/msg00092.html
# ps axco pid,command | grep FWXClientAssistant | awk '{ print $1; }' | xargs kill -9

ps axco pid,command | grep "leapd" | awk '{ print $1; }' | xargs sudo kill -9
