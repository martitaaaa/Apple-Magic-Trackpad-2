# Apple Magic Trackpad 2

This is just a thing I did for fun. It reads the events from the descriptor file and parses it to display them on a canvas using websocket.

In the first place, I reversed engineer what the event file was outputing without knowing anything about EVDEV library. Then I rewrote everything using the library because it was simpler. It was a bit stupid, but at least I was proud of myself because I extracted usable data from "raw" bytes from the event file descriptor

## How to use the files

The main file (the one that runs with the web app) is the one named [main.py](/main.py). When running this, it receives a websocket connection from a browser running [main.html](/main.html) file (you may need to change some hostnames here and there)

The other file named [trackpad.py](/trackpad.py) is used as a library, just import the class Trackpad and it should be good to go.

> **NOTE:** You must have paired and connected the trackpad to the Linux machine beforehand
