from micropython import const
import time
from serial_flash_accessor.spi_device import SpiDevice
from serial_flash_accessor.serial_flash import SerialFlash

class SST25VFxxxBSerialFlash(SerialFlash):
    _READ = const(0x03)
    _FAST_READ = const(0x0B)
    _RDSR = const(0x05)
    _EWSR = const(0x50)
    _WRSR = const(0x01)
    _WREN = const(0x06)
    _WRDI = const(0x04)
    _RDID = const(0x90)
    _CE   = const(0x60)
    _JEDEC_ID = const(0x9F)
    _AAI_PROGRAM = const(0xAD)

    _BP0 = const(0b0000_0100)
    _BP1 = const(0b0000_1000)
    _BP2 = const(0b0001_0000)
    _BP3 = const(0b0010_0000)
    _BP_NONE = const(0b0000_0000)
    _BP_ALL = const(_BP0|_BP1|_BP2|_BP3)
    _BUSY = const(0b0000_0001)

    _TBP_MICRO_SECONDS = const(10)

    @staticmethod
    def create(spi_device: SpiDevice, hint: str):
        jedec_id = bytearray(3)
        spi_device.write_read(bytes([_JEDEC_ID]), jedec_id)
        MEGABIT = 2 ** 20
        MEGA_HZ  = 1000 * 1000
        chip_infos = [
            # JEDEC ID         Name           Capacity          Min Op.MHz 
            [ b'\xBF\x25\x4A', 'SST25VF032B', 32 * MEGABIT >> 3, 66 * MEGA_HZ ],
            #[ b'\xBF\x25\x41', 'SST25VF016B', 16 * MEGABIT >> 3, 50 * MEGA_HZ ],
            #[ b'\xBF\x25\x8E', 'SST25VF080B',  8 * MEGABIT >> 3, 50 * MEGA_HZ ],
            #[ b'\xBF\x25\x8D', 'SST25VF040B',  4 * MEGABIT >> 3, 50 * MEGA_HZ ],
        ]
        for chip_info in chip_infos:
            if chip_info[0] == jedec_id:
                return SST25VFxxxBSerialFlash(spi_device, chip_info)
        return None

    def __init__(self, spi_device: SpiDevice, chip_info):
        self._buffer = memoryview(bytearray(6))
        self._spi_device = spi_device
        self._jedec_id = chip_info[0]
        self._name = chip_info[1]
        self._capacity = chip_info[2]
        spi_device.set_frequency(chip_info[3])

    def get_jedec_id(self) -> bytes:
        return self._jedec_id

    def get_capacity(self) -> int:
        return self._capacity

    def get_vendor(self) -> str:
        return 'Microchip'

    def get_name(self) -> str:
        return self._name

    def set_protect(self, is_protect: bool):
        self._execute_command(_EWSR)
        buffer = self._buffer
        buffer[0] = _WRSR
        buffer[1] = _BP_ALL if is_protect else _BP_NONE
        self._spi_device.write(buffer[:2])
        self._wait_ready()

    def is_protect(self) -> bool:
        return (self._read_status() & _BP_ALL) != _BP_NONE

    def read(self, address: int, read_buffer: bytearray):
        if address + len(read_buffer) >= self._capacity:
            raise ValueError('The address is out of the accessible range.')
        buffer =  self._setup_address(_FAST_READ, address)
        buffer[4] = 0x00
        return self._spi_device.write_read(buffer[:5], read_buffer)

    def write(self, address:int, write_buffer: bytearray):
        write_len = len(write_buffer)
        if address + write_len >= self._capacity:
            raise ValueError('The address is out of the accessible range.')
        if write_len == 0:
            return
        if address % 2 != 0:
            raise ValueError('The address to write must be an even number.')

        try:
            def execute_AAI(buffer: bytearray):
                self._spi_device.write(buffer)
                time.sleep_us(_TBP_MICRO_SECONDS)
            self._execute_command(_WREN)
            buffer = self._setup_address(_AAI_PROGRAM, address)
            buffer[4] = write_buffer[0]
            if write_len < 2:
                buffer[5] = 0xFF
                execute_AAI(buffer[:6])
            else:
                buffer[5] = write_buffer[1]
                execute_AAI(buffer[:6])
                for index in range(2, (write_len >> 1) * 2, 2):
                    buffer[0] = _AAI_PROGRAM
                    buffer[1] = write_buffer[index]
                    buffer[2] = write_buffer[index + 1]
                    execute_AAI(buffer[:3])
                if write_len % 2 != 0:
                    buffer[0] = _AAI_PROGRAM
                    buffer[1] = write_buffer[write_len - 1]
                    buffer[2] = 0xFF
                    execute_AAI(buffer[:3])
        finally:
            self._execute_command(_WRDI)

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
        return self._execute_command(_RDSR, 1)[0]

    def _execute_command(self, command: int, read_len: int = 0) -> bytearray:
        buffer = self._buffer
        buffer[0] = command
        if read_len == 0:
            self._spi_device.write(buffer[:1])
            return None
        else:
            self._spi_device.write_read(buffer[:1], buffer[:read_len])
            return buffer[:read_len]
