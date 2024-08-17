import evdev
import dbus
from enum import Enum


##### DETECT TRACKPAD #####
dev = None
index = 0
while True:
    dev = evdev.InputDevice(f'/dev/input/event{index}')
    if dev.name == "Apple Inc. Magic Trackpad 2":
        break
    else:
        index = index+1


print(f"Found trackpad: \n{dev}")

##### GET TRACKPAD BATTERY AND WARN IF BELOW 20% #####


bus = dbus.SystemBus()
manager = dbus.Interface(bus.get_object(
    'org.freedesktop.UPower', '/org/freedesktop/UPower'), 'org.freedesktop.UPower')
for device in manager.EnumerateDevices():
    device_model = dbus.Interface(bus.get_object(
        'org.freedesktop.UPower', device), 'org.freedesktop.DBus.Properties').Get('org.freedesktop.UPower.Device', 'Model')
    print(f"Device model name: {device_model}")
    if device_model == "Varo's Trackpad":
        device_props = dbus.Interface(bus.get_object(
            'org.freedesktop.UPower', device), 'org.freedesktop.DBus.Properties')
        battery = device_props.Get(
            'org.freedesktop.UPower.Device', 'Percentage')
        # Prints it
        print(f"Current battery percentage: {battery}%")
        if (battery <= 10.0):
            print("BATTERY BELOW MINIMUM, A RECHARGE IS NEEDED")
        break

##### FINGER TRACKING #####
# GLOBAL, finger per index
# Structure: [[(firstFingerX, firstFingerY), clicked, firstFingerForce, globalForce, touchingFingerCounter, totalFingerCounter],
# [uid, (x, y), surface, force]]

# Enum for the codes of the trackpad


class codes(Enum):
    xFirst = 0x0000
    yFirst = 0x0001
    forceFirst = 0x0018
    uid = 0x002f
    surface = 0x0030
    initialSurface = 0x0031
    x = 0x0035
    y = 0x0036
    fingerLiftOrCounter = 0x0039
    globalForce = 0x003a
    click = 0x0110
    oneOrTwoFingers = 0x0145
    fourOrFiveFingersPositive = 0x0148
    anyFinger = 0x014a
    twoOrThreeFingers = 0x014d
    threeOrFourFingers = 0x014e
    fourOrFiveFingersNegative = 0x014f

# Class to represent each finger


class finger:
    def __init__(self, id, x, y, surface, force, display=False):
        self.id = id
        self.x = x
        self.y = y
        self.surface = surface
        self.force = force
        self.display = display

    def setPositionX(self, x):
        self.x = x

    def setPositionY(self, y):
        self.y = y

    def setSurface(self, value):
        if value >= 0:
            self.surface = value

    def setForce(self, value):
        if value >= 0:
            self.force = value

    def setDisplay(self, value):
        self.display = value

# Class to represent global trackpad information. Pretty self explanatory


class globalInfo:
    def __init__(self):
        self.firstFingerPosition = (0, 0)
        self.firstFingerForce = 0
        self.clicked = False
        self.globalForce = 0
        self.touchingFingerCounter = 0
        self.totalFingerCounter = 0

    def setFirstFingerData(self, x, y, force):
        self.firstFingerPosition = (x, y)
        self.firstFingerForce = force

    def setClick(self, value):
        if value == 1 or value == 0:
            self.clicked = value

    def setGlobalForce(self, value):
        if value >= 0:
            self.setGlobalForce = value

    def addTouchingFinger(self):
        self.touchingFingerCounter += 1

    def removeTouchingFinger(self):
        if self.touchingFingerCounter >= 1:
            self.touchingFingerCounter -= 1

    def addTotalFingerCounter(self):
        self.totalFingerCounter += 1

# Class to order both global information and each finger


class infoManager:
    def __init__(self, globalInfo_obj: globalInfo):
        self.globalInfo: globalInfo = globalInfo_obj
        self.currentFingerId = 0
        self.fingerIdIndexes = []
        self.fingerCounter: int = 0
        self.fingers: list[finger] = [None, None, None, None, None]

    def addTotalFingerPress(self):
        self.globalInfo.addTotalFingerCounter()

    def addFinger(self, fingerId, x=0, y=0, surface=0, force=0, display=False):
        self.fingers[self.fingerCounter] = finger(
            fingerId, x, y, surface, force, display)
        self.fingerIdIndexes.append(fingerId)
        self.fingerCounter += 1

    def removeFinger(self, fingerId=-1):
        fingerActualId = self.currentFingerId
        if fingerId != -1:
            fingerActualId = fingerId
        actualIndex = self.fingerIdIndexes.index(fingerActualId)
        while True:
            if self.fingers[actualIndex+1] != None:
                self.fingers[actualIndex] = self.fingers[actualIndex+1]
                self.fingerIdIndexes[actualIndex] = self.fingerIdIndexes[actualIndex+1]
                actualIndex += 1
            else:
                self.fingers[actualIndex] = None
                del self.fingerIdIndexes[actualIndex]
                break
        self.fingerCounter -= 1
        return

    def setFingerId(self, fingerId):
        if not (fingerId in self.fingerIdIndexes):
            # print(f"New finger registered, id: {fingerId}")
            self.addFinger(fingerId)
        else:
            # print(f"Finger already registered, id: {fingerId}")
            if not self.fingers[self.fingerIdIndexes.index(fingerId)]:
                self.setFingerDisplay(True)
        self.currentFingerId = fingerId

    def setFingerPositionX(self, x):
        try:
            self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setPositionX(
                x)
        except:
            self.setFingerId(self.currentFingerId)
            self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setPositionX(
                x)

    def setFingerPositionY(self, y):
        self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setPositionY(
            y)

    def setFingerSurface(self, value):
        self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setSurface(
            value)

    def setFingerForce(self, value):
        self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setForce(
            value)

    def setFingerDisplay(self, value):
        self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setDisplay(
            value)


    # def setFingerPosition(self, x, y):
global_obj = globalInfo()
info = infoManager(global_obj)

debug = False

for event in dev.read_loop():
    value = event.value
    print(info.fingerIdIndexes)
    if event.code == codes.uid.value:
        # print(f"Got uid: {value}")
        info.setFingerId(value)
    elif event.code == codes.fingerLiftOrCounter.value:
        if value == -1:
            print("Finger removed")
            info.removeFinger()
        else:
            # print("New touch")
            info.addTotalFingerPress()
    elif event.code == codes.x.value:
        # print("Got x")
        info.setFingerPositionX(value)
    elif event.code == codes.y.value:
        # print("Got y")
        info.setFingerPositionY(value)
    # try:
    #     print(info.fingers[0].x)
    # except:
    #     None
