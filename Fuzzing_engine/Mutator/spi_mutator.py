import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
import numpy as np
import random
import math


# SPI Mutator
#### inheriting common mutation operators from American Fuzzy Lop (AFL) ####
def bit_flip(data, bit_length):
    print("Use bit flip!")
    bit_pos = random.randint(0, bit_length - 1)
    return data ^ (1 << bit_pos)

def byte_flip(data, bit_length):
    print("Use byte flip!")
    data = bytearray(data.to_bytes(bit_length // 8, 'big'))
    if bit_length < 8:
        pass
    else:
        byte_pos = random.randint(0, bit_length/8 - 1)
        data[byte_pos] ^= 0xFF
    return int.from_bytes(bytes(data),'big')

def arithmetic_op(data, bit_length):
    print("Use arithmetic_op!")
    data = bytearray(data.to_bytes(bit_length // 8, 'big'))
    byte_pos = random.randint(0, bit_length//8 - 1)
    add_sub_val = random.choice([-1, 1]) * random.randint(1, 255)
    data[byte_pos] = (data[byte_pos] + add_sub_val) % 256   # Prevent overflow
    return int.from_bytes(bytes(data),'big')


#### Adding enhanced operators ####
def physical_boundary_op(mutated_data, bit_length, min_v, max_v):
    print("Use physical_boundary_op!")
    if mutated_data < min_v:
        mutated_data = min_v
    elif mutated_data > max_v:
        mutated_data = max_v
    
    return mutated_data

def special_value_op(data, is_float):
    print("Use special_value_op")
    if is_float:
        return random.choice([math.nan, math.inf, -math.inf])
    else:
        print("Warning: Special values only apply to floating-point numbers")
        return data
        
# SPI Mutation
def mutation(data, bit_length, min_v, max_v, is_float=False):
    mutation_op = random.choice([
        bit_flip,
        byte_flip,
        arithmetic_op,
        lambda data, bit_length: physical_boundary_op(data, bit_length, min_v, max_v),
        lambda data, bit_length: special_value_op(data, is_float)
    ])
    return mutation_op(data, bit_length)

        
#### Seed selector ####
def select_seed(corpus_len16, corpus_len28):
    seed_len16 = bytearray(random.choices(list(corpus_len16.keys()), weights=list(corpus_len16.values()), k=1)[0])
    seed_len28 = bytearray(random.choices(list(corpus_len28.keys()), weights=list(corpus_len28.values()), k=1)[0])
    return seed_len16, seed_len28     

def corpus_record(self, spilog):
    with open('spilog_corpus.txt', 'a') as f:
        f.write(f"{spilog}\n")   

