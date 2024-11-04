import json

# Read contents of the txt file
with open('commands.txt', 'r') as file:
    lines = file.readlines()

# Create a dictionary to store data
commands_dict = {}

# Iterate through each line and parse the data
for line in lines:
    if '=' in line:
        key, value = line.split('=')
        key = key.strip()
        value = value.strip().strip(',').replace('0x', '')
        commands_dict[key] = int(value, 16)

# Convert the dictionary to JSON format and save to a file
with open('commands.json', 'w') as json_file:
    json.dump({"COMMANDS": commands_dict}, json_file, indent=4)

print("Data successfully converted and saved as commands.json file.")
