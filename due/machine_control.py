import asyncio
import time
import utils
from galvo.controller import GalvoController

class MachineControl():
    def __init__(self, settings_file):
        #self.cotroller = GalvoController()
        self.settings_file = settings_file
        self.gcode_filepath = None
        self.controller = GalvoController(self.settings_file)
        self.stop_job = False
    
    def convert_gcode_to_job(self):
        points = utils.parse_gcode(self.gcode_filepath)
        #print(points)
        return points
    
    async def mark(self):
        print("mark")
        if self.controller.is_busy():
            print("Controller is busy, stopping job...")
            self.stop_job = True
            return
        
        self.convert_gcode_to_job()

        self.controller.connect_if_needed()
        self.stop_job = False

        i = 0
        while (self.stop_job == False and i < 10):
            print("loop " + str(i))
            with self.controller.marking() as c:
                c.dark(0x8000, 0x8000)
                c.mark(0x2000, 0x2000)
            self.controller.wait_for_machine_idle()
            i += 1
            print("end")
        
        self.controller.disconnect()
        return

    async def light(self):
        print("light")
        if self.controller.is_busy():
            print("Controller is busy, stopping job...")
            self.stop_job = True
            return
        
        self.stop_job = False

        i = 0
        while (self.stop_job == False and i < 10):
            print("loop " + str(i))
            with self.controller.lighting() as c:
                c.dark(0x8000, 0x8000)
                c.light(0x2000, 0x2000)
            self.controller.wait_for_machine_idle()
            i += 1
            print("end")
        
        self.controller.disconnect()
        return
    