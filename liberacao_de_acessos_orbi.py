from asyncio import wait
import shutil
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyodbc
import keyring

def start_driver():
    """
    Inicializa o driver do Selenium com a janela maximizada.
    :return: driver do Selenium com a janela maximizada
    """
    options = Options()
    options.add_argument("--start-maximized")
    return webdriver.Chrome(options=options)

def main_func(driver, wait, resultados): 
    """
    Realiza a liberação dos relatorios cargo no sistema Orbi.
    :param driver: Driver do Selenium
    :param wait: WebDriverWait do Selenium
    :param resultados: lista de tuplas com o nome do perfil e o Cargo
    :return: None
    """

    senha = keyring.get_password("orbi", "e.gustavo.santos") # se futuramente precisar alterar o login, alterar aqui também
    if not senha:
        print("Senha não encontrada no keyring. Por favor, defina a senha.")
        return
    control = 0
    for key in resultados:
        driver.get("https://pegasus/Orbi/modulo-administrativo/gerenciamento-perfis-concessao") # get orbi
        
        if control == 0:
            wait.until(EC.element_to_be_clickable((By.ID, "Login"))).send_keys("e.gustavo.santos" + Keys.TAB + senha + Keys.TAB + Keys.ENTER) # login e senha / se futuramente precisar alterar o login, alterar aqui também
            wait.until(EC.element_to_be_clickable((By.ID, "adopt-accept-all-button"))).click() # aceitar cookies
        control = 1

        time.sleep(7) 
        wait.until(EC.presence_of_element_located((By.XPATH, "//select[@name='lista-relatorio_length']"))).send_keys(Keys.ENTER + Keys.ARROW_DOWN + Keys.ARROW_DOWN + Keys.ARROW_DOWN + Keys.ENTER) # selecionar 40 itens por pagina para os relatorios
        div_relatorios = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[1]/div[2]/div[1]/div[2]/div/div/div[2]/div"))) # div que contem os relatorios
        linhas_relatorios = div_relatorios.find_elements(By.XPATH, "//*[@role='row']") # atualizar a lista de checkbox

        for rl in linhas_relatorios:
            texto_splitado = rl.text.split(" ", 3)
            if len(texto_splitado) > 2:
                nome_relatorio = texto_splitado[3].replace(" POWERBI", "").strip()
                if nome_relatorio in resultados[key]:
                    rl.find_element(By.CLASS_NAME, "select-checkbox").click()
            
        wait.until(EC.presence_of_element_located((By.XPATH, "//select[@name='grupo-centro-resultado_length']"))).send_keys(Keys.ENTER + Keys.ARROW_DOWN + Keys.ARROW_DOWN + Keys.ARROW_DOWN + Keys.ENTER) # selecionar 40 itens por pagina para as liberacoes
        wait.until(EC.presence_of_element_located((By.XPATH, "//table[@id='grupo-centro-resultado']/thead/tr[2]/th[4]/input"))).send_keys(key) # pesquisar cargo
        time.sleep(7) # aguardar carregamento
        elemento_down = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id='grupo-centro-resultado_paginate']/ul/li[2]/a"))) # localizar elemento paginação
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", elemento_down) # rolar para baixo
        itens_paginas = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "li"))) # define todos os elementos de paginação
        total_paginas = int(itens_paginas[-2].find_element(By.TAG_NAME, "a").text) # define o total de páginas
        elemento_up = wait.until(EC.presence_of_element_located((By.XPATH, "//select[@name='lista-relatorio_length']"))) # localizar elemento no topo 
        div_liberacoes = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[1]/div[2]/div[2]/div[2]/div/div/div[2]/div"))) # div que contem os checkbox de cr
        itens_flags = div_liberacoes.find_elements(By.CLASS_NAME, "select-checkbox") # atualizar a lista de checkbox
        for i in range(total_paginas):
            for item in itens_flags:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", item) # rolar para o checkbox
                item.click()
                if item == itens_flags[-1] and total_paginas > 1: # se for o ultimo checkbox e tiver mais de uma pagina
                    wait.until(EC.element_to_be_clickable((By.XPATH, "//li[@id='grupo-centro-resultado_next']/a"))).click() # proxima pagina 
                    driver.execute_script("arguments[0].scrollIntoView(true);", elemento_up)
                    itens_flags = div_liberacoes.find_elements(By.CLASS_NAME, "select-checkbox") # atualizar a lista de checkbox
                    time.sleep(0.5)
                    break
        if i == int(total_paginas) - 1: # se for a ultima pagina
            element_associar = wait.until(EC.presence_of_element_located((By.ID, "associar"))) # localizar elemento associar perfil
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", element_associar) # rolar para baixo
            wait.until(EC.element_to_be_clickable((By.ID, "associar"))).click() # associar perfil
            wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@id='message-box']/div/div/div[3]/button"))).click() # entendi
        print(f"Finalizado para o cargo {key} - liberando os relatorios {resultados[key]}.")

def conexao_bd():
    """
    Conecta ao banco de dados do ROBBYSON e retorna uma lista
    com os resultados da consulta "select * from acessos_orbi".
    Retorna:
    list: Uma lista com os resultados da consulta.
    """

    conn = pyodbc.connect(
    "Driver={SQL Server};"
    "Server=primno4;"  
    "Database=Robbyson;"
    "Trusted_Connection=yes;"  
    )

    cur = conn.cursor()
    cur.execute("select * from acessos_orbi")
    resultados = cur.fetchall()
    cur.close()
    conn.close()

    del resultados[0]

    cargos = (['ANALISTA', 'AUXILIAR', 'COORDENADOR', 'DESENVOLVIMENTO OPERACIONAL', 'GERENTE', 'INSTRUTOR', 'MONITOR', 'SUPERINTENDENTE', 'SUPERVISOR'],)

    dic = {}
    for i in range(9):
        dic[cargos[0][i]] = [tupla[1] for tupla in resultados if cargos[0][i] in tupla]

    return dic

if __name__ == "__main__":

    # keyring.set_password("orbi", "coloque seu login aqui", "coloque sua senha aqui") # se futuramente precisar alterar o login e senha, alterar nas linhas 32 e 35 tambem. Apos isso, descomentar as proximas 3 linhas e rodar o script uma vez
    # time.sleep(5)
    # exit()

    resultados = conexao_bd()
    chromedriver = os.path.expanduser(r'~\.cache\selenium\chromedriver\win64')

    if os.path.exists(chromedriver):
        if len(os.listdir(chromedriver)) >= 2:
            shutil.rmtree(chromedriver+"\\")

    driver = start_driver()
    wait = WebDriverWait(driver, 120)
    main_func(driver, wait, resultados)