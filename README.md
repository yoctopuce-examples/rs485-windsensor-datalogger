# Wind speed measurements

The aim of this example is to collect data measured by a Gill WindSonic ultrasonic wind sensor, and extract key values in accordance with World Meteorological Organization (WMO) standards.

The wind sensor provides wind speed and direction measurements at 4 Hz. These are read out in real time via an RS-485 bus by a specialized device, an Observator OMC-139 display.

In order to add recording capabilities, weadd to the RS-485 bus, in parallel with the display, a Yoctopuce module that listens to the measurements and stores them in its internal memory. Once a day, a small script downloads the measurements from the data logger and calculates the relevant averages and maxima. The script produces a CSV file that can be opened in Excel, for example, including all measured and calculated values to attest to the figures produced.

Read the full article on our web site: https://www.yoctopuce.com/EN/article/wind-speed-measurements
