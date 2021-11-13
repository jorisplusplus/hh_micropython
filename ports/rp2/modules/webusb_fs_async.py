import webusb
import struct
import os
import uasyncio
import io

MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL_WR = const(4)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)

class WebUSBFS(io.IOBase):
    def __init__(self):        
        self.commands = dict()
        self.commands[1] = self.heartbeat
        self.commands[4096] = self.getdir
        self.commands[4097] = self.readfile
        self.commands[4098] = self.writefile
        self.commands[4099] = self.delfile
        self.commands[4100] = self.duplfile
        self.commands[4101] = self.mvfile
        self.commands[4102] = self.mkdir

        self.write_obj = None
        self.write_failed = 0
        self.reader = uasyncio.StreamReader(self)
        self.writer = uasyncio.StreamWriter(self, {})

        self.header = bytearray(12)
        self.header_mv = memoryview(self.header)
        #Clear webusb buffer
        while webusb.read(memoryview(self.header)):
            pass

        self.payload = bytearray(1024)
        self.payload_mv = memoryview(self.payload)

    def run_async(self):
        uasyncio.create_task(self.run())

    def ioctl(self, req, arg):
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                if webusb.available():
                    ret |= MP_STREAM_POLL_RD
            if arg & MP_STREAM_POLL_WR:
                if webusb.write_available():
                    ret |= MP_STREAM_POLL_WR
        return ret
    
    def read(self, len):
        buf = bytearray(min(webusb.available(), len))
        webusb.read(memoryview(buf))
        return buf

    def write(self, buf):
        return webusb.send(buf)

    async def run(self):
        print(self.commands)
        while True:
            print("Starting")
            self.header_mv = await self.reader.read(12)
            [command, size, check, id] = struct.unpack("<HIHI", self.header_mv)
            print([command, size, check, id])
            if check == 0xADDE:
                pos = 0
                received = 0
                if size == 0:
                    if command in self.commands:
                        await self.commands[command](self.payload_mv, command, id, size, 0, 0)
                else:
                    while received < size:
                        endbuf = min(1024, size - (received-pos))
                        delta = webusb.read(self.payload_mv[pos:endbuf])  #Maybe make this async
                        received += delta
                        pos += delta                
                        if command in self.commands:
                            if await self.commands[command](self.payload_mv[:pos], command, id, size, received, pos):
                                pos = 0
                
            else:   #Check failed clearing buffer
                while webusb.read(self.header_mv):
                    pass

    def createheader(self, mv, command, size, id):
        mv[0:12] = struct.pack("<HIHI", command, size, 0xADDE, id)

    async def sendheader(self, command, id, size):
        payload = bytearray(12)
        self.createheader(memoryview(payload), command, size, id)
        self.writer.write(payload)
        await self.writer.drain()

    async def sender(self, command, id):
        payload = bytearray(12+3)
        self.createheader(memoryview(payload), command, 3, id)
        payload[12:14] = b"er"
        self.writer.write(payload)
        await self.writer.drain()

    async def sendok(self, command, id):
        payload = bytearray(12+3)
        self.createheader(memoryview(payload), command, 3, id)
        payload[12:14] = b"ok"
        self.writer.write(payload)
        await self.writer.drain()

    async def sendte(self, command, id):
        payload = bytearray(12+3)
        self.createheader(memoryview(payload), command, 3, id)
        payload[12:14] = b"te"
        self.writer.write(payload)
        await self.writer.drain()

    async def sendto(self, command, id):
        payload = bytearray(12+3)
        self.createheader(memoryview(payload), command, 3, id)
        payload[12:14] = b"to"
        self.writer.write(payload)
        await self.writer.drain()

    async def sendstr(self, command, id, data):
        print(data)
        payload = bytearray(12+len(data))
        self.createheader(memoryview(payload), command, len(data), id)
        payload[12:] = data.encode()
        self.writer.write(payload)
        await self.writer.drain()

    async def heartbeat(self, data, command, id, size, received, length):
        if size != received:
            return 0
        await self.sendok(command, id)
        return 1

    async def getdir(self, data, command, id, size, received, length):
        if size != received:
            return 0
        
        if size == 0 or size == 1 or size == 2:
            response = "/\n"
            print("Listing: /")
            for f in os.listdir("/"):
                if os.stat("/"+f)[0] == 16384:
                    response += "d"
                else:
                    response += "f"
                response += f
                response += "\n"
            await self.sendstr(command, id, response[:-1])
        else:
            dir = str(data,'utf-8').replace("\x00", "")
            rootdir = dir
            print("Listing: "+dir)
            for f in os.listdir(dir):
                if not f:
                    break
                print(f)
                dir += "\n"
                if os.stat(rootdir+"/"+f)[0] == 16384:
                    dir += "d"
                else:
                    dir += "f"
                dir += f
                
            await self.sendstr(command, id, dir)

        return 1

    async def readfile(self, data, command, id, size, received, length):
        if size != received:
            return 0

        try:
            filename = str(data, "utf-8").replace("\x00", "")
            print("Reading: "+filename)
            filesize = os.stat(filename)[6]        
            f = open(str(data, "utf-8"), "rb")
            await self.sendheader(command, id, filesize)
            while True:
                data = f.read(32)
                if not data:
                    break
                self.writer.write(data)
                await self.writer.drain()
            f.close()
        except:
            print("Problem reading file")
            self.sendstr(command, id, "Can't open file")


    async def writefile(self, data, command, id, size, received, length):
        global write_obj, write_failed
        
        if received == length:
            if self.write_obj:
                self.write_obj.close()
            write_failed = 0

        if self.write_obj == None and write_failed == 0:
            for i in range(0, received):
                if data[i] == 0x00:
                    filename = str(data[0:i], "utf-8").replace("\x00", "")
                    try:
                        write_obj = open(filename, "wb")
                        if received > i:
                            write_obj.write(data[i+1:received])
                    except:
                        write_failed = 1
                        print("opening file: "+filename+" failed")

                    if received == size:
                        if write_obj:
                            await self.sendok(command, id)
                            write_obj.close()
                            write_obj = None
                        else:
                            await self.sender(command, id)

                    return 1
            return 0
        elif self.write_obj:
            self.write_obj.write(data[0:length])
            if received == size:
                self.write_obj.close()
                await self.sendok(command, id)
                write_obj = None
            return 1
        else:
            if received == size:
                await self.sender(command, id)
            return 1


    async def delfile(self, data, command, id, size, received, length):
        if size != received:
            return 0

        try:
            os.remove(str(data, "utf-8").replace("\x00", ""))
            await self.sendok(command, id)
        except:
            await self.sender(command, id)
        return 1

    async def duplfile(self, data, command, id, size, received, length):
        if size != received:
            return 0
        
        source = ""
        dest = ""
        for i in range(0, size):
            if data[i] == 0x00:
                source = str(data[0:i], "utf-8").replace("\x00", "")
                dest = str(data[(i+1):], "utf-8").replace("\x00", "")
        
        if source == "" or dest == "":
            await self.sender(command, id)
            return 1
        
        try:
            fsource = open(source, "rb")
            fdest = open(dest, "wb")
            while True:
                data = fsource.read(32)
                if not data:
                    break
                fdest.write(data)
            fsource.close()
            fdest.close()
            await self.sendok(command, id)
        except:
            await self.sender(command, id)

        return 1

    async def mvfile(self, data, command, id, size, received, length):
        if size != received:
            return 0
        
        source = ""
        dest = ""
        for i in range(0, size):
            print(data[i])
            if data[i] == 0:
                source = str(data[0:i], "utf-8").replace("\x00", "")
                dest = str(data[(i+1):], "utf-8").replace("\x00", "")
                break
        print("renaming: "+source +" to: "+dest)
        if source == "" or dest == "":
            await self.sender(command, id)
            return 1

        try:
            os.rename(source, dest)
            await self.sendok(command, id)
        except:
            await self.sender(command, id)

        return 1

    async def mkdir(self, data, command, id, size, received, length):
        if size != received:
            return 0

        try:
            os.mkdir(str(data, "utf-8").replace("\x00", ""))
            await self.sendok(command, id)
        except:
            await self.sender(command, id)
        return 1

def set_global_exception():
    def handle_exception(loop, context):
        import sys
        sys.print_exception(context["exception"])
        sys.exit()
    loop = uasyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

async def main():
    set_global_exception()  # Debug aid
    my_class = WebUSBFS()  # Constructor might create tasks
    uasyncio.sleep(0.1)

def startwebusb():
    print("Test")
    uasyncio.run(main())

import _thread
_thread.start_new_thread(startwebusb, ())