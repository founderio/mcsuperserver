# MCSuperServer

These versions of mcsuperserver and mcsuperserverscript are based on [mcsuperserver.py by Paul Andreassen](http://members.iinet.net.au/~paulone/mcsuperserver.html).

The minecraft communication protocol changed with Versions 1.4.2 and 1.7.2, the versions in this repository are adapted to these changes. Originally, these versions were published on the [Minecraft Forums](https://www.minecraftforum.net/forums/support/server-support/server-administration/1938098-mcsuperserver-py-for-1-7-2-and-1-4-2-1-6-4) and downloadable via Dropbox links.

# mcsuperserver.py

The mcsuperserver automatically starts a Minecraft server instance when the first player joins and stops it again after the last player leaves the server.

* `mcsuperserver.py` is compatible with Minecraft versions before 1.4.
  This is the original version.
* `mcsuperserver_1_4.py` is compatible with Minecraft versions 1.4.2 to 1.6.x.
  Preset for version 1.4.2.
* `mcsuperserver_1_7.py` is compatible with Minecraft versions starting from 1.7.2.
  Preset for version 1.7.2.
* Minecraft versions after 2014 are untested.

## Minecraft Protocol Versions

For any different Minecraft Versions than the preset ones you need to adjust version and protocol version the superserver config file that gets generated on first launch.

You can find some of the versions here: http://wiki.vg/Protocol_History
Example: For 1.6.2 it is 74, for 1.6.4 it is 78.

A more complete list is [available in this repository](protocol_versions.txt).

# mcsuperserverscript.py

The mcsuperserverscript is an extension to the mcsuperserver that allows managing of multiple worlds and gives users some operator rights without having to add them to the ops list.

* `mcsuperserverscript.py` is compatible with Minecraft versions up to 1.6.x.
  This is the original version.
* `mcsuperserverscript_1_7.py` is compatible with the new log format introduced with Minecraft 1.7.2.
  Tested with Minecraft 1.7.5.

## Identifying which mcsuperserverscript version to use

If the log output of your Minecraft server looks like this, use the original version:
```
2014-03-25 16:00:00 [INFO] <founderio> Some Chat Message
```
If it looks like this, use the 1.7 version:
```
[16:00:00] [Server thread/INFO]: <founderio> Some Chat Message
```
For any other log format, this script is likely incompatibly - report an issue if it does not work.