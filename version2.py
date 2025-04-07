import serial
import time
import os

last_status = None
last_update_time = time.time()

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

def print_large_text(message: str, status_code: str):
    print("="*80)
    print(f"{' '*10}{message}     (Status Code: {status_code}) {' '*20} ")
    print("="*80)

def send_command():
    port = 'COM5'
    baudrate = 115200
    try:
        with serial.Serial(port, baudrate, timeout=0.1) as ser:
            frame = build_get_lock_status_frame()
            ser.write(frame)
            # Wait until transmission completes
            while ser.out_waiting > 0:
                pass
            # Read response immediately
            response = ser.readline()
            if response.startswith(b'\x02') and response.endswith(b'\x0D'):
                ascii_data = response[1:-1].decode("ascii")
                return parse_response(ascii_data)
        return False, None, None
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return False, None, None

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def continuous_check():
    global last_update_time
    try:
        while True:
            status_changed, new_status, status_code = send_command()
            current_time = time.time()
            
            if status_changed or (current_time - last_update_time >= 50):
                clear_console()
                if new_status:
                    print_large_text(new_status, status_code)
                    print("\nLast updated:", time.strftime("%Y-%m-%d %H:%M:%S"))
                last_update_time = current_time
    except KeyboardInterrupt:
        print("\nProcess terminated by user. Exiting...")

# Start the monitoring
continuous_check()