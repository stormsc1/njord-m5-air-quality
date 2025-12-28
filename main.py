# NJORD CO2 Monitor Application
#
# Relecvant docs:
# - M5Stack CO2 Unit: https://uiflow-micropython.readthedocs.io/en/latest/units/co2.html
#
# Architecture:
# Try to keep tasks separated to allow easy tweaking for their rates and priorities.

import asyncio
import os, sys, io
import M5
from M5 import *
import m5ui
import lvgl as lv
from hardware import Pin
from hardware import I2C
from unit import CO2Unit


UI_UPDATE_RATE_MS = 20  # UI update rate
CO2_POLL_RATE_MS = 1000  # CO2 sensor polling rate


dashboard = None
label_address = None
label_ppm = None
label_humidity = None
label_temperature = None
label_level = None

i2c0 = None
co2 = None

co2_levels = [
    {
        "level": "Excellent",
        "min_ppm": 0,
        "max_ppm": 500,
        "color": lv.color_hex(0x43c44f),
        "description": "Typical outdoor CO₂ levels."
    },
    {
        "level": "Good",
        "min_ppm": 500,
        "max_ppm": 700,
        "color": lv.color_hex(0x43c44f),
        "description": "Normal indoor air quality."
    },
    {
        "level": "Acceptable",
        "min_ppm": 700,
        "max_ppm": 1000,
        "color": lv.color_hex(0xd6c831),
        "description": "Acceptable indoor air quality; minor discomfort possible."
    },
    {
        "level": "Poor",
        "min_ppm": 1000,
        "max_ppm": 1500,
        "color": lv.color_hex(0xd68131),
        "description": "Reduced concentration and drowsiness. Ventilation recommended."
    },
    {
        "level": "Bad",
        "min_ppm": 1500,
        "max_ppm": float("inf"),
        "color": lv.color_hex(0xd63131),
        "description": "Ventilation required. Headaches, sleepiness, and stale air."
    }
]

def get_co2_level(ppm):
    for level in co2_levels:
        if level["min_ppm"] <= ppm < level["max_ppm"]:
            return level
    return None

async def ui_task():
    print("UI task started")
    while True:
        M5.update()
        await asyncio.sleep_ms(UI_UPDATE_RATE_MS)

async def co2_task():
    global i2c0, co2, label_ppm, label_humidity, label_temperature, label_level

    print("CO2 task started")

    # initialize CO2 unit
    # see: https://uiflow-micropython.readthedocs.io/en/latest/units/co2.html
    i2c0 = I2C(0, scl=Pin(1), sda=Pin(2), freq=100000)
    co2 = CO2Unit(i2c0)
    # stop potentially previously started measurement (this is not done in the py docs)
    # see: https://github.com/m5stack/M5Unit-ENV/blob/master/examples/Unit_CO2_M5Core/Unit_CO2_M5Core.ino
    co2.set_stop_periodic_measurement()
    co2.set_start_periodic_measurement()
    # see also `set_start_low_periodic_measurement` which "sets sensor into low power working mode, with 
    # about 30 seconds per measurement"

    while True:
        if co2.is_data_ready():
            ppm = co2.co2
            level = get_co2_level(ppm)

            print("CO2: {} ppm, Level: {}".format(ppm, level["level"]))

            label_ppm.set_text(str(ppm) + " ppm")
            label_ppm.set_text_color(
                level["color"], 255, lv.PART.MAIN | lv.STATE.DEFAULT
            )

            label_level.set_text(level["level"])
            label_level.set_text_color(
                level["color"], 255, lv.PART.MAIN | lv.STATE.DEFAULT
            )

            label_temperature.set_text(str(co2.temperature) + " °C")
            label_temperature.set_text_color(
                level["color"], 255, lv.PART.MAIN | lv.STATE.DEFAULT
            )

            label_humidity.set_text(str(co2.humidity) + " %")
            label_humidity.set_text_color(
                level["color"], 255, lv.PART.MAIN | lv.STATE.DEFAULT
            )


        await asyncio.sleep_ms(CO2_POLL_RATE_MS)  # sensor rate

async def main():
  global dashboard, label_address, label_ppm, label_temperature, label_humidity, label_level, i2c0, co2

  M5.begin()
  Widgets.setRotation(1)
  m5ui.init()
  dashboard = m5ui.M5Page(bg_c=0x000000)
  label_address = m5ui.M5Label("255.255.255.255", x=9, y=217, text_c=0xffffff, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=dashboard)
  label_ppm = m5ui.M5Label("ppm", x=140, y=106, text_c=0xffffff, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_24, parent=dashboard)
  label_level = m5ui.M5Label("level", x=143, y=132, text_c=0xffffff, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_16, parent=dashboard)
  label_temperature = m5ui.M5Label("temperature", x=140, y=160, text_c=0xffffff, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_16, parent=dashboard)
  label_humidity = m5ui.M5Label("humidity", x=140, y=186, text_c=0xffffff, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_16, parent=dashboard)
  dashboard.screen_load()
    
  asyncio.create_task(ui_task())
  asyncio.create_task(co2_task())

  while True: 
    await asyncio.sleep_ms(10000) # keep main alive

if __name__ == '__main__':
  try:
    asyncio.run(main())
  except (asyncio.CancelledError, KeyboardInterrupt) as e:
    m5ui.deinit()
    from utility import print_error_msg
    print_error_msg(e)
  except ImportError:
    print("please update to latest firmware")
  finally:
    pass