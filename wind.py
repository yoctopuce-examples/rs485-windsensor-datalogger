#!/usr/bin/python
# -*- coding: utf-8 -*-
from yocto_api import *

# IP adresse of the VirtualHub or YoctoHub with the sensor
SensorHub = "127.0.0.1"

# logical name of the genericSensor with the wind speed [m/s]
WindSpeedSensorName = "Speed"

# logical name of the genericSensor with the wind direction [deg]
WindDirSensorName = "Direction"

# fdate/time display formet
def formatTime(timestampUTC):
    return datetime.datetime.fromtimestamp(timestampUTC).strftime("%d-%m-%Y %H:%M:%S.%f")[:-4]

# export file naming pattern
def exportName(timestampUTC):
    return datetime.datetime.fromtimestamp(timestampUTC).strftime("Wind Gill %d-%m-%Y.csv")

#############################################################
#                                                           #
#       Export data for one specific day                    #
#                                                           #
#############################################################

def exportData(day, speedSensor, dirSensor):
    # export data for 24h starting with the selected data
    dayStr = datetime.datetime.fromtimestamp(day).strftime("%d-%m-%Y")
    speedSet = speedSensor.get_recordedData(day, day+86400)
    dirSet = dirSensor.get_recordedData(day, day+86400)

    # 1. Load data from the device datalogger (flash memory)
    print("Loading speed data     :   0%", end='')
    progress = 0
    while progress < 100:
        progress = speedSet.loadMore()
        print("\b\b\b\b{0:3d}%".format(progress), end='', flush=True)
    spdMeasures = speedSet.get_measures()
    print("\b\b\b\b{0:d} mesures chargées".format(len(spdMeasures)))
    print("Loading direction data :   0%", end='')
    progress = 0
    while progress < 100:
        progress = dirSet.loadMore()
        print("\b\b\b\b{0:3d}%".format(progress), end='', flush=True)
    dirMeasures = dirSet.get_measures()
    print("\b\b\b\b{0:d} measurements loaded".format(len(dirMeasures)))
    if len(spdMeasures) == 0 or len(spdMeasures) == 0:
        print("*** Sorry, missing essential data !")
        return
    spdStartStamp = spdMeasures[0].get_startTimeUTC()
    spdEndStamp = spdMeasures[-1].get_endTimeUTC()    
    dirStartStamp = dirMeasures[0].get_startTimeUTC()
    dirEndStamp = dirMeasures[-1].get_endTimeUTC()
    print("Wind speed data available from {0:s} to {1:s}".format(
        datetime.datetime.fromtimestamp(spdStartStamp).strftime("%H:%M:%S"),
        datetime.datetime.fromtimestamp(spdEndStamp).strftime("%H:%M:%S")))
    print("Direction data available from {0:s} to {1:s}".format(
        datetime.datetime.fromtimestamp(dirStartStamp).strftime("%H:%M:%S"),
        datetime.datetime.fromtimestamp(dirEndStamp).strftime("%H:%M:%S")))
    startStamp = min(spdStartStamp,dirStartStamp)
    endStamp = max(spdEndStamp,dirEndStamp)

    # 2. Create the measure table by increments of 0.25s with sliding averages
    print("Calculation of rolling averages :   0%", end='')
    qStart = round(4 * startStamp)
    qEnd = round(4 * endStamp)
    spdIdx = 0
    dirIdx = 0
    currSpd = None
    currDir = None
    avgPer = [ 2, 4, 8, 10, 3*4, 60*4, 2*60*4, 5*60*4, 10*60*4 ]
    # Results are stored by column:
    # 0=time, 1=measured speed, 2=measured direction, 3=current veocity, 4=vector-x, 5=vector-y
    # 6=speed averaged over 0.5s, 7=direction averaged over 0.5s, etc.
    columns = [ None ] * (6 + 2*len(avgPer))
    for c in range(len(columns)):
        columns[c] = [ '' ] * (qEnd - qStart)
    columns[3] = [ None ] * (qEnd - qStart)
    resIdx = 0
    firstIdx = None
    maxIdx = 0
    maxPer = [ None ] * len(avgPer)
    for qSec in range(qStart, qEnd):
        # add next timestamp to the table, and one line for each column
        stamp = qSec / 4
        columns[0][resIdx] = formatTime(stamp)
        # add measures for this specific time, if we have them
        while spdIdx < len(spdMeasures) and spdMeasures[spdIdx].get_startTimeUTC() <= stamp:
            nextSpd = spdMeasures[spdIdx].get_averageValue()
            if nextSpd >= 0:
                columns[1][resIdx] = nextSpd
                currSpd = nextSpd
            spdIdx += 1
        while dirIdx < len(dirMeasures) and dirMeasures[dirIdx].get_startTimeUTC() <= stamp:
            nextDir = dirMeasures[dirIdx].get_averageValue()
            if nextDir >= 0:
                columns[2][resIdx] = nextDir
                currDir = math.radians(nextDir)
            dirIdx += 1
        if currSpd is not None and \
            (columns[1][maxIdx] == '' or currSpd > columns[1][maxIdx]): 
            maxIdx = resIdx
        if currSpd is not None and currDir is not None:
            # if we have both speed and direction, compute sliding average
            # (including the average vector by projection on axis)
            columns[3][resIdx] = currSpd
            if currSpd >= 0.05:
                columns[4][resIdx] = currSpd * math.cos(currDir)
                columns[5][resIdx] = currSpd * math.sin(currDir)
            else:
                columns[4][resIdx] = 0.0
                columns[5][resIdx] = 0.0
            if firstIdx is None:
                firstIdx = resIdx
            for av in range(len(avgPer)):
                period = avgPer[av]
                if resIdx+1 < period: continue
                if columns[3][resIdx-period+1] is None: continue
                col = 6 + 2*av
                columns[col][resIdx] = round(sum(columns[3][resIdx-period+1:resIdx+1])/period, 4)
                sumx = sum(columns[4][resIdx-period+1:resIdx+1])
                sumy = sum(columns[5][resIdx-period+1:resIdx+1])
                if sumy == 0 and sumx == 0:
                    columns[col+1][resIdx] = columns[col+1][resIdx-1]
                else:
                    angle = math.degrees(math.atan2(sumy, sumx))
                    if angle < 0:
                        angle += 360
                    columns[col+1][resIdx] = round(angle, 1)
                # remember max index for each column
                if maxPer[av] is None:
                    maxPer[av] = resIdx
                elif columns[col][resIdx] > columns[col][maxPer[av]]:
                    maxPer[av] = resIdx
        resIdx += 1
        if (resIdx & 511) == 0:
            print("\b\b\b\b{0:3d}%".format(round(100*resIdx/(qEnd-qStart))), end='', flush=True)
    avg24 = round(sum(columns[3][firstIdx:]) / (len(columns[3]) - firstIdx), 4)
    sumx = sum(columns[4][firstIdx:])
    sumy = sum(columns[5][firstIdx:])
    dir24 = round(math.degrees(math.atan2(sumy, sumx)), 1)
    if dir24 < 0:
        dir24 += 360
    print("\b\b\b\bDone !")
    # format maxima nicely
    maxima = [ ['Max over 0.25s', columns[3][maxIdx], columns[2][maxIdx], columns[0][maxIdx] ] ]
    headers1 = '"";"measure";"measure";"wind NS";"wind WE"'
    headers2 = '"time";"[m/s]";"[deg]";"[m/s]";"[m/s]"'
    for av in range(len(avgPer)):
        period = avgPer[av] / 4
        if period < 60:
            pstr = "{0}s".format(period)
        else:
            pstr = "{0:d}min".format(round(period/60))
        avgMaxIdx = maxPer[av]
        if avgMaxIdx is not None:
            col = 6 + 2 * av
            maxima.append([ "Max over "+pstr, columns[col][avgMaxIdx], columns[col+1][avgMaxIdx], columns[0][avgMaxIdx] ])
            headers1 += ';"'+pstr+'";"'+pstr+'"'
            headers2 += ';"[m/s]";"[deg]"'
    maxima.append(["Global average", avg24, dir24, dayStr])
    # affiche les résultats
    for m in maxima:
        if m[1] is None or m[1] == '':
            print("{0} : Missing speed data!".format(m[0]))
        else:
            print("{0} : {1:.3f} m/s ({2:.3f} km/h) à {3:.1f} deg le {4}".format(m[0], m[1], m[1]*3.6, m[2], m[3]))
    # sauve les résultats dans un fichier CSV
    filename = exportName(day)
    with open(filename, 'w') as file:
        file.write('"Wind measurements on ";"'+dayStr+'";;;\n')
        file.write(';;;;\n')
        file.write(';"max [m/s]";"max [km/h]";"[deg]";"heure"\n')
        for m in maxima:
            if m[1] is None or m[1] == '':
                print("{0} : Missing speed data!".format(m[0]))
            else:
                file.write('"{0}";{1:.3f};{2:.3f};{3:.1f};{4}\n'.format(m[0], m[1], m[1]*3.6, m[2], m[3]))
        file.write(';;;;\n')
        file.write(headers1+"\n")
        file.write(headers2)
        for r in range(len(columns[0])):
            if columns[4][r] == '':
                file.write('\n"{0}";{1};{2};;'.format(columns[0][r],columns[1][r],columns[2][r]))
            else:
                file.write('\n"{0}";{1};{2};{3:.4f};{4:.4f}'.format(columns[0][r],columns[1][r],columns[2][r],
                                                                    columns[4][r],columns[5][r]))
            for av in range(len(avgPer)):
                col = 6 + 2 * av
                file.write(';{0};{1}'.format(columns[col][r], columns[col+1][r]))
        file.write('\n')
    print("File "+filename+" created\n")


#############################################################
#                                                           #
#                Program entry point                        #
#                                                           #
#############################################################

# 1. Search for the sensor
errmsg = YRefParam()
if YAPI.RegisterHub(SensorHub, errmsg) != YAPI.SUCCESS:
    sys.exit("No connection with (Virtual)Hub "+SensorHub+": " + errmsg.value)
speedSensor = YSensor.FindSensor(WindSpeedSensorName)
dirSensor = YSensor.FindSensor(WindDirSensorName)
if not speedSensor.isOnline():
    sys.exit("Cannot find sensor named '" + WindSpeedSensorName + "' (check USB cable !)")
if not dirSensor.isOnline():
    sys.exit("Cannot find sensor named '" + WindDirSensorName + "' (check USB cable !)")

# 2. Search for data on the sensor (max last 5 days)
print("Search for available data...")
fullset = speedSensor.get_recordedData(0, 0)
fullset.loadMore()
summary = fullset.get_summary()
start = summary.get_startTimeUTC()
end = summary.get_endTimeUTC()
while True:
    if end > start:
        print("Data available from "+formatTime(start)+" to "+formatTime(end))
    else:
        print("Sorry, no data found on wind sensor !")
        break
    today = math.floor(time.time() / 86400) * 86400
    for j in range(1,5):
        jday = today - j * 86400
        if jday >= start and jday+86400 <= end:
            print("- Type "+str(j)+" to export data for day D-"+str(j))
    print("- Type Q to exit")
    cmd = input("Your choice : ")
    if cmd == 'Q' or cmd == 'q': break
    if cmd >= '0' and cmd <= '9':
        j = int(cmd)
        jday = today - j * 86400
        exportData(jday, speedSensor, dirSensor)

YAPI.FreeAPI()
