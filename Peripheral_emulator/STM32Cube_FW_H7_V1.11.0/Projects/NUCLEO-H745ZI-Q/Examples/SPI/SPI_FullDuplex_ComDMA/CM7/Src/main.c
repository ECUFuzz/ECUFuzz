
#include "main.h"
enum {
  TRANSFER_WAIT,
  TRANSFER_COMPLETE,
  TRANSFER_ERROR
};
/* Private function prototypes -----------------------------------------------*/
static void MPU_Config(void);
static void SystemClock_Config(void);
static void Error_Handler(uint8_t spiNumber);
static void CPU_CACHE_Enable(void);
static void handleSPIComplete(SPI_HandleTypeDef *hspi, volatile uint32_t *activeBufferHalf, uint8_t *doubleBuffer, uint8_t *aRxBuffer, uint32_t chunkSize, uint8_t spiNumber);
static void configureSPI(SPI_HandleTypeDef* spiHandle, SPI_TypeDef* SPIx);
// void prepareNextChunk(uint8_t* buffer, uint8_t spiNumber);

/* Private functions ---------------------------------------------------------*/
SPI_HandleTypeDef SpiHandle1;
SPI_HandleTypeDef SpiHandle2;

// Existing definitions for SPI1
#define TX_BUFFER_SIZE1 16
#define CHUNK_SIZE1 16
#define NUM_SEQUENCES1 61
#define DOUBLE_BUFFER_SIZE1 (2 * CHUNK_SIZE1)

// New definitions for SPI2
#define TX_BUFFER_SIZE2 28
#define CHUNK_SIZE2 28  // Assuming we want to transfer the entire buffer in one chunk
#define NUM_SEQUENCES2 36  // Assuming the same number of sequences as SPI1
#define DOUBLE_BUFFER_SIZE2 (2 * CHUNK_SIZE2)

// Define the shared memory region in SRAM4
#define SHARED_MEMORY_ADDRESS 0x38000000
#define SHARED_MEMORY_SIZE (TX_BUFFER_SIZE1 * NUM_SEQUENCES1 + TX_BUFFER_SIZE2 * NUM_SEQUENCES2)

#define MAX_SEQUENCES 100  // Consistent with M4 core code

typedef struct {
    uint8_t aTxBuffers1[MAX_SEQUENCES][TX_BUFFER_SIZE1];
    uint8_t aTxBuffers2[MAX_SEQUENCES][TX_BUFFER_SIZE2];
    uint32_t sequenceRepeatCounts1[MAX_SEQUENCES];
    uint32_t sequenceRepeatCounts2[MAX_SEQUENCES];
    uint32_t actualNumSequences1;
    uint32_t actualNumSequences2;
    volatile uint32_t flag;
} SharedMemory_TypeDef;
static uint32_t actualNumSequences1 = 0;
static uint32_t actualNumSequences2 = 0;
// Define the shared memory pointer
#define SHARED_MEMORY ((SharedMemory_TypeDef*)SHARED_MEMORY_ADDRESS)

__IO uint32_t wTransferState1 = TRANSFER_WAIT;
__IO uint32_t wTransferState2 = TRANSFER_WAIT;

// Buffers for SPI1
uint8_t doubleBuffer1[DOUBLE_BUFFER_SIZE1];
ALIGN_32BYTES(uint8_t aRxBuffer1[((TX_BUFFER_SIZE1+31)/32)*32]);

// Buffers for SPI2
uint8_t doubleBuffer2[DOUBLE_BUFFER_SIZE2];
ALIGN_32BYTES(uint8_t aRxBuffer2[((TX_BUFFER_SIZE2+31)/32)*32]);

// State variables for SPI1
volatile uint32_t activeBufferHalf1 = 0;
volatile uint32_t currentSequence1 = 0;
volatile uint32_t currentRepeatCount1 = 0;
volatile uint32_t txIndex1 = 0;

// State variables for SPI2
volatile uint32_t activeBufferHalf2 = 0;
volatile uint32_t currentSequence2 = 0;
volatile uint32_t currentRepeatCount2 = 0;
volatile uint32_t txIndex2 = 0;

#define USE_HAL_SPI_REGISTER_CALLBACKS = 1U;
#define HSEM_ID_0 (0U) /* HW semaphore 0*/



/**
  * @brief  Main program
  * @param  None
  * @retval None
  */
int main(void)
{
  int32_t timeout;
  /* Configure the MPU attributes */
  MPU_Config();

  /* Enable the CPU Cache */
  // CPU_CACHE_Enable();

  /* Wait until CPU2 boots and enters in stop mode or timeout*/
  timeout = 0xFFFF;
  while((__HAL_RCC_GET_FLAG(RCC_FLAG_D2CKRDY) != RESET) && (timeout-- > 0));
  if ( timeout < 0 )
  {
    Error_Handler(1);
  }

  HAL_Init();

  /* Configure the system clock to 400 MHz */
  SystemClock_Config();

  /* When system initialization is finished, Cortex-M7 will release Cortex-M4  by means of
     HSEM notification */

  /*HW semaphore Clock enable*/
  __HAL_RCC_HSEM_CLK_ENABLE();

  // Enable D3 domain SRAM1 clock in sleep mode
  __HAL_RCC_D3SRAM1_CLK_SLEEP_ENABLE();

  memset((void*)SHARED_MEMORY, 0, sizeof(SharedMemory_TypeDef));

  /*Take HSEM */
  HAL_HSEM_FastTake(HSEM_ID_0);
  /*Release HSEM in order to notify the CPU2(CM4)*/
  HAL_HSEM_Release(HSEM_ID_0,0);

  /* wait until CPU2 wakes up from stop mode */
  timeout = 0xFFFF;
  while((__HAL_RCC_GET_FLAG(RCC_FLAG_D2CKRDY) == RESET) && (timeout-- > 0));
  if ( timeout < 0 )
  {
    Error_Handler(1);
  }

  /* Configure LED1, LED2 and LED3 */
  BSP_LED_Init(LED1);
  BSP_LED_Init(LED2);
  BSP_LED_Init(LED3);

  // Configure SPI1 and SPI2
  configureSPI(&SpiHandle1, SPI1);
  configureSPI(&SpiHandle2, SPI2);
  HAL_Delay(500);
  // Prepare initial chunks for both SPIs
  prepareNextChunk(&doubleBuffer1[0], 1);
  prepareNextChunk(&doubleBuffer1[CHUNK_SIZE1], 1);
  prepareNextChunk(&doubleBuffer2[0], 2);
  prepareNextChunk(&doubleBuffer2[CHUNK_SIZE2], 2);
  // Start the first transfer for both SPIs
  if(HAL_SPI_TransmitReceive_IT(&SpiHandle1, &doubleBuffer1[0], &aRxBuffer1[0], CHUNK_SIZE1) != HAL_OK) {
      Error_Handler(1);
  }
  if(HAL_SPI_TransmitReceive_IT(&SpiHandle2, &doubleBuffer2[0], &aRxBuffer2[0], CHUNK_SIZE2) != HAL_OK) {
      Error_Handler(2);
  }
  while (1) {
    checkSharedMemoryFlag();

    if (wTransferState1 == TRANSFER_ERROR) {
      Error_Handler(1);
    }
    if (wTransferState2 == TRANSFER_ERROR) {
      Error_Handler(2);
    }
}
}

static void configureSPI(SPI_HandleTypeDef* spiHandle, SPI_TypeDef* SPIx)
{
    spiHandle->Instance = SPIx;
    spiHandle->Init.Mode = SPI_MODE_SLAVE;
    spiHandle->Init.Direction = SPI_DIRECTION_2LINES;
    spiHandle->Init.DataSize = SPI_DATASIZE_8BIT;
    spiHandle->Init.CLKPolarity = SPI_POLARITY_LOW;
    spiHandle->Init.CLKPhase = SPI_PHASE_2EDGE;
    spiHandle->Init.NSS = SPI_NSS_HARD_INPUT;
    spiHandle->Init.FirstBit = SPI_FIRSTBIT_MSB;
    spiHandle->Init.TIMode = SPI_TIMODE_DISABLE;
    spiHandle->Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    spiHandle->Init.CRCPolynomial = 7;
    spiHandle->Init.NSSPMode = SPI_NSS_PULSE_DISABLE;
    spiHandle->Init.NSSPolarity = SPI_NSS_POLARITY_LOW;
    spiHandle->Init.FifoThreshold = SPI_FIFO_THRESHOLD_01DATA;
    spiHandle->Init.TxCRCInitializationPattern = SPI_CRC_INITIALIZATION_ALL_ZERO_PATTERN;
    spiHandle->Init.RxCRCInitializationPattern = SPI_CRC_INITIALIZATION_ALL_ZERO_PATTERN;
    spiHandle->Init.MasterSSIdleness = SPI_MASTER_SS_IDLENESS_00CYCLE;
    spiHandle->Init.MasterInterDataIdleness = SPI_MASTER_INTERDATA_IDLENESS_00CYCLE;
    spiHandle->Init.MasterReceiverAutoSusp = SPI_MASTER_RX_AUTOSUSP_DISABLE;
    spiHandle->Init.IOSwap = SPI_IO_SWAP_DISABLE;

    if(HAL_SPI_Init(spiHandle) != HAL_OK)
    {
        Error_Handler(SPIx == SPI1 ? 1 : 2);
    }

    // Set different interrupt priorities
    if (SPIx == SPI1) {
        HAL_NVIC_SetPriority(SPI1_IRQn, 3, 0);
        HAL_NVIC_EnableIRQ(SPI1_IRQn);
    } else if (SPIx == SPI2) {
        HAL_NVIC_SetPriority(SPI2_IRQn, 2, 0);
        HAL_NVIC_EnableIRQ(SPI2_IRQn);
    }
}

static void SystemClock_Config(void)
{
  RCC_ClkInitTypeDef RCC_ClkInitStruct;
  RCC_OscInitTypeDef RCC_OscInitStruct;
  HAL_StatusTypeDef ret = HAL_OK;

  /*!< Supply configuration update enable */
  HAL_PWREx_ConfigSupply(PWR_DIRECT_SMPS_SUPPLY);
  /* The voltage scaling allows optimizing the power consumption when the device is
     clocked below the maximum system frequency, to update the voltage scaling value
     regarding system frequency refer to product datasheet.  */
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

  while(!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {}

  /* Enable HSE Oscillator and activate PLL with HSE as source */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSIState = RCC_HSI_OFF;
  RCC_OscInitStruct.CSIState = RCC_CSI_OFF;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;

  RCC_OscInitStruct.PLL.PLLM = 5;
  RCC_OscInitStruct.PLL.PLLN = 300;
  RCC_OscInitStruct.PLL.PLLFRACN = 0;
  RCC_OscInitStruct.PLL.PLLP = 2;
  RCC_OscInitStruct.PLL.PLLR = 2;
  RCC_OscInitStruct.PLL.PLLQ = 24;

  RCC_OscInitStruct.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
  RCC_OscInitStruct.PLL.PLLRGE = RCC_PLL1VCIRANGE_1;
  ret = HAL_RCC_OscConfig(&RCC_OscInitStruct);
  if(ret != HAL_OK)
  {
    Error_Handler(1);
  }

/* Select PLL as system clock source and configure  bus clocks dividers */
  RCC_ClkInitStruct.ClockType = (RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_D1PCLK1 | RCC_CLOCKTYPE_PCLK1 | \
                                 RCC_CLOCKTYPE_PCLK2  | RCC_CLOCKTYPE_D3PCLK1);

  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV2;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV2;
  RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV2;
  ret = HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_4);
  if(ret != HAL_OK)
  {
    Error_Handler(1);
  }
  __HAL_RCC_CSI_ENABLE() ;

  __HAL_RCC_SYSCFG_CLK_ENABLE() ;

  HAL_EnableCompensationCell();
}
// Modify the HAL_SPI_TxRxCpltCallback
void HAL_SPI_TxRxCpltCallback(SPI_HandleTypeDef *hspi)
{
    if (hspi->Instance == SPI1) {
        handleSPIComplete(&SpiHandle1, &activeBufferHalf1, doubleBuffer1, aRxBuffer1, CHUNK_SIZE1, 1);
    } else if (hspi->Instance == SPI2) {
        handleSPIComplete(&SpiHandle2, &activeBufferHalf2, doubleBuffer2, aRxBuffer2, CHUNK_SIZE2, 2);
    }
}

static void handleSPIComplete(SPI_HandleTypeDef *hspi, volatile uint32_t *activeBufferHalf, 
                       uint8_t *doubleBuffer, uint8_t *aRxBuffer, uint32_t chunkSize, uint8_t spiNumber)
{
    *activeBufferHalf = 1 - *activeBufferHalf;

    if(HAL_SPI_TransmitReceive_IT(hspi, &doubleBuffer[*activeBufferHalf * chunkSize], aRxBuffer, chunkSize) != HAL_OK) {
        Error_Handler(spiNumber);
    }

    prepareNextChunk(&doubleBuffer[*activeBufferHalf ? 0 : chunkSize], spiNumber);

    BSP_LED_Toggle(spiNumber == 1 ? LED1 : LED2);
}

void HAL_SPI_ErrorCallback(SPI_HandleTypeDef *hspi)
{
  if (hspi->Instance == SPI1) {
    wTransferState1 = TRANSFER_ERROR;
  } else if (hspi->Instance == SPI2) {
    wTransferState2 = TRANSFER_ERROR;
  }
}

static void Error_Handler(uint8_t spiNumber)
{
  BSP_LED_Off(LED1);
  BSP_LED_Off(LED2);
  BSP_LED_On(LED3);
  // Different error handling can be performed based on spiNumber
  while(1)
  {
    // Add different LED blinking patterns to indicate various SPI errors
    if (spiNumber == 1) {
      BSP_LED_Toggle(LED1);
    } else if (spiNumber == 2) {
      BSP_LED_Toggle(LED2);
    }
    HAL_Delay(500);
  }
}

/**
  * @brief  Configure the MPU attributes
  * @param  None
  * @retval None
  */
static void MPU_Config(void)
{
  MPU_Region_InitTypeDef MPU_InitStruct;

  /* Disable the MPU */
  HAL_MPU_Disable();

  /* Configure the MPU as Strongly ordered for not defined regions */
  MPU_InitStruct.Enable = MPU_REGION_ENABLE;
  MPU_InitStruct.BaseAddress = 0x00;
  MPU_InitStruct.Size = MPU_REGION_SIZE_4GB;
  MPU_InitStruct.AccessPermission = MPU_REGION_NO_ACCESS;
  MPU_InitStruct.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;
  MPU_InitStruct.IsCacheable = MPU_ACCESS_NOT_CACHEABLE;
  MPU_InitStruct.IsShareable = MPU_ACCESS_SHAREABLE;
  MPU_InitStruct.Number = MPU_REGION_NUMBER0;
  MPU_InitStruct.TypeExtField = MPU_TEX_LEVEL0;
  MPU_InitStruct.SubRegionDisable = 0x87;
  MPU_InitStruct.DisableExec = MPU_INSTRUCTION_ACCESS_DISABLE;

  HAL_MPU_ConfigRegion(&MPU_InitStruct);

  /* Enable the MPU */
  HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t* file, uint32_t line)
{
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */

  /* Infinite loop */
  while (1)
  {
  }
}
#endif

/**
  * @brief  CPU L1-Cache enable.
  * @param  None
  * @retval None
  */
static void CPU_CACHE_Enable(void)
{
  /* Enable I-Cache */
  SCB_EnableICache();

  /* Enable D-Cache */
  SCB_EnableDCache();
}


// Modify the prepareNextChunk function
void prepareNextChunk(uint8_t* buffer, uint8_t spiNumber)
{
    uint32_t txBufferSize = (spiNumber == 1) ? TX_BUFFER_SIZE1 : TX_BUFFER_SIZE2;
    uint32_t chunkSize = (spiNumber == 1) ? CHUNK_SIZE1 : CHUNK_SIZE2;
    uint32_t numSequences = (spiNumber == 1) ? SHARED_MEMORY->actualNumSequences1 : SHARED_MEMORY->actualNumSequences2;
    volatile uint32_t *currentSequence = (spiNumber == 1) ? &currentSequence1 : &currentSequence2;
    volatile uint32_t *currentRepeatCount = (spiNumber == 1) ? &currentRepeatCount1 : &currentRepeatCount2;
    volatile uint32_t *txIndex = (spiNumber == 1) ? &txIndex1 : &txIndex2;
    const uint32_t *sequenceRepeatCounts = (spiNumber == 1) ? SHARED_MEMORY->sequenceRepeatCounts1 : SHARED_MEMORY->sequenceRepeatCounts2;

    *currentSequence = *currentSequence % numSequences;

    uint32_t remainingBytes = txBufferSize - *txIndex;
    uint32_t bytesToCopy = (remainingBytes < chunkSize) ? remainingBytes : chunkSize;

    if (bytesToCopy > 0) {
        if (spiNumber == 1) {
            memcpy(buffer, &SHARED_MEMORY->aTxBuffers1[*currentSequence][*txIndex], bytesToCopy);
        } else {
            memcpy(buffer, &SHARED_MEMORY->aTxBuffers2[*currentSequence][*txIndex], bytesToCopy);
        }
    }

    if (bytesToCopy < chunkSize) {
        memset(&buffer[bytesToCopy], 0, chunkSize - bytesToCopy);
    }

    *txIndex += bytesToCopy;
    if (*txIndex >= txBufferSize) {
        *txIndex = 0;
        (*currentRepeatCount)++;
        if (*currentSequence < numSequences - 1) {
            if (*currentRepeatCount >= sequenceRepeatCounts[*currentSequence]) {
                *currentRepeatCount = 0;
                *currentSequence = (*currentSequence + 1) % numSequences;
            }
        } else {
            if (*currentRepeatCount >= sequenceRepeatCounts[*currentSequence]) {
                *currentRepeatCount = 0;
                *txIndex = 0;
            }
        }
    }
}

void checkSharedMemoryFlag(void)
{
    if (SHARED_MEMORY->flag == 1)
    {
        // Update local variables
        actualNumSequences1 = SHARED_MEMORY->actualNumSequences1;
        actualNumSequences2 = SHARED_MEMORY->actualNumSequences2;

        // Reset transmission status
        currentSequence1 = 0;
        currentSequence2 = 0;
        currentRepeatCount1 = 0;
        currentRepeatCount2 = 0;
        txIndex1 = 0;
        txIndex2 = 0;

        // Reprepare the initial chunk
        prepareNextChunk(&doubleBuffer1[0], 1);
        prepareNextChunk(&doubleBuffer1[CHUNK_SIZE1], 1);
        prepareNextChunk(&doubleBuffer2[0], 2);
        prepareNextChunk(&doubleBuffer2[CHUNK_SIZE2], 2);

        // Clear flags
        SHARED_MEMORY->flag = 0;
    }
}