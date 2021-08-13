from micropython import const
from serial_flash_accessor.spi_device import SpiDevice
from serial_flash_accessor.serial_flash import SerialFlash

class W25QSerialFlash(SerialFlash):
    _WREN = const(0x06)
    _WREN_VOLATILE_SR = const(0x50)
    _RDID = const(0x9F)
    _READ = const(0x03)
    _READ_FAST = const(0x0B)
    _WRSR1 = const(0x01)
    _RDSR1 = const(0x05)
    _PP = const(0x02)
    _CE = const(0x60)

    _BP0 = const(0x04)
    _BP1 = const(0x08)
    _BP2 = const(0x10)
    _TB = const(0x20)
    _SEC = const(0x40)
    _BP_ALL = const(_BP0|_BP1|_BP2|_TB|_SEC)
    _BP_NONE = const(0x00)
    _BUSY = const(0x01)

    _PAGE_SIZE = const(256)

    @staticmethod
    def create(spi_device: SpiDevice, hint: str):
        jedec_id = bytearray(3)
        spi_device.write_read(bytes([_RDID]), jedec_id)
        MEGABIT = 2 ** 20
        KILOBIT = 2 ** 10 
        MEGA_HZ  = 1000 * 1000
        chip_infos = [
            # JEDEC ID         Name           Capacity          Min Op.MHz 
            # W25Q32JV-IQ
            [ b'\xEF\x40\x16', 'W25Q32JV-IQ', 32 * MEGABIT >> 3,  133 * MEGA_HZ ],
            # W25Q32JV-IM
            #[ b'\xEF\x70\x16', 'W25Q32JV-IM', 32 * MEGABIT >> 3,  133 * MEGA_HZ ],
        ]
        for chip_info in chip_infos:
            if chip_info[0] == jedec_id:
                return W25QSerialFlash(spi_device, chip_info)
        return None

    def __init__(self, spi_device: SpiDevice, chip_info):
        self._buffer = memoryview(bytearray(6))
        self._spi_device = spi_device
        self._jedec_id = chip_info[0]
        self._name = chip_info[1]
        self._capacity = chip_info[2]
        spi_device.set_frequency(chip_info[3])

    def get_vendor(self) -> str:
        return 'Winbond'

    def get_jedec_id(self) -> bytes:
        return self._jedec_id

    def get_capacity(self) -> int:
        return self._capacity
    
    def get_name(self) -> str:
        return self._name

    def set_protect(self, is_protect: bool):
        self._execute_command(_WREN_VOLATILE_SR)
        buffer = self._buffer
        buffer[0] = _WRSR1
        buffer[1] = _BP_ALL if is_protect else _BP_NONE
        self._spi_device.write(buffer[:2])
        self._wait_ready()

    def is_protect(self) -> bool:
        return (self._read_status() & _BP_ALL) != _BP_NONE

    def read(self, address: int, read_buffer: bytearray):
        if address + len(read_buffer) >= self._capacity:
            raise ValueError('The address is out of the accessible range.')
        buffer =  self._setup_address(_READ_FAST, address)
        buffer[4] = 0x00
        return self._spi_device.write_read(buffer[:5], read_buffer)

    def write(self, address:int, write_buffer: bytearray):
        if self.is_protect():
           raise Exception("This chip is write protected.")
        write_len = len(write_buffer)
        if address + write_len >= self._capacity:
            raise ValueError('The write address is out of the accessible range.')
        index = 0
        while index != write_len:
            page_address = address + index
            page_len = min(_PAGE_SIZE - (page_address % _PAGE_SIZE), write_len - index)
            self._execute_command(_WREN)
            self._setup_address(_PP, page_address)
            self._spi_device.writes([self._buffer[:4], write_buffer[index: index + page_len]])
            self._wait_ready()
            index += page_len

    def erase(self):
        if self.is_protect():
          raise Exception("This chip is write protected.")
        self._execute_command(_WREN)
        self._execute_command(_CE)
        self._wait_ready()

    def _wait_ready(self):
        while (self._read_status() & _BUSY) != 0:
            pass

    def _setup_address(self, command:int, address:int) -> bytearray:
        buffer = self._buffer
        buffer[0] = command
        buffer[1] = (address >> 16) & 0xFF
        buffer[2] = (address >> 8) & 0xFF
        buffer[3] = address & 0xFF
        return buffer

    def _read_status(self) -> int:
        return self._execute_command(_RDSR1, 1)[0]

    def _execute_command(self, command: int, read_len: int = 0) -> bytearray:
        buffer = self._buffer
        buffer[0] = command
        if read_len == 0:
            self._spi_device.write(buffer[:1])
            return None
        else:
            self._spi_device.write_read(buffer[:1], buffer[:read_len])
            return buffer[:read_len]
