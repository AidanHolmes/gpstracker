from trackerdisplay import *
from trackergps import TrackerGPS
from trackercontext import StatusContainer
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

def hms(sec):
    hour = int(sec / 3600)
    minute = int((sec - (hour * 3600)) / 60)
    sec = int(sec - (hour * 3600) - (minute * 60))
    return (hour, minute, sec)


class Tracker1SubScreen(BasicScreen):
    def __init__(self):
        BasicScreen.__init__(self)
        self.gps = None
        self.fontsize = 20
        self.indent = 10
        self.showmetric = True
        
    def draw(self):
        line = 0
        self.clearScreen(1)
        if self.gps is None:
            raise DisplayError("No GPS object configured")

        if self.showmetric:
            self.writeText('km: {0:.2f}'.format(self.gps.data.km),self.indent,line,self.fontsize)
        else:
            self.writeText('Miles: {0:.2f}'.format(self.gps.data.mile),self.indent,line,self.fontsize)

        line += self.fontsize
        if self.gps.data.sessions_recorded >= 1:
            (h,m,s) = hms(self.gps.data.secs)
            self.writeText('Total time: {0:02d}h {1:02d}m {2:02d}s'.format(h,m,s),self.indent,line,self.fontsize)
        else:
            self.writeText('Total time: No log',self.indent,line,self.fontsize)
        line += self.fontsize
        self.writeText('Sessions: {0}'.format(self.gps.data.sessions_recorded),self.indent,line,self.fontsize)
        line += self.fontsize
        self.writeText('Max Height: {0}m'.format(self.gps.data.max_height),self.indent,line,self.fontsize)
        line += self.fontsize
        self.writeText('Min Height: {0}m'.format(self.gps.data.min_height),self.indent,line,self.fontsize)
            
class Tracker2SubScreen(BasicScreen):
    def __init__(self):
        BasicScreen.__init__(self)
        self.gps = None
        self.fontsize = 20
        self.indent = 10
        self.showmetric = True

    def draw(self):
        line = 0
        records = 0
        split_time_array = None
        unittext = 'km'
        self.clearScreen(1)
        if self.gps is None:
            raise DisplayError("No GPS object configured")

        summary = self.gps.data

        if self.showmetric:
            self.writeText('Split time per km:',self.indent,line,self.fontsize)
            records = len(summary.split_time_km)
            split_time_array = summary.split_time_km
        else:
            self.writeText('Split time per mile:',self.indent,line,self.fontsize)
            records = len(summary.split_time_miles)
            split_time_array = summary.split_time_miles
            unittext = 'Mile'
            
        line += self.fontsize

        # Last entry is the current km/mile so will not be completely calculated
        # Write the last 5 entries
    
        for i in reversed(split_time_array[-6:-1]):
            hour = i / 3600
            minute = (i - (hour * 3600)) / 60
            second = i - (hour * 3600) - (minute * 60)
            #print ("idx: {0}, h:{1}, m{2}, s{3}".format(i, hour, minute, second))
            self.writeText('{4} {0}: {1:02d}h:{2:02d}m:{3:02d}s'.format(records-1, hour, minute, second,unittext),self.indent,line,self.fontsize)
            line += self.fontsize
            records -= 1

class Tracker3SubScreen(BasicScreen):
    'Show miles/km per hour summary'
    
    def __init__(self):
        BasicScreen.__init__(self)
        self.gps = None
        self.fontsize = 20
        self.indent = 10
        self.showmetric = True

    def draw(self):
        line = 0
        split_time_array = None
        unittext = 'km'
        self.clearScreen(1)
        if self.gps is None:
            raise DisplayError("No GPS object configured")

        summary = self.gps.data
        distance = 0

        if self.showmetric:
            self.writeText('km per hour:',self.indent,line,self.fontsize)
            split_time_array = summary.split_km_hour
        else:
            self.writeText('Miles per hour:',self.indent,line,self.fontsize)
            split_time_array = summary.split_mile_hour
            unittext = 'miles'
            
        line += self.fontsize
        records = len(split_time_array)

        # Last entry is the current km/mile so will not be completely calculated
        # Write the last 5 entries and estimate the last projected speed
        if (records * 3600) > self.gps.data.secs:
            # last record is partial. Very rare chance that this wouldn't be the case
            unitperhour = split_time_array[-1:][0] / ((self.gps.data.secs - ((records-1) * 3600)) / 3600)
            self.writeText('Hour {0}: est {1:.2f} {2}'.format(records, unitperhour, unittext),self.indent,line,self.fontsize)
            line += self.fontsize
            
        for i in reversed(split_time_array[-6:-1]):
            self.writeText('Hour {0}: {1:.2f} {2}'.format(records-1, i, unittext),self.indent,line,self.fontsize)
            line += self.fontsize
            records -= 1


class SummaryScreen(StatusContainer):
    'Displays all tracker summary information'
      
    def __init__(self):
        StatusContainer.__init__(self)
        
        # Override and define slower refresh
        # times for the summary screen
        self.partial_refresh_time = 15
        self.full_refresh_time = 300
        
        self.trackerinfo1 = Tracker1SubScreen()
        self.subscreens.registerScreen(self.trackerinfo1)
        
        self.trackerinfo2 = Tracker2SubScreen()
        self.subscreens.registerScreen(self.trackerinfo2)

        self.trackerinfo3 = Tracker3SubScreen()
        self.subscreens.registerScreen(self.trackerinfo3)

        self.subscreens.nextScreen()

    def metric_units(self,gometric):
        self.trackerinfo1.showmetric = gometric
        self.trackerinfo2.showmetric = gometric
        self.trackerinfo3.showmetric = gometric
            
    def set_gps(self, obj):
        self.gps = obj
        self.trackerinfo1.gps = obj
        self.trackerinfo2.gps = obj
        self.trackerinfo3.gps = obj

