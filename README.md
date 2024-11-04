# EcuFuzz-2025

## Structure-Aware, Diagnosis-Guided ECU Firmware Fuzzing

We propose a structure-aware, diagnosis-guided framework, EcuFuzz, to comprehensively and effectively fuzz ECU firmwares. Specifically, EcuFuzz simultaneously considers external buses (i.e., CAN) and on-board buses (i.e., SPI). It leverages the structure of CAN and SPI to effectively mutate CAN messages and SPI sequences, and incorporates a dual-core microcontroller-based peripheral emulator to handle real-time SPI communication. In addition, EcuFuzz implements a new feedback mechanism to guide the fuzzing process. It leverages automotive diagnostic protocols to collect ECUs’ internal states, i.e., error-related variables, trouble codes, and exception contexts. 

Our compatibility evaluation on ten ECUs from three major Tier 1 automotive suppliers has indicated that our framework is compatible with nine ECUs. Our effectiveness evaluation on three representative ECUs has demonstrated that our framework detects nine previously unknown safety-critical faults, which have been patched by technicians from the suppliers.

<img src="D:\STM32CubeIDE Workstation\ecufuzz\Figure\overview.png" style="zoom: 25%;" />

## Run the Peripheral Emulator

We set up the peripheral emulator in STM32CubeIDE. Ensure that the hardware environment is fully set up as shown in figure below.

<img src="D:\STM32CubeIDE Workstation\ecufuzz\Figure\hardware_setup.jpg" style="zoom: 25%;" />

- First, open `./Peripheral_emulator/` directory in STM32CubeIDE.
- Build the STM32H745I_EVAL_CM7 and then build STM32H745I_EVAL_CM4. 
- Next, select the `main.c` files for both cores simultaneously and run.

## Run the Fuzzing Engine

The fuzzing engine of EcuFuzz works on PC and requires Python3. To install dependencies, run the command below in the  `./Fuzzing_engine/` directory.

```
$ pip install -r requirements.txt
```

The fuzzing engine includes both CAN message mutator and SPI sequence mutator, which operate in parallel. Execute the Fuzzer engine with the following command:

```
$ python3 main.py
```

The folder structure is shown below.

```
├─Fuzzing_engine 
│  ├─Config
│  │  │  Chery_E03_E0Y.dbc			# CAN DBC file
│  │  │  config.json				# Two CAN bus configuration
│  │  │  config1.json
│  │  │  GenerateKeyExImpl.dll
│  │  │  spilog.txt					# Spi log
│  │  │  symbol_table.sym			# Symbol table
│  │  │  
│  │  └─T26_ZD						# Configuration for ECU DTC
│  │          CanMessages.json
│  │          CarCfg.json
│  │          DtcList.json
│  │          FaultList.json
│  │          ImuCal.json
│  │          
│  ├─Mutator
│  │  │  can_fuzz.py				# CAN message mutator Code
│  │  │  main.py
│  │  │  spi_fuzz.py				# SPI sequence mutator Code
│  │  │  spi_mutator.py
│  │  │  uds_analyzer.py        	# UDS Analyzer Code
│  │  │
│  ├─spitest						# Utils for different modes of SPI communication
│  │  │  cg9reg_parsed.py			# Parse the cg9 manual
│  │  │  cg9_instructions.json		# Results of parsing cg9 manual(.json)
│  │  │  cg9_instructions.txt		# Results of parsing cg9 manual(.txt)
│  │  │  smi7reg_parsed.py			# Parse the smi7 manual
│  │  │  smi7_instructions.json
│  │  │  smi7_instructions.txt
│  │  │  smi8reg_parsed.py			# Parse the smi8 manual
│  │  │  smi8_instructions.json
│  │  │  smi8_instructions.txt
│  │  │  spi_parser.py				# Parse SPI frame structure according to three 		 │  │  │								parsed results of manual instructions
│  └─ZDCANLib						# Utils for CAN bus communication and UDS requests
│          requirements.txt
│          ZDcan.py
│          ZDcantp.py
│          ZDuds.py
│          ZDutility.py
```

