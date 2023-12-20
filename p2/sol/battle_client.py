import pickle

from utils import limpiar_terminal
from jugador import Jugador
import sys
import socket

ip = '127.0.0.1'
puerto = 5555

def main():
    # Conectamos con el servidor
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, puerto))
    print('Bienvenidos a Tactical Battle. A jugar!')

    # Elegimos un nombre en el servidor?
    nombre = input("Introduce tu nombre de usuario: ")
    s.sendall(nombre.encode())

    print('Buscando oponente. Espere, por favor.')
    # Hace falta?
    oponente = s.recv(1024)
    oponente = oponente.decode()  # nombre del usuario oponente
    print(f'Oponente encontrado. Jugarás contra {oponente}')

    miturno = s.recv(1024)
    miturno = pickle.loads(miturno)  # True si este cliente empieza

    # Indicar tablero preparado al server
    # Creamos nuestro jugador
    input('Fase de preparación. Pulsa intro para comenzar')
    j1 = Jugador()
    j1.posicionar_equipo()
    s.sendall(pickle.dumps(True))
    print('Tablero preparado. Esperando al oponente...\n')

    limpiar_terminal()
    victoria = False
    while not victoria:
        sys.stdin.flush()  # Eliminar texto que se haya introducido mientras se espera el turno
        if not miturno:
            print('Turno del oponente. Esperando a que termine su ronda...')
            # Recibir ataque
            codigo = s.recv(1024)
            codigo_decodificado = pickle.loads(codigo)

            # Calcular resultado de la accion
            resultado = j1.recibir_accion(codigo_decodificado)
            if resultado is not None:
                victoria = resultado['victoria']
            else:
                j1.informe = 'Nada que reportar'
                victoria = False

            # Codificar respuesta
            resultado_codificado = pickle.dumps(resultado)

            # Enviar respuesta a atacante
            s.sendall(resultado_codificado)

            if victoria:
                print("***** Has perdido la partida! *****")
                v = len(j1.equipo)
                vivos = str(v)
                s.sendall(vivos.encode())
                break
        else:
            input('Es tu turno. Pulsa intro para comenzar')
            if j1.informe is not None:
                print('\n---- INFORME ---- ')
                print(j1.informe)

            print('\n---- SITUACION DEL EQUIPO ---- ')
            for per in j1.equipo:
                print('{} está en {} [Vida {}/{}]'.format(per.nombre, per.posicion, per.vida_actual, per.vida_maxima))

            print('')  # espacio

            # Elegir acción del turno
            accion = j1.realizar_accion()

            # Enviar código de acción
            s.sendall(pickle.dumps(accion))

            # Recibir respuesta
            resultado = s.recv(1024)
            resultado = pickle.loads(resultado)

            if resultado is not None:
                print('\n---- RESULTADO DE LA ACCIÓN ----')
                print(resultado['respuesta'])
                victoria = resultado['victoria']
            else:
                victoria = False

            if not victoria:
                print('Turno terminado')
            else:
                print("***** Has ganado la partida! *****")
                v = len(j1.equipo)
                vivos = str(v)
                s.sendall(vivos.encode())
                break

        # Cambiar jugador
        miturno = not miturno
    print("Cerrando conexión")
    s.close()  # Cerramos socket
    return 0


if __name__ == '__main__':
    main()