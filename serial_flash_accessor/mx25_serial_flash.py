from micropython import const
from serial_flash_accessor.spi_device import SpiDevice
from serial_flash_accessor.serial_flash import SerialFlash

class MX25SerialFlash(SerialFlash):
    _WREN = const(0x06)
    _WRSR = const(0x01)
    _RDID = const(0x9F)
    _RDSR = const(0x05)
    _READ = const(0x03)
    _READ_FAST = const(0x0B)
    _CE = const(0x60)
    _PP = const(0x02)

    _BP0 = const(0x04)
    _BP1 = const(0x08)
    _BP2 = const(0x10)
    _BP3 = const(0x20)
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
            # MX25L6406E
            #[ b'\xC2\x20\x17', 'MX25x64xx',  64 * MEGABIT >> 3,  86 * MEGA_HZ, _BP0|_BP1|_BP2|_BP3 ],
            # MX25L3206E/MX25L3233F/MX25L3236F/MX25L3273F
            #[ b'\xC2\x20\x16', 'MX25x32xx',  32 * MEGABIT >> 3,  86 * MEGA_HZ, _BP0|_BP1|_BP2|_BP3 ],
            # MX25L1606E/MX25V16066/MX25V1606F
            #[ b'\xC2\x20\x15', 'MX25x16xx',  16 * MEGABIT >> 3,  80 * MEGA_HZ, _BP0|_BP1|_BP2|_BP3 ],
            # MX25L8006E/MX25V80066
            #[ b'\xC2\x20\x14', 'MX25x80xx',   8 * MEGABIT >> 3,  86 * MEGA_HZ, _BP0|_BP1|_BP2 ],
            # MX25L4006E/MX25V40066/MX25L4026E
            [ b'\xC2\x20\x13', 'MX25x40xx',   4 * MEGABIT >> 3,  86 * MEGA_HZ, _BP0|_BP1|_BP2 ],
            # MX25L2006E/MX25V20066/MX25V2033F/MX25V2039F/MX25L2026E
            #[ b'\xC2\x20\x12', 'MX25x20xx',   2 * MEGABIT >> 3,  86 * MEGA_HZ, _BP0|_BP1 ],
            # MX25L1006E/MX25V1006F/MX25L1026E
            #[ b'\xC2\x20\x11', 'MX25x10xx',   1 * MEGABIT >> 3, 104 * MEGA_HZ, _BP0|_BP1 ],
            #[ b'\xC2\x22\x11', 'MX25L1021E',   1 * MEGABIT >> 3,  45 * MEGA_HZ ],
            # MX25V5126F/MX25L5126F
            #[ b'\xC2\x22\x10', 'MX25L5121E', 512 * KILOBIT >> 3,  45 * MEGA_HZ ],
            #[ b'\xC2\x23\x15', 'MX25V1635F',  16 * MEGABIT >> 3,  80 * MEGA_HZ ],
            #[ b'\xC2\x23\x14', 'MX25V8035F',   8 * MEGABIT >> 3, 108 * MEGA_HZ ],
            #[ b'\xC2\x23\x13', 'MX25V4035F',   4 * MEGABIT >> 3, 108 * MEGA_HZ ],
            #[ b'\xC2\x25\x15', 'MX25L1636E',  16 * MEGABIT >> 3, 133 * MEGA_HZ ],
            #[ b'\xC2\x24\x15', 'MX25L1673E',  16 * MEGABIT >> 3, 104 * MEGA_HZ ],
        ]
        for chip_info in chip_infos:
            if chip_info[0] == jedec_id:
                return MX25SerialFlash(spi_device, chip_info)
        return None

    def __init__(self, spi_device: SpiDevice, chip_info):
        self._buffer = memoryview(bytearray(6))
        self._spi_device = spi_device
        self._jedec_id = chip_info[0]
        self._name = chip_info[1]
        self._capacity = chip_info[2]
        spi_device.set_frequency(chip_info[3])
        self._protect_value = chip_info[4]

    def get_vendor(self) -> str:
        return 'Macronix'

    def get_name(self) -> str:
        return self._name

    def get_jedec_id(self) -> bytes:
        return self._jedec_id

    def get_capacity(self) -> int:
        return self._capacity
    
    def set_protect(self, is_protect: bool):
        self._execute_command(_WREN)
        buffer = self._buffer
        buffer[0] = _WRSR
        buffer[1] = self._protect_value if is_protect else _BP_NONE
        self._spi_device.write(buffer[:2])
        self._wait_ready()

    def is_protect(self) -> bool:
        return (self._read_status() & self._protect_value) != _BP_NONE

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
