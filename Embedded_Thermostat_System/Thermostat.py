# Developer: Justin Carlo Florida
#
# Thermostat - This is the Python code used to demonstrate
# the functionality of the thermostat that we have prototyped throughout
# the course. 
#
# This code works with the test circuit that was built for module 7.
#
# Functionality:
#
# The thermostat has three states: off, heat, cool
#
# The lights will represent the state that the thermostat is in.
#
# If the thermostat is set to off, the lights will both be off.
#
# If the thermostat is set to heat, the Red LED will be fading in 
# and out if the current temperature is below the set temperature;
# otherwise, the Red LED will be on solid.
#
# If the thermostat is set to cool, the Blue LED will be fading in 
# and out if the current temperature is above the set temperature;
# otherwise, the Blue LED will be on solid.
#
# One button will cycle through the three states of the thermostat.
#
# One button will raise the setpoint by a degree.
#
# One button will lower the setpoint by a degree.
#
# The LCD display will display the date and time on one line and
# alternate the second line between the current temperature and 
# the state of the thermostat along with its set temperature.
#
# The Thermostat will send a status update to the TemperatureServer
# over the serial port every 30 seconds in a comma delimited string
# including the state of the thermostat, the current temperature
# in degrees Fahrenheit, and the setpoint of the thermostat.
#
#------------------------------------------------------------------
# Change History
#------------------------------------------------------------------
# Version   |   Description
#------------------------------------------------------------------
#    1          Initial Development
#    2          Thermostat functionality, GPIO mapping, UART, and cleanup
#------------------------------------------------------------------


##
## Import necessary to provide timing in the main loop
## and to obtain the current date and time.
##
from datetime import datetime

##
## Events, locks, and threads keep the display updates responsive
## while the three buttons continue to accept input.
##
from threading import Event, RLock, Thread
from time import monotonic, sleep

##
## Imports necessary to provide connectivity to the
## thermostat sensor and the I2C bus.
##
import board
import adafruit_ahtx0

##
## These are the packages that we need to pull in so that we can work
## with the GPIO interface on the Raspberry Pi board and work with
## the 16x2 LCD display
##
# import board - already imported for I2C connectivity
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd

## This imports the Python serial package to handle communications over the
## Raspberry Pi's serial port. 
import serial

##
## Imports required to handle the Button and PWMLED devices.
##
from gpiozero import Button, PWMLED

##
## Imports required to build the thermostat state machine.
##
from statemachine import State, StateMachine

##
## DEBUG flag - print status messages on the console.
##
DEBUG = True
SERIAL_PORT = "/dev/ttyS0"  # UART device; confirm availability on the Pi.
BAUD_RATE = 115200

##
## Create an I2C instance to communicate with connected devices.
## Initialize the AHT20 temperature and humidity sensor.
## The red and blue LEDs use GPIO 18 and GPIO 23.
##
i2c = board.I2C()
thSensor = adafruit_ahtx0.AHTx0(i2c)
redLight = PWMLED(18)
blueLight = PWMLED(23)


##
## ManagedDisplay - Class intended to manage the 16x2 
## Display
##
## This code is largely taken from the work done in module 4, and
## converted into a class so that we can more easily consume the 
## operational capabilities.
##
class ManagedDisplay:
    """Own and safely release all six 16x2 LCD GPIO lines."""

    ##
    ## Class Initialization method to setup the display
    ##
    def __init__(self):
        # Match the original Module Four LCD wiring.
        self.lcd_rs = digitalio.DigitalInOut(board.D17)
        self.lcd_en = digitalio.DigitalInOut(board.D27)
        self.lcd_d4 = digitalio.DigitalInOut(board.D5)
        self.lcd_d5 = digitalio.DigitalInOut(board.D6)
        self.lcd_d6 = digitalio.DigitalInOut(board.D13)
        self.lcd_d7 = digitalio.DigitalInOut(board.D26)
        self.lcd = characterlcd.Character_LCD_Mono(
            self.lcd_rs, self.lcd_en,
            self.lcd_d4, self.lcd_d5, self.lcd_d6, self.lcd_d7,
            16, 2,
        )
        self.lcd.clear()

    ##
    ## updateScreen - Convenience method used to update the message.
    ##
    def updateScreen(self, message):
        self.lcd.clear()
        self.lcd.message = message

    ##
    ## cleanupDisplay - Method used to cleanup the digitalIO lines that
    ## are used to run the display.
    ##
    def cleanupDisplay(self):
        try:
            self.lcd.clear()
        finally:
            for pin in (self.lcd_rs, self.lcd_en, self.lcd_d4,
                        self.lcd_d5, self.lcd_d6, self.lcd_d7):
                pin.deinit()


##
## TemperatureMachine - This is our StateMachine implementation class.
## The purpose of this state machine is to manage the three states
## handled by our thermostat:
##
##  off
##  heat
##  cool
##
##
class TemperatureMachine(StateMachine):
    """Thermostat modes and the temperature-controlled status LEDs."""

    off = State(initial=True)
    heat = State()
    cool = State()
    cycle = off.to(heat) | heat.to(cool) | cool.to(off)

    def __init__(self):
        ##
        ## The default set point is 72 degrees Fahrenheit.
        ##
        self.setPoint = 72  # Required initial set point, in Fahrenheit.
        ##
        ## Prevent button events and display updates from changing
        ## shared hardware state at the same time.
        ##
        self.io_lock = RLock()  # Protect state, sensor, and LED operations across threads.
        ##
        ## The stop event lets the LCD thread exit without a long delay.
        ##
        self.stop_event = Event()
        self.display_thread = None
        # Track the LED pattern so the PWM fade is not restarted every second.
        self._last_light_action = None
        super().__init__()

    ##
    ## on_enter_heat - Action performed when the state machine transitions
    ## into the 'heat' state
    ##
    def on_enter_heat(self):
        if DEBUG:
            print("* Changing state to HEAT")
        self.updateLights()

    ##
    ## on_exit_heat - Action performed when the statemachine transitions
    ## out of the 'heat' state.
    ##
    def on_exit_heat(self):
        redLight.off()
        self._last_light_action = None


    ##
    ## on_enter_cool - Action performed when the state machine transitions
    ## into the 'cool' state
    ##
    def on_enter_cool(self):
        if DEBUG:
            print("* Changing state to COOL")
        self.updateLights()


    ##
    ## on_exit_cool - Action performed when the statemachine transitions
    ## out of the 'cool' state.
    ##
    def on_exit_cool(self):
        blueLight.off()
        self._last_light_action = None


    ##
    ## on_enter_off - Action performed when the state machine transitions
    ## into the 'off' state
    ##
    def on_enter_off(self):
        redLight.off()
        blueLight.off()
        self._last_light_action = ("off", "off")
        if DEBUG:
            print("* Changing state to OFF")


    ##
    ## processTempStateButton - Utility method used to send events to the 
    ## state machine. This is triggered by the button_pressed event
    ## handler for our first button
    ##
    def processTempStateButton(self):
        # GPIO Zero runs this callback whenever the green button is pressed.
        with self.io_lock:
            self.cycle()
            if DEBUG:
                print(f"Mode: {self.current_state.id}")


    ##
    ## processTempIncButton - Utility method used to update the 
    ## setPoint for the temperature. This will increase the setPoint
    ## by a single degree. This is triggered by the button_pressed event
    ## handler for our second button
    ##
    def processTempIncButton(self):
        with self.io_lock:
            self.setPoint += 1
            print(f"Set point increased to {self.setPoint} F")
            self.updateLights()


    ##
    ## processTempDecButton - Utility method used to update the 
    ## setPoint for the temperature. This will decrease the setPoint
    ## by a single degree. This is triggered by the button_pressed event
    ## handler for our third button
    ##
    def processTempDecButton(self):
        with self.io_lock:
            self.setPoint -= 1
            print(f"Set point decreased to {self.setPoint} F")
            self.updateLights()

    ##
    ## Get the temperature in Fahrenheit
    ##
    def getFahrenheit(self):
        """AHT20 returns Celsius; convert the reading to Fahrenheit."""
        return (thSensor.temperature * 9.0 / 5.0) + 32.0


    ##
    ## updateLights - Utility method to update the LED indicators on the 
    ## Thermostat
    ##
    def updateLights(self, temperature=None):
        """Fade while calling for heat/cool; stay solid at the target."""
        with self.io_lock:
            if temperature is None:
                temperature = self.getFahrenheit()
            state = self.current_state.id
            if state == "heat":
                action = (state, "fade" if temperature < self.setPoint else "solid")
            elif state == "cool":
                action = (state, "fade" if temperature > self.setPoint else "solid")
            else:
                action = ("off", "off")

            # Don't restart pulse() every second, which would spoil the fade effect.
            if action == self._last_light_action:
                return
            redLight.off()
            blueLight.off()
            if action == ("heat", "fade"):
                redLight.pulse(fade_in_time=1, fade_out_time=1, background=True)
            elif action == ("heat", "solid"):
                redLight.on()
            elif action == ("cool", "fade"):
                blueLight.pulse(fade_in_time=1, fade_out_time=1, background=True)
            elif action == ("cool", "solid"):
                blueLight.on()
            self._last_light_action = action
            if DEBUG:
                print(f"LEDs: {action[0]} / {action[1]}; "
                      f"current={temperature:.1f} F; set={self.setPoint} F")


    ##
    ##  Configure output string for the Thermostat Server
    ##
    def setupSerialOutput(self, temperature=None):
        """Return required comma-delimited state,temp,setpoint string."""
        with self.io_lock:
            if temperature is None:
                temperature = self.getFahrenheit()
            return f"{self.current_state.id},{temperature:.1f},{self.setPoint}"

    ##
    ## run - kickoff the display management functionality of the thermostat
    ##
    def run(self):
        self.display_thread = Thread(target=self.manageMyDisplay, name="thermostat-display")
        self.display_thread.start()

    ##
    ##  This function is designed to manage the LCD Display
    ##
    def manageMyDisplay(self):
        """Refresh the LCD and LEDs every second; send UART every 30 seconds."""
        start = monotonic()
        last_serial = start
        while not self.stop_event.is_set():
            try:
                with self.io_lock:
                    temp = self.getFahrenheit()
                    self.updateLights(temp)
                    state = self.current_state.id
                    set_point = self.setPoint

                    # 16 characters maximum on each LCD line.
                    lcd_line_1 = datetime.now().strftime("%m/%d %I:%M:%S%p")
                    if int(monotonic() - start) % 10 < 5:
                        lcd_line_2 = f"Temp: {temp:.1f} F"
                    else:
                        lcd_line_2 = f"{state.upper()} Set: {set_point} F"
                    screen.updateScreen(f"{lcd_line_1[:16]}\n{lcd_line_2[:16]}")

                    now = monotonic()
                    if now - last_serial >= 30:
                        output = self.setupSerialOutput(temp)
                        ser.write((output + "\n").encode("ascii"))
                        ser.flush()
                        if DEBUG:
                            print("UART sent:", output)
                        last_serial = now
            except Exception as exc:
                print(f"Thermostat display/sensor/UART error: {exc}")
                self.stop_event.set()
                break
            # Wait can be interrupted immediately when Ctrl+C triggers shutdown.
            self.stop_event.wait(1)

    def stop(self):
        self.stop_event.set()
        if self.display_thread is not None:
            self.display_thread.join(timeout=3)


def main():
    global ser, screen
    ser = None
    screen = None
    buttons = []
    tsm = None
    try:
        ## Configure the serial port for UART output at 115200 baud.
        ser = serial.Serial(
            port=SERIAL_PORT, baudrate=BAUD_RATE,
            parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS, timeout=1,
        )
        screen = ManagedDisplay()
        tsm = TemperatureMachine()
        tsm.updateLights()  # Start with both status LEDs off.

        ##
        ## The green button cycles the thermostat state using GPIO 24.
        ## The red button increases the set point using GPIO 12.
        ## The blue button decreases the set point using GPIO 25.
        ## These GPIO numbers match the tested physical button wiring.
        ##
        greenButton = Button(24, bounce_time=0.1)
        redButton = Button(12, bounce_time=0.1)
        blueButton = Button(25, bounce_time=0.1)
        buttons = [greenButton, redButton, blueButton]
        greenButton.when_pressed = tsm.processTempStateButton
        redButton.when_pressed = tsm.processTempIncButton
        blueButton.when_pressed = tsm.processTempDecButton

        print("Thermostat running; initial set point is 72 F. Press Ctrl+C to stop.")
        tsm.run()
        while not tsm.stop_event.is_set():
            sleep(0.2)
    except KeyboardInterrupt:
        print("Stopping thermostat...")
    finally:
        ## Stop button events and the LCD thread before releasing GPIO resources.
        for button in buttons:
            button.when_pressed = None
        if tsm is not None:
            tsm.stop()
        for button in buttons:
            button.close()
        if screen is not None:
            screen.cleanupDisplay()
        redLight.off()
        blueLight.off()
        redLight.close()
        blueLight.close()
        if ser is not None and ser.is_open:
            ser.close()
        if hasattr(i2c, "deinit"):
            i2c.deinit()
        print("Cleanup complete.")


if __name__ == "__main__":
    main()
