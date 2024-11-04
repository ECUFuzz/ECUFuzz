from ZDCANLib.ZDcan import zd_can
from ZDCANLib.ZDutility import TimeoutTimer
from enum import Enum, IntEnum

class CanTpState(Enum):
    IDLE = 0
    SEND_SINGLE_FRAME = 1
    SEND_FIRST_FRAME = 2
    SEND_CONSECUTIVE_FRAME = 3
    SEND_FLOW_CONTROL = 4
    WAIT_FLOW_CONTROL = 5
    WAIT_STMIN_TIMEOUT = 6
    WAIT_WAIT_TIMEOUT = 7
    RECEIVING_CONSECUTIVE_FRAME = 8


class CanTpMessageType(IntEnum):
    SINGLE_FRAME = 0
    FIRST_FRAME = 1
    CONSECUTIVE_FRAME = 2
    FLOW_CONTROL = 3


class CanTpFsTypes(IntEnum):
    CONTINUE_TO_SEND = 0x00
    WAIT = 0x01
    OVERFLOW = 0x02

CANTP_MAX_PAYLOAD_LENGTH = 4095                    # hardcoded maximum based on the ISO 15765 standard
N_PCI_INDEX = 0
SINGLE_FRAME_DL_INDEX = 0
SINGLE_FRAME_DATA_START_INDEX = 1
FIRST_FRAME_DL_INDEX_HIGH = 0
FIRST_FRAME_DL_INDEX_LOW = 1
FIRST_FRAME_DATA_START_INDEX = 2
FC_BS_INDEX = 1
FC_STMIN_INDEX = 2
CONSECUTIVE_FRAME_SEQUENCE_NUMBER_INDEX = 0
CONSECUTIVE_FRAME_SEQUENCE_DATA_START_INDEX = 1
FLOW_CONTROL_BS_INDEX = 1
FLOW_CONTROL_STMIN_INDEX = 2

class zd_cantp(object):
    def __init__(self, cantpConfig=None, canConfig=None, can=None):
        if cantpConfig is not None:      
            self.P2_Star = cantpConfig['P2_Star']
        else:
            print("config.json is not available, use default")
            self.P2_Star = 1
        if can is not None:
            self.can = can
        else:
            if canConfig is not None:
                self.can = zd_can(canConfig)
            else:
                self.can = zd_can()
        self.version = ['CANTP V1.1'] + self.can.version
        if self.can.fd:
            if 'max_pdu_length_fd' in cantpConfig:
                self.maxPduLen = cantpConfig['max_pdu_length_fd']
            else:
                self.maxPduLen = 64
        else:
            if 'max_pdu_length' in cantpConfig:
                self.maxPduLen = cantpConfig['max_pdu_length']
            else:
                self.maxPduLen = 8
        

    def get_can(self):
        return self.can

    def send(self, tx_id, rx_id, payload, timeout=0.75):
        self.can.setFilters([rx_id])
        payloadLength = len(payload)
        payloadPtr = 0
        sequenceNumber = 1
        timeoutTm = TimeoutTimer(timeout)
        stMinTimer = TimeoutTimer(1)
        state = CanTpState.IDLE

        if payloadLength > CANTP_MAX_PAYLOAD_LENGTH:
            raise Exception("Payload too large for CAN Transport Protocol")

        if payloadLength < self.maxPduLen:
            state = CanTpState.SEND_SINGLE_FRAME
        else:
            state = CanTpState.SEND_FIRST_FRAME

        # self.can.clearRecvBuffer()
        timeoutTm.Start()
        while timeoutTm.IsNotExpired():
            txPdu = []
            rxMsg = self.can.recv(rx_id)
            if rxMsg is not None:
                rxPdu = rxMsg.data
                N_PCI = (rxPdu[0] & 0xF0) >> 4
                if N_PCI == CanTpMessageType.FLOW_CONTROL:
                    fs = rxPdu[0] & 0x0F
                    bs = rxPdu[1] & 0xFF
                    stMin = self.decode_stMin(rxPdu[2])
                    if fs == CanTpFsTypes.WAIT:
                        raise Exception("Wait not currently supported")
                    elif fs == CanTpFsTypes.OVERFLOW:
                        raise Exception("Overflow received from ECU")
                    elif fs == CanTpFsTypes.CONTINUE_TO_SEND:
                        if state == CanTpState.WAIT_FLOW_CONTROL:
                            state = CanTpState.SEND_CONSECUTIVE_FRAME
                            stMinTimer.Start(stMin)
                            timeoutTm.Restart()
                        else:
                            print("Unexcept Flow Control")
                    else:
                        print("Unexcept Flow Control - fs")
            if state == CanTpState.SEND_SINGLE_FRAME:
                if payloadLength > 8:
                    txPdu.append((payloadLength & 0x0F00) >> 8)
                    txPdu.append((payloadLength & 0x00FF))
                else:
                    txPdu.append(payloadLength)
                txPdu += payload
                self.can.send(tx_id, self.fillArray(txPdu, 0, self.getDlc(len(txPdu))))
                break
            elif state == CanTpState.SEND_FIRST_FRAME:
                txPdu.append(0x10 + ((payloadLength & 0x0F00) >> 8))
                txPdu.append(payloadLength & 0x00FF)
                txPdu += payload[:self.maxPduLen-2]
                payloadPtr += self.maxPduLen-2
                self.can.send(tx_id, self.fillArray(txPdu))
                state = CanTpState.WAIT_FLOW_CONTROL
                timeoutTm.Restart()
            elif state == CanTpState.SEND_CONSECUTIVE_FRAME:
                if(stMinTimer.IsExpired()):
                   txPdu.append(0x20 + sequenceNumber)
                   txPdu[1:] += payload[payloadPtr:payloadPtr+self.maxPduLen - 1]
                   payloadPtr += self.maxPduLen - 1
                   self.can.send(tx_id, self.fillArray(txPdu))
                   sequenceNumber = (sequenceNumber + 1) % 16
                   stMinTimer.Restart()
                   timeoutTm.Restart()
                   if payloadPtr >= payloadLength:
                       break

    def send_nowait(self, tx_id, payload):
        txPdu = []
        payloadLength = len(payload)
        if payloadLength > CANTP_MAX_PAYLOAD_LENGTH:
            raise Exception("Payload too large for CAN Transport Protocol")
        txPdu.append(payloadLength)
        txPdu += payload
        self.can.send(tx_id, self.fillArray(txPdu))

    def recv(self, tx_id, rx_id, timeout=0.75):
        payload = []
        payloadPtr = 0
        payloadLength = None
        sequenceNumberExpected = 1
        
        timeoutTm = TimeoutTimer(timeout)
        timeoutTm.Start()
        state = CanTpState.IDLE
        while timeoutTm.IsNotExpired():
            rxMsg = self.can.recv(rx_id)
            if(rxMsg is None):
                continue
            rxPdu = rxMsg.data
            rxDlc = rxMsg.dlc
            # print(hex(rxPdu[0]))
            if rxPdu is not None:
                N_PCI = (rxPdu[0] & 0xF0) >> 4
                if state == CanTpState.IDLE:
                    if N_PCI == CanTpMessageType.SINGLE_FRAME:
                        if(rxPdu[1] == 0x7F) and (rxPdu[3] == 0x78): # pending response, wait P2*
                            timeoutTm.Restart(self.P2_Star)
                        else:
                            # For CAN FD messages, if a frame length exceeds 16 bytes, 
                            # the original half-byte length in the PCI will not be sufficient. 
                            # It needs to be extended by adding an additional byte, 
                            # using 1.5 bytes to represent the length
                            if rxDlc < 16:
                                payloadLength = rxPdu[0] & 0x0F
                                payload = rxPdu[1:]
                            else:
                                payloadLength = ((rxPdu[0] & 0x0F) << 8) + rxPdu[1]
                                payload = rxPdu[2:]
                            return payload[:payloadLength]
                    if N_PCI == CanTpMessageType.FIRST_FRAME:
                        payload = rxPdu[2:]
                        payloadLength = ((rxPdu[0] & 0x0F) << 8) + rxPdu[1]
                        payloadPtr = self.maxPduLen - 2
                        #send flow control
                        self.can.send(tx_id, self.fillArray([0x30,0x00,0x0A]))
                        state = CanTpState.RECEIVING_CONSECUTIVE_FRAME
                        timeoutTm.Restart()
                elif state == CanTpState.RECEIVING_CONSECUTIVE_FRAME:
                    if N_PCI == CanTpMessageType.CONSECUTIVE_FRAME:
                        sequenceNumber = rxPdu[0] & 0x0F
                        if sequenceNumber != sequenceNumberExpected:
                            print('error ' + str(sequenceNumber) + ' ' + str(sequenceNumberExpected))
                            # raise Exception("Consecutive frame sequence out of order")
                            print("Consecutive frame sequence out of order")
                        else:
                            sequenceNumberExpected = (sequenceNumberExpected + 1) % 16
                        payload += rxPdu[1:]
                        payloadPtr += self.maxPduLen - 1
                        if payloadPtr >= payloadLength:
                            return payload[:payloadLength]
                        else:
                            timeoutTm.Restart()
                    else:
                        print(rxPdu)
                        print(state)
                        # raise Exception("Unexpected PDU received")
                        print("Unexpected PDU received")
                else:
                    # raise Exception("Unexpected CANTP State")
                    print("Unexpected CANTP State")
        return None

    def getDlc(self, canlen):
        if canlen <= 8:
            return 8
        elif canlen <= 12:
            return 12
        elif canlen <= 16:
            return 16
        elif canlen <= 20:
            return 20
        elif canlen <= 24:
            return 24
        elif canlen <= 32:
            return 32
        elif canlen <= 48:
            return 48
        elif canlen <= 64:
            return 64
        else:
            return 8

    def fillArray(self, data, fillValue=0, dlc=None):
        output = []
        if dlc == None:
            dlc = self.maxPduLen
        for i in range(0, dlc):
            output.append(fillValue)
        for i in range(0, len(data)):
            output[i] = data[i]
        return output
    
    def decode_stMin(self, val):
        if (val <= 0x7F):
            time = val / 1000
            return time
        elif (
                (val >= 0xF1) &
                (val <= 0xF9)
        ):
            time = (val & 0x0F) / 10000
            return time
        else:
            raise Exception("Unknown STMin time")
    
    def close(self):
        self.can.close()
        