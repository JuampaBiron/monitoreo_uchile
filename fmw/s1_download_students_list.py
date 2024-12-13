import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import logging
import os
from dotenv import load_dotenv
from config import Config

# Configuración del logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class UcampusEstudiantesPostgrado:
    def __init__(self, keep_web_alive=True):
        load_dotenv()
        self.url = Config.BASE_URL
        self.keep_web_alive = keep_web_alive
        self.logger = logging.getLogger(self.__class__.__name__)
        self.user = os.getenv("UCAMPUS_USER")
        self.password = os.getenv("UCAMPUS_PASSWORD")
        self.driver = self._setup_driver()
        self.wait_1 = WebDriverWait(self.driver, 1)
        self.wait_2 = WebDriverWait(self.driver, 2)
        self.wait_10 = WebDriverWait(self.driver, 10)
        self.wait_20 = WebDriverWait(self.driver, 20)
        self.students_csv_file = Config.STUDENTS_CSV
        os.makedirs(os.path.dirname(self.students_csv_file), exist_ok=True)

    def _setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--headless=new') 
        chrome_prefs = {
            "download.default_directory": os.path.curdir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True,
            "safebrowsing.disable_download_protection": True,
        }
        chrome_options.add_experimental_option("prefs", chrome_prefs)
        return webdriver.Chrome(options=chrome_options, keep_alive=self.keep_web_alive)
    
    def close(self):
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
        except Exception as e:
            logging.warning(f"Error al cerrar el driver: {str(e)}")
            # Si hay error al cerrar normalmente, intentamos forzar el cierre
            try:
                if self.driver:
                    self.driver.close()
                    self.driver = None
            except:
                pass
    
    def log_in(self):
        self.driver.get(self.url)
        self.driver.maximize_window()
        logging.info(f"Página cargada: {self.url}")
        input_text_field = (By.XPATH,'//input[@name="username"]')
        input_password = (By.XPATH,'//input[@name="password"]')
        btn_ingresar = (By.XPATH, '//input[@type="submit" and @value="Ingresar"]')
        self.wait_10.until(EC.element_to_be_clickable(input_text_field))
        self.driver.find_element(*input_text_field).send_keys(self.user)
        self.driver.find_element(*input_password).send_keys(self.password)
        self.driver.find_element(*btn_ingresar).click()
    
    def get_cookies(self):
        selenium_cookies = self.driver.get_cookies()
        # Convertir las cookies a formato string para requests
        cookies_str = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in selenium_cookies])
        return cookies_str
    
    def get_csrf_token(self, cookies):
        try:
            url = self.url + Config.CSRF_ENDPOINT
            params = {
                "id": "estadisticas__alumnos_postgrado@fcfm.escpostgrado"
            }
            headers = {
                "Cookie": cookies
            }
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                import re
                # Buscar el token CSRF en el script de kernel
                csrf_match = re.search(r'name="csrf"\s+value="([^"]+)"', response.text)
                if csrf_match:
                    return csrf_match.group(1)
                    
            logging.warning(f"No se pudo encontrar el token CSRF. Status code: {response.status_code}")
            return None
            
        except Exception as e:
            logging.error(f"Error obteniendo CSRF: {str(e)}")
            return None
        
    def download_students_csv(self, cookies, csrf):
        logging.info("Iniciando descarga de archivo CSV")
        url = self.url + Config.CSRF_ENDPOINT
        params = {
            "id": "estadisticas__alumnos_postgrado@fcfm.escpostgrado",
            "csrf": csrf,
            "accion": "bajar",
            "bajar": "csv"
        }
        
        headers = {
            "Cookie": cookies
                    }
        try:
            response = requests.get(url, 
                                    params=params,
                                    headers=headers
                                    )
            # Verificar si la solicitud fue exitosa
            if response.status_code == 200:
                # Guardar el archivo
                with open(self.students_csv_file, "wb") as f:
                    f.write(response.content)
                logging.info("Archivo descargado exitosamente")
            else:
                logging.error(f"Error en la descarga. Código de estado: {response.status_code}")
            
        except Exception as e:
            logging.error(f"Error durante la descarga: {str(e)}")
                   
    
    def run_workflow(self):
        logging.info(f"************ Inicio del workflow {self.__class__.__name__} ************")
        try:
            if not self.user or not self.password:
                logging.error("Credenciales no encontradas en las variables de entorno. Finalizando el proceso.")
                return
            logging.info("Starting Ucampus Login")
            self.log_in()
            logging.info("Finishing Ucampus Login")
            
            # Obtener cookies y descargar archivo
            cookies = self.get_cookies()
            csrf = self.get_csrf_token(cookies)
            print(csrf)
            self.download_students_csv(cookies,csrf)
            
        except Exception as e:
            logging.error(f"Error en workflow: {self.__class__.__name__}: {e}", exc_info=True)
        finally:
            self.close()
            logging.info(f"************ Termino del workflow {self.__class__.__name__} ************")

if __name__ == "__main__":
    proceso = UcampusEstudiantesPostgrado()
    proceso.run_workflow()