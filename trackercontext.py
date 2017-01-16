from trackerdisplay import *
from trackergps import TrackerGPS
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import smbus
import time
import subprocess
from datetime import datetime

BATT_SENSOR_ADDRESS = 0x36
TEMP_SENSOR_ADDRESS = 0x48

class GPS1SubScreen(BasicScreen):
      def __init__(self):
            BasicScreen.__init__(self)
            self.gps = None
            self.fontsize = 20
            self.indent = 10

      def draw(self):
            line = 0
            self.clearScreen(1)
            if self.gps is None:
                  raise DisplayError("No GPS object configured")

            if self.gps.isrunning:
                  gpsinfo = self.gps.data.info
                  self.writeText(u'Time: {0:02d}:{1:02d}:{2:02d} \N{PLUS-MINUS SIGN} {3:.1f}sec'.format(self.gps.time.hour, self.gps.time.minute, self.gps.time.second, self.gps.error_time),self.indent, line, self.fontsize)
                  line += self.fontsize

                  if self.gps.mode >= 2:
                        (east, north) = self.gps.WGS84toOSGB36(gpsinfo['latitude'], gpsinfo['longitude'])
                        self.writeText(u'Lon: {0:.6f} \N{PLUS-MINUS SIGN} {1:.2f}'.format(gpsinfo['longitude'], gpsinfo['error_longitude']),self.indent,line,self.fontsize)
                        line += self.fontsize
                        self.writeText(u'Lat: {0:.6f} \N{PLUS-MINUS SIGN} {1:.2f}'.format(gpsinfo['latitude'], gpsinfo['error_latitude']),self.indent,line,self.fontsize)
                        line += self.fontsize
                        self.writeText('East: {0:.2f}'.format(east),self.indent,line,self.fontsize)
                        line += self.fontsize
                        self.writeText('North: {0:.2f}'.format(north),self.indent,line,self.fontsize)

            else:
                  self.writeText('Time: --:--:--',self.indent, line, self.fontsize)
                  line += self.fontsize
                  self.writeText('Lon: --',self.indent, line, self.fontsize)
                  line += self.fontsize
                  self.writeText('Lat: --',self.indent, line, self.fontsize)
                  line += self.fontsize
                  self.writeText('East: --',self.indent, line, self.fontsize)
                  line += self.fontsize
                  self.writeText('North: --',self.indent, line, self.fontsize)

class GPS2SubScreen(GPS1SubScreen):
      def draw(self):
            line = 0
            self.clearScreen(1)
            if self.gps is None:
                  raise DisplayError("No GPS object configured")
            if self.gps.isrunning and self.gps.mode >= 2:
                  gpsinfo = self.gps.data.info
                  self.writeText(u'Speed: {0} \N{PLUS-MINUS SIGN} {1:.2f}m/s'.format(gpsinfo['speed'], gpsinfo['error_speed']),self.indent,line,self.fontsize)
                  line += self.fontsize
                  self.writeText(u'Alt: {0} \N{PLUS-MINUS SIGN} {1:.2f}m'.format(gpsinfo['altitude'], gpsinfo['error_altitude']),self.indent,line,self.fontsize)
                  line += self.fontsize
                  self.writeText(u'Climb: {0} \N{PLUS-MINUS SIGN} {1:.2f}m'.format(gpsinfo['climb'], gpsinfo['error_climb']),self.indent,line,self.fontsize)
            else:
                  self.writeText('Speed: --',self.indent, line, self.fontsize)
                  line += self.fontsize
                  self.writeText('Alt: --',self.indent, line, self.fontsize)
                  line += self.fontsize
                  self.writeText('Climb: --',self.indent, line, self.fontsize)

class GPS3SubScreen(GPS1SubScreen):
      def draw(self):
            line = 0
            self.clearScreen(1)
            if self.gps is None:
                  raise DisplayError("No GPS object configured")
            if self.gps.isrunning:
                  self.writeText('Satellites: {0}'.format(self.gps.satellites),self.indent,line,self.fontsize)
                  line += self.fontsize
                  self.writeText('Satellites in use: {0}'.format(self.gps.satellites_used),self.indent,line,self.fontsize)
            else:
                  self.writeText('Satellites: --',self.indent, line, self.fontsize)
                  line += self.fontsize
                  self.writeText('Satellites in use: --',self.indent, line, self.fontsize)

            
class StatusContainer(ScreenDisplay):
      def loadresources(self):
            self.battlow = Image.open('/home/pi/tracker/gpstracker/res/battlow.png').convert(mode='1')
            self.batt100 = Image.open('/home/pi/tracker/gpstracker/res/batt100.png').convert(mode='1')
            self.batt75 = Image.open('/home/pi/tracker/gpstracker/res/batt75.png').convert(mode='1')
            self.batt50 = Image.open('/home/pi/tracker/gpstracker/res/batt50.png').convert(mode='1')
            self.batt25 = Image.open('/home/pi/tracker/gpstracker/res/batt25.png').convert(mode='1')
            self.gpsimg = Image.open('/home/pi/tracker/gpstracker/res/satellite.png').convert(mode='1')
            self.trackingimg = Image.open('/home/pi/tracker/gpstracker/res/gpstracking.png').convert(mode='1')

      def __init__(self):
            ScreenDisplay.__init__(self)

            self.partial_refresh_time = 5
            self.full_refresh_time = 120
            self.border = 5
            self.header = 20
            self.bus = None
            self.loadresources()
            self.gps = None

            # Create sub screens. Override the full PaPirus screen
            # to use a sub screen image
            self.subscreens = Screens()
            self.sub_offset = {'left':self.border, 'right':self.border, 'top': self.border + self.header, 'bottom':0}
            width = self.subscreens.pap.size[0] - (self.sub_offset['left'] + self.sub_offset['right'])
            height = self.subscreens.pap.size[1] - (self.sub_offset['top'] + self.sub_offset['bottom'])
            self.sub_size = (width, height)
            self.subscreens.image = Image.new('1', self.sub_size, 1)

      def draw(self):
            self.clearScreen(1)
            battimg = self.getBattImage(self.percent)
            x = self.image.size[0] - battimg.size[0] - self.border
            self.image.paste(battimg, box=(x,self.border))
            if self.gps is None:
                  raise DisplayException("No GPS object configured")
            if self.gps.isrunning:
                  self.image.paste(self.gpsimg, box=(self.border, self.border))
                  if self.gps.mode >= 2:
                        if self.gps.islogging:
                              self.image.paste(self.trackingimg, box=(self.border+self.gpsimg.size[0], self.border))
                        if self.gps.mode >=3:
                              self.writeText(u'\N{CIRCLED DIGIT THREE}', self.border+self.gpsimg.size[0]+self.trackingimg.size[0], self.border,15)
                        else:
                              self.writeText(u'\N{CIRCLED DIGIT TWO}', self.border+self.gpsimg.size[0]+self.trackingimg.size[0], self.border,15)
                  else:
                        self.writeText('No Signal', self.border+self.gpsimg.size[0],self.border,15)
            else:
                  self.writeText('GPS Disabled',0,5,15)

            try:
                  self.subscreens.currentScreen().draw()
                  self.image.paste(self.subscreens.currentScreen().image, box=(self.sub_offset['left'], self.sub_offset['top']))
            except DisplayError:
                  # Fails if no screens registered
                  pass

      def getBattImage(self, percent):
            if percent > 75:
                  return self.batt100
            elif percent > 50:
                  return self.batt75
            elif percent > 25:
                  return self.batt50
            elif percent > 10:
                  return self.batt25
            else:
                  return self.battlow
            
      @property
      def percent(self):
            # May return > 100
            raw_val = 0
            try:
                  raw_val = self.bus.read_byte_data(BATT_SENSOR_ADDRESS,0x04)
            except IOError:
                  print "IO Error received reading battery"
                  return 0
            
            return raw_val

class TrackerMain(StatusContainer):
      'Main screen for GPS information. Enables GPS when displayed'

      def __init__(self):
            StatusContainer.__init__(self)

            self.subtime = GPS1SubScreen()
            self.subscreens.registerScreen(self.subtime)

            self.subgps2 = GPS2SubScreen()
            self.subscreens.registerScreen(self.subgps2)

            self.subgps3 = GPS3SubScreen()
            self.subscreens.registerScreen(self.subgps3)

            # Initialise first screen
            self.subscreens.nextScreen()

      def set_gps(self, obj):
            self.gps = obj
            self.subtime.gps = obj
            self.subgps2.gps = obj
            self.subgps3.gps = obj

      def enter(self):
            BasicScreen.enter(self)
            if self.gps is not None:
                  self.gps.start()

      def finish(self):
            if self.gps is not None:
                  self.gps.stop()
            
class Lowpowersub(BasicScreen):
      'Contained screen for low power'
      def __init__(self):
            BasicScreen.__init__(self)
            self.fontsize = 20
            self.indent = 10
            self.pwrimg = Image.open('/home/pi/tracker/gpstracker/res/pwrsave.png').convert(mode='1')

      def draw(self):
            line = 0
            self.clearScreen(1)
            self.image.paste(self.pwrimg, box=(0, 0))
            self.writeText("Low Power Screen", self.indent, line, self.fontsize)
            line += self.fontsize
            self.writeText("Press power button briefly to exit", self.indent, line, 16)
            
class Lowpower(StatusContainer):
      'Low refresh screen'

      def __init__(self):
            StatusContainer.__init__(self)
            self.partial_refresh_time = 1800
            self.full_refresh_time = 7200
            self.pwrbtn = None
            self.runbtn = None
            self.bus = None
            self.prev_pwrbtn = True
            self.prev_runbtn = False
            self.pwrimg = Image.open('/home/pi/tracker/gpstracker/res/pwrsave.png').convert(mode='1')
            self.sub1 = Lowpowersub()
            self.subscreens.registerScreen(self.sub1)

            self.subscreens.nextScreen()

      def set_gps(self, gps):
            self.gps = gps
            
      def enter(self):
            StatusContainer.enter(self)
            if self.pwrbtn is not None:
                  self.prev_pwrbtn = self.pwrbtn.indicator
                  self.pwrbtn.indicator = False
            if self.runbtn is not None:
                  self.prev_runbtn = self.runbtn.indicator
                  self.runbtn.indicator = False

      def finish(self):
            if self.pwrbtn is not None:
                  self.pwrbtn.indicator = self.prev_pwrbtn
            if self.runbtn is not None:
                  self.runbtn.indicator = self.prev_runbtn
                  
class Shutdown(ScreenDisplay):
      'Shutdown screen'
      def __init__(self):
            ScreenDisplay.__init__(self)

      def draw(self):
            self.clearScreen(1)
            self.writeText('Power Off',0,0,20)
            self.writeText(time.strftime("%d-%b %H:%M:%S") , 0, 50, 25)
            
class TrackerDiag(ScreenDisplay):
      'Display system diagnostics'

      def __init__(self):
            ScreenDisplay.__init__(self)

            # Initialise any context variables used
            self.partial_refresh_time = 5
            self.full_refresh_time = 300
            self.net_refresh = 60
            self.bus = None
            self.ip = 'No Network'
            self.fontsize = 18
            self.tabstop = 120

      def enter(self):
            ScreenDisplay.enter(self)
            self.update_network_info()
            
      def update_network_info(self):
            exe = subprocess.Popen(["hostname", "-I"], stdout=subprocess.PIPE)
            self.ip = exe.communicate()[0].rstrip()
            if len(self.ip) == 0:
                  self.ip = 'No Network'
            
      def tick(self,t):
            ScreenDisplay.tick(self,t)
            if t - self.last_tick > self.net_refresh:
                  self.update_network_info()
                  
      def draw(self):
            startline = 30
            self.clearScreen(1)
            self.writeText('System',0,5,20)
            self.writeText('Network:',0,startline,self.fontsize)
            self.writeText(self.ip, self.tabstop, startline, self.fontsize)

            startline += self.fontsize
            self.writeText('Internal Temp:',0,startline,self.fontsize)
            self.writeText(u'{0:.1f}\N{DEGREE SIGN}C'.format(self.temperature), self.tabstop, startline, self.fontsize)

            startline += self.fontsize
            self.writeText('Battery %:',0,startline,self.fontsize)
            self.writeText('{0}%'.format(self.battpercent), self.tabstop, startline, self.fontsize)

            startline += self.fontsize
            self.writeText('Battery V:',0,startline,self.fontsize)
            self.writeText('{0:.1f}mV'.format(self.battvoltage), self.tabstop, startline, self.fontsize)

            startline += self.fontsize
            self.writeText('Internal Time:',0,startline,self.fontsize)
            t = datetime.now()
            self.writeText('{0:02d}:{1:02d}:{2:02d}'.format(t.hour, t.minute, t.second),self.tabstop, startline, self.fontsize)

      @property
      def battpercent(self):
            try:
                  raw_val = self.bus.read_byte_data(BATT_SENSOR_ADDRESS,0x04)
            except IOError:
                  print "IO Error received reading battery"
                  return 0
		
            return raw_val

      @property
      def battvoltage(self):
            high_val = 0
            low_val = 0
            try:
                  high_val = self.bus.read_byte_data(BATT_SENSOR_ADDRESS,0x02)
                  low_val = self.bus.read_byte_data(BATT_SENSOR_ADDRESS,0x03)
            except IOError:
                  print ("IO Error received reading battery")
                  return 0
		
            raw_val = ((low_val | (high_val << 8)) >> 4)
            return raw_val * 1.25

      @property
      def temperature(self):
            raw_temp = 0
            try:
                  raw_temp = self.bus.read_word_data(TEMP_SENSOR_ADDRESS,0x00)
            except IOError:
                  print ("IO Error received reading temperature")
                  return 0

            return self.reverse_word_bytes(raw_temp) * 0.125

      


