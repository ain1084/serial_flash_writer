from serial_flash_accessor.serial_flash import SerialFlash
from serial_flash_accessor.spi_device import SpiDevice
from serial_flash_accessor.sst25vfxxxb_serial_flash import SST25VFxxxBSerialFlash
from serial_flash_accessor.mx25_serial_flash import MX25SerialFlash
from serial_flash_accessor.w25q_serial_flash import W25QSerialFlash
from serial_flash_accessor.microchip_25xx640a_serial_flash import Microchip25XX640ASerialFlash

def create_serial_flash(spi, cs_pin_id, hint: str = None) -> SerialFlash:
    spi_device = SpiDevice(spi, cs_pin_id)
    device_creators = [
        Microchip25XX640ASerialFlash.create,
        SST25VFxxxBSerialFlash.create,
        MX25SerialFlash.create,
        W25QSerialFlash.create,
    ]
    for device_creator in device_creators:
        device = device_creator(spi_device, hint)
        if device != None:
            return device
    return None
