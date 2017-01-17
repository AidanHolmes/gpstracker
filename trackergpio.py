# Copyright 2017 Aidan Holmes

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import RPi.GPIO as io
import time
from threading import Lock

class GPIOButton(object):
    'Button object to represent a GPIO input'

    UP = 1
    DN = 0
    btnbouncems = 200

    def __init__(self, pin, mode = 'BCM'):

        self.__lock = Lock()
        self.mode = mode
        # making this private as changing the pin will not work as
        # expected since the pin is only setup once in __init__
        self.__pin = pin 
        # Callback functions held for rise and fall. Although these
        # can be changed when running I'm unsure if exceptions could
        # be raised if set to None mid check of value. A Lock may be required
        self.rise_fn = None
        self.fall_fn = None
        self.state = GPIOButton.UP # Track the state of the button
        self.__heldtime = 0 # Time button has been last held

        io.setwarnings(False)
        
        if mode == 'BCM':
            io.setmode(io.BCM)
        else:
            io.setmode(io.BOARD)

    def __del__(self):
        self.stop()

    def callback_fall(self, channel):
        self.__lock.acquire()
        self.state = GPIOButton.DN
        self.__heldtime = time.time()
        self.__lock.release()
        
        if self.fall_fn is not None: self.fall_fn(self.__pin)
        
    def start(self):
        # Do some custom setup before starting the detection
        # Configure the pin
        io.setup(self.__pin, io.IN, pull_up_down=io.PUD_UP)
        # Detect button falls. Trying to do BOTH causes issues when also used with
        # button bounce prevention. The rising edges can get missed when buttons
        # are quickly pressed.
        io.add_event_detect(self.__pin, io.FALLING, callback=self.callback_fall, bouncetime=GPIOButton.btnbouncems)

    def stop(self):
        io.remove_event_detect(self.__pin)
        io.cleanup(self.__pin)

    def tick(self,t):
        self.__lock.acquire()
        if io.input(self.__pin) == io.HIGH and self.state == GPIOButton.DN:
            # Reset the heldtime button. This also indicates
            # that the last state was DN so trigger the callback
            self.__heldtime = 0
            self.state = GPIOButton.UP
            if self.rise_fn is not None: self.rise_fn(self.__pin)
        self.__lock.release()
        
    @property
    def heldtime(self):
        self.__lock.acquire()
        if self.__heldtime == 0: val = 0
        else: val = time.time() - self.__heldtime
        self.__lock.release()
        return val


class IndicatorButton(GPIOButton):
    'Button using 2 GPIO channels to read button state and indicate state'

    def __init__(self, pin, ind_pin, mode = 'BCM'):
        GPIOButton.__init__(self, pin, mode)
        self.__ind_pin = ind_pin
        self.__indicator = True

    def start(self):
        GPIOButton.start(self)
        io.setup(self.__ind_pin, io.OUT)

    def stop(self):
        GPIOButton.stop(self)
        io.cleanup(self.__ind_pin)

    @property
    def indicator(self):
        return self.__indicator

    @indicator.setter
    def indicator(self, ind):
        self.__indicator = ind
        if ind:
            io.output(self.__ind_pin, io.HIGH)
        else:
            io.output(self.__ind_pin, io.LOW)
