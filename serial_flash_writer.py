import os
from machine import SPI
import serial_flash_accessor

def from_file(name: str, hint: str = None):
    buffer_size = const(1024)
    flash = serial_flash_accessor.create_serial_flash(SPI(2), 'Y5', hint)
    if flash == None:
        print('Unsupported flash memory')
        return
    jedec_id = flash.get_jedec_id()
    print('JEDEC ID : {0}'.format(' '.join(['0x{0:02X}'.format(d) for d in jedec_id]) if jedec_id != None else 'None'))
    print('Vendor   : {0}'.format(flash.get_vendor()))
    print('Name     : {0}'.format(flash.get_name()))
    print('Capacity : {0} bytes'.format(flash.get_capacity()))

    file_stat = os.stat(name)
    file_size = file_stat[6]
    if file_size > flash.get_capacity():
        print('Insufficient flash memory capacity.')
        return

    is_protect = flash.is_protect()
    if is_protect:
        print('Unprotect memory.')
        flash.set_protect(False)

    print('Erasing...')
    flash.erase()

    with open(name, 'r') as file:
        file_buffer = memoryview(bytearray(buffer_size))
        read_buffer = memoryview(bytearray(buffer_size))
        address = 0
        while True:
            readed = file.readinto(file_buffer)
            if readed == 0:
                if is_protect:
                    print('Protect memory.')
                    flash.set_protect(True)
                print('Completed.')
                return
            print('Writing: {0:06x}-{1:06x}'.format(address, address + readed - 1))
            flash.write(address, file_buffer[:readed])
            flash.read(address, read_buffer[:readed])
            if file_buffer != read_buffer:
                print('Verify error')
                return
            address += readed
