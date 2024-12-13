import logging
import os
from enum import Enum
from config import Config
from build_worktray import BuildWorktray
from s1_download_students_list import UcampusEstudiantesPostgrado
from s2_ucampus_get_estudiantes import UcampusGetEstudiantesRegulares  

# Configuración del logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class State(Enum):
    BUILD_WORKTRAY = 0
    DOWNLOAD_STUDENTS = 1
    GET_ESTUDIANTES = 2

class Robot:
    def __init__(self, start_state: int, final_state: int):
        self.url = Config.BASE_URL
        self.state = start_state
        self.final_state = final_state
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        self.logger.info(f"Iniciando proceso desde estado {self.state} hasta estado {self.final_state}")
        try:
            while self.state <= self.final_state:
                self.logger.info(f"Ejecutando estado {self.state}")
                
                if self.state == State.BUILD_WORKTRAY.value:
                    BuildWorktray().run_workflow()
                elif self.state == State.DOWNLOAD_STUDENTS.value:
                    UcampusEstudiantesPostgrado().run_workflow()
                elif self.state == State.GET_ESTUDIANTES.value:
                    UcampusGetEstudiantesRegulares().run_workflow()
                else:
                    self.logger.warning(f"Estado {self.state} no implementado")
                
                self.state += 1
                
        except Exception as e:
            self.logger.error(f"Error en estado {self.state}: {str(e)}", exc_info=True)
            raise
        
        self.logger.info("Proceso completado exitosamente")

if __name__ == "__main__":    
    try:
        robot = Robot(start_state=0, final_state=2)
        robot.run()
    except Exception as e:
        logging.error(f"Error en la ejecución del robot: {str(e)}", exc_info=True)
        exit(1)