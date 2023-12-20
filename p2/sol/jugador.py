from utils import validar_celda, comprobar_celda_disponible
from personajes import *


class Jugador:
    def __init__(self):
        self.oponente = None
        self.equipo = []
        self.crear_equipo() # Declaro el posicionamiento en el cliente para poder utilizar la clase sin ejecutarlo.

        self.informe = None


    def set_oponente(self, jugador):
        assert issubclass(type(jugador),
                          Jugador), "Error asignando oponente. Tiene que ser de tipo Jugador y es " + str(type(jugador))
        self.oponente = jugador

    def turno(self):
        if self.informe is not None:
            print('\n---- INFORME ---- ')
            print(self.informe)

        print('\n---- SITUACION DEL EQUIPO ---- ')
        for per in self.equipo:
            print('{} está en {} [Vida {}/{}]'.format(per.nombre, per.posicion, per.vida_actual, per.vida_maxima))

        print('')  # espacio

        accion = self.realizar_accion()
        resultado = self.oponente.recibir_accion(accion)  # Fuera del if siguiente para que oponente actualice su informe
        if resultado is not None:
            print('\n---- RESULTADO DE LA ACCIÓN ----')
            print(resultado['respuesta'])
            victoria = resultado['victoria']
        else:
            self.informe = 'Nada que reportar'
            victoria = False  # No se puede ganar sin agredir al contrario
        return victoria

    def realizar_accion(self):
        acciones_disponibles = self.get_acciones()

        print('\n---- ACCIONES DISPONIBLES ---- ')
        for num, accion in acciones_disponibles.items():
            print('{}: {}'.format(num, accion[0]))

        while True:
            # Elegir accion
            accion = input('Seleccion la acción de este turno: ')
            if accion not in acciones_disponibles:
                print('ERROR: acción inválida')
                continue

            codigo = acciones_disponibles[accion][1]()
            return codigo  # Devolvemos el código de acción

    def recibir_accion(self, codigo):
        # Cuando la acción del contrario no afecta a tu tablero, actualizar informe y devolver None
        if codigo is None:
            self.informe = 'Nada que reportar'
            return None

        personaje = codigo[0]
        coordenadas = codigo[1:]
        resultado = {'respuesta': None, 'victoria': False}  # Plantilla para rellenar

        if personaje == 'A':
            celdas_afectadas = []
            max_col = ord(coordenadas[0]) + 1 if coordenadas[0] < 'D' else ord(coordenadas[0])
            max_row = ord(coordenadas[1]) + 1 if coordenadas[1] < '4' else ord(coordenadas[1])

            for col in range(ord(coordenadas[0]), max_col+1):
                for row in range(ord(coordenadas[1]), max_row + 1):
                    celdas_afectadas.append(chr(col)+chr(row))

            respuesta = ''
            bajas = []
            for c in celdas_afectadas:
                for idx, per in enumerate(self.equipo):
                    if per.posicion == c:
                        per.vida_actual -= 1  # herir
                        if per.vida_actual == 0:
                            respuesta += '{} ha sido eliminado\n'.format(per.nombre)
                            bajas.append(idx)
                            self.info_vivos()
                        else:
                            respuesta += '{} ha sido herido en {} [Vida restante: {}]\n'.format(per.nombre, per.posicion, per.vida_actual)
                            

            for idx in bajas:
                del self.equipo[idx]  # Borrar del equipo
            danyo_restante = 0
            for per in self.equipo:
                danyo_restante += per.danyo
            if len(self.equipo) == 0 or danyo_restante == 0:
                resultado['victoria'] = True

            if respuesta == '':
                respuesta = 'Ningún personaje ha sido herido\n'
            resultado['respuesta'] = respuesta

        elif personaje == 'F':
            idx = 0
            respuesta = ''
            for idx, per in enumerate(self.equipo):
                if per.posicion == coordenadas:
                    per.vida_actual = 0
                    respuesta = '{} ha sido eliminado\n'.format(per.nombre)
                    break

            del self.equipo[idx]  # Borrar del equipo

            danyo_restante = 0
            for per in self.equipo:
                danyo_restante += per.danyo
            if len(self.equipo) == 0 or danyo_restante == 0:
                resultado['victoria'] = True

            if respuesta == '':
                respuesta = 'Ningún personaje ha sido herido\n'
            resultado['respuesta'] = respuesta

        elif personaje == 'I':
            celdas_afectadas = []
            max_col = ord(coordenadas[0]) + 1 if coordenadas[0] < 'D' else ord(coordenadas[0])
            max_row = ord(coordenadas[1]) + 1 if coordenadas[1] < '4' else ord(coordenadas[1])

            for col in range(ord(coordenadas[0]), max_col+1):
                for row in range(ord(coordenadas[1]), max_row + 1):
                    celdas_afectadas.append(chr(col)+chr(row))

            respuesta = ''
            for c in celdas_afectadas:
                for per in self.equipo:
                    if per.posicion == c:
                        respuesta += '{} ha sido avistado en {}\n'.format(per.nombre, per.posicion)

            if respuesta == '':
                respuesta = 'Ningún personaje ha sido revelado\n'
            resultado['respuesta'] = respuesta
        self.informe = resultado['respuesta']
        return resultado

    def posicionar_equipo(self):
        assert len(self.equipo) > 0, 'Error: no hay equipo que posicionar!'

        print('Vamos a posicionar a nuestros personajes en el tablero!')
        for personaje in self.equipo:
            celda_valida = False
            while not celda_valida:
                celda = input('Indica la celda (A-D, 1-4. p.ej: B2) en la que posicionar al {}: '.format(personaje.nombre))
                celda = celda.upper()
                celda_valida = validar_celda(celda, 'D', '4')
                if not celda_valida:
                    print('Ups... valor de celda incorrecto. ')
                else:
                    disponible = comprobar_celda_disponible(celda, self.equipo)
                    if disponible:
                        personaje.posicion = celda
                    else:
                        celda_valida = False
                        print('Ups... la celda ya está ocupada!')
                        continue

        print('Posicionamiento terminado\n')

    def crear_equipo(self):
        # Equipo por defecto. Se podría sobrecargar para cambiar la configuración de personajes como extensión
        medico = Medico(self.equipo)
        artillero = Artillero(self.equipo)
        francotirador = Francotirador(self.equipo)
        intel = Inteligencia(self.equipo)
        self.equipo.extend([medico, artillero, francotirador, intel])

    def get_acciones(self):
        acciones_disponibles = dict()
        contador_acciones = 1
        for per in self.equipo:
            acciones_disponibles[str(contador_acciones)] = ('Mover ({})'.format(per.nombre), per.mover)
            contador_acciones += 1
            if per.habilidad_disponible():
                acciones_disponibles[str(contador_acciones)] = ('{} ({})'.format(per.desc_habilidad(), per.nombre), per.habilidad)
                contador_acciones += 1

        return acciones_disponibles

    def info_vivos(self) -> int:
        return len(self.equipo)