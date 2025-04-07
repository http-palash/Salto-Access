import serial
import time
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
import requests

console = Console()
last_status = None
last_update_time = time.time()
LOG_FILE = "door_status_log.txt"



import time

def send_payload_to_salto_server(payload: str):
    """Send the payload to the alto server with retry logic."""
    retries = 2  
    delay = 2   
    for attempt in range(retries):
        try:
            data = {
                "payload": payload,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            console.print(payload)
            response = requests.post("http://10.10.1.158:8090", json=data)

            if response.status_code == 200:
                console.print(f"[green]Payload sent successfully to the Salto server.[/]")
                return
            else:
                console.print(f"[red]Failed to send payload. Server responded with status code: {response.status_code}[/]")
        
        except requests.RequestException as e:
            console.print(f"[red]Error occurred while sending payload to Salto server: {str(e)}[/]")
            if attempt < retries - 1:
                console.print(f"[yellow]Retrying in {delay} seconds...[/]")
                time.sleep(delay)
            else:
                console.print("[red]Max retries exceeded. Could not send the payload.[/]")


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
            "80": ("Door is Locked", "80"),
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

def print_large_text(message: str, status_code: str, ascii_response: str = "", response : str=""):
    # Create main status panel with centered content
    status_content = Align.center(
        f"[green]Status: {message}\n"
        f"[yellow]Status Code: {status_code}[/]",
        vertical="middle"
    )
    status_panel = Panel(
        status_content,
        title="[cyan]DOOR STATUS MONITOR",
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(status_panel)
    
    # Create frame details panel if available
    if ascii_response:
        frame_content = Align.center(
            f"[white]ASCII Response: [cyan]{ascii_response}\n"
            f"[white]Type: [cyan]{ascii_response[:2]}\n"
            f"[white]Seq: [cyan]{ascii_response[2:4]}\n"
            f"[white]Cmd: [cyan]{ascii_response[4:6]}\n"
            f"[white]Param: [cyan]{ascii_response[6:8]}\n"
            f"[white]Checksum: [cyan]{ascii_response[8:10]}[/]",
            vertical="middle"
        )
        frame_panel = Panel(
            frame_content,
            title="[yellow]Frame Details",
            border_style="yellow",
            padding=(1, 2)
        )
        console.print(frame_panel)
    
    # Create ASCII payload details panel
    if ascii_response:
        payload_content = Align.center(
            f"[yellow]Parameter Value:[cyan] {ascii_response[6:8]}",
            vertical="middle"
        )
        payload_panel = Panel(
            payload_content,
            title="[yellow]Payload Details",
            border_style="yellow",
            padding=(1, 2)
        )
        console.print(payload_panel)


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

            if response.startswith(b'\x02') and response.endswith(b'\r'):
                clean_response = response[13:-1].decode('utf-8', errors='ignore')
                if clean_response[4:6] == '05' and clean_response[0:2] == '00':
                    payload = clean_response[6:-2]
                    try:
                        byte_data = bytes.fromhex(payload)
                        length_in_bytes = len(byte_data)
                        print(f"Length of the payload in bytes: {length_in_bytes}")
                        if length_in_bytes > 36:
                            print("Payload is too large, not sending to the server.")
                        else:
                            print("Payload to send to the server:")
                            # print(payload) 
                            send_payload_to_salto_server(payload)
                    except ValueError:
                        pass

            if response.startswith(b'\x02') and response.endswith(b'\x0D'):
                try:
                    ascii_data = response[1:-1].decode("ascii")
                    status_changed, current_status, status_code = parse_response(ascii_data)
                    # Extract full ASCII payload for detailed logging
                    ascii_payload = response[1:-1].decode("ascii")
                    return {
                        'status_changed': status_changed,
                        'current_status': current_status,
                        'status_code': status_code,
                        'ascii_payload': ascii_payload,
                        'response': response,
                    }
                except UnicodeDecodeError:
                    pass

    except serial.SerialException as e:
        error_message = f"Serial error: {str(e)}"
        console.print(f"[red]{error_message}[/]")
        log_status(error_message, "ERR")
        return {
            'status_changed': False,
            'current_status': None,
            'status_code': None,
            'response': b'',
            'ascii_payload': ""
        }

    # If no valid response was processed, return a safe default
    return {
        'status_changed': False,
        'current_status': None,
        'status_code': None,
        'response': b'',
        'ascii_payload': ""
    }


def continuous_check():
    global last_update_time
    try:
        while True:
            result = send_command()
            if not result:
                continue  # If result is None or invalid, continue to next loop

            current_time = time.time()

            if result['status_changed']:
                clear_console()
                print_large_text(
                    result['current_status'],
                    result['status_code'],
                    result['ascii_payload'],  
                    result['response'],
                )

                timestamp_text_content = Align.center(
                    f"[white]Last updated at : [cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]",
                    vertical="middle"
                )
                timestamp_text_panel = Panel(
                    timestamp_text_content,
                    title="[yellow]Last Updated",
                    border_style="yellow",
                    padding=(1, 2)
                )
                console.print(timestamp_text_panel)
                log_status(result['current_status'], result['status_code'])

    except KeyboardInterrupt:
        console.print("\n" + str(Align.center(
            "[white]Process terminated by user. Exiting...[/]",
            vertical="middle"
        )))

def log_status(status: str, status_code: str):
    """Log status changes to file with extended details"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Status: {status} (Code: {status_code})"
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + '\n')

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

continuous_check()