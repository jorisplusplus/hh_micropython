import webusb
import struct
import os


def sendpayload(payload):
    mv = memoryview(payload)
    size = len(payload)
    pos = 0
    while pos < size:
        pos += webusb.send(mv[pos:])

def createheader(mv, command, size, id):
    mv[0:12] = struct.pack("<HIHI", command, size, 0xADDE, id)

def sendheader(command, id, size):
    payload = bytearray(12)
    createheader(memoryview(payload), command, size, id)
    sendpayload(payload)

def sender(command, id):
    payload = bytearray(12+3)
    createheader(memoryview(payload), command, 3, id)
    payload[12:14] = b"er"
    sendpayload(payload)

def sendok(command, id):
    payload = bytearray(12+3)
    createheader(memoryview(payload), command, 3, id)
    payload[12:14] = b"ok"
    sendpayload(payload)

def sendte(command, id):
    payload = bytearray(12+3)
    createheader(memoryview(payload), command, 3, id)
    payload[12:14] = b"te"
    sendpayload(payload)

def sendto(command, id):
    payload = bytearray(12+3)
    createheader(memoryview(payload), command, 3, id)
    payload[12:14] = b"to"
    sendpayload(payload)

def sendstr(command, id, data):
    print(data)
    payload = bytearray(12+len(data))
    createheader(memoryview(payload), command, len(data), id)
    payload[12:] = data.encode()
    sendpayload(payload)

def heartbeat(data, command, id, size, received, length):
    if size != received:
        return 0
    sendok(command, id)
    return 1

def getdir(data, command, id, size, received, length):
    if size != received:
        return 0
    
    if size == 0 or size == 1 or size == 2:
        response = "/\n"
        for f in os.listdir("/"):
            if os.stat("/"+f)[0] == 16384:
                response += "d"
            else:
                response += "f"
            response += f
            response += "\n"
        sendstr(command, id, response[:-1])
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
            
        sendstr(command, id, dir)

    return 1

def readfile(data, command, id, size, received, length):
    if size != received:
        return 0

    try:
        filename = str(data, "utf-8").replace("\x00", "")
        print("Reading: "+filename)
        filesize = os.stat(filename)[6]        
        f = open(str(data, "utf-8"), "rb")
        sendheader(command, id, filesize)
        while True:
            data = f.read(32)
            if not data:
                break
            sendpayload(data)
        f.close()
    except:
        print("Problem reading file")
        sendstr(command, id, "Can't open file")

write_obj = None
write_failed = 0
def writefile(data, command, id, size, received, length):
    global write_obj, write_failed
    
    if received == length:
        if write_obj:
            write_obj.close()
        write_failed = 0

    if write_obj == None and write_failed == 0:
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
                        sendok(command, id)
                        write_obj.close()
                        write_obj = None
                    else:
                        sender(command, id)

                return 1
        return 0
    elif write_obj:
        write_obj.write(data[0:length])
        if received == size:
            write_obj.close()
            sendok(command, id)
            write_obj = None
        return 1
    else:
        if received == size:
            sender(command, id)
        return 1


def delfile(data, command, id, size, received, length):
    if size != received:
        return 0

    try:
        os.remove(str(data, "utf-8").replace("\x00", ""))
        sendok(command, id)
    except:
        sender(command, id)
    return 1

def duplfile(data, command, id, size, received, length):
    if size != received:
        return 0
    
    source = ""
    dest = ""
    for i in range(0, size):
        if data[i] == 0x00:
            source = str(data[0:i], "utf-8").replace("\x00", "")
            dest = str(data[(i+1):], "utf-8").replace("\x00", "")
    
    if source == "" or dest == "":
        sender(command, id)
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
        sendok(command, id)
    except:
        sender(command, id)

    return 1

def mvfile(data, command, id, size, received, length):
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
        sender(command, id)
        return 1

    try:
        os.rename(source, dest)
        sendok(command, id)
    except:
        sender(command, id)

    return 1

def mkdir(data, command, id, size, received, length):
    if size != received:
        return 0

    try:
        os.mkdir(str(data, "utf-8").replace("\x00", ""))
        sendok(command, id)
    except:
        sender(command, id)
    return 1

commands = dict()
commands[1] = heartbeat
commands[4096] = getdir
commands[4097] = readfile
commands[4098] = writefile
commands[4099] = delfile
commands[4100] = duplfile
commands[4101] = mvfile
commands[4102] = mkdir

header = bytearray(12)

#Clear webusb buffer
while webusb.read(memoryview(header)):
    pass

payload = bytearray(1024)
payload_mv = memoryview(payload)
while True:
    if webusb.available() >= 12:
        webusb.read(memoryview(header))
        [command, size, check, id] = struct.unpack("<HIHI", memoryview(header))
        if check == 0xADDE:
            pos = 0
            received = 0
            if size == 0:
                if command in commands:
                    commands[command](payload_mv, command, id, size, 0, 0)
            else:
                while received < size:
                    endbuf = min(1024, size - (received-pos))
                    delta = webusb.read(payload_mv[pos:endbuf])
                    received += delta
                    pos += delta                
                    if command in commands:
                        if commands[command](payload_mv[:pos], command, id, size, received, pos):
                            pos = 0
            
        else:   #Check failed clearing buffer
            while webusb.read(memoryview(header)):
                pass


