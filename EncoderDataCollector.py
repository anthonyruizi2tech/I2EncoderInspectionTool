import serial
import csv
import time
import os
from plot_csv import plot_encoders

#DC Voltage For Fast ~ 9.23V
#DC Voltage For Slow ~ 3.8V
#Firmware Version: r56d06d41-log-i2aX
COARSE_MAX_COUNTS=5198400   #max counts for coarse motor encoder
FINE_MAX_COUNTS=327680      #max counts for fine work encoder



def process_twos_complement_hex(hex_str):
    bits = len(hex_str) * 4
    value = int(hex_str, 16)

    is_negative = bool(value & (1 << (bits - 1))) #tuple flag to check if the processed hex was changed from 2s Complement Serial Val

    if is_negative:
        max_value = 1 << bits
        complement = (max_value - value) & (max_value - 1)
        result_hex = f"{complement:0{bits // 4}X}"
        return result_hex, True
    else:
        return hex_str.upper(), False


def coarse_hex_to_angle(hex_str):
    new_hex, was_negative = process_twos_complement_hex(hex_str)
    value = int(new_hex, 16)
    angle = (value / COARSE_MAX_COUNTS) * 360
    if was_negative:
        angle = -angle
    return angle

def fine_hex_to_angle(hex_str):
    new_hex, was_negative = process_twos_complement_hex(hex_str)
    value = int(new_hex, 16)
    angle = (value / FINE_MAX_COUNTS) * 360
    if was_negative:
        angle = -angle
    return angle

def command_conversion(hex_str):
    new_hex, was_negative = process_twos_complement_hex(hex_str)
    value = int(new_hex, 16)
    if was_negative:
        value = -value
    return value



def EncoderDataCollector(base_name):



    HEADER_BYTE = 0x5A          # 'Z'
    MESSAGE_LENGTH = 31         # 1-byte header + 24-byte payload # will need to increase from 25 to 31 to incorporate index
    SAMPLING_DURATION = 600      # Sample Duration in seconds (set to 10 min data collection for now


    # Create logs subfolder if it doesn't exist
    log_folder = "encoder_logs"
    os.makedirs(log_folder, exist_ok=True)

    # Generate timestamp and full filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")  # e.g., 20250415_154501
    filename = f"{base_name}_{timestamp}.csv"
    filepath = os.path.join(log_folder, filename)



    ser = serial.Serial(
        port='COM3',            # Change to your actual serial port
        baudrate=460800,        # Given Baudrate from John's Firmware
        timeout=1
    )

    buffer = bytearray()
    message_count = 0

    # Start timing
    start_time = time.time()
    end_time = start_time + SAMPLING_DURATION

    with open(filepath, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            'Message #',
            #'Elapsed Time (ms)',
            'Coarse Encoder Counts (6B)', # Motor Encoder Counts
            'Coarse Degree',
            'Fine Encoder Counts (6B)', # Work/Glass Encoder Counts
            'Fine Degree',
            'Index Angle',
            'Coarse Encoder Commands (4B)', # Motor Commands -> called encoder commands for convention only
            'Fine Encoder Commands (4B)', # Work/Glass Encoder Counts
            #'Inner Encoder Counts (4B)' # Not Being used as of this implementation
        ])

        print(f"Listening for messages starting with 'Z' (0x{HEADER_BYTE:02X}) for {SAMPLING_DURATION} seconds...")

        try:
            print(f"Logging to: {filepath}")
            while time.time() < end_time:
                if ser.in_waiting:
                    buffer += ser.read(ser.in_waiting)
                    while True:
                        try:
                            start = buffer.index(HEADER_BYTE)
                        except ValueError:
                            break

                        if len(buffer) - start >= MESSAGE_LENGTH:
                            message = buffer[start:start + MESSAGE_LENGTH]
                            payload_bytes = message[1:]  # Strip header

                            # Submessage slices
                            c_encoder_com = payload_bytes[0:4]
                            c_encoder_cts = payload_bytes[4:10]
                            f_encoder_cts = payload_bytes[10:16]
                            f_encoder_com = payload_bytes[16:20]
                            i_encoder_cts = payload_bytes[20:24] #unused might also include commands, will check during implementation
                            fine_index = payload_bytes[24:] #Gives back absolute angle of work encoder

                            #Flips the bytes that john sends to give expected vals
                            true_c_encoder_com = c_encoder_com[::-1]
                            true_c_encoder_cts = c_encoder_cts[::-1]
                            true_f_encoder_cts = f_encoder_cts[::-1]
                            true_f_encoder_com = f_encoder_com[::-1]
                            true_i_encoder_cts = i_encoder_cts[::-1]
                            true_fine_index = fine_index[::-1]

                            # Decode submessages (hex)
                            true_c_encoder_com_str = true_c_encoder_com.decode(errors='replace')
                            true_c_encoder_cts_str = true_c_encoder_cts.decode(errors='replace')
                            true_f_encoder_cts_str = true_f_encoder_cts.decode(errors='replace')
                            true_f_encoder_com_str = true_f_encoder_com.decode(errors='replace')
                            true_i_encoder_cts_str = true_i_encoder_cts.decode(errors='replace')
                            true_fine_index_str = true_fine_index.decode(errors='replace')

                            c_degrees = coarse_hex_to_angle(true_c_encoder_cts_str)
                            f_degrees = -fine_hex_to_angle(true_f_encoder_cts_str) # -sign is to swap sign convention of work encoder angle
                            absolute_index = -fine_hex_to_angle(true_fine_index_str) # The actual angle read from the index point

                            c_cmd_val = command_conversion(true_c_encoder_com_str)
                            f_cmd_val = command_conversion(true_f_encoder_com_str)


                            elapsed_time_ms = int((time.time() - start_time) * 1000)
                            message_count += 1

                            print(f"[{message_count}] [{elapsed_time_ms} ms] Coarse Encoder Commands: {true_c_encoder_com_str} | Coarse Encoder Counts(Degrees): {c_degrees} | Fine Encoder Counts(Degrees): {f_degrees} | Fine Encoder Commands: {true_f_encoder_com_str} | Inner Encoder Counts: {true_i_encoder_cts_str} |Absolute Index Angle {absolute_index}")

                            writer.writerow([
                                message_count, #changed data collection for 1st column to message count instead of elapsed_time_ms
                                #elapsed_time_ms,
                                true_c_encoder_cts_str, #ASCII read for debug
                                #c_encoder_cts_int, #byte to int for debug
                                c_degrees, #not coming out correct Should give -180 to 180
                                true_f_encoder_cts_str,
                                f_degrees,
                                absolute_index,
                                c_cmd_val, #Coarse Encoder Commands Value
                                f_cmd_val #Fine Encoder Commands Value
                                #true_i_encoder_cts_str
                            ])

                            buffer = buffer[start + MESSAGE_LENGTH:]
                        else:
                            break

        finally:
            print(f"Done logging {message_count} messages.")

            plot_encoders(filepath,base_name,timestamp)
            # to see if bit swap works
            #print(c_encoder_cts)

            #print(true_c_encoder_cts)

            #print(c_encoder_cts_int)

            ser.close()
