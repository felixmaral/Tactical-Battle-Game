import random
import socket
import pickle
import sys
import threading
from cola import Cola, Nodo

# python3 servidor.py <puerto> <numero_partidas_simultaneas> 

puerto = int(sys.argv[1])
max_partidas = int(sys.argv[2])
file = sys.argv[3]

lock_lobby = threading.Lock()
lock_partidas = threading.Lock()
lock_cola_espera = threading.Lock()  # Agrega la declaración del candado aquí

usuarios_lobby = []
partidas_en_curso = []
cola_espera = Cola()

class Partida:
    def __init__(self, j1, j2):
        self.j1 = j1
        self.j2 = j2

class Cliente:
    def __init__(self, nombre, skt):
        self.nombre = nombre
        self.socket = skt
        self.info_vivos = None
        self.score = None

def manejar_cola_espera():
    while True:
        if not cola_espera.vacia() and len(partidas_en_curso) < max_partidas:
            lock_cola_espera.acquire()
            cliente_en_espera = cola_espera.desencolar()
            lock_cola_espera.release()

            lock_partidas.acquire()
            j1 = usuarios_lobby[0]
            j2 = cliente_en_espera
            juego = Partida(j1, j2)
            partidas_en_curso.append(juego)
            threading.Thread(target=jugar_partida, args=(juego,)).start()
            print(f'{len(partidas_en_curso)} partidas en curso')
            lock_partidas.release()

def bienvenida_usuario(clt_socket):
    global lock_lobby,lock_partidas,lock_cola_espera,partidas_en_curso
    global cola_espera
    global max_partidas

    # Elegir nombre de usuario
    nombre = clt_socket.recv(1024)
    if not nombre:
        clt_socket.close()
        print("El cliente ha cancelado la conexión antes de elegir nombre")
        return
    nombre_decoded = nombre.decode()

    # Meter cliente a lobby o emparejar si hay alguien esperando
    lock_lobby.acquire()
    if len(usuarios_lobby) != 0:  # Alguien esperando a jugar, emparejar
        
        usuarios_lobby.append(Cliente(nombre_decoded,clt_socket))
        j2 = usuarios_lobby[1]
        j1 = usuarios_lobby[0]

        lock_partidas.acquire()
        try:
            if len(partidas_en_curso) < max_partidas:  # Asegurémonos de que no exceda el límite
                usuarios_lobby.remove(usuarios_lobby[1])
                usuarios_lobby.remove(usuarios_lobby[0])
                juego = Partida(j1, j2)
                partidas_en_curso.append(juego)
                threading.Thread(target=jugar_partida, args=(juego,)).start()
                print(f'{len(partidas_en_curso)} partidas en curso')
            else:
                lock_cola_espera.acquire()
                cola_espera.encolar(j2)
                lock_cola_espera.release()
                print(f'Cliente en cola de espera ({cola_espera.size} en espera)')
        finally:
            lock_partidas.release()

    else:  # Registrar usuario al lobby
        usuarios_lobby.append(Cliente(nombre_decoded, clt_socket))  # Usuario en lobby
        
        if len(partidas_en_curso) >= max_partidas:
            try:
                lock_cola_espera.acquire()
                cola_espera.encolar(usuarios_lobby[0])
            finally:
                lock_cola_espera.release()
                print(f'Cliente en cola de espera ({cola_espera.size} en espera)')

    lock_lobby.release()

def terminar_partida():
    global lock_partidas, cola_espera, partidas_en_curso
    lock_partidas.acquire()
    try:
        if len(partidas_en_curso) < max_partidas and cola_espera.size >= 2:
   
            j1 = cola_espera.desencolar()
            j2 = cola_espera.desencolar()

            lock_lobby.acquire()
            usuarios_lobby.remove(usuarios_lobby[1])
            usuarios_lobby.remove(usuarios_lobby[0])
            lock_lobby.release()

            juego = Partida(j1,j2)
            partidas_en_curso.append(juego)
            threading.Thread(target=jugar_partida, args=(juego,)).start()
            print(f'{len(partidas_en_curso)} partidas en curso')
    finally:    
            lock_partidas.release()

def ranking(j1, j2, ganador, turno, partida):

    global file
    
    # Puntuaciones base
    puntuacion_ganador = 1000
    puntuacion_perdedor = 0

    # Puntuación por personajes vivos y eliminados
    puntuacion_vivos_j1 = 100 * j1.info_vivos
    puntuacion_vivos_j2 = 100 * j2.info_vivos
    
    puntuacion_eliminados_j1 =  100 * (4 - j2.info_vivos)
    puntuacion_eliminados_j2 = 100 * (4 - j1.info_vivos)

    # Puntuación por turnos restantes (máximo 200 puntos)
    puntuacion_turnos_g = max(0, (20 - (turno))) * 20
    puntuacion_turnos_p = 0
    if (turno) > 10: 
       puntuacion_turnos_p = ((turno) - 10) * 20

    # Asignación de puntuaciones al ganador y perdedor
    if j1 is ganador:
        puntuacion_ganador += puntuacion_vivos_j1 + puntuacion_eliminados_j1 + puntuacion_turnos_g
        puntuacion_perdedor += puntuacion_vivos_j2 + puntuacion_eliminados_j2 + puntuacion_turnos_p
    elif j2 is ganador:
        puntuacion_ganador += puntuacion_vivos_j2 + puntuacion_eliminados_j2 + puntuacion_turnos_g
        puntuacion_perdedor += puntuacion_vivos_j1 + puntuacion_eliminados_j1 + puntuacion_turnos_p

    if puntuacion_ganador < puntuacion_perdedor:
        puntuacion_perdedor = 900
        puntuacion_ganador = 1000

    puntuaciones = {
        partida.j1.nombre: str(puntuacion_ganador) if j1 is ganador else str(puntuacion_perdedor),
        partida.j2.nombre: str(puntuacion_ganador) if j2 is ganador else str(puntuacion_perdedor)
    }

    if j1 is ganador:
        j1.score = puntuacion_ganador
        j2.score = puntuacion_perdedor
    else:
        j1.score = puntuacion_perdedor
        j2.score = puntuacion_ganador

    print(turno)

    for jugador, puntuacion in puntuaciones.items():
        print(f'{jugador}: {puntuacion}')

    with open(file, 'a') as file:
        for clave, valor in puntuaciones.items():
            file.write(f'{clave}: {valor}\n')
    
    scores = [j1.score, j2.score]
    
    return scores

def jugar_partida(partida):
    global partidas_en_curso
    print(f"Partida comenzada entre {partida.j1.nombre} y {partida.j2.nombre}")

    jugadores = [partida.j1, partida.j2]  # Facilitar turnos de jugadores

    # Les damos a conocer
    jugadores[0].socket.sendall(jugadores[1].nombre.encode())
    jugadores[1].socket.sendall(jugadores[0].nombre.encode())

    # Tirar moneda para ver quien empieza
    jugador_activo = random.randint(0, 1)
    empieza_j1 = jugador_activo == 0

    # Les indico quien empieza
    jugadores[0].socket.sendall(pickle.dumps(empieza_j1))
    jugadores[1].socket.sendall(pickle.dumps(not empieza_j1))

    # Espero a que tengan los tableros preparados. TODO Comprobar mensaje?
    jugadores[0].socket.recv(1024)
    jugadores[1].socket.recv(1024)

    # Bucle de turnos
    turno = 1
    while True:
        print("Ronda", turno, ". Ataca:", jugadores[jugador_activo].nombre, "Defiende:", jugadores[jugador_activo-1].nombre)
        # Recibir acción del jugador activo
        codigo = jugadores[jugador_activo].socket.recv(1024)

        # Enviar acción al jugador que espera
        print("Contactando con el oponente para recibir resultado")
        jugadores[jugador_activo-1].socket.sendall(codigo)

        # Recibir resultado del jugador atacado
        resultado = jugadores[jugador_activo-1].socket.recv(1024)
        resultado_decodificado = pickle.loads(resultado)
        print("Resultado recibido:", resultado_decodificado)

        # Enviar resultado de la acción al jugador que atacó
        print("Enviando resultado al atacante")
        jugadores[jugador_activo].socket.sendall(resultado)

        if resultado_decodificado is not None and resultado_decodificado["victoria"]:
            print("Partida terminada. Ha ganado:", jugadores[jugador_activo].nombre)
            # TODO Actualizar algo en la lista de partidas?

            v1 = jugadores[0].socket.recv(1024).decode()
            v2 = jugadores[1].socket.recv(1024).decode()

            jugadores[0].info_vivos = int(v1)
            jugadores[1].info_vivos = int(v2)
            ganador = jugadores[jugador_activo]
            scores = ranking(jugadores[0], jugadores[1], ganador, turno, partida)

            score1 = (str(scores[0])).encode()
            score2 = (str(scores[1])).encode()

            jugadores[0].socket.sendall(score1)
            jugadores[1].socket.sendall(score2)

            partidas_en_curso.remove(partida)
            terminar_partida()
            break

        # Actualizar el índice del jugador activo
        jugador_activo = (jugador_activo+1) % 2

        turno += 1


print("Arrancando servidor...")
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('127.0.0.1', puerto))
server_socket.listen()

# Imprimir IP del servidor
nombre_server = socket.gethostname()
print(socket.gethostbyname(nombre_server))

try:
     # Inicia un hilo para manejar la cola de espera
    threading.Thread(target=manejar_cola_espera).start()
    while True:
        client_socket, addr = server_socket.accept()
        if client_socket:
            print("Cliente conectado: ", addr)
            threading.Thread(target=bienvenida_usuario, args=(client_socket,)).start()

except KeyboardInterrupt:
    print("Apagado solicitado")

server_socket.close()
print("Apagando servidor...")