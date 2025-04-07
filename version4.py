import serial
import time
import os
from datetime import datetime

last_status = None
last_update_time = time.time()
LOG_FILE = "door_status_log.txt"

def build_get_lock_status_frame():
    stx = bytes([0x02])
    ascii_payload = "00012100DF".encode("ascii")
    cr = bytes([0x0D])
    return stx + ascii_payload + cr

def parse_response(ascii_data: str):
    global last_status
    if len(ascii_data) >= 10:
        parameter = ascii_data[6:8]
        status_map = {
            "80": ("Door is Simply Locked", "80"),
            "81": ("The door is held open", "81"),
            "82": ("Locked and closed from inside", "82"),
            "83": ("Locked but open, lock is in passage mode", "83")
        }
        result = status_map.get(parameter, ("Unknown Status", parameter))
        current_status = result[0]
        status_code = result[1]
        
        if current_status != last_status:
            last_status = current_status
            return True, current_status, status_code
        return False, None, None
    return False, None, None

def print_large_text(message: str, status_code: str, raw_hex: str = "", length: int = 0):
    print("="*80)
    print(f"{' '*10}{message}     (Status Code: {status_code}) {' '*20}")
    if raw_hex:
        print(f"{' '*10}Raw Hex: {raw_hex}")
        print(f"{' '*10}Frame Length: {length} bytes")
    print("="*80)



def send_command():
    port = 'COM5'
    baudrate = 115200
    try:
        with serial.Serial(port, baudrate, timeout=0.1) as ser:
            frame = build_get_lock_status_frame()
            ser.write(frame)
            while ser.out_waiting > 0:
                pass
            response = ser.readline()
            
            if response.startswith(b'\x02') and response.endswith(b'\x0D'):
                try:
                    ascii_data = response[1:-1].decode("ascii")
                    status_changed, current_status, status_code = parse_response(ascii_data)
                    
                    # Return all needed information
                    return {
                        'status_changed': status_changed,
                        'current_status': current_status,
                        'status_code': status_code,
                        'response': response  # Include the raw response
                    }
                except UnicodeDecodeError:
                    hex_data = response[1:-1].hex()
                    error_message = f"Received invalid data: {hex_data}"
                    print(error_message)
                    log_status(error_message, "ERR")
                    return {
                        'status_changed': False,
                        'current_status': error_message,
                        'status_code': "ERR",
                        'response': response
                    }
            else:
                hex_data = response.hex()
                error_message = f"Invalid frame received: {hex_data}"
                print(error_message)
                log_status(error_message, "ERR")
                return {
                    'status_changed': False,
                    'current_status': error_message,
                    'status_code': "ERR",
                    'response': response
                }
                
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        log_status(f"Serial error: {str(e)}", "ERR")
        return {
            'status_changed': False,
            'current_status': None,
            'status_code': None,
            'response': b''
        }

def continuous_check(flag):
    global last_update_time
    try:
        while True:
            result = send_command()
            
            current_time = time.time()
            
            if result['status_changed']:
                clear_console(flag)
           
                print_large_text(
                    result['current_status'],
                    result['status_code'],
                    result['response'].hex(),
                    len(result['response'])
                )
                flag = 0
                print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                log_status(result['current_status'], result['status_code'])
            elif current_time - last_update_time >= 50:
                clear_console(flag)
                print("\nNo status changes detected")
                print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                last_update_time = current_time
                
    except KeyboardInterrupt:
        print("\nProcess terminated by user. Exiting...")

# Create log file if it doesn't exist
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as f:
        f.write("Door Status Monitoring Log\n")
        f.write("=" * 40 + "\n")

def log_status(status: str, status_code: str):
    """Log status changes to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Status: {status} (Code: {status_code})"
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + '\n')

def clear_console(flag):
    os.system('cls' if os.name == 'nt' else 'clear')
    if flag == 1 : print("Status is : ") 
    elif flag == 0 : print("\nStatus Change Detected!")



continuous_check(flag=1)