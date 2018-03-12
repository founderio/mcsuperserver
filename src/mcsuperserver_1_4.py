#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   MCSuperServer - Starts and stops the minecraft server to reduce memory and cpu usage
#   Copyright (C) 2011, 2012  Paul Andreassen
#   paul@andreassen.com.au

#   MC 1.4+ Version by Oliver Kahrmann (founderio), 2012
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

# 0.01 20111227 proxy and subprocess start / stop working
# 0.02 20120121 attempt at stopping the subprocess exiting during starting when multiple connections
# 0.03 20120426 fix for connection problems
# 0.04 20120121 attempt at fix for connections during the start / stop of the subprocess (worked but used sleep, needed timeout)
# 0.05 20120515 windows support and console stdin support
# 0.06 20120520 scripting support and signal terminate support
# 0.06.01 20120831 fix bug with python 2.4 and earier
# 0.06.02 20120928 fix bug when getting handle_close on both server and proxy
# 0.07 20131026 (founderio) modified for Minecraft 1.4+, Protocol Version & Minecraft Version read from config
# 0.07.01 20131112 (founderio) fixed mistake in version definition

# http://www.wiki.vg/Protocol#Server_List_Ping_.280xFE.29
# https://gist.github.com/1209061
# http://www.wiki.vg/Authentication#Login
# http://wiki.vg/Rcon
# http://docs.python.org/modindex.html

# must use select for windows
#  poll - Not existing on older unixes nor in Windows before Vista
# must use threads for windows
#  Applications which need to support a more general approach should integrate 
#  I/O over pipes with their select() loops, or use separate threads to read 
#  each of the individual files provided by whichever popen*() function or 
#  Popen* class was used.
#  Note that on Windows, it only works for sockets; on other operating systems, 
#  it also works for other file types (in particular, on Unix, it works on 
#  pipes).
#  http://code.activestate.com/recipes/525487-extending-socketsocketpair-to-work-on-windows/
# SocketServer uses threads or forks

import os, os.path, sys, shlex, asyncore, subprocess, struct, socket, threading, signal, tempfile, select, time, errno
# Threads interact strangely with interrupts: the KeyboardInterrupt exception will be 
# received by an arbitrary thread. (When the signal module is available, interrupts 
# always go to the main thread.)


VER = 0.07
ss = None
ssStdin = None
mcProcess = None
mcStdout = None
mcStdin = None
mcCount = 0
mcStopping = False

config={}
config['ssfile']="mcsuperserver.properties"
config['ss'] = {
        "host" : "",
        "port" : "25555",
        "command" : "java -Xmx1024M -Xms128M -jar minecraft_server.jar nogui",
        "work-path" : "",
		"protocol-version" : "47",
		"minecraft-version" : "1.4.2"
}

config['mcfile'] = "server.properties"
config['mc'] = {
        "server-ip" : "",
        "server-port" : "25565",
        "motd" : "A Minecraft Server",
        "max-players" : "20",
}


def mcstarting():
    pass

def mcstarted():
    pass
    #ssStdin.findthendo( , )
    #mcStdout.findthendo(" tried command: ", triedcommand)
    #mcStdin.send("say {%s}\n" % line)

def mcstopping():
    pass

def mcstopped():
    pass


def log(text):
    print "  "+text


if "socketpair" not in socket.__dict__:
    # drop in Windows support
    # Availability: Unix.
    # New in version 2.4.

    if "AF_UNIX" in socket.__dict__:
        pairfamily = socket.AF_UNIX
    else:
        pairfamily = socket.AF_INET

    def socketsocketpair(family=pairfamily, type_=socket.SOCK_STREAM, proto=socket.IPPROTO_IP):
        """Wraps socketpair() to support Windows using local ephemeral ports"""
        listensock = socket.socket(family, type_, proto)
        listensock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if family == socket.AF_INET:
            address = ('localhost', 0)
        elif family == socket.AF_UNIX:
            address = tempfile.mktemp(prefix='listener-', dir=tempfile.gettempdir())
        elif family == socket.AF_PIPE:
            address = tempfile.mktemp(prefix=r'\\.\pipe\pyc-%d-%d-' %
                    (os.getpid(), _mmap_counter.next()))
        else:
            raise ValueError('unrecognized family')
        listensock.bind(address)
        laddress = listensock.getsockname()  # assigned (host, port) pair
        listensock.listen(1)

        socket1 = socket.socket(family, type_, proto)
        socket1.connect(laddress)
        socket2, sock2addr = listensock.accept()
        listensock.close()
        return (socket1, socket2)

    socket.socketpair = socketsocketpair


if "file_dispatcher" not in asyncore.__dict__:
    # drop in Windows support but requires new constructer parameters and close() called
    # 'pipes' aren't 'select'able on Windows

    class asyncorefile_dispatcher(asyncore.dispatcher):

        def __init__(self, fd, map=None, readable = True, writeable = True):
            (self.socket1, socket2) = socket.socketpair()
            asyncore.dispatcher.__init__(self, socket2, map)
            try:
                fd = fd.fileno()
            except AttributeError:
                pass
            #self.fd = os.dup(fd)
            self.fd = fd

            # can't test file for readablility or writeablility, so please specify
            # the thread_reader blocks on file read so will exit nicely if file not readable or closed
            # the thread_writer blocks on a socket so doesn't test for file writeablilty or closed, so please call close()
            self.b_readable = readable
            if readable:
                #print "  thread reader started"
                self.thread_reader = threading.Thread(
                        target=self.thread_reader_func,
                        args=(self.fd, self.socket1))
                self.thread_reader.setDaemon(True)
                self.thread_reader.start()

            self.b_writeable = writeable
            if writeable:
                #print "  thread writer started"
                self.thread_writer = threading.Thread(
                        target=self.thread_writer_func,
                        args=(self.fd, self.socket1))
                self.thread_writer.setDaemon(True)
                self.thread_writer.start()

        def readable(self):
            return self.b_readable

        def writable(self):
            return self.b_writeable

        def thread_reader_func(self, fd, socket1):
            try:
                data = os.read(self.fd, 8192)
            except OSError, e:
                if e[0] != 9: # Bad file descriptor
                    raise
                else:
                    self.b_readable = False
                    #print "thread reader exited not readable"
                    return  # not open for reading
            while data:
                #print " '" + data + "' length= %d" % len(data)
                #print ".",
                socket1.sendall(data)
                data=os.read(self.fd, 8192)
            socket1.close()
            #print "  thread reader exited"

        def thread_writer_func(self, fd, socket1):
            data = socket1.recv(8192)
            while data:
                while data:
                    num_sent = os.write(fd, data)
                    #os.fsync(fd)
                    data = data[num_sent:]
                data = socket1.recv(8192)
            socket1.close()
            #print "  thread writer exited"

        def close(self):
            #os.close(self.fd) # close it here and get IOError: [Errno 9] Bad file descriptor
            asyncore.dispatcher.close(self)
            self.socket1.close()
            self.thread_reader = None
            self.thread_writer = None

    asyncore.file_dispatcher = asyncorefile_dispatcher

else:

    asyncore.file_dispatcher.__init__old = asyncore.file_dispatcher.__init__

    def __init__new(self, fd, map=None, readable = True, writeable = True):
        asyncore.file_dispatcher.__init__old(self, fd, map)

    asyncore.file_dispatcher.__init__ = __init__new


class Timeout(asyncore.dispatcher):

    def __init__(self, seconds=None, func=None, data=None, map=None):
        (self.trigger, socket2) = socket.socketpair()
        asyncore.dispatcher.__init__(self, socket2, map)
        self.thread_timer = None
        if seconds != None:
            self.set_timeout(seconds)
        self.func = func
        self.data = data

    def set_timeout(self, seconds):
        if self.thread_timer:
            raise RuntimeError("Tried to set timer twice")
        self.thread_timer = threading.Timer(seconds, self.thread_timer_func)
        self.thread_timer.start()

    def thread_timer_func(self):
        self.trigger.send('x')
        self.thread = None

    def handle_close(self):
        self.close()

    def close(self):
        if self.thread_timer:
            self.thread_timer.cancel()
            self.thread_timer = None
        asyncore.dispatcher.close(self)
        self.trigger.close()

    def handle_read(self):
        self.recv(8192)
        self.timedout()

    def timedout(self):
        if self.func:
            self.func(self.data)


class FileLockException(Exception):
    pass


class FileLock(object):
    def __init__(self, file_name, timeout=3, delay=.05):
        self.is_locked = False
        self.lockfile = os.path.join(os.getcwd(), "%s.lock" % file_name)
        self.file_name = file_name
        self.timeout = timeout
        self.delay = delay
        self.fd = None

    def acquire(self):
        start_time = time.time()
        delay = self.delay
        while True:
            try:
                self.fd = os.open(self.lockfile, os.O_CREAT|os.O_EXCL|os.O_RDWR)
                break
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise 
                if (time.time() - start_time) >= self.timeout:
                    raise FileLockException("Timeout occured.")
                time.sleep(delay)
                delay *= 2  # please note this increase in delay
        os.write(self.fd, "%d" % os.getpid())
        self.is_locked = True

    def release(self):
        if self.is_locked:
            os.close(self.fd)
            self.fd = None
            os.unlink(self.lockfile)
            self.is_locked = False

    def __del__(self):
        self.release()


class SuperServerStdinHandler(asyncore.file_dispatcher):

    def __init__(self, fd, map=None):
        asyncore.file_dispatcher.__init__(self, fd, map, writeable=False)
        self.in_buffer = '\n'
        self.stolf = {}
        self.findthendo('show w', self.warranty)
        self.findthendo('show c', self.conditions)
        self.findthendo('halt', self.halt)

    def writable(self):
        return False

    def findthendo(self, substring, func):
        if self.stolf.has_key(substring):
            self.stolf[substring].append(func)
        else:
            self.stolf[substring]=[func]

    def removefindthendo(self, substring, func):
        if self.stolf.has_key(substring):
            self.stolf[substring].remove(func)
            if len(self.stolf[substring]) == 0:
                del self.stolf[substring]

    def handle_read(self):
        data = self.in_buffer + self.recv(8192)
        pos = data.rfind("\r")
        if pos == -1:
            pos = data.rfind("\n")
        if pos != -1:
            self.in_buffer = data[pos:]
            data=data[:pos]
        data=data.replace("\r\n", "\n").replace("\r", "\n")
        if len(data) > 0 and data[0] == "\n":
            data = data[1:]
            passthrough = True
            for s, lf in self.stolf.items():
                if data.find(s) != -1:
                    for f in lf:
                        try:
                            (nextfunction, passthrough) = f(data)
                            if not nextfunction:
                                break
                        except:
                            nil, t, v, tbinfo = asyncore.compact_traceback()
                            try:
                                self_repr = repr(self)  # sometimes a user repr method will crash.
                            except:
                                self_repr = '<__repr__(self) failed for object at %0x>' % id(self)
                            log('uncaptured python exception, ignoring %s (%s:%s %s)' % (
                                    self_repr, t, v, tbinfo))
            if passthrough and mcStdin:
                mcStdin.send(data+"\n")

    def warranty(self, data):
        if data.strip()=="show w":
            print "This program is distributed in the hope that it will be useful,\n" \
                    "but WITHOUT ANY WARRANTY; without even the implied warranty of\n" \
                    "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n" \
                    "GNU General Public License for more details."
            return (False, False)
        else:
            return (True, True)

    def conditions(self, data):
        if data.strip()=="show c":
            print "This program is free software: you can redistribute it and/or modify\n" \
                    "it under the terms of the GNU General Public License as published by\n" \
                    "the Free Software Foundation, either version 3 of the License, or\n" \
                    "(at your option) any later version."
            return (False, False)
        else:
            return (True, True)

    def halt(self, data):
        global ss, ssStdin, mcProcess, mcStopping, mcStdin
        if data.strip()=="halt":
            ss.close()
            ssStdin.close()
            if mcProcess and mcStopping == False:
                mcstopping()
                mcStopping = True
                log("Sent 'stop'")
                mcStdin.send("stop\n")
            return (True, False)
        else:
            return (True, True)

class mcStdoutHandler(asyncore.file_dispatcher):

    def __init__(self, fd, map=None):
        asyncore.file_dispatcher.__init__(self, fd, map, writeable=False)
        self.in_buffer = '\n'
        self.stolf = {}
        self.login = []
        self.foundDone = False
        self.after_close = []

    def writable(self):
        return False

    def findthendo(self, substring, func):
        if self.stolf.has_key(substring):
            self.stolf[substring].append(func)
        else:
            self.stolf[substring]=[func]

    def removefindthendo(self, substring, func):
        if self.stolf.has_key(substring):
            self.stolf[substring].remove(func)
            if len(self.stolf[substring]) == 0:
                del self.stolf[substring]

    def do_connect(self, obj):
        if not obj in self.login:
            self.login.append(obj)

    def handle_read(self):
        data = self.in_buffer + self.recv(8192)
        pos = data.rfind("\r")
        if pos == -1:
            pos = data.rfind("\n")
        if pos != -1:
            self.in_buffer = data[pos:]
            data=data[:pos]
        data=data.replace("\r\n", "\n").replace("\r", "\n")
        if len(data) > 0 and data[0] == "\n":
            data = data[1:]
            print data
            if (len(self.login) > 0) and (
                    #MinecraftForge v4.0.0.247 Initialized
					#(not self.foundDone and (data.find("MinecraftForge v4.0.0.247 Initialized") != -1)) or 
					#(not self.foundDone and (data.find(" Done ") != -1)) or 
					(not self.foundDone and (data.find(" achievements") != -1)) or 
                    (self.foundDone and (data.find(" logged in ") != -1))):
                while len(self.login) > 0:
                    obj = self.login.pop(0)
                    if not obj.connected and not obj.connecting:
                        log("Attempting ' Done ' or ' logged in ' connect (%d) with %d remaining in queue" % 
                                (len(obj.out_buffer), len(self.login)))
                        obj.do_connect()
                        break
                    else:
                        log("Already connecting or connected")
                self.foundDone = True
            for s, lf in self.stolf.items():
                if data.find(s) != -1:
                    for f in lf:
                        try:
                            nextfunction = f(data)
                            if not nextfunction:
                                break
                        except:
                            nil, t, v, tbinfo = asyncore.compact_traceback()
                            try:
                                self_repr = repr(self)  # sometimes a user repr method will crash.
                            except:
                                self_repr = '<__repr__(self) failed for object at %0x>' % id(self)
                            log('uncaptured python exception, ignoring %s (%s:%s %s)' % (
                                    self_repr, t, v, tbinfo))

    def handle_close(self):
        global mcProcess, mcStopping, mcStdout, mcStdin
        self.close()
        mcProcess = None
        mcStopping = False
        mcStdout = None
        mcStdin.close()
        mcStdin = None
        mcstopped()
        for f in self.after_close:
            f()
        self.after_close = []


class mcStdinHandler(asyncore.file_dispatcher):

    def __init__(self, fd, map=None):
        asyncore.file_dispatcher.__init__(self, fd, map, readable=False)
        self.out_buffer = ''

    def readable(self):
        return False

    def initiate_send(self):
        num_sent = 0
        num_sent = asyncore.file_dispatcher.send(self, self.out_buffer[:512])
        self.out_buffer = self.out_buffer[num_sent:]

    def handle_write(self):
        self.initiate_send()

    def writable(self):
        return (not self.connected) or len(self.out_buffer)

    def send(self, data):
        if self.debug:
            self.log_info('sending %s' % repr(data))
        print " "+data,
        self.out_buffer = self.out_buffer + data
        self.initiate_send()


class ServerHandler(asyncore.dispatcher_with_send):

    def __init__(self, proxy, data=''):
        asyncore.dispatcher_with_send.__init__(self)
        self.proxy = proxy
        self.out_buffer = data
        self.connecting = False

    def do_connect(self):
        if self.connected or self.connecting:
            log("Attempted to connect to an already connecting or connected server")
        else:
            self.connecting = True
            self.create_socket(asyncore.socket.AF_INET, asyncore.socket.SOCK_STREAM)
            self.set_reuse_addr()
            host = config['mc']["server-ip"].strip()
            if len(host) == 0: host="localhost"
            self.connect( (host, int(config['mc']["server-port"])) )
            log("Attempt to connect to server")

    #def initiate_send(self):
    #    if self.connected:
    #        num_sent = asyncore.dispatcher.send(self, self.out_buffer[:512])
    #        self.out_buffer = self.out_buffer[num_sent:]

    def handle_connect(self):
        global mcCount
        self.connecting = False
        log("Server connected")
        if len(self.out_buffer) > 0:
            self.initiate_send()
        mcCount += 1

    def handle_close(self):
        global mcCount, mcStopping, mcStdin
        log("Server connection closed")
        self.close()
        if self.proxy.connected:
            self.proxy.close()
            mcCount -= 1
            if mcCount < 0:
                log("mcCount less then 0")
            if mcCount <= 0:
                mcCount = 0
                if mcStdin != None:
                    mcstopping()
                    mcStopping = True
                    log("Sent 'stop'")
                    mcStdin.send("stop\n")

    def handle_read(self):
        try:
            self.proxy.send(self.recv(8192))
        except asyncore.socket.error, e:
            if e[0] != 9: # Bad file descriptor
                raise


class ProxyHandler(asyncore.dispatcher_with_send):

    #ignore_log_types = frozenset()
    #debug = True

    def __init__(self, sock=None, map=None):
        global mcProcess, mcStopping, mcCount, mcStdout
        asyncore.dispatcher_with_send.__init__(self, sock, map)
        self.sent = None
        self.server = ServerHandler(self)
        if mcProcess != None:    # server started
            if mcCount > 0:     # server connectable
                self.server.do_connect()
            else:               # server not connectable
                if not mcStopping:  # server starting
                    mcStdout.do_connect(self.server)
                else:           # server stopping
                    pass

    def initiate_send(self):
        #if self.connected:
            #num_sent = asyncore.dispatcher.send(self, self.out_buffer[:512])
            #self.out_buffer = self.out_buffer[num_sent:]
        asyncore.dispatcher_with_send.initiate_send(self)
        if self.sent != None and len(self.out_buffer) == 0:
            self.sent()
            self.sent = None

    def handle_read(self):
        global mcProcess, mcStopping, mcCount, mcStdout
        if not self.server.connected:
            data = self.recv(8192)
            #print 'Recieved : %s' % repr(data)
            if mcProcess == None or mcStopping:
                c = data[:1]
                if c == '\xFE': # 'Server List Ping'
                    log("Recieved 'Server List Ping'")
                    self.sent = self.close
                    string = u'\xa71\x00%d\x00%s\x00%s\x00%d\x00%d' % (int(config['ss']["protocol-version"]), config['ss']["minecraft-version"], config['mc']["motd"], 0, int(config['mc']["max-players"]))
                    strlen = len(string)
                    string = string.encode('utf-16be')
                    desc = '\xFF' + struct.pack('>h%ds' % len(string), strlen, string)
                    self.send(desc) # 'Disconnect/Kick'
                    log("Sent 'Disconnect/Kick' and closed connection")
                    log("Server has "+config['mc']["max-players"]+
                            " maximum players and the motd is '"+config['mc']["motd"]+"'")
                elif c == '\x02': # 'Handshake'
                    log("Recieved 'Handshake'")
                    if len(data) >= 3:
                        strlen = struct.unpack('>h', data[1:3])[0]
                        if (len(data)-3) >= (strlen*2):
                            string = data[3:(strlen*2+3)]
                            log("Username is '"+string.decode('utf-16be')+"'")

                    if not mcStopping:
                        self.start_subprocess(data)
                    else:   # server stopping
                        if len(mcStdout.after_close) == 0: # restart
                            def restart():
                                self.start_subprocess(data)
                            mcStdout.after_close.append(restart)
                        else:                             # connect to new server
                            self.server.out_buffer+=data
                            def restart():
                                mcStdout.do_connect(self.server)
                            mcStdout.after_close.append(restart)
                else:
                    log("WARNING! Recieved unsupported protocol so closing connection")
                    self.close()
            else:   # server starting
                self.server.out_buffer+=data
                if mcCount > 0:
                    if not self.server.connecting:
                        self.server.do_connect()
                else:
                    mcStdout.do_connect(self.server)
        else:
            try:
                self.server.send(self.recv(8192))
            except asyncore.socket.error, e:
                if e[0] != 9: # Bad file descriptor
                    raise

    def start_subprocess(self, data=''):
        global mcProcess, mcStdout, mcStdin
        log("Attempting server start")
        try:
            args=config['ss']['command']
            if sys.platform != "win32":
                args = shlex.split(args)
            mcstarting()
            mcProcess = subprocess.Popen(args=args, bufsize=8192, stdin=subprocess.PIPE, 
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=config['ss']['work-path'], 
                    universal_newlines=True)
            mcStdin=mcStdinHandler(mcProcess.stdin)
            mcStdout=mcStdoutHandler(mcProcess.stdout)
            mcstarted()
            self.server.out_buffer+=data
            mcStdout.do_connect(self.server)
        except ValueError, e:
            log("A ValueError will be raised if Popen is called with invalid arguments.")
            log("command is '"+config['ss']['command']+"'")
            if config['ss']['work-path'] != None: log("work path is '"+config['ss']['work-path']+"'")
            raise
        except OSError, e:
            log("A OSError occurs, for example, when trying to execute a non-existent file.")
            raise

    def handle_close(self):
        global mcCount, mcStopping, mcStdin
        log("Client connection closed")
        self.close()
        if self.server.connected:
            self.server.close()
            mcCount -= 1
            if mcCount < 0:
                log("mcCount less then 0")
            if mcCount <= 0:
                mcCount = 0
                if mcStdin != None:
                    mcstopping()
                    mcStopping = True
                    log("Sent 'stop'")
                    mcStdin.send("stop\n")


class MCSuperServer(asyncore.dispatcher):

    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(asyncore.socket.AF_INET, asyncore.socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        log("Listening on '%s:%d'" % (host, port))
        self.listen(5)

    def handle_accept(self):
        pair = self.accept()
        if pair is None:
            pass
        else:
            sock, addr = pair
            log('Incoming connection from %s' % repr(addr))
            handler = ProxyHandler(sock)


def propertiesRead(filename, config, nofile):
    try:
        fo = open(filename, 'r')
        lines = fo.readlines()
        fo.close()
        for line in lines:
            line.lstrip()
            if not line.startswith("#"):
                line=line.replace("\r","").replace("\n","")
                keyvalue=line.split("=",1)
                config[keyvalue[0]]=keyvalue[1]
    except IOError, e:
        if e[0] == 2: # 'No such file or directory'
            nofile()
        else:
            raise

def propertiesWrite(name, config):
    fo = open(name, "w")
    for key, value in config.items():
        fo.write(key+"="+value+"\n")
    fo.close()

def configLoad():
    global config
    def nofile():
        log("No '"+config['ssfile']+"' using defaults and creating file")
        propertiesWrite(config['ssfile'], config['ss'])
    propertiesRead(config['ssfile'], config['ss'], nofile)

    if len(config['ss']['work-path'].strip()) != 0:
        config['mcfile'] = os.path.join(config['ss']['work-path'], config['mcfile'])
    def nofile():
        log("No '"+config['mcfile']+"' using defaults")
    propertiesRead(config['mcfile'], config['mc'], nofile)

    if len(config['ss']['work-path'].strip()) == 0:
        config['ss']['work-path'] = None

def signalTERM(signalNumber, stackFrame):
    global ss, ssStdin, mcProcess, mcStopping, mcStdin
    log("Signal TERM")
    ss.close()
    ssStdin.close()
    if mcProcess and mcStopping == False:
        mcstopping()
        mcStopping = True
        log("Sent 'stop'")
        mcStdin.send("stop\n")

def main():
    global ss, ssStdin
    print "MCSuperServer " + str(VER) + " Copyright (C) 2011, 2012  Paul Andreassen\n" \
          "Modifications by Oliver Kahrmann, 2012\n" \
          "This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.\n" \
          "This is free software, and you are welcome to redistribute it\n" \
          "under certain conditions; type `show c' for details.\n"

    signal.signal(signal.SIGTERM, signalTERM)
    #signal.signal(signal.SIGINT, signalTERM)
    configLoad()
    ss = MCSuperServer(config['ss']['host'], int(config['ss']['port']))
    ssStdin = SuperServerStdinHandler(sys.stdin)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        print "KeyboardInterrupt"

if __name__ == "__main__":
    main()
