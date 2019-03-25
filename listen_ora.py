#!/usr/bin/env python
import sys
import serial
import math
from pprint import pprint
from time import sleep, time
from datetime import datetime

def init():
    # 設定 pySerial
    serial_port = '/dev/{}'.format(sys.argv[1])
    ser = serial.Serial(
        serial_port,
        115200, 
        timeout = 1)
    sleep(1)

    send_at(ser, 'AT+MODE=0\r\n')
    send_at(ser, 'AT+ADDRESS=10\r\n')
    send_at(ser, 'AT+NETWORKID=1\r\n')
    send_at(ser, 'AT+BAND=915000000\r\n')
    send_at(ser, 'AT+PARAMETER=10,7,1,7\r\n')
    send_at(ser, 'AT+CRFOP=05\r\n')
    
    return ser

def send_at(ser, at_string):
    ser.write(at_string.encode())
    sleep(1)
    while True:
        read_out = ser.readline().decode('ascii')
        if not read_out:
            sleep(1)
            continue
        else:
            break
    print('Setup "{}" : {}'.format(
        at_string.strip(), 
        read_out.strip()
        ))

def convert_data(hex_string):
    """回傳 agri_data
    將收到資料部分解析成各項 data 數值內容
    """
    # testing data
    # hex_string = '017C107Cf57C647C737C01057C28607C028d7C7d'
    # hex_string = '0b7C107C010d7C3b7C557C007C007C007C0b7C14'
    cut_hex = hex_string.split('7C')
    try:
        val_list = [int(x, 16) for x in cut_hex]
    except ValueError:
        print('Convert hex error. Cut_hex: {}'.format(cut_hex))
    except IndexError:
        print('Index Out of range when convert: {}'.format(hex_string))
    return val_list

def gamma(T, RH, a, b):
    g = (a * T / (b + T)) + math.log(RH/100.0)
    return g

def dewpoint_approximation(T, RH):
    # constants
    a = 17.271
    b = 237.7 # degC

    gm = gamma(T, RH, a, b)
    Td = (b * gm) / (a - gm)

    return round(Td, 1)

def parse_from_receive(data_string):
    data_string = data_string.replace('+RCV=', '')
    row_data = data_string.rstrip().split(',')

    cuted_data = convert_data(row_data[2])
    if cuted_data[1] == 16:
        # wand type DA
        agri_data = {
            'soil_temperature': (cuted_data[2]/10),
            'soil_moisture': cuted_data[3],
            'soil_conductivity': (cuted_data[4]/1000),
            'air_temperature': (cuted_data[5]/10),
            'air_pressure': (cuted_data[6]/10),
            'air_humidity': (cuted_data[7]/10),
            'solar_lux': cuted_data[8],
            'voltage': (cuted_data[9]/10),
            'rssi': int(row_data[3])
        }
    elif cuted_data[1] == 18:
        # wand type DB
        agri_data = {
            'soil_temperature': (cuted_data[2]/10),
            'soil_moisture': cuted_data[3],
            'soil_conductivity': (cuted_data[4]/1000),
            'soil_ph': (cuted_data[5]/10),
            'air_temperature': (cuted_data[6]/10),
            'air_humidity': (cuted_data[7]/10),
            'dew_point': (cuted_data[8]/10),
            'air_co2': cuted_data[9],
            'solar_lux': cuted_data[10],
            'bug_num': (cuted_data[11]/10),
            'voltage': (cuted_data[12]/10),
            'rssi': int(row_data[3])
        }
    elif cuted_data[1] == 20:
        # wand type DC
        agri_data = {
            'air_temperature': (cuted_data[2]/10),
            'air_humidity': (cuted_data[3]/10),
            'air_temperature02': (cuted_data[4]/10),
            'air_humidity02': (cuted_data[5]/10),
            'air_co2': cuted_data[6],
            'air_co2_temperature': (cuted_data[7]/10),
            'air_co2_humidity': (cuted_data[8]/10),
            'air_nh3': cuted_data[9],
            'rssi': int(row_data[3])
        }
    elif cuted_data[1] == 22:
        # wand type WC
        agri_data = {
            'air_temperature': (cuted_data[2]/10),
            'air_humidity': (cuted_data[3]/10),
            'wind_speed': (cuted_data[4]/10),
            'wind_direction': (cuted_data[5]/10),
            'rain_rate': cuted_data[6],
            'rainfalls': (cuted_data[7]/10),
            'dew_point': dewpoint_approximation(cuted_data[2]/10, cuted_data[3]/10),
            'solar_radiation': (cuted_data[8]/10),
            'uvi': cuted_data[9],
            'voltage': cuted_data[10],
            'rssi': int(row_data[3])
        }
    return agri_data

def get_now_time():
    """
    取得現在的時間字串
    """
    return datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')

if __name__ == '__main__':
    ser = init()
    while True:
        print("Attempt to Read")
        while True:
            try:
                read_out = ser.readline().decode('ascii')
            except serial.SerialException as e:
                print('Serial Exception: ' + repr(e))
                pass
            except Exception as e:
                print('Exception:' + repr(e))
                pass

            try:
                if not read_out:
                    sleep(1)
                    continue
                elif read_out.strip() == '+OK':
                    print('Setting: ', read_out)
                else:
                    read_time = get_now_time()
                    print('At: {}'.format(read_time))
                    print('Reading: {}'.format(read_out))
                    recv_status = read_out.rstrip().split('=')
                    if recv_status[0] == '+ERR':
                        print('Read LoRa Error: {}'.format(read_out))
                        break
                agri_data = parse_from_receive(read_out)
                pprint(agri_data)
            except Exception as e:
                print('Exception:' + repr(e))
                pass

            print('=========== Separation line ======================')
        print ("Restart")
        ser.flush()
