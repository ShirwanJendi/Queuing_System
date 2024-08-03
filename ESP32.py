from machine import Pin, I2C, unique_id, reset
import time
import ubinascii
from umqtt.simple import MQTTClient
from lcd_i2c import LCD

# MQTT configuration
mqtt_server = 'elab.local'
client_id = ubinascii.hexlify(unique_id()).decode('utf-8')
topic_pub = b'esp32/button'

# I2C configuration for the LCD
I2C_ADDR = 0x27  # I2C address of the 2004A LCD
NUM_ROWS = 4
NUM_COLS = 20

# Setup I2C interface for the LCD
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=800000)
lcd = LCD(addr=I2C_ADDR, cols=NUM_COLS, rows=NUM_ROWS, i2c=i2c)
lcd.begin()

# Set up button
button = Pin(18, Pin.IN, Pin.PULL_UP)

# Connect to MQTT broker
def connect_mqtt():
    client = MQTTClient(client_id, mqtt_server)
    try:
        client.connect()
        print('Connected to %s MQTT broker' % mqtt_server)
        
        # Display "Connected to MQTT" on the LCD
        lcd.clear()
        lcd.set_cursor(0, 1)  # Centered vertically on the screen
        lcd.print(center_text("Connected to MQTT", NUM_COLS))
        
        # Keep the message displayed for 20 seconds
        time.sleep(20)
        lcd.clear()
        
        return client
    except OSError as e:
        print('Failed to connect to MQTT broker. Reconnecting...')
        time.sleep(5)
        reset()

# Center the text on the line
def center_text(text, width):
    if len(text) < width:
        padding = (width - len(text)) // 2
        return ' ' * padding + text + ' ' * padding
    else:
        return text

# Publish the next number to the MQTT topic and display it on the LCD
current_number = 1

def publish(client):
    global current_number
    value = str(current_number)
    print('Publishing: %s' % value)
    client.publish(topic_pub, value)
    
    # Display the value on the LCD
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.print("Your number:")
    
    centered_value = center_text(value, NUM_COLS)
    lcd.set_cursor(0, 2)  # Leave one line space between the two lines
    lcd.print(centered_value)

    # Clear the LCD after 10 seconds
    time.sleep(10)
    lcd.clear()
    
    # Increment the number and reset to 1 if it exceeds 100
    current_number += 1
    if current_number > 100:
        current_number = 1

# Main loop
def main():
    client = connect_mqtt()
    button_pressed = False

    while True:
        if button.value() == 0 and not button_pressed:
            button_pressed = True
            time.sleep(0.05)  # debounce delay
            if button.value() == 0:
                publish(client)
        elif button.value() == 1 and button_pressed:
            button_pressed = False

if __name__ == '__main__':
    main()

