from enum import Enum
import evdev
import dbus
from threading import Thread


class _codes(Enum):
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


class _finger:
    def __init__(self, id, x, y, surface, force, display=False):
        self._id = id
        self._x = x
        self._y = y
        self._surface = surface
        self._force = force
        self._display = display

    def getPosition(self):
        return (self._x, self._y)

    def getSurface(self):
        return self._surface

    def getDisplay(self):
        return self._display

    def getForce(self):
        return self._force

    def setPositionX(self, x):
        self._x = x

    def setPositionY(self, y):
        self._y = y

    def setSurface(self, value):
        if value >= 0:
            self._surface = value

    def setForce(self, value):
        if value >= 0:
            self._force = value

    def setDisplay(self, value):
        self._display = value


# Class to represent global trackpad information. Pretty self explanatory
class _globalInfo:
    def __init__(self):
        self._firstFingerPositionX: int = 0
        self._firstFingerPositionY: int = 0
        self._firstFingerForce: int = 0
        self._clicked: bool = 0
        self._globalForce: int = 0
        # How many fingers are actually touching the trackpad
        self._touchingFingerCounter: int = 0
        # How many times has the trackpad been touched since turned on
        self._totalFingerPressCounter: int = 0

    # GETTER FUNCTIONS

    def getFirstFingerPosition(self) -> int:
        return (self._firstFingerPositionX, self._firstFingerPositionY)

    def getFirstFingerForce(self) -> int:
        return self._firstFingerForce

    def isClicked(self) -> bool:
        return self._clicked

    def getGlobalForce(self) -> int:
        return self._globalForce

    def getFingersTouching(self) -> int:
        return self._touchingFingerCounter

    def getFingerPressCounter(self) -> int:
        return self._totalFingerPressCounter

    # SETTER FUNCTIONS

    def setFirstFingerX(self, x: int):
        self._firstFingerPositionX = x

    def setFirstFingerY(self, y: int):
        self._firstFingerPositionY = y

    def setFirstFingerForce(self, value: int):
        self._firstFingerForce = value

    def setClick(self, value: bool):
        if value == 1 or value == 0:
            self._clicked = value

    def setGlobalForce(self, value: int):
        if value >= 0:
            self._globalForce = value

    # Stats functions

    def addTouchingFinger(self):
        self._touchingFingerCounter += 1

    def removeTouchingFinger(self):
        if self._touchingFingerCounter >= 1:
            self._touchingFingerCounter -= 1

    # Number of times the trackpad has been touched
    def addTotalFingerPressCounter(self):
        self._totalFingerPressCounter += 1


# Class to order both global information and each finger
class _infoManager:
    def __init__(self, globalInfo_obj: _globalInfo = _globalInfo()):
        # Saves global info to an instance variable
        self.globalInfo: _globalInfo = globalInfo_obj
        # Represents the current ID of the finger (could be 3, 5, 9....)
        self._currentFingerId = 0
        # Stores the ids of the fingers that are touching the trackpad, HAS THE SAME ORDER AS THE self.fingers ARRAY, USED AS REFERENCE
        self._fingerIdIndexes = []
        # Counts how many fingers are touching the trackpad
        self._fingerCounter: int = 0
        # Stores each finger information
        self._fingers: list[_finger] = [None, None, None, None, None]

    def getCoords(self, fingerIndex: int):
        try:
            return self._fingers[fingerIndex].getPosition()
        except:
            return (None, None)

    def getSurface(self, fingerIndex: int):
        try:
            return self._fingers[fingerIndex].getSurface()
        except:
            return None

    def getIdsPerIndex(self):
        return self._fingerIdIndexes

    def getNumberOfFingers(self):
        return self._fingerCounter

    def getFingerObject(self, index: int):
        return self._fingers[index]

    # Setter function

    def _addTotalFingerPress(self):
        self.globalInfo.addTotalFingerPressCounter()

    # Adds finger to the self.fingers array
    def _addFinger(self, fingerId: int, x: int = 0, y: int = 0, surface: int = 0, force: int = 0, display: bool = False):
        # Stores the finger information with default values
        self._fingers[self._fingerCounter] = _finger(
            fingerId, x, y, surface, force, display)
        # Stores the finger ID into the ID arrays
        self._fingerIdIndexes.append(fingerId)
        # Adds 1 to the finger counter
        self._fingerCounter += 1

    def _removeFinger(self, fingerId: int = -1):
        # Takes the last given ID (because the trackpad will call the UID code before calling the FingerLift)
        fingerActualId = self._currentFingerId
        # If any finger id is specified, use it instead
        if fingerId != -1:
            fingerActualId = fingerId
        # Saves the index of the finger in use in the self.fingers array (SAME INDEX AS IN self.fingerIdIndexes)
        actualIndex = self._fingerIdIndexes.index(fingerActualId)
        # Loops through until all fingers are in their correct new position
        while True:
            # Checks if next element is None, if so, jump to "else"
            if actualIndex < 4:
                if self._fingers[actualIndex+1] != None:
                    # Move to the current index (the unusable one) the index of the next finger
                    self._fingers[actualIndex] = self._fingers[actualIndex+1]
                    # Same with the self.fingerIdIndexes (to keep the relation between arrays)
                    self._fingerIdIndexes[actualIndex] = self._fingerIdIndexes[actualIndex+1]
                    # Adds 1 to the actualIndex variable to check next element in the following reiteration
                    actualIndex += 1
                else:
                    # Set the last value to None to clear said element
                    self._fingers[actualIndex] = None
                    # Deletes last index of self.fingerIdIndexes as it wont be used anymore (its been moved to previous position before)
                    del self._fingerIdIndexes[actualIndex]
                    break
            else:
                # Set the last value to None to clear said element
                self._fingers[actualIndex] = None
                # Deletes last index of self.fingerIdIndexes as it wont be used anymore (its been moved to previous position before)
                del self._fingerIdIndexes[actualIndex]
                break
        # Remove the finger counter
        self._fingerCounter -= 1
        return

    def _setFingerId(self, fingerId: int):
        # Change the current fingerId to the last given one (main purpose of method)
        self._currentFingerId = fingerId

        # If the given id its not registered previously, create a new finger with said id
        if not (fingerId in self._fingerIdIndexes):
            self._addFinger(fingerId)
        # else:
        #     # Otherwise, check if display value is false, if so, reverse it
        #     if not self.fingers[self.fingerIdIndexes.index(fingerId)].display:
        #         self.setFingerDisplay(True)

    def _setFingerPositionX(self, x: int):
        try:
            # Tries setting the x coordenate of the finger
            # "Tries" because trackpad may give a new coordenate for a lifted finger (no longer in the self.fingers array)
            # that has touched again the trackpad, so there's no new id, it reuses last one without a warning
            self._fingers[self._fingerIdIndexes.index(self._currentFingerId)].setPositionX(
                x)
        except:
            # If it cannot set the coordenate, it means that it has reused the last id of a previously lifted finger,
            # so we need to create a new finger with that last id
            self._setFingerId(self._currentFingerId)
            self._fingers[self._fingerIdIndexes.index(self._currentFingerId)].setPositionX(
                x)

    def _setFingerPositionY(self, y: int):
        # Sets the y coordenate
        # No need to do anything related to the x coord since the codes.x always comes before the codes.y --> So finger
        # has alreday been created either way
        self._fingers[self._fingerIdIndexes.index(self._currentFingerId)].setPositionY(
            y)
        # As the Y code is the last one to send related to a single finger that determinates the position,
        # once it has been sent, the finger is fully defined so its displayable
        if not self._fingers[self._fingerIdIndexes.index(self._currentFingerId)].getDisplay():
            self._setFingerDisplay(True)

    def _setFingerSurface(self, value: int):
        try:
            # Sets the finger surface over the trackpad
            self._fingers[self._fingerIdIndexes.index(self._currentFingerId)].setSurface(
                value)
        except:
            # Creates new finger
            self._setFingerId(self._currentFingerId)
            # Sets the finger surface over the trackpad
            self._fingers[self._fingerIdIndexes.index(self._currentFingerId)].setSurface(
                value)

    def _setFingerForce(self, value: int):
        # Sets the finger force over the trackpad
        self._fingers[self._fingerIdIndexes.index(self._currentFingerId)].setForce(
            value)

    def _setFingerDisplay(self, value: bool):
        # Sets the display property (defines wether the finger is complete with all its properties and ready to be used)
        self._fingers[self._fingerIdIndexes.index(self._currentFingerId)].setDisplay(
            value)


class Trackpad:

    def __init__(self):
        self.debug = False
        self._device = self._getTrackpad()
        self.battery = self.getBattery()
        self.trackpadInfo = _infoManager()
        self._thread = Thread(target=self.loop, name="MainLoop").start()

    def loop(self):
        # Loops through every event in the corresponding event file
        for event in self._device.read_loop():
            # Saves the event value for later
            value = event.value
            # Kind of switch statement to determine what code its been sent to the event file
            if event.code == _codes.uid.value:
                if self.debug:
                    print(f"Got uid: {value}")
                self.trackpadInfo._setFingerId(value)
            elif event.code == _codes.fingerLiftOrCounter.value:
                # If it's a finger lift code or the counter, check for the value for futher determination
                if value == -1:
                    if self.debug:
                        print("Finger removed")
                    self.trackpadInfo._removeFinger()
                else:
                    if self.debug:
                        print("New touch")
                    self.trackpadInfo._addTotalFingerPress()
            elif event.code == _codes.x.value:
                if self.debug:
                    print(f"Got x: {value}")
                self.trackpadInfo._setFingerPositionX(value)
            elif event.code == _codes.y.value:
                if self.debug:
                    print(f"Got y: {value}")
                self.trackpadInfo._setFingerPositionY(value)
            elif event.code == _codes.surface.value:
                if self.debug:
                    print(f"Finger surface: {value}")
                self.trackpadInfo._setFingerSurface(value)
            elif event.code == _codes.click.value:
                if self.debug:
                    print(f"Clicked: {value}")
                self.trackpadInfo.globalInfo.setClick(value)
            elif event.code == _codes.globalForce.value:
                if self.debug:
                    print(f"Force: {value}")
                self.trackpadInfo.globalInfo.setGlobalForce(value)

    def _getTrackpad(self):
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
        if self.debug:
            print(f"Found trackpad: \n{dev}")
        return dev

    def getBattery(self):
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
            if self.debug:
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
                if self.debug:
                    print(f"Current battery percentage: {battery}%")
                # if (battery <= 10.0):
                #     print("BATTERY BELOW MINIMUM, A RECHARGE IS NEEDED")
                break
            else:
                exit()
        return battery
