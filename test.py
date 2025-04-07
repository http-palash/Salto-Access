# Testing dummy payload


response = b'\x02000121815E\r\x02006505000000003252E987EB51992DF11669216C59C7C3A8777338309D7D26BA3BF00FC29F49C3CA\r'
print(f"Raw response: {response}")


if response.startswith(b'\x02') and response.endswith(b'\r'):

    clean_response = response[13:-1].decode('utf-8', errors='ignore')

    print(clean_response)

    if clean_response[4:6] == '05':
        payload = clean_response[6:-2]

        print("Payload to send to the server:")
        print(payload)
        print("Sending payload to salto server...")
        print(f"Payload: {payload}")
    else:
        print("The sequence at positions 5 and 6 is not '05'. Skipping payload send.")
else:
    print("Invalid response format (missing STX or CR).")
