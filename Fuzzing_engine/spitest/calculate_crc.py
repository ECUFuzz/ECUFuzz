def crc3_spi(data_uint32: int) -> int:
    # CRC parameters
    poly = 0b1011  # Polynomial: X^3 + X + 1
    width = 3
    init = 0b001  # Initial value

    # Mask to remove the last 5 bits and keep bits 31 to 5
    mask = 0xFFFFFFE0
    # Apply mask and shift right to remove last 5 bits
    data_bin = (data_uint32 & mask) >> 5

    # Convert data to string to use in existing CRC calculation
    data_str = format(data_bin, '027b') + '001'  # Append zeros as per existing logic

    # Convert input data to binary
    data_bin = int(data_str, 2)

    # Main CRC calculation
    for i in range(len(data_str) - width):
        # If the leading bit is 1, XOR with polynomial
        if data_bin & (1 << (len(data_str) - 1 - i)):
            data_bin ^= poly << (len(data_str) - width - 1 - i)

    # Extract the CRC result
    crc_result = data_bin & ((1 << width) - 1)
    
    # Combine the original data (without the last 5 bits) with the CRC result (placed in bits 2 to 4)
    result = (data_uint32 & 0xFFFFFFE0) | (crc_result << 2)
    
    return result

# Example usage
data_uint32 = 0x44001E1C  # Example data in hex format
result = crc3_spi(data_uint32)
result_bin = format(result, '032b')  # Convert result to binary string for visualization
result, result_bin
