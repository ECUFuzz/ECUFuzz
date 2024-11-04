from ZDCANLib.ZDcantp import zd_cantp
from ZDCANLib.ZDutility import zd_utility
from termcolor import colored, cprint
from enum import Enum, IntEnum
from threading import Thread
import time
import sys
import can
import numpy
import ctypes

class zd_uds(object):
    def __init__(self, config=None, cantp=None):
        if config is not None:
            # self.t1 = Thread(target=self.ThreadTestPresent)
            # self.ThreadRun = True
            # self.TestPresentRun = False
            # self.TestPresentCycleTime = 4
            # self.t1.start()
            self.udsConfig = config['uds_config']
            self.config = config
            self.tx_id = int(self.udsConfig['IntPhyAddr'], 16)
            self.rx_id = int(self.udsConfig['IntResAddr'], 16)
            self.did = self.DataIdentifier(self)
            self.rid = self.RoutineIdentifier(self)
            if cantp is not None:
                self.can = cantp.get_can()
                self.cantp = cantp
            else:
                self.cantp = zd_cantp(config['cantp_config'], config['can_config'])
            self.can = self.cantp.get_can()
            self.version = ['UDS V1.6'] + self.cantp.version
        else:
            raise Exception('UDS configuration is not available')
    
    def get_can(self):
        return self.can

    def transmit(self, payload, canid = None):
        if canid is not None:
            tx_id = canid[0]
            rx_id = canid[1]
        else:
            tx_id = self.tx_id
            rx_id = self.rx_id

        retryCnt = 2
        while(retryCnt != 0):
            cprint(hex(tx_id) + ': ' + zd_utility.ConvertBytes2Hex(payload), 'green')
            self.cantp.send(tx_id, rx_id, payload)
            recvPayload = self.cantp.recv(tx_id, rx_id)
            if(recvPayload is not None):
                cprint(hex(rx_id) + ': ' + zd_utility.ConvertBytes2Hex(recvPayload), 'blue')
                return recvPayload
            else:
                retryCnt -= 1
                cprint('TIMEOUT and RETRY ' + str(retryCnt), 'yellow')
        cprint('TIMEOUT', 'red')
        self.can.flush_tx_buffer() # If there is no communication for an extended period, clear the Tx buffer to prevent it from becoming full
        return None

    def SwitchTransmitID(self, tx_id, rx_id):
        self.tx_id = tx_id
        self.rx_id = rx_id
        return [True, ['']]

    # def ThreadTestPresent(self):
    #     while(self.ThreadRun):
    #         if (self.TestPresentRun == True):
    #             # sys.stdout.flush()
    #             # cprint(zd_utility.ConvertBytes2Hex([0x3E, 0x80]), 'green')
    #             self.cantp.send_nowait(self.tx_id, [0x3E, 0x80])
    #         time.sleep(self.TestPresentCycleTime)

    def TestPresent(self, ctrl = True, cycleTime = 4):
        # self.TestPresentRun = ctrl
        # self.TestPresentCycleTime = cycleTime
        if ctrl == True:
            msg = can.Message(arbitration_id = self.tx_id, timestamp=time.time(), is_fd = self.can.fd, is_rx=False, bitrate_switch=self.can.brs, is_extended_id=False, data=[0x02, 0x3E, 0x80, 0, 0, 0, 0, 0])
            self.can.start_periodic(msg, cycleTime)
        else:
            self.can.remove_periodic(self.tx_id)
        return [True, ['']]
    
    def SessionControl(self, session):
        log = []
        res = self.transmit([0x10, session])
        log.append(zd_utility.ConvertBytes2Hex([0x10, session]))
        if res != None:
            log.append(zd_utility.ConvertBytes2Hex(res))
            if((res[0] == 0x50) and (res[1] == session)):
                P2Server = ((res[2] << 8) + res[3]) / 1000
                P2Server_Star = ((res[4] << 8) + res[5]) / 10000
                return [True, log]
            else:
                return [False, log]
        else:
            return [False, log.append('Timeout')]
    
    def EcuReset(self):
        log = []
        res = self.transmit([0x11, 0x01])
        log.append(zd_utility.ConvertBytes2Hex([0x11, 0x01]))
        if res != None:
            log.append(zd_utility.ConvertBytes2Hex(res))
            if((res[0] == 0x51) and (res[1] == 0x01)):
                return [True, log]
            else:
                return [False, log]
        else:
            return [False, log.append('Timeout')]

    def ServiceRun(self, cmd):
        log = []
        res = self.transmit(cmd)
        log.append(zd_utility.ConvertBytes2Hex(cmd))
        if res != None:
            log.append(zd_utility.ConvertBytes2Hex(res))
            if(res[0] == (cmd[0] + 0x40)):
                return [True, log]
            else:
                return [False, log]
        else:
            return [False, log.append('Timeout')]

    def CommunicationControl(self, controlType, communicationType):
        log = []
        res = self.transmit([0x28, controlType, communicationType])
        log.append(zd_utility.ConvertBytes2Hex([0x28, controlType, communicationType]))
        if res != None:
            log.append(zd_utility.ConvertBytes2Hex(res))
            if((res[0] == 0x68) and (res[1] == controlType)):
                return [True, log]
            else:
                return [False, log]
        else:
            return [False, log.append('Timeout')]

    def ControlDTCSetting(self, cmd):
        log = []
        res = self.transmit([0x85, cmd])
        log.append(zd_utility.ConvertBytes2Hex([0x85, cmd]))
        if res != None:
            log.append(zd_utility.ConvertBytes2Hex(res))
            if((res[0] == 0xC5) and (res[1] == cmd)):
                return [True, log]
            else:
                return [False, log]
        else:
            return [False, log.append('Timeout')]
    
    def StartPeriodicMessages(self, proj='T26'):
        loglist = []
        proj_config = zd_utility.LoadJson('Config/'+proj+"/CanMessages.json")
        config = proj_config['can_messages']
        for cfg in config.values():
            datalist = zd_utility.ConvertStr2Bytes(cfg["data"])
            msg = can.Message(arbitration_id=int(cfg["id"], 16), timestamp=time.time(), is_fd=cfg['fd'], bitrate_switch=cfg['fd'], is_rx=False, is_extended_id=False, data=datalist, dlc=len(datalist))
            self.can.start_periodic(msg, cfg["cycle"]/1000)
            loglist.append(cfg["id"] + ":" + cfg["data"] + " is sent " + str(cfg["cycle"]) + " ms")
        return [True, ['start succeed']]
    def StopPeriodicMessages(self, proj='T26'):
        proj_config = zd_utility.LoadJson('Config/'+proj+"/CanMessages.json")
        config = proj_config['can_messages']
        for cfg in config.values():
            self.can.remove_periodic(int(cfg['id'], 16))
        return [True, 'stop succeed']

    def SendPeriodicMessage(self, framelist=[{"id":0x123, "cycle":100, "fd":False, "data":[0,0,0,0,0,0,0,0]}]):
        loglist = []
        for frame in framelist:
            msg = can.Message(arbitration_id=frame["id"], timestamp=time.time(), is_fd=frame["fd"], bitrate_switch=frame["fd"], is_rx=False, is_extended_id=False, data=frame["data"], dlc=len(frame["data"]))
            self.can.start_periodic(msg, frame["cycle"]/1000)
            loglist.append(hex(frame["id"]) + ":" + zd_utility.ConvertBytes2Hex(frame["data"]) + " is sent " + str(frame["cycle"]) + " ms")
        return [True, loglist]
    
    # def StopPeriodicMessages(self):
    #     self.can.stop_periodic()
    #     return [True, ['periodic message stopped']]

    def RemovePeriodicMessages(self, msgid):
        self.can.remove_periodic(msgid)
        return [True, [hex(msgid) + ' is removed']]

    def ReadMemory(self, startaddress, memorysize):
        DCM_SIZE = 3072
        DataBuffer = []
        while(memorysize > 0):
            blocksize = min(DCM_SIZE, memorysize)
            res = self.transmit([0x23, 0x24, (startaddress & 0xFF000000) >> 24, (startaddress & 0x00FF0000) >> 16, (startaddress & 0x0000FF00) >> 8, (startaddress & 0x000000FF) >> 0, (blocksize & 0xFF00) >> 8, (blocksize & 0x00FF)])
            if res is not None:
                if res[0] == 0x63:
                    DataBuffer += res[1:]
                else:
                    return res
            else:
                return None
            memorysize -= blocksize
            startaddress += blocksize
        return [0x63] + DataBuffer

    def SearchFault(self, Id, Status, List, DtcMask):
        DTC_testFailed = 0x01
        DTC_testFailedThisOperationCycle = 0x02
        DTC_pendingDTC = 0x04
        DTC_confirmedDTC = 0x08
        DTC_testNotCompletedSinceLastClear = 0x10
        DTC_testFailedSinceLastClear = 0x20
        DTC_testNotCompletedThisOperationCycle = 0x40
        DTC_warningIndicatorRequested = 0x80
        
        Status = Status & DtcMask
        StatusTxt = 'UNKNOWN'
        if (Status & (DTC_testFailed | DTC_testFailedSinceLastClear)) != 0:
            StatusTxt = 'Active'
        elif (Status & DTC_confirmedDTC) != 0:
            StatusTxt = 'History'
        elif (Status & (DTC_testNotCompletedSinceLastClear | DTC_testNotCompletedThisOperationCycle)) != 0:
            StatusTxt = 'Untested'
        # try:
        #     NameTxt = List[Id]
        # except:
        #     NameTxt = 'UNKNOWN'
        if StatusTxt != 'UNKNOWN':
            try:
                NameTxt = List[Id]
            except Exception as e:
                NameTxt = e
            return [Id, NameTxt, StatusTxt]
        else:
            return None

    def ReadDtc(self, cmd=[0x22, 0xfd, 0x39], dtcList=None):
        log = []
        dtcDecodeList = []
        log.append(zd_utility.ConvertBytes2Hex(cmd))
        res = self.transmit(cmd)
        log.append(zd_utility.ConvertBytes2Hex(res))
        
        Is19Server = False
        dtcSize = 3
        dtcMask = 0xCB
        dtcFormat = '{:d}'
        if cmd[0] == 0x19:
            Is19Server = True
            dtcSize = 4
            dtcMask = cmd[2]
            dtcFormat = '{:06X}'

        if res is not None:
            if res[0] == (cmd[0] + 0x40):
                for i in range(3, len(res), dtcSize):
                    dtcValue = 0
                    for j in range(i, i + dtcSize):
                        dtcValue = (dtcValue << 8) + res[j]
                    dtcStatus = dtcValue & 0x000000FF
                    dtcValue = dtcValue >> 8
                    if dtcList is not None:
                        dtcDeocde= self.SearchFault(dtcFormat.format(dtcValue), dtcStatus, dtcList, dtcMask)
                        if dtcDeocde is not None:
                            dtcDecodeList.append(dtcDeocde)
                return [True, log, dtcDecodeList]
            else:
                return [False, log]
        else:
            return [False, log]


    def SecurityAccess(self, type='T26', level=0x01):
        seed = []
        key = []
        log = []
        type = type.replace('T002', 'T26')
        type = type+'_'+"{:0>2X}".format(level)
        type = type.encode('utf-8')
        res = self.transmit([0x27, level])
        log.append(zd_utility.ConvertBytes2Hex([0x27, level]))
        if res != None:
            log.append(zd_utility.ConvertBytes2Hex(res))
            if((res[0] == 0x67) and (res[1] == level)):
                seed += res[2:]
                if (level == 0x61):
                    for seedelement in seed:
                        key.append((~seedelement) & 0xFF)
                else:
                    key = zd_utility.GenerateSecKey(type, seed)
            else:
                return [False, log]
        else:
            return [False, log.append('Timeout')]
        
        res = self.transmit([0x27, level + 1] + key)
        log.append(zd_utility.ConvertBytes2Hex([0x27, level + 1] + key))
        if res is not None:
            log.append(zd_utility.ConvertBytes2Hex(res))
            if((res[0] == 0x67) and (res[1] == (level + 1))):
                return [True, log]
            else:
                return [False, log]
        else:
            return [False, log.append('Timeout')]


    def RequestDownloadByFile(self, format, files, blockInfo = None):
        startaddress, transferData = zd_utility.DecodeS37FileList(files)
        length = len(transferData)
        if blockInfo is not None:
            startaddress = blockInfo[0]
            length = blockInfo[1]
        return self.RequestDownloadByData(format, transferData, startaddress, length)

    def RequestDownloadByData(self, format, transferData, startaddress, length):
        log = []
        if format != 0:
            if(startaddress is not None):
                res = self.EraseMemory(format, startaddress, length)
                if res[0] == True:
                    log += res[1]
                else:
                    return [False, log]
            else:
                return [False, log.append('Transfer Data Not Available')]

        if(startaddress is not None):
            res = self.TransferRequest(format, startaddress, length)
            log += res[1]
            if res[0] == False:
                return [False, log]
        else:
            return [False, log.append('Transfer Data Not Available')]
        
        if(startaddress is not None):
            maxDataLen = res[2]
            res = self.TransferData(transferData, maxDataLen)
            log += res[1]
            if res[0] == False:
                return [False, log]
        else:
            return [False, log.append('Transfer Data Not Available')]
        
        if(startaddress is not None):
            res = self.TransferExit()
            log += res[1]
            if res[0] == False:
                return [False, log]
        else:
            return [False, log.append('Transfer Data Not Available')]
        
        return [True, log]

    
    def EraseMemory(self, format=None, startaddress=None, length=None ):
        log = []
        waitingFinish = False
        frameData = [0x31, 0x01, 0xFF, 0x00]
        if format == 0x44:
            frameData += [0x44]
        frameData += [(startaddress&0xFF000000)>>24, (startaddress&0x00FF0000)>>16, (startaddress&0x0000FF00)>>8, (startaddress&0x000000FF)>>0,
                     (length&0xFF000000)>>24, (length&0x00FF0000)>>16, (length&0x0000FF00)>>8, (length&0x000000FF)>>0,]
        res = self.transmit(frameData)
        log.append(zd_utility.ConvertBytes2Hex(frameData))
        if res != None:
            log.append(zd_utility.ConvertBytes2Hex(res))
            # res[4] is no need to check， T26 is 1， E03 is 0
            if((res[0] == 0x71) and (res[1] == 0x01) and (res[2] == 0xFF) and (res[3] == 0x00)):
                waitingFinish = True
            else:
                return [False, log]
        else:
            return [False, log.append('Timeout')]

        if format == None:
            while(waitingFinish):
                time.sleep(3)
                frameData = [0x31, 0x03, 0xFF, 0x00]
                res = self.transmit(frameData)
                log.append(zd_utility.ConvertBytes2Hex(frameData))
                if res != None:
                    log.append(zd_utility.ConvertBytes2Hex(res))
                    if((res[0] == 0x71) and (res[1] == 0x03) and (res[2] == 0xFF) and (res[3] == 0x00) and (res[4] == 0x02)):
                        waitingFinish = False
                    else:
                        waitingFinish = True
                else:
                    return [False, log.append('Timeout')]
                
            frameData = [0x31, 0x02, 0xFF, 0x00]
            res = self.transmit(frameData)
            log.append(zd_utility.ConvertBytes2Hex(frameData))
            if res != None:
                log.append(zd_utility.ConvertBytes2Hex(res))
                if((res[0] == 0x71) and (res[1] == 0x02) and (res[2] == 0xFF) and (res[3] == 0x00) and (res[4] == 0x04)):
                    waitingFinish = False
                else:
                    return [False, log] 
            else:
                return [False, log.append('Timeout')]
        return [True, log]

    def TransferRequest(self, format=0x44, startaddress=None, length=None):
        log = []
        maxDataLen = 0xF02
        if(startaddress is not None):
            frameData = [0x34, 0x00, 0x44, 
                            (startaddress&0xFF000000)>>24, (startaddress&0x00FF0000)>>16, (startaddress&0x0000FF00)>>8, (startaddress&0x000000FF)>>0,
                            (length&0xFF000000)>>24, (length&0x00FF0000)>>16, (length&0x0000FF00)>>8, (length&0x000000FF)>>0]
            res = self.transmit(frameData)
            log.append(zd_utility.ConvertBytes2Hex(frameData))
            if res != None:
                log.append(zd_utility.ConvertBytes2Hex(res))
                if(res[0] == 0x74):
                    lenSize = (res[1] & 0xF0) >> 4
                    maxDataLen = 0
                    for i in range(lenSize):
                        maxDataLen = (maxDataLen << 8) + res[2 + i]
                    return [True, log, maxDataLen] 
                else:
                    return [False, log] 
            else:
                return [False, log.append('Timeout')]
        else:
            return [False, log.append('Timeout')]
    
    def TransferData(self, transferData=None, maxDataLen=0xF02):
        log = []
        if(maxDataLen != 0):
            frameSN = 1
            isRunning = True
            maxDataLen -= 2 # remove the size of 36 01
            while(isRunning):
                frameData = [0x36, frameSN]
                frameDataStart = (frameSN - 1) * maxDataLen
                if (frameSN * maxDataLen) < len(transferData):
                    frameDataEnd = (frameSN * maxDataLen)
                else:
                    frameDataEnd = len(transferData)
                    isRunning = False

                for i in range(frameDataStart, frameDataEnd):
                    frameData.append(transferData[i])
                res = self.transmit(frameData)
                log.append(zd_utility.ConvertBytes2Hex(frameData))
                if res != None:
                    log.append(zd_utility.ConvertBytes2Hex(res))
                    if(res[0] == 0x76) and (res[1] == frameSN): # 2 bytes length
                        frameSN += 1
                        if frameSN == 0x100:
                            frameSN = 0
                    else:
                        return [False, log]
                else:
                    return [False, log.append('Timeout')]
            return [True, log]
        else:
            return [False, log.append('Max Data Len is 0')]
            
    def TransferExit(self):
        log = []
        res = self.transmit([0x37])
        if res != None:
            log.append(zd_utility.ConvertBytes2Hex([0x37]))
            if(res[0] == 0x77):
                log.append(zd_utility.ConvertBytes2Hex(res))
                return [True, log]
            else:
                return [False, log]
        else:
            return [False, log.append('Timeout')]

    def close(self):
        # self.TestPresentRun = False
        # self.ThreadRun = False
        # self.t1.join()
        # time.sleep(1)
        self.cantp.close()

    class DataIdentifier:
        def __init__(self, father):
            self.father = father

        def ImuGetPhysicalSignal(self, canFrame, data_start, data_len, data_shift, data_mask):
            signalData = 0
            for j in range(0, data_len):
                signalData = (signalData << 8) + canFrame[data_start + j]
            signalData = signalData >> data_shift
            signalData = signalData & data_mask
            return signalData

        def ImuInternalCalibrationCollect(self, ImuCfgList):
            can = self.father.can

            retVal = {}

            filterList = []
            for ImuCfg in ImuCfgList:
                filterList.append(int(ImuCfg["msg_id"], 16))
            can.setFilters([0x127,0x128,0x136])

            for ImuCfg in ImuCfgList:
                if ImuCfg["required"] == True:
                    msgCnt = 0
                    canId = int(ImuCfg["msg_id"], 16)
                    signalList = []
                    while(msgCnt < 25):
                        msg = can.recv_msg()
                        if msg is not None:
                            if msg.arbitration_id == canId:
                                signal = self.ImuGetPhysicalSignal(msg.data, ImuCfg["data_start"], ImuCfg["data_len"], ImuCfg["data_shift"], ImuCfg["data_mask"])
                                signalList.append(signal)
                                msgCnt += 1
                    avgSignal = numpy.mean(signalList)
                    initNullFloat = avgSignal * ImuCfg["factor"] + ImuCfg["offset"]
                    print(initNullFloat)
                    initNull = ctypes.c_uint16(int(initNullFloat * ImuCfg["sensitivity"])).value
                    print(initNull)
                    if (ImuCfg["null_low"] <= initNullFloat) and (initNullFloat <= ImuCfg["null_high"]):
                        retVal[ImuCfg["signal_name"]] = initNull
                        # retVal.append({ImuCfg["signal_name"], "init_null": initNull, "sensitivity": ImuCfg["sensitivity"]})
                    else:
                        return None
            return retVal

        def ImuInternalCalibration(self, InitList = {"x": 0x0000, "y": 0x0000, "z": 0x0000, "roll": 0x0000, "yaw": 0x0000}, SensitivityList = {"x": 0x1388, "y": 0x1388, "z": 0x1388}):
            log = []
            init_x = InitList["x"]
            init_y = InitList["y"]
            init_z = InitList["z"]
            init_roll = InitList["roll"]
            init_yaw = InitList["yaw"]
            sens_x = SensitivityList["x"]
            sens_y = SensitivityList["y"]
            sens_z = SensitivityList["z"]
            payload_x = [((init_x & 0xFF00) >> 8), ((init_x & 0x00FF) >> 0), ((sens_x & 0xFF00) >> 8), ((sens_x & 0x00FF) >> 0)]
            crc_x = zd_utility.Crc8(payload_x)
            payload_y = [((init_y & 0xFF00) >> 8), ((init_y & 0x00FF) >> 0), ((sens_y & 0xFF00) >> 8), ((sens_y & 0x00FF) >> 0)]
            crc_y = zd_utility.Crc8(payload_y)
            payload_z = [((init_z & 0xFF00) >> 8), ((init_z & 0x00FF) >> 0), ((sens_z & 0xFF00) >> 8), ((sens_z & 0x00FF) >> 0)]
            crc_z = zd_utility.Crc8(payload_z)
            payload_roll = [((init_roll & 0xFF00) >> 8), ((init_roll & 0x00FF) >> 0)]
            crc_roll = zd_utility.Crc8(payload_roll)
            payload_yaw = [((init_yaw & 0xFF00) >> 8), ((init_yaw & 0x00FF) >> 0)]
            crc_yaw = zd_utility.Crc8(payload_yaw)
            payloadlist = [
                [0x2E, 0xFD, 0x33, payload_x[0], payload_x[1], payload_x[2], payload_x[3], crc_x], # LogG X
                # [0x2E, 0xFD, 0x34, 0x00, 0x00, 0x13, 0x88, 0x23], # LogG X Redundant
                [0x2E, 0xFD, 0x35, payload_y[0], payload_y[1], payload_y[2], payload_y[3], crc_y], # LogG Y
                # [0x2E, 0xFD, 0x36, 0x00, 0x00, 0x13, 0x88, 0x23], # LogG Y Redundant
                [0x2E, 0xFD, 0x37, payload_z[0], payload_z[1], payload_z[2], payload_z[3], crc_z], # LogG Z
                [0x2E, 0xFD, 0x03, payload_roll[0], payload_roll[1], crc_roll], # RollRate
                [0x2E, 0xFD, 0x14, payload_yaw[0], payload_yaw[1], crc_yaw], # YawRate
                # [0x2E, 0xFD, 0x15, 0x00, 0x00, 0x56], # YawRate Redundant
                # [0x2E, 0xFD, 0x25, 0x00, 0x00, 0x56], # PitchRate
            ]
            for payload in payloadlist:
                res = self.father.transmit(payload)
                if res is not None:
                    log.append(zd_utility.ConvertBytes2Hex(payload))
                    log.append(zd_utility.ConvertBytes2Hex(res))
                    if res[0] != 0x6E:
                        return [False, log]
                else:
                    return [False, log.append('Timeout')]
            return [True, log]

        def WriteVIN(self, carcfg=None, vindata=None):
            log = []
            if carcfg is not None:
                vin = carcfg['VIN']
                framedata = [0x2E, 0xF1, 0x90] + zd_utility.ConvertStr2Bytes(vin)
            elif vindata is not None:
                framedata = [0x2E, 0xF1, 0x90] + vindata
            else:
                framedata = [0x22, 0xF1, 0x90]
            res = self.father.transmit(framedata)
            log.append(zd_utility.ConvertBytes2Hex(framedata))
            if res is not None:
                log.append(zd_utility.ConvertBytes2Hex(res))
                if res[0] == (framedata[0] + 0x40):
                    return [True, log]
                else:
                    return [False, log]
            else:
                return [False, log.append('Timeout')]
        
        def WriteFingerPrint(self, project):
            log = []
            if project == 'T26_ZD':
                cmd = [0x2E, 0xF1, 0x5A, 0x23, 0x09, 0x13, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B]
            elif project == 'E03':
                cmd = [0x2E, 0xF1, 0x84, 0x23, 0x09, 0x13, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F]
            else:
                print('unknow project '+project)
                return [False, ['None']]
            log.append(zd_utility.ConvertBytes2Hex(cmd))
            res = self.father.transmit(cmd)
            if res is not None:
                log.append(zd_utility.ConvertBytes2Hex(res))
                if res[0] == 0x6E:
                    return [True, log]
                else:
                    return [False, log]
            else:
                return [False, log.append('Timeout')]

    class RoutineIdentifier:
        def __init__(self, father):
            self.father = father

        def SwitchPhase(self, phase = None):
            log = []
            if phase is not None:
                cmd = [0x31, 0x01, 0xF1, 0x06, phase]
                res = self.father.transmit(cmd)
                log.append(zd_utility.ConvertBytes2Hex(cmd))
                if res is not None:
                    log.append(zd_utility.ConvertBytes2Hex(res))
                    if(res[0] != 0x71):
                        return [False, log]
                    else:
                        return [True, log]
                else:
                    return [False, log.append('Timeout')]
            else:
                cmd = [0x22, 0xFD, 0x73]
                res = self.father.transmit(cmd)
                log.append(zd_utility.ConvertBytes2Hex(cmd))
                if res is not None:
                    log.append(zd_utility.ConvertBytes2Hex(res))
                    if(res[0] != 0x62):
                        return [False, log]
                    else:
                        return [True, log]
                else:
                    return [False, log.append('Timeout')]

        def ImuExternalCalibration(self):
            log = []
            res = self.father.transmit([0x31, 0x01, 0x64, 0x36])
            log.append(zd_utility.ConvertBytes2Hex([0x31, 0x01, 0x64, 0x36]))
            if res is not None:
                log.append(zd_utility.ConvertBytes2Hex(res))
                if(res[0] != 0x71):
                    return [False, log]
            else:
                return [False, log.append('Timeout')]

            if(res[4] == 0x01):
                tryCnt = 0
                while(True):
                    res = self.father.transmit([0x31, 0x03, 0x64, 0x36])
                    log.append(zd_utility.ConvertBytes2Hex([0x31, 0x03, 0x64, 0x36]))
                    if res is not None:
                        log.append(zd_utility.ConvertBytes2Hex(res))
                        if(res[0] == 0x71):
                            if(res[4] == 0x02):
                                cprint("IMU External Calibration Success", 'green')
                                return [True, log]
                            else:
                                if(res[5] == 0x01):
                                    cprint("IMU External Calibration Failed with Internal Calibration Not Finished", 'red')
                                elif(res[5] == 0x02):
                                    cprint("IMU External Calibration Failed with Sensor Invalid", 'red')
                                elif(res[5] == 0x03):
                                    cprint("IMU External Calibration Failed with Vehicle Speed Out Of Range", 'red')
                                elif(res[5] == 0x04):
                                    cprint("IMU External Calibration Failed with Sample Data Out Of Range", 'red')
                                elif(res[5] == 0x05):
                                    cprint("IMU External Calibration Failed with Phase Of Life Is Not Correct", 'red')
                                else:
                                    cprint("IMU External Calibration Failed with Unknown Failure Reason", 'red')
                                if tryCnt < 10:
                                    time.sleep(1)
                                    tryCnt += 1
                                else:
                                    return [False, log]
                        else:
                            return [False, log]
                    else:
                        return [False, log.append('Timeout')]
        
        def CheckSignature(self, type, startaddress, transferData):
            rsa_sign = zd_utility.GenerateRsaSignWAddr(type, startaddress, transferData)
            if type == 'E03':
                cmd = [0x31, 0x01, 0xDD, 0x02] + rsa_sign
            elif type == 'T26_ZD':
                cmd = [0x31, 0x01, 0xD0, 0x02] + rsa_sign
            else:
                return [False, ['None']]
            return self.father.ServiceRun(cmd)
        
        def CheckSignatureByFile(self, type, rsa_file):
            with open(rsa_file, 'r') as f:
                rsa_txt = f.read()
                rsa_sign = zd_utility.ConvertStr2Bytes(rsa_txt)
            if type == 'E03':
                cmd = [0x31, 0x01, 0xDD, 0x02] + rsa_sign
            elif type == 'T26_ZD':
                cmd = [0x31, 0x01, 0xD0, 0x02] + rsa_sign
            else:
                return [False, ['None']]
            return self.father.ServiceRun(cmd)
        
        def CheckProgrammingPreCondition(self):
            log = []
            cmd = [0x31, 0x01, 0x02, 0x03]
            log.append(zd_utility.ConvertBytes2Hex(cmd))
            res = self.father.transmit(cmd)
            if res is not None:
                log.append(zd_utility.ConvertBytes2Hex(res))
                if (res[0] == 0x71) and (res[1] == 0x01) and (res[2] == 0x02) and (res[3] == 0x03) and (res[4] == 0x00):
                    return [True, log]
                else:
                    return [False, log]
            else:
                return [False, log.append('Timeout')]