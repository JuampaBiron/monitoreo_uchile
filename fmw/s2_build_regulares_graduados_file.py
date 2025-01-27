from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import logging
import os
import time
import pandas as pd
from dotenv import load_dotenv
from config import Config
from datetime import datetime
from typing import Optional, Dict, List

load_dotenv()

class UcampusEstudiantesManager:
    def __init__(self, keep_web_alive: bool = True):
        load_dotenv()
        self._initialize_config()
        self._setup_logging()
        self._initialize_driver(keep_web_alive)
        self._initialize_waits()

    def _initialize_config(self) -> None:
        self.url = Config.BASE_URL
        self.min_year = Config.MIN_COHORTE
        self.max_year = Config.MAX_COHORTE
        self.estudiantes_path = Config.STUDENTS_CSV
        self.regulares_path = Config.REGULARES
        self.graduados_path = Config.GRADUADOS
        self.regulares_memory_path = Config.REGULARES_MEMORY
        self.graduados_memory_path = Config.GRADUADOS_MEMORY
        self.min_cohorte_regulares = Config.COHORTE_MIN_REGULARES
        self.min_cohorte_graduados = Config.COHORTE_MIN_GRADUADOS
        self.filter_max_rows = Config.FILTER_MAX_ROWS
        self.credentials = {
            'user': os.getenv("UCAMPUS_USER"),
            'password': os.getenv("UCAMPUS_PASSWORD")
        }

    def _setup_logging(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def _initialize_driver(self, keep_web_alive: bool) -> None:
        options = self._configure_chrome_options()
        self.driver = webdriver.Chrome(options=options, keep_alive=keep_web_alive)

    def _configure_chrome_options(self) -> Options:
        options = Options()
        options.add_argument('--disable-gpu')
        #options.add_argument('--headless=new')
        prefs = {
            "download.default_directory": os.path.curdir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True,
            "safebrowsing.disable_download_protection": True,
        }
        options.add_experimental_option("prefs", prefs)
        return options

    def _initialize_waits(self) -> None:
        self.waits = {
            'short': WebDriverWait(self.driver, 1),
            'medium': WebDriverWait(self.driver, 2),
            'long': WebDriverWait(self.driver, 10),
            'extended': WebDriverWait(self.driver, 20)
        }
    
    def log_in(self) -> None:
        """Realiza el inicio de sesión en Ucampus"""
        self.logger.info("Iniciando proceso de login en Ucampus")
        try:
            self.driver.get(self.url)
            self.driver.maximize_window()
            self.logger.info(f"Página cargada exitosamente: {self.url}")

            elements = {
                'username': (By.XPATH, '//input[@name="username"]'),
                'password': (By.XPATH, '//input[@name="password"]'),
                'submit': (By.XPATH, '//input[@type="submit" and @value="Ingresar"]')
            }

            self.logger.info("Esperando elementos del formulario de login...")
            self.waits['long'].until(EC.element_to_be_clickable(elements['username']))
            
            self.logger.info(f"Ingresando credenciales para usuario: {self.credentials['user']}")
            self.driver.find_element(*elements['username']).send_keys(self.credentials['user'])
            self.driver.find_element(*elements['password']).send_keys(self.credentials['password'])
            
            self.logger.info("Enviando formulario de login")
            self.driver.find_element(*elements['submit']).click()
            
            self.logger.info("Login completado exitosamente")
            
        except TimeoutException:
            self.logger.error("Timeout esperando elementos de login")
            raise
        except Exception as e:
            self.logger.error(f"Error en login: {str(e)}")
            raise

    def _navigate_to_boletines(self) -> None:
        """Navega a la sección de boletines"""
        self.logger.info("Navegando a la sección de boletines...")
        try:
            btn_boletines = (By.XPATH, "//a[contains(@href, 'https://ucampus.uchile.cl/m/fcfm_bia/') and contains(text(), 'Boletines')]")
            self.waits['long'].until(EC.element_to_be_clickable(btn_boletines))
            self.driver.find_element(*btn_boletines).click()
            self.logger.info("Navegación a boletines exitosa")
        except Exception as e:
            self.logger.error(f"Error navegando a boletines: {str(e)}")
            raise

    def _search_student(self, rut: str) -> None:
        """Busca un estudiante por RUT"""
        try:
            # Definir elementos de búsqueda
            elements = {
                'search_field': (By.XPATH, "//input[@type='text' and @class='autofocus' and @placeholder='Persona']"),
                'search_button': (By.XPATH, "//input[@type='submit' and contains(@value, 'Buscar')]")
            }

            # Realizar búsqueda
            self.waits['medium'].until(EC.element_to_be_clickable(elements['search_field']))
            search_field = self.driver.find_element(*elements['search_field'])
            search_field.clear()  # Limpiar campo antes de ingresar nuevo RUT
            search_field.send_keys(rut)
            self.driver.find_element(*elements['search_button']).click()
            
        except TimeoutException:
            raise TimeoutException(f"Timeout buscando estudiante con RUT: {rut}")
        except Exception as e:
            raise Exception(f"Error buscando estudiante {rut}: {str(e)}")
    
    def _check_tesis_section(self) -> bool:
        """Verifica si existe la sección de tesis"""
        try:
            seccion = (By.XPATH, "//h2[contains(text(), 'Exámenes de Grado y/o Título')]")
            self.waits['short'].until(EC.element_to_be_clickable(seccion))
            return True
        except:
            self.logger.info("No existe sección de tesis")
            return False

    def _extract_tesis_row_data(self, row) -> Dict:
        """Extrae la información de una fila de tesis cuando está en la sección de tesis"""
        try:
            return {
                'professor': row.find_element("xpath", "./td[contains(@class, 'privado')]").text,
                'nota': row.find_element("xpath", "./td[contains(@class, 'number')]").text,
                'fecha_examen': row.find_element("xpath", "./td[contains(@class, 'date')]").text,
                'titulo_examen': row.find_element("xpath", ".//a[contains(@href, 'cybertesis')]").text,
                'url_examen': row.find_element("xpath", ".//a[contains(@href, 'cybertesis')]").get_attribute('href'),
                'fecha_inscripcion': '',  # Campo nuevo para mantener consistencia
                'tiene_inscripcion': False  # Indicador de si viene de inscripción
            }
        except Exception as e:
            self.logger.error(f"Error extrayendo datos de fila: {str(e)}")
            return {}

    def _get_info_from_situaciones(self, programa):
        """Extrae la información de tesis desde la sección situaciones"""
        try:
            situaciones_btn = self.driver.find_element("xpath", "//a[contains(@href, 'situaciones?rut=') and text()='Situaciones']")
            situaciones_btn.click()
            
            inscripcion = self.driver.find_element("xpath", f"//td[contains(.,'Inscripción del Tema de Tesis') and contains(.,'{programa}')]")
            if inscripcion:
                texto_completo = inscripcion.find_element("xpath", "./following-sibling::td[contains(@class, 'no-movil')]//h2").text
                
                partes = texto_completo.split("Prof. Guía")
                titulo = partes[0].strip().rstrip('.')
                
                info_adicional = partes[1].split("F.A.E.P.")
                prof_guia = info_adicional[0].strip().rstrip('.')
                
                fecha_raw = info_adicional[1].strip().rstrip('.')
                fecha_dt = datetime.strptime(fecha_raw, '%d.%m.%Y')
                fecha_inscripcion = fecha_dt.strftime('%d-%m-%Y')
                
                # Si encontramos profesor guía e inscripción, debe marcarse como tesista
                return {
                    'professor': prof_guia,
                    'nota': '',
                    'fecha_examen': '',
                    'titulo_examen': titulo,
                    'url_examen': '',
                    'fecha_inscripcion': fecha_inscripcion,
                    'tiene_inscripcion': True  # Esto garantiza que se marque como tesista
                }
                    
            return None
                    
        except Exception as e:
            self.logger.error(f"Error obteniendo información de situaciones: {str(e)}")
            return None
        finally:
            self.driver.back()

    def _get_tesis_info(self, programa: str) -> Optional[Dict]:
        """
        Obtiene la información de tesis para un programa específico.
        
        Args:
            programa (str): Nombre del programa académico
            
        Returns:
            Optional[Dict]: Diccionario con información de la tesis o None si no se encuentra
            {
                'professor': str,
                'nota': str,
                'fecha_examen': str,
                'titulo_examen': str,
                'url_examen': str,
                'fecha_inscripcion': str,
                'tiene_inscripcion': bool
            }
        """
        try:
            seccion_tesis = self._check_tesis_section()
            if not seccion_tesis:
                self.logger.info("No se encontró sección de tesis, buscando en situaciones...")
                info_situaciones = self._get_info_from_situaciones(programa)
                if info_situaciones:
                    return info_situaciones
                return None

            target_table = self.driver.find_element(
                "xpath", 
                "//h2[contains(text(), 'Exámenes de Grado y/o Título')]/following::table[.//th[contains(text(), 'Examen / Título')]]"
            )
            rows = target_table.find_elements("xpath", ".//tbody/tr")

            for row in rows:
                if programa in row.text:
                    return self._extract_tesis_row_data(row)
            return None

        except Exception as e:
            self.logger.error(f"Error obteniendo información de tesis: {str(e)}")
            return None
                
    def _get_fecha_ingreso(self, cohorte: str, semestre: str) -> str:
        """
        Calcula la fecha de ingreso basada en la cohorte y el semestre
        Args:
            cohorte: Año de ingreso
            semestre: 'Primavera' u 'Otoño'
        Returns:
            str: Fecha en formato dd-mm-yyyy
        """
        try:
            año = int(cohorte)
            mes = 9 if semestre == 'Primavera' else 3
            return f"01-{mes:02d}-{año}"
        except ValueError as e:
            self.logger.error(f"Error calculando fecha de ingreso para cohorte {cohorte}: {e}")
            return ""
        
    def _process_single_student(self, row: pd.Series, index: int, df: pd.DataFrame, process_type: str) -> None:
        self._search_student(row['RUT'])
        tesis_info = self._get_tesis_info(row['Nombre del Plan'])

        if tesis_info:
            self.logger.info(f" Información de tesis encontrada para {row['RUT']}")
            self.logger.info(f" Profesor guía: {tesis_info.get('professor', 'No disponible')}")
            self.logger.info(f" Nota: {tesis_info.get('nota', 'No disponible')}")
            self.logger.info(f" Fecha defensa: {tesis_info.get('fecha_examen', 'No disponible')}")
            self.logger.info(f" Titulo: {tesis_info.get('titulo_examen', 'No disponible')}")
            self._update_dataframe(df, index, tesis_info, process_type)
        else:
            self.logger.info(f"No se encontró información de tesis para {row['RUT']}")

    def _update_dataframe(self, df: pd.DataFrame, index: int, tesis_info: Dict, process_type: str) -> None:
        """Actualiza el DataFrame con la información de tesis"""
        try:
            if process_type == 'graduados':
                df.at[index, "Profesor guia"] = tesis_info.get('professor', '')
                df.at[index, "Nota"] = tesis_info.get('nota', '')
                df.at[index, "Fecha examen"] = tesis_info.get('fecha_examen', '')
                df.at[index, "Titulo examen"] = tesis_info.get('titulo_examen', '')
                df.at[index, "Url tesis"] = tesis_info.get('url_examen', '')
                
                if tesis_info.get('fecha_inscripcion'):  # Si viene de situaciones
                    df.at[index, "Permanencia"] = self.calcular_permanencia(
                        tesis_info['fecha_inscripcion'],
                        int(df.at[index, 'Cohorte']),
                        df.at[index, 'Semestre']
                    )
                elif tesis_info.get('fecha_examen'):  # Si viene de exámenes
                    df.at[index, "Permanencia"] = self.calcular_permanencia(
                        tesis_info['fecha_examen'],
                        int(df.at[index, 'Cohorte']),
                        df.at[index, 'Semestre']
                    )
            else:  # regulares
                df.at[index, "Profesor guia"] = tesis_info.get('professor', '')
                df.at[index, "Tesista"] = "TRUE" if tesis_info.get('professor') else "FALSE"

        except Exception as e:
            self.logger.error(f"Error actualizando DataFrame: {str(e)}")

    def _load_and_filter_estudiantes(self, estado_filter: List[str]) -> pd.DataFrame:
        df = pd.read_csv(self.estudiantes_path)
        mask = df["Estado del Plan"].isin(estado_filter)
        return df[mask].copy()

    def _process_dataframe(self, df: pd.DataFrame, additional_columns: Dict) -> pd.DataFrame:
        """
        Procesa el DataFrame aplicando las transformaciones necesarias.
        
        Args:
            df (pd.DataFrame): DataFrame a procesar
            additional_columns (Dict): Columnas adicionales a agregar
            
        Returns:
            pd.DataFrame: DataFrame procesado
        """
        # Crear una copia explícita del DataFrame
        df = df.copy()
        
        # Procesar el Plan
        new_cols = df['Plan'].str.split(' ', n=1, expand=True)
        df.loc[:, 'Codigo Plan'] = new_cols[0]
        df.loc[:, 'Nombre del Plan'] = new_cols[1]

        # Filtrar solo Magíster y Doctorado
        mask = df['Nombre del Plan'].str.contains('Magíster|Doctorado', case=False, na=False)
        df = df[mask].copy()

        # Procesar Semestre Ingreso
        new_cols = df['Semestre Ingreso'].str.extract(r'(\d{4})\s+(.*)')
        df.loc[:, 'Cohorte'] = new_cols[0]
        df.loc[:, 'Semestre'] = new_cols[1]
        
        # Agregar columnas adicionales
        for col, default_value in additional_columns.items():
            df.loc[:, col] = default_value

        return df

    def build_regulares_df(self) -> pd.DataFrame:
        """
        Construye el DataFrame para estudiantes regulares.
        
        Procesa la información de estudiantes en estado Regular, En Proceso de Graduación
        y Postergación, agregando información sobre su condición de tesista y profesor guía.
        
        Returns:
            pd.DataFrame: DataFrame con la información procesada de estudiantes regulares
        """
        try:
            # Asumiendo que tienes una ruta definida para el archivo CSV
            estados_regulares = ["Regular", "En Proceso de Graduación", "Postergación"]
            df_regulares = self._load_and_filter_estudiantes(estados_regulares)
            
            additional_columns = {
                'Tesista': '',
                'Profesor guia': '',
                'Fecha ingreso': ''
            }
            
            df_nuevos_regulares = self._process_dataframe(df_regulares, additional_columns)
            
            # Calcular la fecha de ingreso para cada estudiante
            df_nuevos_regulares['Fecha ingreso'] = df_nuevos_regulares.apply(
                lambda row: self._get_fecha_ingreso(row['Cohorte'], row['Semestre']), 
                axis=1
            )
            
            # Generar ID combinando RUT y código de plan
            df_nuevos_regulares['id'] = df_nuevos_regulares.apply(
                lambda row: f"{row['RUT']}_{row['Codigo Plan']}", 
                axis=1
            )
            
            self.logger.info("DataFrame de regulares construido exitosamente con fechas de ingreso")
            df_nuevos_regulares['Cohorte'] = df_nuevos_regulares['Cohorte'].astype(int)
            df_nuevos_regulares = df_nuevos_regulares.loc[
                df_nuevos_regulares['Cohorte'] >= self.min_cohorte_regulares
            ]
            
            return df_nuevos_regulares[[
                'id', 'RUT', 'Codigo Plan', 'Nombre del Plan', 'Estado del Plan', 
                'Cohorte', 'Semestre', 'Fecha ingreso', 'Tesista', 'Profesor guia'
            ]]
        
        except Exception as e:
            self.logger.error(f"Error construyendo DataFrame de regulares: {e}")
            raise

    def build_graduados_df(self) -> pd.DataFrame:
        """
        Construye el DataFrame para estudiantes graduados.
        
        Procesa la información de estudiantes en estado Graduado y Egresado,
        incluyendo datos de su tesis, calificaciones y tiempo de permanencia
        
        Returns:
            pd.DataFrame: DataFrame con la información procesada de estudiantes graduados
        """
        # Leer base de datos existente
        df_graduados_memory = pd.read_csv(self.graduados_memory_path)
        estados_graduados = ["Graduado", "Egresado"]
        df_graduados = self._load_and_filter_estudiantes(estados_graduados)
        
        # Preparar columnas para comparación en df_graduados
        df_graduados = self._process_dataframe(df_graduados, additional_columns={})
        
        # Crear conjunto de pares (RUT, Código Plan) existentes en la base de datos
        pares_existentes = set(zip(df_graduados_memory['RUT'], df_graduados_memory['Codigo Plan']))
        
        # Filtrar registros que no existen en la base de datos
        mask = ~df_graduados.apply(lambda x: (x['RUT'], x['Codigo Plan']) in pares_existentes, axis=1)
        df_nuevos_graduados = df_graduados[mask].copy()
        logging.info(f"Total graduados {len(df_graduados)}")
        logging.info(f"Nuevos graduados {len(df_nuevos_graduados)}")

        additional_columns = {
            'Titulo examen': '',
            'Url tesis': '',
            'Fecha examen': '',
            'Nota': '',
            'Profesor guia': '',
            'Permanencia': ''
        }
        
        df_nuevos_graduados = self._process_dataframe(df_nuevos_graduados, additional_columns)
        
        # Generar ID combinando RUT y código de plan
        df_nuevos_graduados['id'] = df_nuevos_graduados.apply(
            lambda row: f"{row['RUT']}_{row['Codigo Plan']}", 
            axis=1
        )
        
        df_nuevos_graduados['Cohorte'] = df_nuevos_graduados['Cohorte'].astype(int)
        df_nuevos_graduados = df_nuevos_graduados.loc[
            df_nuevos_graduados['Cohorte'] >= self.min_cohorte_graduados
        ]
        
        return df_nuevos_graduados[[
            'id', 'RUT', 'Codigo Plan', 'Nombre del Plan', 'Estado del Plan', 
            'Cohorte', 'Semestre', 'Titulo examen', 'Fecha examen', 'Url tesis',
            'Nota', 'Profesor guia', 'Permanencia'
        ]]

    def calcular_permanencia(self, fecha_examen: str, cohorte: int, semestre: str) -> float:
        """
        Calcula el tiempo de permanencia de un estudiante en el programa.
        
        Args:
            fecha_examen (str): Fecha del examen de grado en formato dd-mm-yyyy
            cohorte (int): Año de ingreso al programa
            semestre (str): Semestre de ingreso ('Primavera' u 'Otoño')
            
        Returns:
            float: Tiempo de permanencia en años, redondeado a 2 decimales
        """
        fecha_examen_dt = datetime.strptime(fecha_examen, '%d-%m-%Y')
        fecha_inicio = datetime(cohorte, 9 if semestre == 'Primavera' else 3, 1)
        permanencia = (fecha_examen_dt - fecha_inicio).days / 365.25
        return round(permanencia, 2)

    def process_student_data(self, df: pd.DataFrame, process_type: str) -> None:
        """
        Procesa los datos de cada estudiante del DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame con la información de estudiantes a procesar
            process_type (str): Tipo de procesamiento ('regulares' o 'graduados')
        """
        total_students = len(df)
        self.logger.info(f"Iniciando procesamiento de {total_students} estudiantes - Tipo: {process_type}")
        
        self._navigate_to_boletines()
        processed_count = 0
        
        for index, row in df.iterrows():
            processed_count += 1
            self.logger.info(f"Procesando estudiante {processed_count}/{total_students}")
            self.logger.info(f"RUT: {row['RUT']} - Programa: {row['Nombre del Plan']}")
            
            try:
                self._process_single_student(row, index, df, process_type)
                self.logger.info(f"Estudiante procesado exitosamente: {row['RUT']}")
                
                # Logging de progreso cada 10 estudiantes
                if processed_count % 10 == 0:
                    self.logger.info(f"Progreso: {processed_count}/{total_students} ({(processed_count/total_students)*100:.1f}%)")
                
            except Exception as e:
                self.logger.error(f"Error procesando estudiante {row['RUT']}: {e}")
        self._save_progress(df, process_type)
        self.logger.info(f"Procesamiento completado. Total estudiantes: {total_students}")

    

    def _save_progress(self, df: pd.DataFrame, process_type: str) -> None:
        output_path = self.regulares_path if process_type == 'regulares' else self.graduados_path
        try:
            df.to_csv(output_path, index=False)
            self.logger.info(f"Progreso guardado exitosamente en {output_path}")
        except Exception as e:
            self.logger.error(f"Error guardando progreso en {output_path}: {e}")
            raise

    def _merge_and_save_memory(self, new_df: pd.DataFrame, db_path: str) -> None:
        """
        Combina el nuevo DataFrame con la base de datos existente y guarda el resultado.
        
        Args:
            new_df (pd.DataFrame): DataFrame con nuevos registros
            db_path (str): Ruta al archivo de base de datos
        """
        try:
            # Leer base de datos existente
            if os.path.exists(db_path):
                db_df = pd.read_csv(db_path)
                # Combinar DataFrames existentes con nuevos
                merged_df = pd.concat([db_df, new_df], ignore_index=True)
                # Eliminar duplicados basados en 'id' si existe, sino en todos los campos
                merged_df = merged_df.drop_duplicates(subset=['id'] if 'id' in merged_df.columns else None)
            else:
                merged_df = new_df
                
            # Guardar resultado
            merged_df.to_csv(db_path, index=False)
            self.logger.info(f"Base de datos actualizada exitosamente en {db_path}")
            
        except Exception as e:
            self.logger.error(f"Error al combinar y guardar base de datos en {db_path}: {e}")
            raise

    
    def run_workflow(self) -> None:
        """
        Ejecuta el flujo completo de procesamiento de datos.
        """
        self.logger.info(f"=== Iniciando workflow {self.__class__.__name__} ===")
        start_time = time.time()
        
        try:
            if not all(self.credentials.values()):
                self.logger.error("Credenciales no encontradas en las variables de entorno")
                raise ValueError("Credenciales no encontradas en las variables de entorno")
            
            self.logger.info("Iniciando proceso de login")
            self.log_in()
            
            # Procesar graduados
            self.logger.info("Procesando estudiantes graduados")
            graduados_df = self.build_graduados_df()
            self.logger.info(f"Total estudiantes graduados a procesar: {len(graduados_df)}")
            if not graduados_df.empty:
                self.process_student_data(graduados_df, 'graduados')
                self._merge_and_save_memory(graduados_df, self.graduados_memory_path)
            else:
                self.logger.info("No hay nuevos estudiantes graduados para procesar")
            """
            # Procesar regulares
            self.logger.info("Procesando estudiantes regulares")
            regulares_df = self.build_regulares_df()
            self.logger.info(f"Total estudiantes regulares a procesar: {len(regulares_df)}")
            if not regulares_df.empty:
                self.process_student_data(regulares_df, 'regulares')
                self._merge_and_save_memory(regulares_df, self.regulares_memory_path)
            else:
                self.logger.info("No hay nuevos estudiantes regulares para procesar")
                """
        except Exception as e:
            self.logger.error(f"Error en workflow: {e}", exc_info=True)
            raise
        finally:
            execution_time = time.time() - start_time
            self.logger.info(f"Tiempo total de ejecución: {execution_time:.2f} segundos")
            self.driver.quit()
            self.logger.info(f"=== Workflow {self.__class__.__name__} finalizado ===")


if __name__ == "__main__":
    manager = UcampusEstudiantesManager()
    manager.run_workflow()