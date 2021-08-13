from machine import Pin

class SpiDevice:
    def __init__(self, spi, cs_pin_id):
        self._spi = spi
        self._cs_pin = Pin(cs_pin_id, Pin.OUT)
        self._cs_pin.high()
        self._spi.init(baudrate=1000000)

    @micropython.native
    def write(self, write_buffer):
        self._cs_pin.low()
        self._spi.write(write_buffer)
        self._cs_pin.high()

    @micropython.native
    def writes(self, write_buffers):
        self._cs_pin.low()
        for write_buffer in write_buffers:
            self._spi.write(write_buffer)
        self._cs_pin.high()

    @micropython.native
    def write_read(self, write_buffer, read_buffer):
        self._cs_pin.low()
        self._spi.write(write_buffer)
        self._spi.readinto(read_buffer)
        self._cs_pin.high()

    def set_frequency(self, frequency):
        self._spi.init(baudrate=frequency)
