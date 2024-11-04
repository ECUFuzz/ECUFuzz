import can
import queue
import time
import threading

canCfgDefault = {'interface': 'virtual', 'app_name': 'CANalyzer', 'channel': 'virtual_ch', 'bitrate': 500000, 'sjw_abr': 1, 'tseg1_abr': 16, 'tseg2_abr': 3, 'fd': False, 'data_bitrate': 2000000, 'sjw_dbr': 1, 'tseg1_dbr': 16, 'tseg2_dbr': 3}

class zd_can(object):
    def __init__(self, canCfg=canCfgDefault):
        self.logfile = open('logfile.asc', 'wt')
        # allcan = can.detect_available_configs(interfaces='pcan')
        # print(allcan)
        self.fd = canCfg['fd']
        self.brs = canCfg['brs']
        device = canCfg['interface']
        if device == 'vector':
            self.bus = can.Bus(interface=canCfg['interface'], 
                                app_name=canCfg['app_name'], 
                                channel=canCfg['channel'], 
                                bitrate=canCfg['bitrate'], 
                                sjw_abr=canCfg['sjw_abr'], 
                                tseg1_abr=canCfg['tseg1_abr'], 
                                tseg2_abr=canCfg['tseg2_abr'], 
                                fd=canCfg['fd'],
                                data_bitrate=canCfg['data_bitrate'],
                                sjw_dbr=canCfg['sjw_dbr'],
                                tseg1_dbr=canCfg['tseg1_dbr'],
                                tseg2_dbr=canCfg['tseg2_dbr'])
        elif device == 'pcan':
            self.bus = can.Bus(interface=canCfg['interface'], 
                    app_name=canCfg['app_name'], 
                    channel=canCfg['channel'], 
                    bitrate=canCfg['bitrate'],
                    f_clock=canCfg['f_clock'],
                    f_clock_mhz=canCfg['f_clock_mhz'],
                    nom_brp=canCfg['nom_brp'],
                    nom_sjw=canCfg['sjw_abr'], 
                    nom_tseg1=canCfg['tseg1_abr'], 
                    nom_tseg2=canCfg['tseg2_abr'], 
                    fd=canCfg['fd'],
                    data_brp=canCfg['data_brp'],
                    data_bitrate=canCfg['data_bitrate'],
                    data_sjw=canCfg['sjw_dbr'],
                    data_tseg1=canCfg['tseg1_dbr'],
                    data_tseg2=canCfg['tseg2_dbr'])

        # self.recvBuffer = queue.Queue(5000)
        # logger = can.Logger("logfile.asc")
        # listeners = [
        #     self.__callback_onReceive,
        #     # logger,
        # ]
        # self.notifier = can.Notifier(self.bus, listeners) # Set up a listener
        self.lock = threading.RLock()
        self.receiveTime = 0
        self.receiveTimestamp = 0
        self.version = ["CAN V2.1"]
        self.threadFunc = threading.Thread(target=self.threadSending)
        self.periodicMsgCfgList = []
        self.threadRunning = False
        self.threadExit = False
        self.threadFunc.start()
        

    def threadSending(self):
        while self.threadExit == False:
            if self.threadRunning:
                currTime = time.time()
                for msgCfg in self.periodicMsgCfgList:
                    if (currTime - msgCfg['ts']) > msgCfg['period']:
                        msg = msgCfg['msg']
                        self.send(msg.arbitration_id, msg.data)
                        msgCfg['ts'] = currTime
                time.sleep(0.01)
            else:
                time.sleep(0.5)

    def setFilters(self, filter_id):
        filters = []
        for id in filter_id:
            if id < 0x800:
                filters.append({"can_id": id, "can_mask": 0x7FF, "extended": False})
            else:
                filters.append({"can_id": id, "can_mask": 0x1FFFFFFF, "extended": True})
        self.bus.set_filters(filters)

    def send(self, tx_id, listdata):
        self.lock.acquire()
        is_extended_id = False
        if tx_id < 0x800:
            is_extended_id = False
        else:
            is_extended_id = True
        msg = can.Message(arbitration_id=tx_id, timestamp=((time.time() - self.receiveTime) + self.receiveTimestamp), is_fd = self.fd, is_rx=False, bitrate_switch=self.brs, is_extended_id=is_extended_id, data=listdata)
        print(msg, file=self.logfile, flush = True)
        self.bus.send(msg, 0.07)
        self.lock.release()

    def start_periodic(self, msg, period):
        # self.bus.send_periodic(msg, period)
        self.periodicMsgCfgList.append({'msg':msg, 'ts':0.0, 'period':period})
        self.threadRunning = True
    
    def stop_periodic(self):
        # self.bus.stop_all_periodic_tasks()
        self.threadRunning = False
        self.periodicMsgCfgList = []
    
    def remove_periodic(self, msgid):
        for msgCfg in self.periodicMsgCfgList:
            arbitration_id = msgCfg['msg'].arbitration_id
            if msgid == arbitration_id:
                self.periodicMsgCfgList.remove(msgCfg)

    # def __callback_onReceive(self, msg):
    #     print(msg, file=self.logfile, flush = True)
    #     if not self.recvBuffer.full():
    #         self.recvBuffer.put_nowait(msg)

    def recv(self, rx_id, timeout=0.0):
        msg = self.bus.recv(timeout)
        if msg is not None:
            self.receiveTime = time.time()
            self.receiveTimestamp = msg.timestamp
            print(msg, file=self.logfile, flush = True)
            if rx_id == msg.arbitration_id:
                return msg
    
    def recv_msg(self):
        return self.bus.recv(0.0)
        # st=time.time()
        # while ((time.time() - st) < timeout):
        #     if not self.recvBuffer.empty():
        #         msg = self.recvBuffer.get_nowait()
        #         if rx_id == msg.arbitration_id:
        #             return msg
        #     else:
        #         return None
        # return None

    def close(self):
        # self.notifier.stop()
        self.threadExit = True
        self.threadFunc.join()
        self.bus.shutdown()
        self.logfile.close()

    
    def flush_tx_buffer(self):
        self.bus.flush_tx_buffer()

    # def clearRecvBuffer(self):
    #     self.recvBuffer.queue.clear()