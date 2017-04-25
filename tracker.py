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

from trackerdisplay import Screens
from trackercontext import *
from summarydisplay import SummaryScreen
from trackergpio import IndicatorButton
import smbus
import time
from trackergps import TrackerGPS
import subprocess
from config import appconfig

class trackerapp(object):

    def __init__(self):
        self.tracker_screens = Screens()
        self.runbtn = IndicatorButton(appconfig['gpio_run_pin'],appconfig['gpio_run_indicator'])
        self.runbtn.rise_fn = self.run_btn_up
        self.runbtn.fall_fn = self.run_btn_dn

        self.pwrbtn = IndicatorButton(appconfig['gpio_pwr_pin'],appconfig['gpio_pwr_indicator'])
        self.pwrbtn.rise_fn = self.pwr_btn_up
        self.pwrbtn.fall_fn = self.pwr_btn_dn

        self.gps = None
        self.gps_running = False
        self.run_held = False
        self.pwr_held = False
        
    def pwr_btn_up(self, channel):
        if self.pwr_held:
            self.pwr_held = False
            # Do other things
        else:
            # Brief press
            self.tracker_screens.nextScreen()
        pass

    def pwr_btn_dn(self, channel):
        pass

    def run_btn_dn(self, channel):
        pass
        
    def run_btn_up(self, channel):
        if self.run_held:
            self.run_held = False
            if self.gps_running:
                print ("Stopping GPS")
                self.gps.stop()
                self.gps.log_gps(False)
            else:
                print ("Running GPS")
                self.gps.start()
                self.gps.log_gps(True)
            self.gps_running = not self.gps_running
            self.tracker_screens.currentScreen().invalidate()
        else:
            # Brief press
            if self.tracker_screens.currentScreen().name == 'Main' or self.tracker_screens.currentScreen().name == 'Activity':
                self.tracker_screens.currentScreen().subscreens.nextScreen()
                self.tracker_screens.currentScreen().invalidate()
            pass
        
    def run(self):

        try:
            data_bus = smbus.SMBus(1)
            self.gps = TrackerGPS()
            self.gps.loadlog() # Attempt to load previous day's log
            
            activity_screen = SummaryScreen()
            activity_screen.name = 'Activity'
            activity_screen.bus = data_bus
            activity_screen.metric_units(appconfig['metric'])
            activity_screen.set_gps(self.gps)
            
            default_screen = TrackerMain()
            default_screen.name = 'Main'
            default_screen.bus = data_bus
            default_screen.set_gps(self.gps)

            diagnostics_screen = TrackerDiag()
            diagnostics_screen.name = 'Diagnostics'
            diagnostics_screen.bus = data_bus

            sleep_screen = Lowpower()
            sleep_screen.name = "Sleep"
            sleep_screen.pwrbtn = self.pwrbtn
            sleep_screen.runbtn = self.runbtn
            sleep_screen.bus = data_bus
            sleep_screen.set_gps(self.gps)

            shutdown_screen = Shutdown()
            shutdown_screen.name = "shutdown"
            shutdown_screen.hidden = True
            shutdown_screen.set_gps(self.gps)

            self.tracker_screens.registerScreen(activity_screen)
            self.tracker_screens.registerScreen(default_screen)
            self.tracker_screens.registerScreen(diagnostics_screen)
            self.tracker_screens.registerScreen(sleep_screen)
            self.tracker_screens.registerScreen(shutdown_screen)

            # Initiate first screen. 
            # This calls all the startup and ensures only the first
            # visible screen is shown
            self.tracker_screens.nextScreen()

            self.runbtn.start()
            self.runbtn.indicator = False
        
            self.pwrbtn.start()
            self.pwrbtn.indicator = True

            while True:
                t = time.time()
                self.tracker_screens.currentScreen().tick(t)
                self.pwrbtn.tick(t)
                self.runbtn.tick(t)

                if self.runbtn.heldtime > 3:
                    if not self.run_held:
                        self.runbtn.indicator = not self.gps_running
                    self.run_held = True 
                        
                if self.pwrbtn.heldtime > 5:
                    self.pwr_held = True
                    self.tracker_screens.getScreen('shutdown').tick(t)
                    self.shutdownpi()
                
                time.sleep(0.1)                                            

        except KeyboardInterrupt:
            print ("Interrupt received, stopping tracker")
        except:
            print ("Unhandled exception")
            raise
        #finally:
        self.pwrbtn.stop()
        self.runbtn.stop()
        self.gps.terminate()
        #exit()
            
    def shutdownpi(self):
        for i in range(1,7):
            self.pwrbtn.indicator = not self.pwrbtn.indicator
            time.sleep(0.2)
        self.pwrbtn.indicator = False
        subprocess.Popen(["shutdown", "-h", "now"])
        time.sleep(100)
# Main

if __name__ == "__main__":
    app = trackerapp()
    app.run()
        


