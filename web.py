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

from flask import Flask, render_template, request, url_for
import trackergps as gps
from summarydisplay import hms
import os
from config import webconfig

app = Flask(__name__)

def update_bounds(bounds, data):
    if bounds is None:
        bounds = {}
        bounds['minlat'] = data['latitude']
        bounds['maxlat'] = data['latitude']
        bounds['minlon'] = data['longitude']
        bounds['maxlon'] = data['longitude']
        return bounds
    
    bounds['minlat'] = min(bounds['minlat'], data['latitude'])
    bounds['minlon'] = min(bounds['minlon'], data['longitude'])
    bounds['maxlon'] = max(bounds['maxlon'], data['longitude'])
    bounds['maxlat'] = max(bounds['maxlat'], data['latitude'])

    return bounds

@app.route('/')
def showmenu():
    gpslogfiles = []
    glog = gps.TrackerGPS()
    files = os.listdir(glog.logdir)
    files.sort()
    for fname in files:
        if fname[0:len(glog.logfilename)] == glog.logfilename:
            # Match found
            # Attempt to read
            try:
                f = open(glog.logdir + '/' + fname, "r")
                sline = f.readline()
                while sline != "":
                    try:
                        glog.data.gps_serial_data = sline
                        glog.data.commit_data() # Build summary information
                    except ValueError:
                        pass

                    sline = f.readline()

                # Take the summary info and add to web template data
                kms = round(glog.data.km,2)
                miles = round(glog.data.mile,2)
                (h,m,s) = hms(glog.data.secs)

                gpslogfiles.append({'name': fname,
                                    'hlink': url_for('showroute', name=fname, filter='y'),
                                    'miles': miles,
                                    'kms': kms,
                                    'hour': format(h, '02d'),
                                    'min': format(m, '02d'),
                                    'sec': format(s, '02d')})
                glog.data.reset() # Reset summary data
                
            except IOError:
                # Ignore IO errors on files
                pass

    return render_template('main.html', data=gpslogfiles)

@app.route('/route/<name>')
def showroute(name):
    bounds = None
    glog = gps.TrackerGPS()
    filt = False

    try:
        if request.args.get('filter','') == 'y':
            filt = True
    except KeyError:
        pass

    openfile = glog.logdir + '/' + name
    sessions = glog.readsessionlog(openfile, filterrecords=filt)

    # Calculate bounds
    for s in sessions:
        s.mile = round(s.mile, 2)
        s.km = round(s.km,2)
        (s.h, s.m, s.s) = hms(s.secs)
        for log in s.log_items:
            bounds = update_bounds(bounds, log)

    return render_template('route.html', data=sessions, bounds=bounds, key = webconfig['googlekey'])
    
@app.route('/log/')
@app.route('/log/<name>')
def showlog(name = None):
    gpspoints = []
    f = None
    bounds = None
    
    if name is None:
        # Directory listing
        return showmenu() # OR should this redirect?

    glog = gps.TrackerGPS()

    # To Do: Check that this file name is safe
    try:
        f = open(glog.logdir + '/' + name, "r")
    except IOError:
        return "Error"
    s = f.readline()
    while s != "":
        try:                
            glog.data.gps_serial_data = s
            glog.data.commit_data()
            bounds = update_bounds(bounds, glog.data.info)
            gpspoints.append(glog.data.info)
            
        except ValueError:
            # Ignore errors from bad lines
            pass

        s = f.readline()

    f.close()

    return render_template('map.html', data=gpspoints, bounds=bounds,, key = webconfig['googlekey'])


if __name__ == '__main__':
    app.run(webconfig['interface'], webconfig['port'], debug=True)
