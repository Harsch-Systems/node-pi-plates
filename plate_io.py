import sys
import json

# All Pi Plate communication must go through this one process to ensure
# SPI communications don't overlap / interfere and corrupt the device state(s)
#
# listen for json messages on stdin of the format:
# {
#   addr: <pi plate address 0-7>,
#   plate_type: <RELAY|DAQC>,
#   cmd: <command string>, args: {<command-specific args>}
# }

# The following functions are (mostly) shared by all plate types,
# though some vary in args and output type (see differences inline)
common_funcs = ['setLED', 'clrLED', 'toggleLED', 'getLED', 'getID', 'getFWrev',
                'getHWrev', 'getVersion', 'getADDR', 'RESET', 'VERIFY']


def common_handler(PP, plate_type, addr, cmd, args):
    result = {}
    if (cmd == "getID"):
        result['ID'] = PP.getID(addr)
    elif (cmd == "getFWrev"):
        result['FWrev'] = PP.getFWrev(addr)
    elif (cmd == "getHWrev"):
        result['HWrev'] = PP.getHWrev(addr)
    elif (cmd == "getVersion"):
        result['Version'] = PP.getVersion()
    elif (cmd == "getADDR"):
        if (plate_type == 'POWER24'):
            result['ADDR'] = PP.getADDR()
        else:
            result['ADDR'] = PP.getADDR(addr)
    elif (cmd == "VERIFY"):
        if (plate_type == 'POWER24'):
            poll = PP.getADDR()
        else:
            poll = PP.getADDR(addr)

        # the DAQC plate's getADDR method adds 8 to the address.
        if (plate_type == "DAQC"):
            poll = poll - 8
        if (poll == addr):
            result['state'] = 0
        else:
            result['state'] = 1
    elif (cmd == "RESET"):
        if (plate_type in ['DAQC', 'POWER24']):
            result['RESET'] = "RESET() Unavailable"
        else:
            PP.RESET(addr)
            result['RESET'] = "OK"
    elif (cmd == "setLED"):
        if (plate_type == "POWER24"):
            if ('color' in args):
                color = args['color']
                if color in ['red', 'green', 'yellow', 'off']:
                    if (color == 'red'):
                        PP.setLED(0, 'RED')
                    elif (color == 'green'):
                        PP.setLED(0, 'GREEN')
                    elif (color == 'yellow'):
                        PP.setLED(0, 'YELLOW')
                    elif (color == 'off'):
                        PP.setLED(0, 'OFF')
                    result['state'] = color
                else:
                    sys.stderr.write("unsupported POWERplate24 LED color: " + color)
            else:
                # default to green (LED 1)
                PP.setLED(0, 'GREEN')
        elif (plate_type == "DAQC"):
            if ('color' in args):
                color = args['color']
                if color in ['red', 'green', 'yellow', 'off']:
                    if (color == 'red'):
                        PP.setLED(addr, 0)
                    elif (color == 'green'):
                        PP.setLED(addr, 1)
                    elif (color == 'yellow'):
                        PP.setLED(addr, 0)
                        PP.setLED(addr, 1)
                    elif (color == 'off'):
                        PP.clrLED(addr, 0)
                        PP.clrLED(addr, 1)
                    result['state'] = color
                else:
                    sys.stderr.write("unsupported DAQCplate LED color: " + color)
            else:
                # default to green (LED 1)
                PP.setLED(addr, 1)
                result['state'] = 1
        elif (plate_type == "DAQC2"):
            if ('color' in args):
                color = args['color']

                if color in ['off', 'red', 'green', 'yellow', 'blue',
                             'magenta', 'cyan', 'white']:
                    PP.setLED(addr, color)
                    result['state'] = color
                else:
                    sys.stderr.write("unsupported LED color: " + color)
            else:
                PP.setLED(addr, 'white')
                result['state'] = 1
        elif (plate_type == "TINKER"):
            PP.setLED(addr, 0)
            result['state'] = 1
        else:
            PP.setLED(addr)
            result['state'] = 1
    elif (cmd == "clrLED"):
        if (plate_type == "POWER24"):
            PP.setLED(0, 'off')
            result['state'] = 0

        elif (plate_type == "DAQC"):
            if ('color' in args):
                color = args['color']
                if (color == 'red'):
                    PP.clrLED(addr, 0)
                elif (color == 'green'):
                    PP.clrLED(addr, 1)
                else:
                    sys.stderr.write("unsupported LED color: " + color)
            else:
                PP.clrLED(addr, 0)
                PP.clrLED(addr, 1)
                result['state'] = 0

        elif (plate_type == "DAQC2"):
            PP.setLED(addr, 'off')
            result['state'] = 0
        elif (plate_type == "TINKER"):
            PP.clrLED(addr, 0)
            result['state'] = 0
        else:
            PP.clrLED(addr)
            result['state'] = 0
    elif (cmd == "toggleLED"):
        if (plate_type == "POWER24"):
            sys.stderr.write("LED toggle not supported on POWERplate24")
            result['state'] = "UNKNOWN"
        elif (plate_type == "DAQC"):
            if ('color' in args):
                color = args['color']
                if (color == 'red'):
                    PP.toggleLED(addr, 0)
                    result['state'] = PP.getLED(addr, 0)
                elif (color == 'green'):
                    PP.toggleLED(addr, 1)
                    result['state'] = PP.getLED(addr, 1)
                else:
                    sys.stderr.write("LED color should be 'red' or 'green'")
            else:
                # default to the green LED (1)
                PP.toggleLED(addr, 1)
                result['state'] = PP.getLED(addr, 1)
        elif (plate_type == "DAQC2"):
            # No DAQC2plate.toggleLED() but we can fake it
            cur_color = PP.getLED(addr)
            if (cur_color == "off"):
                PP.setLED(addr, "white")
            else:
                PP.setLED(addr, "off")
        elif (plate_type == "TINKER"):
            PP.toggleLED(addr, 0)
            result['state'] = PP.getLED(addr, 0)
        else:
            PP.toggleLED(addr)
            result['state'] = "UNKNOWN"

    elif (cmd == "getLED"):
        if plate_type in ['ADC', 'DAQC', 'DAQC2', 'THERMO', 'TINKER']:
            if (plate_type == 'DAQC'):
                if ('color' in args):
                    color = args['color']
                    if (color == 'red'):
                        result['state'] = PP.getLED(addr, 0)
                    elif (color == 'green'):
                        result['state'] = PP.getLED(addr, 1)
                    else:
                        sys.stderr.write("LED color should be red or green")
                else:
                    # default to green LED (1)
                    result['state'] = PP.getLED(addr, 1)
            elif (plate_type == 'TINKER'):
                # default to onboard LED (0)
                result['state'] = PP.getLED(addr, 0)
            else:
                result['state'] = PP.getLED(addr)
        else:
            sys.stderr.write("getLED() unsupported for plate: " + plate_type)
            result['state'] = "UNKNOWN"

    return result


while True:
    try:
        line = sys.stdin.readline()
        # TODO: add error handling for invalid JSON
        msg = json.loads(line)
        addr = msg['addr']
        plate_type = msg['plate_type']
        cmd = msg['cmd']
        args = msg['args']
        resp = {}
        if (plate_type == "RELAY" or plate_type == "RELAY2"):
            if (plate_type == "RELAY2"):
                import piplates.RELAYplate2 as RP2
                RP = RP2
            else:
                import piplates.RELAYplate as RP
                RP = RP
            if (cmd in common_funcs):
                resp = common_handler(RP, plate_type, addr, cmd, args)
            elif ("relay" in cmd):
                relay = args['relay']
                if (cmd == "relayON"):
                    RP.relayON(addr, relay)
                elif (cmd == "relayOFF"):
                    RP.relayOFF(addr, relay)
                elif (cmd == "relayTOGGLE"):
                    RP.relayTOGGLE(addr, relay)
                elif (cmd == "relaySTATE"):
                    pass
                state = RP.relaySTATE(addr)
                this_state = (state >> (relay - 1)) & 1
                resp['relay'] = relay
                resp['state'] = this_state
            elif (cmd == "ACTIVATE"):
                RP.relaysPresent[addr] = 1
                resp['state'] = 1
            else:
                sys.stderr.write("unknown relay cmd: " + cmd)
                break
            print(json.dumps(resp))
        elif (plate_type == "DAQC" or plate_type == "DAQC2"):
            # switch between DAQC and DAQC2 for their common API
            if (plate_type == "DAQC2"):
                import piplates.DAQC2plate as DP2
                PP = DP2
            else:
                import piplates.DAQCplate as DP
                PP = DP
            if (cmd in common_funcs):
                resp = common_handler(PP, plate_type, addr, cmd, args)
            elif (cmd == "getDINbit"):
                bit = args['bit']
                state = PP.getDINbit(addr, bit)
                resp['bit'] = bit
                resp['state'] = state
            elif (cmd == "setDOUTbit"):
                bit = args['bit']
                PP.setDOUTbit(addr, bit)
                resp['bit'] = bit
                resp['state'] = 1
            elif (cmd == "clrDOUTbit"):
                bit = args['bit']
                PP.clrDOUTbit(addr, bit)
                resp['bit'] = bit
                resp['state'] = 0
            elif (cmd == "toggleDOUTbit"):
                bit = args['bit']
                PP.toggleDOUTbit(addr, bit)
                resp['bit'] = bit
                resp['state'] = 'UNKNOWN'
            elif (cmd == "getADC"):
                channel = args['channel']
                voltage = PP.getADC(addr, channel)
                resp['channel'] = channel
                resp['voltage'] = voltage
            elif (cmd == "getADCall"):
                voltages = PP.getADCall(addr)
                resp['voltages'] = voltages
            elif (cmd == "getTEMP" and plate_type == "DAQC"):
                bit = args['bit']
                scale = args['scale']
                temp = PP.getTEMP(addr, bit, scale)
                resp['temp'] = temp
                resp['bit'] = bit
            elif (cmd == "getDAC"):
                channel = args['channel']
                value = PP.getDAC(addr, channel)
                resp['channel'] = channel
                resp['value'] = value
            elif (cmd == "setDAC"):
                channel = args['channel']
                value = args['value']
                PP.setDAC(addr, channel, value)
                resp['channel'] = channel
                resp['value'] = value
            elif (cmd == "getPWM"):
                channel = args['channel']
                value = PP.getPWM(addr, channel)
                resp['channel'] = channel
                resp['value'] = value
            elif (cmd == "setPWM"):
                channel = args['channel']
                value = args['value']
                PP.setPWM(addr, channel, value)
                resp['channel'] = channel
                resp['value'] = value
            elif (cmd == "calDAC"):
                PP.calDAC(addr)
            elif (cmd == "getOSCtraces"):

                channel1 = args['channel1']
                channel2 = args['channel2']
                rate = args['rate']
                triggerType = args['triggerType']
                triggerEdge = args['triggerEdge']
                triggerLevel = args['triggerLevel']
                triggerManual = args['triggerManual']
                triggerChannel = args['triggerChannel']

                PP.startOSC(addr)
                PP.setOSCchannel(addr, channel1 if 1 else 0, channel2 if 1 else 0)

                PP.setOSCsweep(addr,rate)
                PP.intEnable(addr)          #enable interrupts
                PP.runOSC(addr)             #start oscope

                if triggerManual:
                    PP.trigOSCnow(addr)
                else:
                    PP.setOSCtrigger(addr, triggerChannel, triggerType, triggerEdge, triggerLevel)

                dataReady=False

                while not dataReady:
                    if(PP.GPIO.input(22)==0):
                        dataReady=True
                        PP.getINTflags(addr) #clear interrupt flags

                if dataReady:

                    PP.getOSCtraces(addr)

                    if channel1:
                        result = []
                        for f in PP.trace1:
                            result.append((f-2048)*12.0/2048)
                        resp['trace1'] = result

                    if channel2:
                        result = []
                        for f in PP.trace2:
                            result.append((f-2048)*12.0/2048)
                        resp['trace2'] = result

                PP.intDisable(addr)          #enable interrupts
                PP.stopOSC(addr)

            elif (cmd == "setOSCtrigger"):
                channel = args['channel']
                trigger_type = args['type']
                edge = args['edge']
                level = args['level']
                PP.setOSCtrigger(addr,channel,trigger_type,edge,level)
            elif (cmd == "trigOSCnow"):
                PP.trigOSCnow(addr)
            elif (cmd == "runOSC"):
                PP.runOSC(addr)
            elif (cmd == "getFREQ" and plate_type == "DAQC2"):
                value = DP2.getFREQ(addr)
                resp['value'] = value
            elif (cmd == "ACTIVATE" and plate_type == "DAQC"):
                PP.daqcsPresent[addr] = 1
                PP.Vcc[addr] = PP.getADC(addr, 8)
                resp['state'] = 1
            elif (cmd == "ACTIVATE" and plate_type == "DAQC2"):
                PP.daqc2sPresent[addr] = 1
                PP.getCalVals(addr)
                resp['state'] = 1
            else:
                sys.stderr.write("unknown daqc(2) cmd: " + cmd)
            print(json.dumps(resp))
        elif (plate_type == "MOTOR"):
            import piplates.MOTORplate as MOTOR
            if ("dc" in cmd or "stepper" in cmd):
                motor = args['motor']
            if (cmd == "dcCONFIG"):
                dir = args['dir']
                speed = args['speed']
                acceleration = args['acceleration']
                MOTOR.dcCONFIG(addr, motor, dir, speed, acceleration)
            elif (cmd == "dcSTART"):
                MOTOR.dcSTART(addr, motor)
            elif (cmd == "dcSPEED"):
                speed = args['speed']
                MOTOR.dcSPEED(addr, motor, speed)
            elif (cmd == "dcSTOP"):
                MOTOR.dcSTOP(addr, motor)
            elif (cmd in common_funcs):
                resp = common_handler(MOTOR, plate_type, addr, cmd, args)
            else:
                sys.stderr.write("unknown or unsupported motor cmd: " + cmd)
            print(json.dumps(resp))
        elif (plate_type == "THERMO"):
            import piplates.THERMOplate as TP
            if (cmd in common_funcs):
                resp = common_handler(TP, plate_type, addr, cmd, args)
            elif (cmd == "getTEMP"):
                channel = args['channel']
                if ('scale' in args):
                    value = TP.getTEMP(addr, channel, args['scale'])
                else:
                    value = TP.getTEMP(addr, channel)
                resp['channel'] = channel
                resp['value'] = value
            elif (cmd == "getCOLD"):
                if ('scale' in args):
                    value = TP.getCOLD(addr, args['scale'])
                else:
                    value = TP.getCOLD(addr)
                resp['value'] = value
            elif (cmd == "setTYPE"):
                TP.setTYPE(addr, args['channel'], args['tc_type'])
            elif (cmd == "ACTIVATE"):
                TP.THERMOsPresent[addr] = 1
                TP.getCalVals(addr)
                resp['state'] = 1
            else:
                sys.stderr.write("unknown or unimplemented thermo cmd: " + cmd)
            print(json.dumps(resp))
        elif (plate_type == "TINKER"):
            import piplates.TINKERplate as TINK
            if (cmd in common_funcs):
                resp = common_handler(TINK, plate_type, addr, cmd, args)
            elif("relay" in cmd):
                relay = args['relay']
                if(cmd == "relayON"):
                    TINK.relayON(addr, relay)
                elif (cmd == "relayOFF"):
                    TINK.relayOFF(addr, relay)
                elif (cmd == "relayTOGGLE"):
                    TINK.relayTOGGLE(addr, relay)
                state = TINK.relaySTATE(addr, relay)
                resp['relay'] = relay
                resp['state'] = state
            elif("DOUT" in cmd):
                chan = args['bit']
                if(cmd == "setDOUTbit" or cmd == "setDOUT"):
                    TINK.setDOUT(addr, chan)
                    resp['state'] = 1
                elif(cmd == "clrDOUTbit"):
                    TINK.clrDOUT(addr, chan)
                    resp['state'] = 0
                elif(cmd == "toggleDOUTbit"):
                    TINK.toggleDOUT(addr, chan)
                    resp['state'] = 'UNKNOWN'
                resp['bit'] = chan
            elif(cmd == "getDINbit" or cmd == "getDIN"):
                chan = args['bit']
                state = TINK.getDIN(addr, chan)
                resp['state'] = state
                resp['bit'] = chan
            elif(cmd == "getADC"):
                channel = args['channel']
                voltage = TINK.getADC(addr, channel)
                resp['channel'] = channel
                resp['voltage'] = voltage
            elif(cmd == "getADCall"):
                voltages = TINK.getADCall(addr)
                resp['voltages'] = voltages
            elif(cmd == "getTEMP"):
                bit = args['bit']
                scale = args['scale']
                temp = TINK.getTEMP(addr, bit, scale)
                resp['temp'] = temp
                resp['bit'] = bit
            elif (cmd == "setOUT"):
                chan = args['bit']
                TINK.setMODE(addr, chan, 'dout')
                resp['state'] = "out"
            elif (cmd == "setTEMP"):
                chan = args['bit']
                TINK.setMODE(addr, chan, 'temp')
                resp['state'] = "temp"
            elif (cmd == "setPWM"):
                channel = args['channel']
                value = args['value']
                TINK.setPWM(addr, channel, value)
                resp['channel'] = channel
                resp['value'] = value
            elif (cmd == "setPWMmode"):
                chan = args['bit']
                TINK.setMODE(addr, chan, 'pwm')
                resp['state'] = "pwm"
            elif (cmd == "setIN"):
                chan = args['bit']
                TINK.setMODE(addr, chan, 'din')
                resp['state'] = "in"
            elif (cmd == "ACTIVATE"):
                TINK.platesPresent[addr] = 1
                resp['state'] = 1
            else:
                sys.stderr.write("unknown or unimplemented tinker cmd: " + cmd)
            print(json.dumps(resp))
        elif (plate_type == "ADC"):
            import piplates.ADCplate as ADC
            if (cmd in common_funcs):
                resp = common_handler(ADC, plate_type, addr, cmd, args)
            elif (cmd == "getDINbit"):
                bit = args['bit']
                state = ADC.getDINbit(addr, bit)
                resp['bit'] = bit
                resp['state'] = state
            elif (cmd == "getDINall"):
                bits = ADC.getDINall(addr)
                bit_list = []
                for i in range(4):
                    if bits & 1 << i != 0:
                        bit_list.insert(i, 1)
                    else:
                        bit_list.insert(i, 0)
                resp['bits'] = bits
                resp['states'] = bit_list
            elif (cmd == "getADC"):
                channel = args['channel']
                reading = ADC.getADC(addr, channel)
                if channel.startswith('I'):
                    resp['milliamps'] = reading
                else:
                    resp['voltage'] = reading
            elif (cmd == "getADCall"):
                voltages = ADC.getADCall(addr)
                resp['voltages'] = voltages
            elif (cmd == "setMODE"):
                mode = args['mode']
                ADC.setMODE(addr, mode)
                resp['mode'] = mode
            else:
                sys.stderr.write("unknown or unimplemented adc cmd: " + cmd)
            print(json.dumps(resp))
        elif (plate_type == "DIGI"):
            import piplates.DIGIplate as DIGI
            if (cmd in common_funcs):
                resp = common_handler(DIGI, plate_type, addr, cmd, args)
            elif (cmd == "getDINbit"):
                bit = args['bit']
                state = DIGI.getDINbit(addr, bit)
                resp['bit'] = bit
                resp['state'] = state
            elif (cmd == "getDINall"):
                bits = DIGI.getDINall(addr)
                bit_list = []
                for i in range(7):
                    if bits & 1 << i != 0:
                        bit_list.insert(i, 1)
                    else:
                        bit_list.insert(i, 0)
                resp['bits'] = bits
                resp['states'] = bit_list
            else:
                sys.stderr.write("unknown or unimplemented digi cmd: " + cmd)
            print(json.dumps(resp))
        elif (plate_type == "CURRENT"):
            import piplates.CURRENTplate as CURRENT
            if (cmd in common_funcs):
                resp = common_handler(CURRENT, plate_type, addr, cmd, args)
            elif (cmd == "getI"):
                channel = args['channel']
                mA = CURRENT.getI(addr, channel)
                resp['milliamps'] = mA
            elif (cmd == "getIall"):
                readings = CURRENT.getIall(addr)
                resp['currents'] = readings
            else:
                sys.stderr.write("unknown current cmd: " + cmd)
            print(json.dumps(resp))
        elif (plate_type == "POWER24"):
            import piplates.POWERplate24 as POW
            if (cmd in common_funcs):
                resp = common_handler(POW, plate_type, addr, cmd, args)
            elif (cmd == "getADC"):
                channel = args['channel']
                resp['channel'] = channel
                if (channel == "getVin"):
                    resp['voltage'] = POW.getVin(0)
                elif (channel == "getHVin"):
                    resp['voltage'] = POW.getHVin(0)
                elif (channel == 0):
                    resp['voltage'] = POW.getADC(0, 0)
                elif (channel == 1):
                    resp['voltage'] = POW.getADC(0, 1)
                else:
                    sys.stderr.write("unknown channel: " + channel)
            elif ("fan" in cmd):
                if (cmd == "fanON"):
                    POW.fanON(0)
                elif (cmd == "fanOFF"):
                    POW.fanOFF(0)
                elif (cmd == "fanSTATE"):
                    pass
                resp['state'] = POW.fanSTATE(0)
            elif (cmd == "getPOWstatus"):
                bits = POW.getPOWstatus(0)
                resp['NO_AC'] = bits & 1 != 0
                resp['LOW_BAT'] = bits & 2 != 0
                resp['LOW_DC_IN'] = bits & 4 != 0
            print(json.dumps(resp))
        else:
            sys.stderr.write("unknown plate_type: " + plate_type)
    except (EOFError, SystemExit, AssertionError):
        sys.exit(3)
