import evdev
import dbus
from enum import Enum


##### DETECT TRACKPAD #####
dev = None
# Declares a number that will increment to check every event file
index = 0
while True:
    # Gets the event file corresponding to given index
    dev = evdev.InputDevice(f'/dev/input/event{index}')
    # Checks if its the trackpad file
    if dev.name == "Apple Inc. Magic Trackpad 2":
        # If it is, break the loop and continue
        break
    else:
        # If it isn't, run it again with next index
        index += 1


print(f"Found trackpad: \n{dev}")

##### GET TRACKPAD BATTERY AND WARN IF BELOW 20% #####

# Declares the bus
bus = dbus.SystemBus()
# Declares the Inferface for the bus and the UPower interface
manager = dbus.Interface(bus.get_object(
    'org.freedesktop.UPower', '/org/freedesktop/UPower'), 'org.freedesktop.UPower')
# Loops for every device found in the UPower interface
for device in manager.EnumerateDevices():
    # Looks for the model name of given device
    device_model = dbus.Interface(bus.get_object(
        'org.freedesktop.UPower', device), 'org.freedesktop.DBus.Properties').Get('org.freedesktop.UPower.Device', 'Model')
    print(f"Device model name: {device_model}")
    # Checks wether is a trackpad or not
    if device_model == "Varo's Trackpad":
        # Gets the properties of given device
        device_props = dbus.Interface(bus.get_object(
            'org.freedesktop.UPower', device), 'org.freedesktop.DBus.Properties')
        # Looks for the battery property
        battery = device_props.Get(
            'org.freedesktop.UPower.Device', 'Percentage')
        # Prints it
        print(f"Current battery percentage: {battery}%")
        if (battery <= 10.0):
            print("BATTERY BELOW MINIMUM, A RECHARGE IS NEEDED")
        break
    else:
        exit()
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
        self.clicked: bool = 0
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
    def __init__(self, globalInfo_obj: globalInfo = globalInfo()):
        # Saves global info to an instance variable
        self.globalInfo: globalInfo = globalInfo_obj
        # Represents the current ID of the finger (could be 3, 5, 9....)
        self.currentFingerId = 0
        # Stores the ids of the fingers that are touching the trackpad, HAS THE SAME ORDER AS THE self.fingers ARRAY, USED AS REFERENCE
        self.fingerIdIndexes = []
        # Counts how many fingers are touching the trackpad
        self.fingerCounter: int = 0
        # Stores each finger information
        self.fingers: list[finger] = [None, None, None, None, None]

    # Setter function
    def addTotalFingerPress(self):
        self.globalInfo.addTotalFingerCounter()

    # Adds finger to the self.fingers array
    def addFinger(self, fingerId, x=0, y=0, surface=0, force=0, display=False):
        # Stores the finger information with default values
        self.fingers[self.fingerCounter] = finger(
            fingerId, x, y, surface, force, display)
        # Stores the finger ID into the ID arrays
        self.fingerIdIndexes.append(fingerId)
        # Adds 1 to the finger counter
        self.fingerCounter += 1

    def removeFinger(self, fingerId=-1):
        # Takes the last given ID (because the trackpad will call the UID code before calling the FingerLift)
        fingerActualId = self.currentFingerId
        # If any finger id is specified, use it instead
        if fingerId != -1:
            fingerActualId = fingerId
        # Saves the index of the finger in use in the self.fingers array (SAME INDEX AS IN self.fingerIdIndexes)
        actualIndex = self.fingerIdIndexes.index(fingerActualId)
        # Loops through until all fingers are in their correct new position
        while True:
            # Checks if next element is None, if so, jump to "else"
            if actualIndex != 5:
                if self.fingers[actualIndex+1] != None:
                    # Move to the current index (the unusable one) the index of the next finger
                    self.fingers[actualIndex] = self.fingers[actualIndex+1]
                    # Same with the self.fingerIdIndexes (to keep the relation between arrays)
                    self.fingerIdIndexes[actualIndex] = self.fingerIdIndexes[actualIndex+1]
                    # Adds 1 to the actualIndex variable to check next element in the following reiteration
                    actualIndex += 1
                else:
                    # Set the last value to None to clear said element
                    self.fingers[actualIndex] = None
                    # Deletes last index of self.fingerIdIndexes as it wont be used anymore (its been moved to previous position before)
                    del self.fingerIdIndexes[actualIndex]
                    break
            else:
                # Set the last value to None to clear said element
                self.fingers[actualIndex] = None
                # Deletes last index of self.fingerIdIndexes as it wont be used anymore (its been moved to previous position before)
                del self.fingerIdIndexes[actualIndex]
                break
        # Remove the finger counter
        self.fingerCounter -= 1
        return

    def setFingerId(self, fingerId):
        # Change the current fingerId to the last given one (main purpose of method)
        self.currentFingerId = fingerId

        # If the given id its not registered previously, create a new finger with said id
        if not (fingerId in self.fingerIdIndexes):
            self.addFinger(fingerId)
        # else:
        #     # Otherwise, check if display value is false, if so, reverse it
        #     if not self.fingers[self.fingerIdIndexes.index(fingerId)].display:
        #         self.setFingerDisplay(True)

    def setFingerPositionX(self, x):
        try:
            # Tries setting the x coordenate of the finger
            # "Tries" because trackpad may give a new coordenate for a lifted finger (no longer in the self.fingers array)
            # that has touched again the trackpad, so there's no new id, it reuses last one without a warning
            self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setPositionX(
                x)
        except:
            # If it cannot set the coordenate, it means that it has reused the last id of a previously lifted finger,
            # so we need to create a new finger with that last id
            self.setFingerId(self.currentFingerId)
            self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setPositionX(
                x)

    def setFingerPositionY(self, y):
        # Sets the y coordenate
        # No need to do anything related to the x coord since the codes.x always comes before the codes.y --> So finger
        # has alreday been created either way
        self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setPositionY(
            y)
        # As the Y code is the last one to send related to a single finger that determinates the position,
        # once it has been sent, the finger is fully defined so its displayable
        if not self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].display:
            self.setFingerDisplay(True)

    def setFingerSurface(self, value):
        try:
            # Sets the finger surface over the trackpad
            self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setSurface(
                value)
        except:
            # Creates new finger
            self.setFingerId(self.currentFingerId)
            # Sets the finger surface over the trackpad
            self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setSurface(
                value)

    def setFingerForce(self, value):
        # Sets the finger force over the trackpad
        self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setForce(
            value)

    def setFingerDisplay(self, value):
        # Sets the display property (defines wether the finger is complete with all its properties and ready to be used)
        self.fingers[self.fingerIdIndexes.index(self.currentFingerId)].setDisplay(
            value)


# Create the information manager class instance
info = infoManager()

# Loops through every event in the corresponding event file
for event in dev.read_loop():
    # Saves the event value for later
    value = event.value
    # Kind of switch statement to determine what code its been sent to the event file

    if event.code == codes.uid.value:
        # print(f"Got uid: {value}")
        info.setFingerId(value)
    elif event.code == codes.fingerLiftOrCounter.value:
        # If it's a finger lift code or the counter, check for the value for futher determination
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
    elif event.code == codes.surface.value:
        info.setFingerSurface(value)
    elif event.code == codes.click.value:
        info.globalInfo.setClick(value)
    # try:
    #     print(f"First finger: ({info.fingers[0].x}, {info.fingers[0].y})")
    #     print(f"Second finger: ({info.fingers[1].x}, {info.fingers[1].y})")
    #     print(f"Third finger: ({info.fingers[2].x}, {info.fingers[2].y})")
    #     print(f"Forth finger: ({info.fingers[3].x}, {info.fingers[3].y})")
    #     print(f"Fifth finger: ({info.fingers[4].x}, {info.fingers[4].y})")
    # except:
    #     None
