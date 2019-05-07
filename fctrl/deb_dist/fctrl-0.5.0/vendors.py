
class Vendor:
    vendor_db = {}

    def __init__(self, id, name, type):
        self.id = id
        self.name = name
        self.type = type
        Vendor.vendor_db[id] = self

    @staticmethod
    def get(id):
        try:
            return Vendor.vendor_db[id]
        except KeyError:
            return None


def get(id):
    return Vendor.get(id)


Vendor("0x10de", "Nvidia", "GPU")
Vendor(-1, "N/A", "N/A")
Vendor(0, "unknown", "N/A")
