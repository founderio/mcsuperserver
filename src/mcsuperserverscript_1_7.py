#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   MCSuperServerScript - Adds multi-worlds to minecraft and gives users some operater commands
#   Copyright (C) 2011, 2012  Paul Andreassen
#   paul@andreassen.com.au

#   MC 1.7+ Version by Oliver Kahrmann (founderio), 2014
#   oliver.kahrmann@gmail.com

#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

# requried mcsuperserver.py version in brackets
# 0.01 20120520 (0.6) multi-worlds works and user commands works
# 0.02 20120525 (0.6) fix bug with writing out of running in mcstopped
# 0.03 20120526 (0.6) fix bug when the world is changed when no users connected
# 0.04 20120527 (0.6) fix bug spaces in world names and motd is prepended with world name
# 0.05 20120802 (0.6) had to change from using '/' for commands
# 0.06 20140325 (0.7) (founderio) Changes in Command Line Output parsing, tested with 1.7.5

import mcsuperserver, re, os, os.path, textwrap

commandsShortSurvial={
        "w":"worlds",
        "l":"world ",
        "r":"tp you lily567489",
        "a":"tp you zzcoolman",
        "p":"tp you zzPaul8888zz",
        "s":"tp you zzSarah"}
commandsShortCreative={
        "g":"gamemode you ",
        "n":"time set 13000",
        "d":"time set 1000",
        "f":"toggledownfall"}

commandsScript=["help", "helpshort", "worlds", "world", "cancel"]
commandsConsole=["help","?","list"]
commandsSurvial=["tp","tell","say"]
commandsCreative=["give","time","gamemode","toggledownfall","xp"]
commandsOp=["kick","ban","pardon","ban-ip","pardon-ip","op","deop","stop",
        "save-all","save-off","save-on","whitelist"]

dt = r"^\[\d\d:\d\d:\d\d\] "
reoSM = re.compile(dt+r"\[Server thread/INFO\]: <(?P<user1>[^ ]+)> (?P<command>.*)$")
reoW = re.compile(r"'(?P<world>.*)'")

def say(text, colour='§3'):
    texts=textwrap.wrap(text, 95) # 99
    for text in texts:
        mcsuperserver.mcStdin.send("say "+colour+text+"\n")

def tell(user1, text, colour='§3'):
    say(text, colour)
    # in 1.3.1 /tell has disappeared
    #texts=textwrap.wrap(text, 95) # 99
    #for text in texts:
        #mcsuperserver.mcStdin.send("tell "+user1+" "+colour+text+"\n")

def creativeMode():
    return mcsuperserver.config['mc']['gamemode']=="1"

def getWorlds():
    if mcsuperserver.config['ss']['work-path'] != None:
        worlds=os.listdir(mcsuperserver.config['ss']['work-path'])
    else:
        worlds=os.listdir('.')
    worlds=[d for d in worlds if os.path.isdir(d) and not d.startswith(".")]
    return worlds

def changeWorld(world):
    oldworld=mcsuperserver.config['mc']['level-name']
    mcsuperserver.config['mc']['level-name'] = world
    if mcsuperserver.config['mc']['motd'].find(oldworld) == 0:
        mcsuperserver.config['mc']['motd'] = mcsuperserver.config['mc']['motd'].replace(oldworld, world)
    else:
        mcsuperserver.config['mc']['motd'] = world + " " + mcsuperserver.config['mc']['motd']
    mcsuperserver.propertiesWrite(mcsuperserver.config['mcfile'], mcsuperserver.config['mc'])

worldChangeTimeout = None

def worldChange(world):
    global worldChangeTimeout
    worldChangeTimeout.close()
    worldChangeTimeout = None
    changeWorld(world)
    if mcsuperserver.mcProcess and mcsuperserver.mcStopping == False:
        mcsuperserver.mcstopping()
        mcsuperserver.mcStopping = True
        mcsuperserver.mcStdin.send("stop\n")

def sentMessage(line):
    global worldChangeTimeout
    #mcsuperserver.mcStdin.send("say {%s}\n" % line)
    mo=reoSM.match(line)
    if mo:
        user1 = mo.group("user1")
        command = mo.group("command")
        if user1 and command:
            args=command.split(" ", 1)
            args[0]=args[0].lower()
            if (args[0] in commandsShortSurvial) or (args[0] in commandsShortCreative and
                    creativeMode()):
                if args[0] in commandsShortSurvial:
                    commandShort=commandsShortSurvial[args[0]]
                else:
                    commandShort=commandsShortCreative[args[0]]
                if len(args)==1 or commandShort.endswith(" "):
                  command=commandShort.replace("you",user1)                  
                  if command.endswith(" ") and len(args)>1:
                      command+=args[1]
                  args=command.split(" ", 1)
                  args[0]=args[0].lower()
            if args[0] == "help" and len(args)==1:
                commands = commandsScript + commandsSurvial
                if creativeMode():
                    commands += commandsCreative
                tell(user1, ", ".join(commands))
            elif args[0] == "helpshort" and len(args)==1:
                commandsShort = commandsShortSurvial
                if creativeMode():
                    commandsShort.update(commandsShortCreative)
                text = []
                for c,t in commandsShort.items():
                    t=t.replace("you",user1)
                    tell(user1, "'"+c+"' is '"+t+"'")
            elif args[0] == "worlds" and len(args)==1:
                worlds = getWorlds()
                tell(user1, "'"+"', '".join(worlds)+"'")
            elif args[0] == "world" and len(args)>1:
                mo=reoW.match(args[1])
                if mo:
                    args[1] = mo.group("world")
                worlds = getWorlds()
                if args[1] in worlds:
                    if worldChangeTimeout:
                        say("world change was canceled by "+user1)
                        worldChangeTimeout.close()
                    say("%s is changing the world to '%s', use 'cancel' to stop" % (user1, args[1]))
                    worldChangeTimeout = mcsuperserver.Timeout(seconds=10, func=worldChange, data=args[1])
                else:
                    tell(user1, "world '%s' doesn't exist" % args[1])
            elif args[0] == "cancel" and len(args)==1 and worldChangeTimeout != None:
                say("world change was canceled by "+user1)
                worldChangeTimeout.close()
                worldChangeTimeout=None
            elif (args[0] in commandsSurvial) or (args[0] in commandsCreative and
                    creativeMode()):
                mcsuperserver.mcStdin.send("%s\n" % (command))
                if args[0] == "gamemode" and len(args)>1:  # in 1.3.1 /gamemode args are swapped
                    subargs=args[1].split(" ", 1)
                    if len(subargs)>1:
                        mcsuperserver.mcStdin.send("%s %s %s\n" % (args[0], subargs[1], subargs[0]))

    return True

runningWorldsFile = os.path.join("..", ".minecraft.running.worlds.txt")

def mcstarting():
    if os.path.isfile(runningWorldsFile):
        world=mcsuperserver.config['mc']['level-name']
        hostport=mcsuperserver.config['ss']['host'].strip()+":"+mcsuperserver.config['ss']['port'].strip()
        oldworld=world

        filelock = mcsuperserver.FileLock(runningWorldsFile)
        filelock.acquire()
        try:
            running={}
            fo = open(runningWorldsFile, 'r+')
            lines = fo.read(16000).splitlines()
            for line in lines:
                sline = line.split(" ", 1)
                if len(sline)!=2:
                    continue
                (lhostport, lworld) = sline
                running[lworld]=lhostport

            if world in running:
                worlds=getWorlds()
                for pworld in worlds:
                    if pworld not in running:
                        world=pworld
                        break
                if world==oldworld:
                    mcsuperserver.log("No unused worlds to start minecraft_server.jar with")
                    raise RuntimeError("No unused worlds to start minecraft_server.jar with")

            running[world]=hostport

            fo.seek(0)
            text=""
            for pworld in running:
                text+=running[pworld]+" "+pworld+"\n"
            fo.write(text)
            fo.truncate()
            fo.close()

            filelock.release()
        except:
            filelock.release()
            raise

        if world != oldworld:
            mcsuperserver.log("World '%s' is in use changing to '%s'" % (oldworld, world))
            changeWorld(world)

mcsuperserver.mcstarting = mcstarting

def mcstarted():
    #mcsuperserver.ssStdin.findthendo( , )
    #mcsuperserver.mcStdout.findthendo(" tried command: ", triedCommand)
    #mcsuperserver.mcStdout.findthendo(" [INFO] <", sentMessage)
    mcsuperserver.mcStdout.findthendo("INFO]: <", sentMessage)
    # ' [INFO] user1 tried command: deop user2'
    # ' [INFO] user1 issued server command: deop user2'
    # ' [INFO] Unknown console command. Type "help" for help.'
    # ' [INFO] user1: Giving 5000 orbs to user2'
    # ' [INFO] Connected players: user1'
    # ' [INFO] user1 [/127.0.0.1:39695] logged in with entity id 392 at (-0.84375, 74.0, 10.75)'
    # ' [INFO] user1 lost connection: disconnect.quitting'
    # ' [INFO] user1: Kicking user2'
    # ' [INFO] Disconnecting /127.0.0.1:54527: Took too long to log in'
    # 2012-08-02 15:43:33 [INFO] <user1> message

mcsuperserver.mcstarted = mcstarted

def mcstopping():
    pass

mcsuperserver.mcstopping = mcstopping

def mcstopped():
    if os.path.isfile(runningWorldsFile):
        world = None # world could have been changed above
        hostport=mcsuperserver.config['ss']['host'].strip()+":"+mcsuperserver.config['ss']['port'].strip()

        filelock = mcsuperserver.FileLock(runningWorldsFile)
        filelock.acquire()
        try:
            running={}
            fo = open(runningWorldsFile, 'r+')
            lines = fo.read(16000).splitlines()
            for line in lines:
                sline = line.split(" ", 1)
                if len(sline)!=2:
                    continue
                (lhostport, lworld) = sline
                running[lhostport]=lworld

            if not running.has_key(hostport):
                mcsuperserver.log("Couldn't find and remove current world for '%s' from '%s'" % (porthost, runningWorldsFile))
            else:
                world = running[hostport]
                fo.seek(0)
                text=""
                for phostport in running:
                    if phostport!=hostport and running[phostport]!=world:
                        text+=phostport+" "+running[phostport]+"\n"
                fo.write(text)
                fo.truncate()
            fo.close()

            filelock.release()
        except:
            filelock.release()
            raise

mcsuperserver.mcstopped = mcstopped

if __name__ == "__main__":
    mcsuperserver.main()
