import asyncio
import time
import utils
from galvo.controller import GalvoController

class MachineControl():
    def __init__(self, settings_file):
        self.settings_file = settings_file
        self.gcode_filepath = None
        self.controller = GalvoController(self.settings_file)
        self.stop_job = False
        self.current_task = None  # Variável para armazenar a task atual

    def convert_gcode_to_light_job(self, points):
        with self.controller.lighting() as c:
            for point in points:
                x, y = utils.mm_to_galvo(point[0], point[1])
                s_val = point[2]
                if s_val == 0:
                    c.dark(x, y)
                else:
                    c.light(x, y)
    
    async def _light_loop(self):
        """Loop de light executado como uma task separada."""
        self.stop_job = False
        try:
            self.controller.connect_if_needed()
        except Exception as e:
            print("Error connecting to Galvo Controller: " + str(e))
            return
        points = utils.parse_gcode(self.gcode_filepath)
        i = 0
        while not self.stop_job:
            print("loop " + str(i))
            self.convert_gcode_to_light_job(points)
            await asyncio.sleep(0.1)  # Simula espera não bloqueante
            self.controller.wait_for_machine_idle()
            i += 1
            print("end")

        self.controller.disconnect()
        print("Lighting task finished")

    async def light(self):
        """Inicia o trabalho de light como uma task."""
        print("light")
        
        # Cancela a task atual, se estiver em execução
        await self.stop()

        # Inicia uma nova task para o loop de marcação
        self.current_task = asyncio.create_task(self._light_loop())
        print("New lighting task started")
        return
    
    def convert_gcode_to_mark_job(self, points):
        with self.controller.marking() as c:
            for point in points:
                x, y = utils.mm_to_galvo(point[0], point[1])
                s_val = point[2]
                if s_val == 0:
                    c.dark(x, y)
                else:
                    c.mark(x, y)
    
    async def _mark_loop(self):
        """Loop de marcação executado como uma task separada."""
        self.stop_job = False
        self.controller.connect_if_needed()
        points = utils.parse_gcode(self.gcode_filepath)
        
        print("mark loop start")
        self.convert_gcode_to_mark_job(points)
        await asyncio.sleep(0.1)  # Simula espera não bloqueante
        self.controller.wait_for_machine_idle()
        print("end")

        self.controller.disconnect()
        print("Marking task finished")
    
    async def mark(self):
        """Inicia o trabalho de marcação como uma task."""
        print("mark")

        # Cancela a task atual, se estiver em execução
        await self.stop()

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

    def status(self):
        """Retorna o status da máquina."""
        controllerStatus = "disconnected"
        status = "disconnected"
        try:
            statusInt = self.controller.status()
            print (statusInt)
            if statusInt > -1:
                controllerStatus = "connected"
        except:
            pass
        print ("controllerStatus: " + controllerStatus)
        if controllerStatus == "connected": # self.controller.is_connected
            if self.current_task and not self.current_task.done():
                status = "busy"
            else:
                status = "idle"
        return {"status": controllerStatus + " - " + status}