import webusb
import micropython
import os

micropython.kbd_intr(3)
micropython.alloc_emergency_exception_buf(100)
if webusb.mode() == 1:
    print("launching webusb_fs")
    import webusb_fs
elif webusb.mode() == 2:
    print("Starting app")
    try:
        f = open("/startup.txt", "r")
        mod = f.read()
        f.close()
        os.remove("/startup.txt")        
    except:
        import webusb_fs
    finally:
        __import__(mod)
