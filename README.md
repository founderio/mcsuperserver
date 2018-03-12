# MCSuperServer

These versions of mcsuperserver and mcsuperserverscript are based on [mcsuperserver.py by Paul Andreassen](http://members.iinet.net.au/~paulone/mcsuperserver.html).

The minecraft communication protocol changed with Versions 1.4.2 and 1.7.2, the versions in this repository are adapted to these changes. Originally, these versions were published on the [Minecraft Forums](https://www.minecraftforum.net/forums/support/server-support/server-administration/1938098-mcsuperserver-py-for-1-7-2-and-1-4-2-1-6-4) and downloadable via Dropbox links.

# mcsuperserver.py

The mcsuperserver automatically starts a Minecraft server instance when the first player joins and stops it again after the last player leaves the server.
The Minecraft server is stopped to reduce memory and cpu usage. If you have servers that are only used occasionally or only by a small number of people then they are better of being super served. A super server uses very little memory and cpu and only starts the Minecraft server when users want it. This allows many Minecraft servers with different worlds on one machine provided they aren't all running at the same time. For example with only four users the most Minecraft servers that will be running will be four but many more can be super served.

## How does it work?

The superserver handles all incoming requests by wrapping the first packages sent by the client. After starting the server, the game is directly connected to the Minecraft server.

## Compatibility

* `mcsuperserver.py` is compatible with Minecraft versions before 1.4.
  This is the original version.
* `mcsuperserver_1_4.py` is compatible with Minecraft versions 1.4.2 to 1.6.x.
  Preset for version 1.4.2.
* `mcsuperserver_1_7.py` is compatible with Minecraft versions starting from 1.7.2.
  Preset for version 1.7.2.
* Minecraft versions after 2014 are untested.

## Prerequisites

mcsuperserver requires Python 2.7 to be installed on the server machine. Python 3 is currently not supported.
It has been tested with Windows, Linux and Mac (tested with OS X Lion - might not work on more recent macOS).

## Usage

* Copy the `mcsuperserver.py` file to your minecraft server directory
* Execute the `mcsuperserver.py` file by running `python mcsuperserver.py`
	* On Linux or Mac you can also run it by making it executable `chmod +x mcsuperserver.py` and then run it directly with `./mcsuperserver.py`.
* Connect with the Minecraft client on the default port which is 25555 by entering `localhost:25555` in the server address
	* You can change the port number in the generated `mcsuperserver.properties` file.

To force the superserver to stop, use the default termination method for your system (^C) - mcsuperserver handles the teminate signal, allowing the graceful shutdown of the Minecraft server.
This also makes it possible for use with init.d scripts or similar mechanisms.

## Configuration Files

* `mcsuperserver.properties`: Automaticly created on first run. Contains settings for mcsuperserver.py in the same format as the server.properties file.
* `server.properties`: The configuration used by the Minecraft server. Read by mcsuperserver.py for settings for minecraft_server.jar.

## Minecraft Protocol Versions

For any different Minecraft Versions than the preset ones you need to adjust version and protocol version the superserver config file that gets generated on first launch.
The 1.4 and 1.7 versions allow you to change the minecraft and protocol version in their `mcsuperserver.properties` file.

You can find some of the versions here: http://wiki.vg/Protocol_History
Example: For 1.6.2 it is 74, for 1.6.4 it is 78.

A more complete list is [available in this repository](protocol_versions.txt).

# mcsuperserverscript.py

The mcsuperserverscript is an extension to the mcsuperserver that allows managing of multiple worlds and gives users some operator rights without having to add them to the ops list.

## Compatibility

* `mcsuperserverscript.py` is compatible with Minecraft versions up to 1.6.x.
  This is the original version.
* `mcsuperserverscript_1_7.py` is compatible with the new log format introduced with Minecraft 1.7.2.
  Tested with Minecraft 1.7.5.

## Prerequisites

In addition to the mcsuperserver prerequisites above:
* Requires `mcsuperserver.py` in the same directory
* Some basic knowledge of Python if you want to edit the behaviour

## How does it work?

This script overloads some functions from mcsuperserver.py to change functionality. Worlds are changed by rewriting the server.properties file and 'stop'ing the server.
All scripting is done by using console output and input, so quite limited.

## Usage

* Copy the `mcsuperserverscript.py` and `mcsuperserver.py` file to your minecraft server directory.
* Execute the `mcsuperserverscript.py` file by running `python mcsuperserverscript.py`
	* On Linux or Mac you can also run it by making it executable `chmod +x mcsuperserverscript.py` and then run it directly with `./mcsuperserverscript.py`.
* Then connect with the Minecraft client on the default port which is 25555 by entering "localhost:25555" in the server address.
	* You can change the port number in the generated `mcsuperserver.properties` file.

Using the commands:
* Enter chat mode by pressing 't' or whatever you've changed it to and type 'help' for the list of commands. Note there is no '/'.
* Enter 't' then 'helpshort' for the list of one letter commands.
* Enter 't' then 'w' or 'worlds' for a list of available worlds.
* Enter 't' then 'l {name}' or 'world {name}' to change to the {name} world.
* Enter 't' then 'd' for daytime. Creative servers only.
* Enter 't' then 'n' for nighttime. Creative servers only.
* Enter 't' then 'f' for toggledownfall. Creative servers only.
* Enter 't' then 'g {mode}' for gamemode {mode}. Creative servers only.

Basic behaviour:
* By default survial (gamemode=0 in server.properties) server users get teleport (tp)
* By default creative (gamemode=1 in server.properties) server users get teleport (tp), give, time, gamemode, toggledownfall and xp
* Each subdirectory in the Minecraft server directory is assumed to be a world except ones that start with '.'
* Multiple servers sharing the same set of worlds is supported, but disabled by default. To enable this behaviour, create an empty (zero length) file `.minecraft.running.worlds.txt` *one folder above mcsuperserverscript.py*. (The lookup is done with `../.minecraft.running.worlds.txt`)

## Configuration Files

mcsuperserverscript uses the same configuration files as mcsuperserver.

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