import asyncio
import time
import utils
from galvo.controller import GalvoController

class MachineControl():
    def __init__(self):
        #self.cotroller = GalvoController()
        self.settings_file = None
        self.gcode_filepath = None
    
    def convert_gcode_to_job(self):
        points = utils.parse_gcode(self.gcode_filepath)
        print(points)
        return
    
    async def mark(self):
        print("mark")
        self.convert_gcode_to_job()

        controller = GalvoController(self.settings_file)

        def my_job(c):
            c.marking_configuration()
            c.dark(0x8000, 0x8000)
            c.mark(0x2000, 0x2000)
            return False

        controller.submit(my_job)
        time.sleep(2)
        controller.shutdown()
        return

    async def light(self):
        controller = GalvoController(self.settings_file)

        def my_job(c):
            c.lighting_configuration()
            c.dark(0x8000, 0x8000)
            c.light(0x2000, 0x2000)
            return False

        controller.submit(my_job)
        time.sleep(2)
        controller.shutdown()
        return
    