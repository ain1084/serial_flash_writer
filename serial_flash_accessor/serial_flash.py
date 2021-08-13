class SerialFlash:
    def get_jedec_id(self) -> bytes:
        raise NotImplementedError()

    def get_vendor(self) -> str:
        raise NotImplementedError()

    def get_name(self) -> str:
        raise NotImplementedError()

    def get_capacity(self) -> int:
        raise NotImplementedError()

    def set_protect(self, is_protect: bool):
        raise NotImplementedError()

    def is_protect(self) -> bool:
        raise NotImplementedError()

    def read(self, address: int, read_buffer: bytearray):
        raise NotImplementedError()

    def write(self, address: int, write_buffer: bytearray):
        raise NotImplementedError()

    def erase(self):
        raise NotImplementedError()
