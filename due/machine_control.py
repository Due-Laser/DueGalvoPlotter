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
        self.current_task = None  # Variável para armazenar a task atual

    def convert_gcode_to_job(self):
        points = utils.parse_gcode(self.gcode_filepath)
        #print(points)
        return points
    
    async def _mark_loop(self):
        """Loop de marcação executado como uma task separada."""
        self.stop_job = False
        self.controller.connect_if_needed()

        i = 0
        while not self.stop_job and i < 10:
            print("loop " + str(i))
            with self.controller.marking() as c:
                c.dark(0x8000, 0x8000)
                c.mark(0x2000, 0x2000)
            await asyncio.sleep(0.1)  # Simula espera não bloqueante
            self.controller.wait_for_machine_idle()
            i += 1
            print("end")

        self.controller.disconnect()
        print("Marking task finished")
    
    async def mark(self):
        """Inicia o trabalho de marcação como uma task."""
        print("mark")
        if self.controller.is_busy():
            print("Controller is busy, stopping job...")
            self.stop_job = True
            return

        self.convert_gcode_to_job()

        # Cancela a task atual, se estiver em execução
        if self.current_task and not self.current_task.done():
            print("Stopping current task...")
            self.stop_job = True
            await self.current_task  # Aguarda o término da task atual

        # Inicia uma nova task para o loop de marcação
        self.current_task = asyncio.create_task(self._mark_loop())
        print("New marking task started")
        return
    
    async def stop(self):
        """Interrompe o trabalho atual."""
        print("Stopping current task...")
        if self.current_task and not self.current_task.done():
            self.stop_job = True
            await self.current_task  # Aguarda o término da task atual
        print("Current task stopped")

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
    