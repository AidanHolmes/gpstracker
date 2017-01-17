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

import gps
import dateutil.parser
import time
import json
from datetime import datetime
from threading import Thread, Lock
from math import sqrt, pi, sin, cos, tan, atan2, radians, asin, floor, ceil
from config import appconfig

kmtomiles = 0.621371

class GPSSummary(object):
    'Provides a summary record for a GPS log file'

    def __init__(self):
        self.dbg = appconfig['debug']
        self.reset()
        
    def reset(self):
        self.records = 0
        self.km = 0.0 # Total distance from log
        self.mile = 0.0
        self.secs = 0.0
        self.sigma_lon_error_metres = 0 # Avg error from GPS
        self.sigma_lat_error_metres = 0 # Avg error from GPS
        self.km_per_hour = 0 # Avg speed
        self.split_time_km = [] # Each km is an entry with time taken
        self.split_time_miles = [] # Each mile is an entry with the time taken
        self.split_km_hour = [] # Each entry is an hour with distance travelled
        self.split_mile_hour = []
        self.elevation_per_km = [] # Height covered per km
        self.min_height = 0
        self.max_height = 0
        self.sigma_alt_error_metres = 0
        self.sessions_recorded = 0 # Times that the recording was started
        self.log_items = [] # only used by web interface to hold a cache of log
        
        self.longlatheld = None
        self.previnfo = None
        self.info = {'gpstime':'',
                     'timesec':0,
                     'latitude':0,
                     'longitude':0,
                     'error_latitude':0,
                     'error_longitude':0,
                     'altitude':0,
                     'error_altitude':0,
                     'speed':0,
                     'error_speed':0,
                     'climb':0,
                     'error_climb':0,
                     'start_record':True}

    @property
    def gps_serial_data(self):
        return json.dumps(self.info)
    
    @gps_serial_data.setter
    def gps_serial_data(self, s):
        self.info = json.loads(s)

    @staticmethod
    def haversine(lon1, lat1, lon2, lat2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        # Radius calculation can be improved with https://rechneronline.de/earth-radius/
        # Radius changes depending on latitude. 
        #km = 6367 * c # Halfway radius
        km = 6371 * c # Avg radius
        return km

    @staticmethod
    def iswithinerror(dis_km, info1, info2):
            # Check the error from GPS. Only include distances outside the largest error result. This is really rough
            # and unscientific but should exclude small distances which are due to wandering GPS coordinates
            error1 = max(info1['error_longitude'], info1['error_latitude'])
            error2 = max(info2['error_longitude'], info2['error_latitude'])

            return dis_km < (((error1 + error2)/4) /1000)
        
    def calculate_distance(self):
        global kmtomiles
        if self.longlatheld is not None:
            # Only if another record has been written as held can this code run

            # Compare previous long and lat to calculate distance
            deltakm = self.haversine(self.longlatheld['longitude'], self.longlatheld['latitude'], self.info['longitude'], self.info['latitude'])

            if not self.iswithinerror(deltakm, self.longlatheld, self.info):
                # Distance is outside the error so attribute to distance covered
                # Note the log entry used for this distance calculation
                self.km += deltakm
                self.mile += deltakm * kmtomiles
                if self.dbg:
                    print ("From ({0}, {1}) to ({2}, {3}), distance delta is {4:.3f}, error {5:.3f}".format(self.longlatheld['longitude'],
                                                                                                            self.longlatheld['latitude'],
                                                                                                            self.info['longitude'],
                                                                                                            self.info['latitude'],
                                                                                                            deltakm,
                                                                                                            (error1+error2)/1000))

                # Create entries in km split time list
                while len(self.split_time_km) < self.km:
                    self.split_time_km.append(0)
                    if self.dbg: print ("Creating split km record {0}".format(len(self.split_time_km)))

                # Create entries in mile split time list
                while len(self.split_time_miles) < self.km * kmtomiles:
                    self.split_time_miles.append(0)
                    if self.dbg: print ("Creating split mile record {0}".format(len(self.split_time_miles)))

                # This works unless rolling over midnight where timesec will reset.
                timedelta = self.info['timesec'] - self.longlatheld['timesec']
                self.secs += timedelta
                hours = self.secs / 3600.0
                if self.dbg: print ("Time delta is {0}sec".format(timedelta))
                while len(self.split_km_hour) <= hours:
                    self.split_km_hour.append(0)
                    if self.dbg: print ("Creating split km time record {0}".format(len(self.split_km_hour)))
                    
                while len(self.split_mile_hour) < hours:
                    self.split_mile_hour.append(0)
                    if self.dbg: print ("Creating split mile time record {0}".format(len(self.split_mile_hour)))

                # Calculate time taken between points
                try:
                    self.split_km_hour[int(floor(hours))] += deltakm
                    self.split_mile_hour[int(floor(hours))] += deltakm * kmtomiles
                    self.split_time_km[int(floor(self.km))] += self.info['timesec'] - self.longlatheld['timesec']
                    self.split_time_miles[int(floor(self.km * kmtomiles))] += self.info['timesec'] - self.longlatheld['timesec']
                except KeyError:
                    # May be an old log file, parse date/time string and calculate difference in seconds
                    # Remove this soon! Not applied for miles
                    self.split_time_km[int(floor(self.km))] += TrackerGPS.time_to_sec(dateutil.parser.parse(self.info['gpstime']).time()) - TrackerGPS.time_to_sec(dateutil.parser.parse(self.longlatheld['gpstime']).time())

                if self.dbg:
                    print ("Accumulated time in split km {0} is {1:.2f}".format(int(ceil(self.km)), self.split_time_km[int(floor(self.km))]))
                    print ("Accumulated time in split mile {0} is {1:.2f}".format(int(ceil(self.km * kmtomiles)), self.split_time_miles[int(floor(self.km * kmtomiles))]))

                self.longlatheld = self.info.copy()
            else:
                if self.dbg: print ("Distance delta is too small {0:.3f}, error {1:.3f}".format(deltakm,
                                                                                                (error1+error2)/1000))
                pass
        else:
            # This is a section which is run for the first GPS entry for a session
            self.longlatheld = self.info.copy() # just copy the whole record
        
    def commit_data(self):
        # This confirms that the record is final and to compute
        # the summary data
        try:
            if self.info['start_record'] == True:
                self.sessions_recorded += 1
                self.previnfo = None
                self.longlatheld = None
        except KeyError:
            # Missing from this record, ignore
            pass
        
        self.calculate_distance()
        
        if self.records == 0:
            # This is a section which is run for the first GPS entry
            self.min_height = self.info['altitude']
            self.max_height = self.info['altitude']

        # Check if max or min altitudes need updating
        if self.min_height > self.info['altitude']:
            self.min_height = self.info['altitude']
        if self.max_height < self.info['altitude']:
            self.max_height = self.info['altitude']

        self.sigma_lon_error_metres += self.info['error_longitude']
        self.sigma_lat_error_metres += self.info['error_latitude']
        self.sigma_alt_error_metres += self.info['error_altitude']
        
        self.previnfo = self.info.copy()
        self.records += 1
        
class TrackerGPS(Thread):
    'GPS wrapper class with worker thread to read GPS buffer'
    
    def __init__(self):
        Thread.__init__(self)
        self.gps = gps.gps()
        self.time = datetime.now()
        self.error_time = 0
        self.mode = 0
        self.satellites = 0
        self.satellites_used = 0
        self.__references = 0 # Track numbers using this object
        self.__quit = False
        self.__firstrun = True
        self.logdir = appconfig['logdir']
        self.logfilename = appconfig['prefix']
        self.loghandle = None
        self.lastlogwrite = 0
        self.logperiod = 20 # seconds
        self.__lock = Lock()
        self.data = GPSSummary()

    @staticmethod
    def time_to_sec(t):
        return (t.hour * 3600) + (t.minute * 60) + t.second
            
    def todaylogname(self):
        return '{0}/{1}{2}'.format(self.logdir, self.logfilename, time.strftime('%Y%m%d'))
    
    def log_gps(self, start = True):
        # Log GPS data as it is streaming
        # Set a critical section due to the thread checking these values. We don't want
        # to pull a file handle from under the threads feet
        self.__lock.acquire() 
        if start == False and self.loghandle is not None:
            self.loghandle.close()
            self.loghandle = None
        else:
            if self.loghandle is None:
                # Open the log
                filename = self.todaylogname() 
                try:
                    self.loghandle = open(filename, 'a')
                    self.loghandle.write('\n') # Start new line to avoid incomplete previous log lines
                    self.data.info['start_record'] = True
                except IOError:
                    # Cannot open the file.
                    print ("Cannot open the log file {0}".format(filename))
                    pass
        self.__lock.release() 
            
    def run(self):
        while not self.__quit:
            try:
                gpsdat = self.gps.next()
                if gpsdat['class'] == 'TPV':
                    if hasattr(gpsdat, 'time'):
                        self.data.info['gpstime'] = gpsdat.time
                        self.time = dateutil.parser.parse(gpsdat.time)
                        self.data.info['timesec'] = self.time_to_sec(self.time.time())
                    if hasattr(gpsdat, 'ept'): self.data.error_time = float(gpsdat.ept)
                    if hasattr(gpsdat, 'mode'): self.mode = int(gpsdat.mode)
                    if hasattr(gpsdat, 'lat'): self.data.info['latitude'] = float(gpsdat.lat)
                    if hasattr(gpsdat, 'lon'): self.data.info['longitude'] = float(gpsdat.lon)
                    if hasattr(gpsdat, 'epy'): self.data.info['error_latitude'] = float(gpsdat.epy)
                    if hasattr(gpsdat, 'epx'): self.data.info['error_longitude'] = float(gpsdat.epx)
                    if hasattr(gpsdat, 'alt'): self.data.info['altitude'] = float(gpsdat.alt)
                    if hasattr(gpsdat, 'epv'): self.data.info['error_altitude'] = float(gpsdat.epv)
                    if hasattr(gpsdat, 'speed'): self.data.info['speed'] = float(gpsdat.speed)
                    if hasattr(gpsdat, 'eps'): self.data.info['error_speed'] = float(gpsdat.eps)
                    if hasattr(gpsdat, 'climb'): self.data.info['climb'] = float(gpsdat.climb)
                    if hasattr(gpsdat, 'epc'): self.data.info['error_climb'] = float(gpsdat.epc)
                if hasattr(gpsdat, 'satellites'): # Read sky data
                    self.satellites = len(gpsdat.satellites)
                    self.satellites_used = 0
                    for sat in gpsdat.satellites:
                        if hasattr(sat, 'used'):
                            if sat.used:
                                self.satellites_used += 1
                        
            except KeyError:
                pass
            except StopIteration:
                # Attempt to restart
                self.gps = gps.gps()
                self.gps.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
            
            # For demo purposes mess up the lon and lat
            #self.data.latitude -= 1
            #self.data.longitude += 0.1

            # Write to log file
            self.writetolog()

    def readsessionlog(self, name=None, filterrecords=False):
        # This is a utility function for use outside this class
        # Multiple GPSSummaries are created and returned. This doesn't
        # prime the GPS session with past entries. Use loadlog to do that

        f = None
        sessions = []
        if name is None:
            name = self.todaylogname()
        try:
            f = open(name, 'r')
        except IOError:
            print ("Error: Cannot open log file - {0}".format(name))
            return sessions # empty list

        s = f.readline()
        sessions.append(GPSSummary())
        sessionindex = 0
        session = sessions[sessionindex]
        bfirstrecord = True
        lastinfo = None
        while s != "":
            try:
                session.gps_serial_data = s
                if not bfirstrecord and session.info['start_record']:
                    sessionindex += 1
                    # Create new summary object
                    sessions.append(GPSSummary())
                    session = sessions[sessionindex]
                    session.gps_serial_data = s
                    
                session.commit_data()
                # Filtering can be enabled to remove records which appear as error points
                # in the GPS results. This uses the same logic for distance calculations
                if filterrecords and (lastinfo is None or lastinfo != session.longlatheld):
                    # Only append longlatheld records which change
                    session.log_items.append(session.longlatheld)
                    lastinfo = session.longlatheld
                elif not filterrecords:
                    session.log_items.append(session.info) # Append to self
                    
                bfirstrecord = False
            except ValueError:
                pass # ignore malformed log entries
            
            s = f.readline()

        f.close()
        return sessions
        
    def loadlog(self, name = None, fn = None):
        # Load today's log if no name specified

        f = None
        entries = 0
        if name is None:
            name = self.todaylogname()
        try:
            f = open(name, 'r')
        except IOError:
            print ("Warning: Cannot open log file, this may be due to a new log: {0}".format(name))
            return 0

        s = f.readline()
        while s != "":
            try:
                self.data.gps_serial_data = s
                self.data.commit_data()
                if fn is not None:
                    # Call back with the info data loaded from file
                    fn(self.data.info)
                entries += 1
            except ValueError:
                pass
            
            s = f.readline()

        f.close()
        self.data.previnfo = None
        return entries
        
    @property
    def islogging(self):
        if self.loghandle is not None: return True
        return False

    def writetolog(self):
        # Only write if we have a GPS lock
        self.__lock.acquire()
        if self.islogging and time.time() - self.lastlogwrite > self.logperiod:
            if self.mode >= 2:
                try:
                    self.loghandle.write(self.data.gps_serial_data)
                    self.loghandle.write('\n')
                    self.loghandle.flush()
                    self.lastlogwrite = time.time()
                    self.data.commit_data()
                    self.data.info['start_record'] = False # record committed to log
                except:
                    print ("Something went wrong trying to write to the log file")
                
        self.__lock.release()
 
    def start(self):
        # Increment reference
        self.__references += 1
        if self.__references == 1:
            # Start the GPS watching for first reference
            self.gps.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)

        if self.__firstrun:
            Thread.start(self) # Only start once
            self.__firstrun = False
            
    def stop(self):
        # Stop the thread looping. Note that this may block if GPS
        # is waiting for data
        self.__references -= 1

        if self.is_alive() and self.__references <= 0:
            # Request a stop to the watch.
            # This should cause the next() read to block
            self.gps.stream(gps.WATCH_DISABLE)
            self.data.previnfo = None # Clear previous entries

    def terminate(self):
        self.__quit = True

        # Start the GPS to unblock the wait
        self.gps.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
        
        if self.is_alive():
            self.join()
        
    @property
    def isrunning(self):
        if self.__references > 0: return True
        return False

    @staticmethod
    def WGS84toOSGB36(lat, lon):

        #First convert to radians
        #These are on the wrong ellipsoid currently: GRS80. (Denoted by _1)
        lat_1 = lat*pi/180
        lon_1 = lon*pi/180

        #Want to convert to the Airy 1830 ellipsoid, which has the following:
        a_1, b_1 =6378137.000, 6356752.3141 #The GSR80 semi-major and semi-minor axes used for WGS84(m)
        e2_1 = 1- (b_1*b_1)/(a_1*a_1) #The eccentricity of the GRS80 ellipsoid
        nu_1 = a_1/sqrt(1-e2_1*sin(lat_1)**2)

        #First convert to cartesian from spherical polar coordinates
        H = 0 #Third spherical coord.
        x_1 = (nu_1 + H)*cos(lat_1)*cos(lon_1)
        y_1 = (nu_1+ H)*cos(lat_1)*sin(lon_1)
        z_1 = ((1-e2_1)*nu_1 +H)*sin(lat_1)

        #Perform Helmut transform (to go between GRS80 (_1) and Airy 1830 (_2))
        s = 20.4894*10**-6 #The scale factor -1
        tx, ty, tz = -446.448, 125.157, -542.060 #The translations along x,y,z axes respectively
        rxs,rys,rzs = -0.1502, -0.2470, -0.8421#The rotations along x,y,z respectively, in seconds
        rx, ry, rz = rxs*pi/(180*3600.), rys*pi/(180*3600.), rzs*pi/(180*3600.) #In radians
        x_2 = tx + (1+s)*x_1 + (-rz)*y_1 + (ry)*z_1
        y_2 = ty + (rz)*x_1+ (1+s)*y_1 + (-rx)*z_1
        z_2 = tz + (-ry)*x_1 + (rx)*y_1 +(1+s)*z_1

        #Back to spherical polar coordinates from cartesian
        #Need some of the characteristics of the new ellipsoid
        a, b = 6377563.396, 6356256.909 #The GSR80 semi-major and semi-minor axes used for WGS84(m)
        e2 = 1- (b*b)/(a*a) #The eccentricity of the Airy 1830 ellipsoid
        p = sqrt(x_2**2 + y_2**2)

        #Lat is obtained by an iterative proceedure:
        lat = atan2(z_2,(p*(1-e2))) #Initial value
        latold = 2*pi
        while abs(lat - latold)>10**-16:
            lat, latold = latold, lat
            nu = a/sqrt(1-e2*sin(latold)**2)
            lat = atan2(z_2+e2*nu*sin(latold), p)

        #Lon and height are then pretty easy
        lon = atan2(y_2,x_2)
        H = p/cos(lat) - nu

        #E, N are the British national grid coordinates - eastings and northings
        F0 = 0.9996012717 #scale factor on the central meridian
        lat0 = 49*pi/180#Latitude of true origin (radians)
        lon0 = -2*pi/180#Longtitude of true origin and central meridian (radians)
        N0, E0 = -100000, 400000#Northing & easting of true origin (m)
        n = (a-b)/(a+b)

        #meridional radius of curvature
        rho = a*F0*(1-e2)*(1-e2*sin(lat)**2)**(-1.5)
        eta2 = nu*F0/rho-1

        M1 = (1 + n + (5/4)*n**2 + (5/4)*n**3) * (lat-lat0)
        M2 = (3*n + 3*n**2 + (21/8)*n**3) * sin(lat-lat0) * cos(lat+lat0)
        M3 = ((15/8)*n**2 + (15/8)*n**3) * sin(2*(lat-lat0)) * cos(2*(lat+lat0))
        M4 = (35/24)*n**3 * sin(3*(lat-lat0)) * cos(3*(lat+lat0))

        #meridional arc
        M = b * F0 * (M1 - M2 + M3 - M4)

        I = M + N0
        II = nu*F0*sin(lat)*cos(lat)/2
        III = nu*F0*sin(lat)*cos(lat)**3*(5- tan(lat)**2 + 9*eta2)/24
        IIIA = nu*F0*sin(lat)*cos(lat)**5*(61- 58*tan(lat)**2 + tan(lat)**4)/720
        IV = nu*F0*cos(lat)
        V = nu*F0*cos(lat)**3*(nu/rho - tan(lat)**2)/6
        VI = nu*F0*cos(lat)**5*(5 - 18* tan(lat)**2 + tan(lat)**4 + 14*eta2 - 58*eta2*tan(lat)**2)/120

        N = I + II*(lon-lon0)**2 + III*(lon- lon0)**4 + IIIA*(lon-lon0)**6
        E = E0 + IV*(lon-lon0) + V*(lon- lon0)**3 + VI*(lon- lon0)**5

        #Job's a good'n.
        return (E,N)
        
