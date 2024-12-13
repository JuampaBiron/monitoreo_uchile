
class Config:
    # URLs
    BASE_URL = "https://ucampus.uchile.cl"
    CSRF_ENDPOINT = "/m/estadisticas/funcion"
    
    # Parametros
    ESTADISTICAS_PARAMS = {
        "id": "estadisticas__alumnos_postgrado@fcfm.escpostgrado"
    }
    #Cohortes
    MIN_COHORTE = 2018
    MAX_COHORTE = 2024

    PROCESS_DATA_FOLDER = r"process_data"
    #archivos input
    TEMPLATE_WORKTRAY = r"input\_worktray_template.xlsx"
    TEMPLATE_ESTUDIANTES = r"input\_estudiantes_postgrado.xlsx"
    TEMPLATE_PROGRAMAS= r"input\_programas_postgrado.xlsx"
    TEMPLATE_PROFESORES = r"input\_profesores.xlsx"
    #archivos process_data
    WORKTRAY = r"process_data\worktray.xlsx"
    ESTUDIANTES = r"process_data\estudiantes_postgrados.xlsx"
    PROGRAMAS = r"process_data\programas_postgrado.xlsx"
    PROFESORES = r"process_data\profesores.xlsx"
    STUDENTS_CSV = r"process_data\alumnos_postgrado.csv"
    #s2_ucampus_get_estudiantes
