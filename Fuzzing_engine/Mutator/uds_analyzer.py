import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
import logging


logger = logging.getLogger(__name__)
handler = logging.FileHandler("log.txt")
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

console = logging.StreamHandler()
console.setLevel(logging.INFO)

logger.addHandler(handler)
logger.addHandler(console)


# Monitor
class UdsAnalyzer:
    def __init__(self, uds, elf_file):
        self.uds = uds
        self.memory_addrs = self.extract_symbol_table(elf_file)
    

    # Extract memory addresses and data length of key variables
    def extract_symbol_table(self, elf_file):
        # Retrieve the memory address and data length to query by analyzing the ELF file, 
        # then obtain the corresponding memory values
        with open(elf_file, 'r') as f:
            lines = f.readlines()
        memory_addrs = {}       # {addr: data_length}

        for l in lines:
            if 'error' in l or 'invalid' in l or 'fault' in l:
                addr, _, memo_size, _ = l.rstrip('\n').split(',')
                memory_addrs[addr] = int(memo_size)

        return memory_addrs


    def monitor(self, spilog):
        # set flag
        error_flag = 0
        
        #### Monitoring Diagnostic Trouble Codes. ####
        # 0x19 0x01 request
        res_flag, log, dtclist = self.uds.ReadDtc([0x19, 0x01, 0xFF])
        if res_flag and len(dtclist):
            logger.error(f"DTC: {dtclist}")
            self.error_record(spilog, log)
            error_flag = 1

            # If dtc exists, use 0x14 0xff request to clear dtc list, and then continue
            res2, log2, dtclist = self.uds.ReadDtc([0x14, 0xFF, 0xFF])
            if res2:
                logger.info("DTC list has been cleared.")
            else:
                logger.error("Failed to clear DTC list.")
            
        
        #### Inspecting Memory State Variables ####
        for addr in self.memory_addrs:
            res = self.uds.ReadMemory(addr, self.memory_addrs[addr])
            if res is not None:
                if res[0] == 0x63:
                    databuffer = res[1:]
                    if True in databuffer:
                        error_flag = 1
                else:
                    error_flag = 1
                    logger.error(f"NRC code: {res[0]}")
                    self.error_record(spilog, res[0])
            
        return error_flag


    # Recorder
    def error_record(self, spilog, anomaly_info):
        with open('anomalies.log', 'a') as f:
            f.write(f"Input: {spilog}, Anomaly: {anomaly_info}\n")
