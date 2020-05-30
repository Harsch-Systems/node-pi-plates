import sys
import json
import piplates.DAQCplate as DP
import piplates.DAQC2plate as DP2
import piplates.RELAYplate as RP
import piplates.MOTORplate as MP
import piplates.THERMOplate as TP
import piplates.TINKERplate as TINK

# All Pi Plate communication must go through this one process to ensure
# SPI communications don't overlap / interfere and corrupt the device state(s)
#
# listen for json messages on stdin of the format:
# {
#   addr: <pi plate address 0-7>,
#   plate_type: <RELAY|DAQC>,
#   cmd: <command string>, args: {<command-specific args>}
# }

#TODO: scan for plates at startup so we can handle wrong-address
#      or plate_type mismatch exceptions

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
        TINK.relayTOGGLE(0, 1)
        if (plate_type == "RELAY"):
            if (cmd == "setLED"):
                RP.setLED(addr)
                resp['LED'] = 1
            elif (cmd == "clrLED"):
                RP.clrLED(addr)
                resp['LED'] = 0
            elif (cmd == "toggleLED"):
                RP.toggleLED(addr)
                resp['LED'] = "UNKNOWN"
            elif (cmd == "getID"):
                resp['ID'] = RP.getID(addr)
            elif (cmd == "getHWrev"):
                resp['HWrev'] = RP.getHWrev(addr)
            elif (cmd == "getFWrev"):
                resp['FWrev'] = RP.getFWrev(addr)
            elif (cmd == "getPMrev"):
                resp['PMrev'] = RP.getPMrev()
            elif (cmd == "getADDR"):
                resp['ADDR'] = RP.getADDR(addr)
            elif ("relay" in cmd):
                relay = args['relay']
                if (cmd == "relayON"):
                    RP.relayON(addr, relay)
                elif (cmd == "relayOFF"):
                    RP.relayOFF(addr, relay)
                elif (cmd == "relayTOGGLE"):
                    RP.relayTOGGLE(addr, relay)
                state = RP.relaySTATE(addr)
                this_state = (state >> (relay - 1)) & 1
                resp['relay'] = relay
                resp['state'] = this_state
            elif (cmd == "RESET"):
                RP.RESET(addr)
                resp['RESET'] = "OK";
            else:
                sys.stderr.write("unknown relay cmd: " + cmd)
                break
            print(json.dumps(resp))
        elif (plate_type == "DAQC" or plate_type == "DAQC2"):
            # switch between DAQC and DAQC2 for their common API
            if (plate_type == "DAQC2"):
                PP = DP2
            else:
                PP = DP
            if (cmd == "getDINbit"):
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
            elif (cmd == "getTEMP"):
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
                resp['channgetel'] = channel
                resp['value'] = value
            elif (cmd == "setPWM"):
                channel = args['channel']
                value = args['value']
                PP.setPWM(addr, channel, value)
                resp['channel'] = channel
                resp['value'] = value
            elif (cmd == "calDAC"):
                PP.calDAC(addr)
            elif (cmd == "getFREQ" and plate_type == "DAQC2"):
                value = DP2.getFREQ(addr)
                resp['value'] = value
            elif (cmd == "setLED" and plate_type == "DAQC"):
                color = args['color']

                if color == 'off':
                    DP.clrLED(addr, 0)
                    DP.clrLED(addr, 1)
                elif color == 'red':
                    DP.setLED(addr, 0)
                    DP.clrLED(addr, 1)
                elif color == 'green':
                    DP.clrLED(addr, 0)
                    DP.setLED(addr, 1)
                elif color == 'yellow':
                    DP.setLED(addr, 0)
                    DP.setLED(addr, 1)
                else:
                    sys.stderr.write("unsupported LED color: " + color)

                resp['color'] = color
            elif (cmd == "setLED" and plate_type == "DAQC2"):
                color = args['color']

                if color in ['off','red','green','yellow','blue','magenta','cyan','white']:
                    DP2.setLED(addr, color)
                else:
                    sys.stderr.write("unsupported LED color: " + color)

                resp['color'] = color
            else:
                sys.stderr.write("unknown daqc(2) cmd: " + cmd)
            print(json.dumps(resp))
        elif (plate_type == "MOTOR"):
            break
        elif (plate_type == "THERMO"):
            if (cmd == "getTEMP"):
                channel = args['channel']
                value = TP.getTEMP(addr, channel)
                resp['channel'] = channel
                resp['value'] = value
            elif (cmd == "getCOLD"):
                value = TP.getCOLD(addr)
                resp['value'] = value
            elif (cmd == "setLED"):
                TP.setLED(addr)
                resp['LED'] = 1
            elif (cmd == "clrLED"):
                TP.clrLED(addr)
                resp['LED'] = 0
            elif (cmd == "toggleLED"):
                TP.toggleLED(addr)
                resp['LED'] = TP.getLED(addr)
            else:
                sys.stderr.write("unknown or unimplemented thermo cmd: " + cmd)
            print(json.dumps(resp))
        elif (plate_type == "TINKER"):
            if("relay" in cmd):
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
            elif(cmd == "setDOUTbit"):
                chan = args['bit']
                TINK.setDOUT(addr, 1)
                resp['bit'] = chan
                resp['state'] = 1
            elif(cmd == "clrDOUTbit"):
                chan = args['bit']
                TINK.clrDOUT(addr, 1)
                resp['bit'] = chan
                resp['state'] = 0
            elif(cmd == "toggleDOUTbit"):
                chan = args['bit']
                TINK.toggleDOUT(addr, 1)
                resp['bit'] = chan
                resp['state'] = 'UNKNOWN'
            else:
                sys.stderr.write("unknown or unimplemented tinker cmd: " + cmd)
            print(json.dumps(resp))
        else:
            sys.stderr.write("unknown plate_type: " + plate_type)
    except (EOFError, SystemExit):
        sys.exit(0)
