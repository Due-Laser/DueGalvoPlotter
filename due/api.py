import asyncio
import socket
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from due.machine_control import MachineControl

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

PORT = find_free_port()  # Encontra uma porta disponível
PORT = 5000  # Porta fixa para facilitar a execução do exemplo

class MachineAPI:
    def __init__(self):
        self.app = FastAPI()
        self.settings_file = "settings_lmw200.json"
        self.machine_control = MachineControl(self.settings_file)
        self.gcode_filepath = "C:/Users/User/Documents/Due Laser/Github/DueGalvoPlotter/due/weg_50x50.g"  # Variável de instância ao invés de global

        # Adicionando rotas à API
        self.app.post("/gcode_filepath")(self.set_gcode_filepath)
        self.app.get("/gcode_filepath")(self.get_gcode_filepath)
        self.app.post("/light")(self.light)
        self.app.post("/mark")(self.mark)
        self.app.post("/stop")(self.stop)
        self.app.get("/machine_status")(self.machine_status)

    class FilePathRequest(BaseModel):
        filePath: str

    async def set_gcode_filepath(self, request: FilePathRequest):
        """Define o caminho do arquivo GCode."""
        self.gcode_filepath = request.filePath
        return {"message": "GCode path set successfully", "filePath": self.gcode_filepath}

    async def get_gcode_filepath(self):
        """Retorna o caminho do GCode armazenado."""
        if self.gcode_filepath is None:
            raise HTTPException(status_code=400, detail="GCode file path not set")
        return {"filePath": self.gcode_filepath}

    async def mark(self):
        """Executa a marcação."""
        if self.settings_file is None:
            raise HTTPException(status_code=400, detail="Settings file not set")
        if self.gcode_filepath is None:
            raise HTTPException(status_code=400, detail="GCode file path not set")
        self.machine_control.gcode_filepath = self.gcode_filepath
        self.machine_control.settings_file = self.settings_file
        # Executa o job de forma assíncrona
        #asyncio.create_task(self.machine_control.mark())
        await self.machine_control.mark()
        return {"message": "Marking process started", "filePath": self.gcode_filepath}

    async def light(self):
        """Executa o light."""
        if self.settings_file is None:
            raise HTTPException(status_code=400, detail="Settings file not set")
        if self.gcode_filepath is None:
            raise HTTPException(status_code=400, detail="GCode file path not set")
        self.machine_control.gcode_filepath = self.gcode_filepath
        self.machine_control.settings_file = self.settings_file
        asyncio.create_task(self.machine_control.light())
        return {"message": "Lighting process started", "filePath": self.gcode_filepath}
    
    async def stop(self):
        await self.machine_control.stop()
        return {"message": "Marking/lighting stopped"}
    
    async def machine_status(self):
        status = self.machine_control.status()
        return status

# Criando uma instância da classe e acessando o FastAPI
api_instance = MachineAPI()
app = api_instance.app

if __name__ == "__main__":
    print(f"API rodando na porta {PORT}")
    uvicorn.run(app, host="127.0.0.1", port=PORT)