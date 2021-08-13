from micropython import const
from serial_flash_accessor.spi_device import SpiDevice
from serial_flash_accessor.serial_flash import SerialFlash

class Microchip25XX640ASerialFlash(SerialFlash):
    _READ  = const(0b0000_0011)
    _WRITE = const(0b0000_0010)
    _WRDI  = const(0b0000_0100)
    _WREN  = const(0b0000_0110)
    _RDSR  = const(0b0000_0101)
    _WRSR  = const(0b0000_0001)

    _BP_VALUE = const(0b0000_1100)
    _BP_NONE = const(0b00000_0000)

    _PAGE_SIZE = const(32)

    @staticmethod
    def create(spi_device: SpiDevice, hint: str):
        MEGABIT = 2 ** 20
        KILOBIT = 2 ** 10 
        MEGA_HZ  = 1000 * 1000
        chip_infos = [
            [ '25AA640A', 64 * KILOBIT >> 3, 5 * MEGA_HZ ],
            [ '25LC640A', 64 * KILOBIT >> 3, 5 * MEGA_HZ ],
        ]
        for chip_info in chip_infos:
            if chip_info[0] == hint:
                return Microchip25XX640ASerialFlash(spi_device, chip_info)
        return None

    def __init__(self, spi_device: SpiDevice, chip_info):
        self._buffer = memoryview(bytearray(3))
        self._spi_device = spi_device
        self._name = chip_info[0]
        self._capacity = chip_info[1]
        spi_device.set_frequency(chip_info[2])

    def get_vendor(self) -> str:
        return 'Microchip'

    def get_jedec_id(self) -> bytes:
        return None

    def get_capacity(self) -> int:
        return self._capacity
    
    def get_name(self) -> str:
        return self._name

    def set_protect(self, is_protect: bool):
        self._execute_command(_WREN)
        self._write_status(_BP_VALUE if is_protect else _BP_NONE)
        self._wait_ready()

    def is_protect(self) -> bool:
        return self._read_status() & _BP_VALUE != 0

    def read(self, address: int, read_buffer: bytearray):
        if address + len(read_buffer) >= self._capacity:
            raise ValueError('The address is out of the accessible range.')
        buffer =  self._setup_address(_READ, address)
        return self._spi_device.write_read(buffer[:3], read_buffer)

    def write(self, address:int, write_buffer: bytearray):
        if self.is_protect():
           raise Exception("This chip is write protected.")
        write_len = len(write_buffer)
        if address + write_len >= self._capacity:
            raise ValueError('The write address is out of the accessible range.')
        if write_len == 0:
            return
        index = 0
        while index != write_len:
            page_address = address + index
            page_len = min(_PAGE_SIZE - (page_address % _PAGE_SIZE), write_len - index)
            self._execute_command(_WREN)
            self._setup_address(_WRITE, page_address)
            self._spi_device.writes([self._buffer[:3], write_buffer[index: index + page_len]])
            self._wait_ready()
            index += page_len

    def erase(self):
        pass

    def _wait_ready(self):
        while self._read_status() & 0x1 == 1:
            pass

    def _setup_address(self, command:int, address:int) -> bytearray:
        buffer = self._buffer
        buffer[0] = command
        buffer[1] = (address >> 8) & 0xFF
        buffer[2] = address & 0xFF
        return buffer

    def _read_status(self) -> int:
        return self._execute_command(_RDSR, 1)[0]

    def _write_status(self, value):
        self._execute_command(_WREN)
        buffer = self._buffer
        buffer[0] = _WRSR
        buffer[1] = value
        self._spi_device.write(buffer[:2])

    def _execute_command(self, command: int, read_len: int = 0) -> bytearray:
        buffer = self._buffer
        buffer[0] = command
        if read_len == 0:
            self._spi_device.write(buffer[:1])
            return None
        else:
            self._spi_device.write_read(buffer[:1], buffer[:read_len])
            return buffer[:read_len]
