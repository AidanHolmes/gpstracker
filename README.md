# Raspberry Pi with PaPiRus e-ink, LiPo battery and GPS module

This code captures and manages GPS status, log files and system status.
Data summeries are provided to a PaPiRus e-ink screen and maps are hosted from a web server.

There are a few dependencies to create a GPS tracking device.
Minimal dependencies are:
* GPS device connected to a running gpsd
* 2x GPIO connected buttons (the pins are configurable)
* Sparkfun LiPo battery charger connected to the I2C bus

Software dependencies:
* apt-get install libfuse-dev
* apt-get install fonts-freefont-ttf
* git clone https://github.com/repaper/gratis.git
* git clone https://github.com/PiSupply/PaPiRus.git

Strictly speaking the LiPo charger can be left out, but the code assumes it is there and will show a flat battery.
Note that connecting a serial GPS device to the UART pins will stop the PiPyRus screen from working (if configured to use alternative GPIO pins).
The only fix is to isolate the UART pins from the PaPiRus whilst still allowing the GPS device to connect.
My build can be seen at http://orbitalfruit.blogspot.co.uk/2016/08/papirus-gps.html

Full setup of the PaPiRus can be seen here http://orbitalfruit.blogspot.co.uk/2016/02/papirus-e-ink-display.html
There's some setup to perform to get the e-ink libraries and drivers setup. Code should work without any fixes so ignore any advice to update code.

# Running

Clone the code to a separate folder.
Check the config.py and change any settings. The web interface requires a Google API key

Main Application
> python gpstracker/tracker.py &

Flask Web Application
> python gpstracker/web.py &

The app should run in the background. Add to /etc/rc.local to run on start up.

# Buttons
There are 2 buttons. One is called the Power button and the other the Run button.
They do a bit more than this but for simplicity they will be referred to as this.
## Power button
If pressed briefly this will change the screen (see screens below).
When held this will shutdown the Raspberry Pi with a 'shutdown -h now' command and the power off screen will display.
The indicator GPIO pin will be high when the application is running. It will strobe low-high when shutting down and then turn off.
## Run button
This changes a sub screen if one exists. See the description of screens below.
If held this will enable the GPS tracking and set the indicator GPIO pin high (see config.py)

# Screens

## Status bar
Most screens show GPS status and battery charge.
When GPS is enabled a dish symbol appears, otherwise "GPS Disabled" appears.
GPS takes time to lock on. A 2 or 3 symbol appears when a lock has been made.
If the application is recording location then a walking person symbol appears on the screen. 

## First screen
The first screen shows a summary of the logged data for the day.
All log files assume 1 days worth of data and starts a new log after midnight.
Multiple sessions can exist in a day. Sessions are started when the GPS is enabled and locked to a signal.
Change config.py to specify imperial or metric measurements on the screen.
Press the run button briefly to change the sub screen
### Split time per mile/km
Shows the last 5 miles/km and time taken to complete each one
### Miles/km per hour
Shows the last 5 hours and distance travelled in miles or km

## GPS screen
This enables the GPS but doesn't enable logging.
### GPS detail
First sub screen shows GPS longitude, latitude, time and OS landranger coordinates.
### More GPS detail
The second sub screen shows more GPS info
### Satellites
The third screen shows number of satellites and the count of satellites in use

## System screen
This is a single screen and omits the status bar.
System information is shown here. If there's a network connection to the Pi then it will be shown here. This is fairly useful if you have a dynamic IP allocated to the pi.

## Low power screen
When this is shown all the button indicators are pulled low. The screen refresh is set to be very low but will still refresh to update battery and show GPS status (if enabled).
Press the Power button to exit this screen and restore the indicator buttons.
It extends battery life a small amount and could give up to 45 min extra for a 1000mAh battery.

# Web interface
Configuration in config.py will control the interface and port to run on.
This uses Flask and isn't as good as an Apache server, but does the job.

Logs are read from the appconfig location in config.py.

## Root web page
Shows a list of all logs. Click on each one to see a map and sessions logged

## Map view
This shows a Google map with the GPS points and start/end pins.
There's one line per session.
Click on the line or the end pin to see some summary information. 