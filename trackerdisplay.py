from papirus import Papirus
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

class DisplayError(Exception):
    'Standard error class for PaPiRus display'
    
    def __init__(self, err):
        self.value = err
    def __str__(self):
        return repr(self.value)
    
# NOTE: Be really, really careful renaming this class. There are instance checks in the Screen
# class which assume this class name
class BasicScreen(object):
    'Simple screen display for Screens container'
    
    def __init__(self):
        self.__name = ''
        self.image = None
        self.drawobj = None
        # Set hidden to True to prevent appearing in prev and next calls
        self.hidden = False
        
    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = name

    def enter(self):
        # Do setup to initialise screen.
        # This is called via the Screens class when switching display
        # Derived classes will probably want to call this base method before
        # doing their own processing
        if self.drawobj is None:
            self.drawobj = ImageDraw.Draw(self.image)

    def finish(self):
        # Do any required clean up
        # This is called via the Screens class when switching display
        pass

    def draw(self):
        pass

    def clearScreen(self, colour):
        if self.drawobj is None:
            raise DisplayError("No draw object")

        self.drawobj.rectangle([(0,0),self.image.size], fill = colour)

    # Helper function to create simple text on PaPirus screen
    def writeText(self, t, x, y, size):
        if self.drawobj is None:
            raise DisplayError("No draw object")

        #fnt = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeMono.ttf', size)
        fnt = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', size)
        self.drawobj.text((x,y), t, font=fnt, fill=0)
        
    @staticmethod
    def reverse_word_bytes(w):
        bitval = int(format(w,'016b')[-8:] + format(w, '016b')[:3], 2)
        if (format(bitval, '011b')[0] == '1'):
            bitval -=2048
        return bitval

# NOTE: Be really, really careful renaming this class. There are instance checks in the Screen
# class which assume this class name
class ScreenDisplay(BasicScreen):
    'Implements a single screen and displays content. Derive for custom screen'

    def __init__(self):
        BasicScreen.__init__(self)
        self.last_tick = 0
        self.last_full_refresh = 0
        self.pap = None
        self.do_full_refresh = True # Flag to force full screen update

        # Refresh times can be disabled with -1
        # Refreshes are actually driven by the partial times
        # so at least partial times need setting to enable
        # any refreshes. Make these times match if just full refreshes
        # are wanted.
        # Full refreshes happen on the next partial refresh interval
        self.partial_refresh_time = -1 # disable
        self.full_refresh_time = -1 # disable

    def invalidate(self):
        # Full updates can be driven by self.do_full_refresh attribute
        # This call resets last_tick so either a partial or full is
        # conducted on next tick. This is useful for smaller screen
        # events
        self.last_tick = 0
        
    def tick(self, t):
        # Use this to capture time passed and
        # take action if required. This provides a time slice to the
        # display, although it's up to the display to determine how long
        # it spends processing. Recommendation is quick processing per tick.
        # Longer jobs/processing should be started in a new thread.

        if self.full_refresh_time > 0:
            # Set full refresh flag for next draw call 
            if t - self.last_full_refresh > self.full_refresh_time:
                self.do_full_refresh = True

        if self.partial_refresh_time > 0 or self.do_full_refresh:
            # Work out if a screen refresh is due 
            if t - self.last_tick > self.partial_refresh_time:
                self.last_tick = t
                self.draw() # execute a screen redraw
                self.display() # finally update the display
            
    def enter(self):
        BasicScreen.enter(self)
        self.do_full_refresh = True

    def draw(self):
        # Draw the screen. Override this method for your own
        # class to create the screen. This only prints a basic message on screen
        if self.image is None:
            raise DisplayError("No image")
        if self.drawobj is None:
            raise DisplayError("No draw object")
        if self.pap is None:
            raise DisplayError("No PaPiRus object")

        self.clearScreen(1)
        self.writeText("Tracker", 10, 50, 40)
        
    def display(self):
        # write changes to the screen
        # Called from tick events but will need special calling
        # if refresh is required for other reasons
        self.pap.display(self.image)
        
        if self.do_full_refresh:
            self.last_full_refresh = self.last_tick
            self.pap.update()
            self.do_full_refresh = False
        else:
            self.pap.partial_update()


class Screens(object):
    'Encapsulates all the screens for the tracker application'

    def __init__(self):
        self.screen_list = []
        self.current_screen = -1
        self.pap = Papirus()
        self.image = Image.new('1', self.pap.size, 1)
            
    def registerScreen(self, screen):
        if not isinstance(screen, BasicScreen):
            raise DisplayError("Unsupported screen type")
        screen.image = self.image # copy image to screen
        if isinstance(screen, ScreenDisplay):
            screen.pap = self.pap # reference the Papirus object
        self.screen_list.append(screen)

    def count(self):
        return len(screen_list)

    def getScreen(self, index):
        # index can be a number or a string. Check which it is and return screen
        last_screen = self.current_screen
        if type(index).__name__ == 'str':
            i = 0
            for s in self.screen_list:
                if s.name == index:
                    self.current_screen = i
                    break;
                i += 1
                if i == len(self.screen_list):
                    raise DisplayError("Index not found")
        else:
            if index < 0 or index >= len(self.screen_list):
                raise DisplayError("Index out of range")
            self.current_screen = index

        if last_screen < 0 or last_screen != self.current_screen:
            # This is moving from another different screen
            # Run the finish and entry calls
            # If this is the first run then last screen will be -1
            if last_screen > 0: self.screen_list[last_screen].finish()
            self.screen_list[self.current_screen].enter()
            if isinstance(self.screen_list[self.current_screen], ScreenDisplay):
                self.screen_list[self.current_screen].invalidate()
            
        return self.screen_list[self.current_screen]

    def nextScreen(self):
        s = self.current_screen + 1
        while True:
            if s >= len(self.screen_list):
                s = 0
            # Check the hidden attribute. Skip if set
            try:
                if not self.screen_list[s].hidden or s == self.current_screen:
                    break # stop if not hidden or we return to original screen
                s += 1
            except IndexError:
                raise DisplayError("No screens available")
            

        # Call getScreen so the entry and finish calls are also called
        return self.getScreen(s)

    def prevScreen(self):
        s = self.current_screen - 1
        while True:
            if s < 0:
                s = len(self.screen_list) - 1
                if s <= 0:
                    raise DisplayError("No screens available")
                    
            if not self.screen_list[s].hidden or s == self.current_screen:
                break # stop if not hidden or we return to original screen
            s -= 1

        # Call getScreen so the entry and finish calls are also called
        return self.getScreen(s)

    def currentScreen(self):
        if self.current_screen < 0:
            raise DisplayError("No screens can be found")
        return self.screen_list[self.current_screen]
