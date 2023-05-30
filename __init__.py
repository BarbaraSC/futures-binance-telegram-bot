from enum import *
from binance import enums
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException
from telegram.ext import Updater, CommandHandler
from binance.client import Client
from binance.enums import *
from commands import *
import requests
from dotenv import load_dotenv

load_dotenv()
import os

# url = 'https://testnet.binancefuture.com'

apikey = os.getenv('TELEGRAM_API_KEY')


updater = Updater(token=apikey, use_context=True)
dispatcher = updater.dispatcher
dispatcher.add_handler(CommandHandler('uwu', command_uwu))
dispatcher.add_handler(CommandHandler('owo', command_owo))


#Binance API Futures
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

# Testnet futures
# api_key = '8c44e5545bd3dfbda1a910f2d67d25d381cfd128db02314a1c85986837b8f62c'
# api_secret = 'bdad1b1d8300fff96d77a964022f9d1415b95d2e20a2b20061c4af14e81f4cf7'
hedgeMode: True

# client = Client(api_key, api_secret, testnet=True)
client = Client(api_key, api_secret)
# client.futures_change_position_mode(dualSidePosition=True)


# Obtener información de la cuenta
info = client.futures_account_balance()
print (info)


# Consultar el saldo de tu cuenta de futuros en USDT
def consultar_saldo(update, context):
    futures_balance = client.futures_account_balance()[8]['withdrawAvailable']
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Tu saldo de USDT en Binance Futures es: {futures_balance}")  
    
dispatcher.add_handler(CommandHandler('saldo', consultar_saldo))

def get_futures_leverage(update, context):
    args = context.args
    symbol = args[0].upper()
    futures_position_info = client.futures_account_positionrisk(symbol=symbol)
    leverage = futures_position_info[0]['leverage']
    return f"El apalancamiento utilizado para {symbol} es {leverage}"

dispatcher.add_handler(CommandHandler('ver_apalancamiento', get_futures_leverage))



### Setear el apalancamiento ###
def set_leverage(update, context):
    # Obtener los argumentos del comando
    args = context.args 

    # Verificar si se proporcionaron suficientes argumentos
    if len(args) != 2:
        update.message.reply_text('Debes proporcionar el símbolo del par y el apalancamiento. Ejemplo: /leverage BTCUSDT 10')
        return

    # Obtener el símbolo del par y el apalancamiento del comando
    symbol = args[0].upper()
    leverage = int(args[1])

    # Configurar el apalancamiento del par en Binance
    try:
         # Configurar el apalancamiento del par
        client.futures_change_leverage(symbol=symbol, leverage=leverage)

        # Responder al usuario con un mensaje de confirmación
        update.message.reply_text(f'Se ha establecido el apalancamiento del par {symbol} en {leverage}x')
    except BinanceAPIException as e:
        # Si se produce un error, responder al usuario con un mensaje de error
        update.message.reply_text(f'Error al establecer el apalancamiento: {e}')

dispatcher.add_handler(CommandHandler('apalancar', set_leverage))

# Distribucion seteado estandard
global_distribution = {}
global_distribution['num_entries'] = 8
global_distribution['percentages'] = [3.0,3.0,6.0,8.0,10.0,15.0,20.0,30.0]

def set_distribution(update, context):
    # Acceder a la variable global
    global global_distribution
    
    # Obtener los argumentos del comando
    args = context.args

    # Verificar si se proporcionaron suficientes argumentos
    if len(args) < 2:
        update.message.reply_text('Debes proporcionar el número de entradas y los porcentajes separados por coma. Ejemplo: /distribucion 6 5,5,10,15,15,20,30')
        return

    # Obtener el número de entradas
    num_entries = int(args[0])

    # Obtener los porcentajes
    try:
        percentages = [float(p.strip()) for p in args[1].split(',')]
        if len(percentages) != num_entries:
            raise ValueError()
    except:
        update.message.reply_text('Porcentajes inválidos. Ejemplo: 5,5,10,15,15,20,30')
        return

    # Verificar que los porcentajes sumen 100
    if sum(percentages) != 100:
        update.message.reply_text('La suma de los porcentajes debe ser 100')
        return

    # Almacenar la distribución de porcentajes en la variable global
    global_distribution['num_entries'] = num_entries
    global_distribution['percentages'] = percentages  

    # Responder al usuario con un mensaje de confirmación
    update.message.reply_text(f'Se ha configurado la distribución de porcentajes: {num_entries} entradas con los siguientes porcentajes: {", ".join(map(str, percentages))}')

# Asignar el manejador al dispatcher
dispatcher.add_handler(CommandHandler('distribucion', set_distribution))




### abrir una posicion en long ###
def open_long_position(update, context):
    # Obtener los argumentos del comando
    args = context.args

    # Verificar si se proporcionaron suficientes argumentos
    if len(args) != 2:
        update.message.reply_text('Debes proporcionar el símbolo del par y el precio de apertura. Ejemplo: /long BTCUSDT 50000-56000')
        return
    
    # Obtener el saldo de tu cuenta en USDT
    usdt_balance = client.futures_account_balance()[8]['balance']
    print(usdt_balance)    
    investment_amount = float(usdt_balance) * 0.05
    print(f"saldo en USDT a abrir: {investment_amount}")

    # Obtener el símbolo del par, la cantidad de USDT a utilizar y el precio de apertura del comando
    symbol = args[0].upper()
    price_range = args[1].split('-')
    price_min = float(price_range[0])
    price_max = float(price_range[1])
    side='BUY'
    
    # Calcular el precio de apertura para cada posición
    num_entries = global_distribution['num_entries']
    price_step = (price_max - price_min) / (num_entries-1)
    prices = [round((price_min + i * price_step),0) for i in range(num_entries)]
    prices = sorted(prices, reverse=True)

    print (prices)
    # Abrir la posición limit en long en Binance
    try:
        # Obtener la información del exchange para el par
        exchange_info = client.futures_exchange_info()
        symbol_info = next(filter(lambda x: x['symbol'] == symbol, exchange_info['symbols']), None)
        if symbol_info is None:
            update.message.reply_text(f'El par {symbol} no se encuentra disponible en Binance')
            return

        # Obtener el tamaño del lote para el par
        filters = symbol_info['filters']
        lot_size_filter = next(filter(lambda x: x['filterType'] == 'LOT_SIZE', filters), None)
        if lot_size_filter is None:
            update.message.reply_text(f'No se pudo obtener el tamaño del lote para el par {symbol}')
            return
        lot_size = float(lot_size_filter['stepSize'])

        # obtener el apalancamiento 
        leverage_info = client.futures_position_information(symbol=symbol)
        leverage = int(leverage_info[0]['leverage'])
        print(f"apalancamiento: {leverage}")

        # Calculo de conratos por entrada
        contratos_por_posicion = []
        for i in range(len(prices)):
            contrato = round((investment_amount/prices[i] * (global_distribution['percentages'][i]/100)) * leverage, 3)
            print(f"contrato : {contrato}")
            contratos_por_posicion.append(contrato)

        print(f"contratos  x posicion : {contratos_por_posicion}")

        lista_precio_por_contrato = []
        for i in range(len(prices)):
            precio_por_contrato = prices[i] * contratos_por_posicion[i]
            lista_precio_por_contrato.append(precio_por_contrato)
        
        contratos_totales = round(sum(contratos_por_posicion),3)
        print(f" contratos totales: {contratos_totales}")
        suma_precios = sum(lista_precio_por_contrato)
        precio_ponderado = round(suma_precios/ contratos_totales,0)

        # Calcular el precio del SL -300%
        porcentaje = (400 / leverage)/100
        print(porcentaje)
        precio_stop = round(precio_ponderado - precio_ponderado*porcentaje,0)
        print(f" precio ponderado: {precio_ponderado}")
        print(f"precio de stop: {precio_stop}")

        # Obtener la lista de órdenes abiertas para el par de divisas
        open_orders = client.futures_get_open_orders(symbol=symbol)

        if any(order['positionSide'] == 'LONG' for order in open_orders):
              update.message.reply_text(f'Ya hay una posición abierta para {symbol} en {side} dirección')
        else:
        # Abrir la posición limit en long     
            for i in range(len(contratos_por_posicion)):   
                order = client.futures_create_order(symbol=symbol, positionSide='LONG', side='BUY', type='LIMIT', timeInForce='GTC', margin_type="CROSSED", hedgeMode=True, quantity=contratos_por_posicion[i], price=format(prices[i], 'f'))
               # Responder al usuario con un mensaje de confirmación
                update.message.reply_text(f'Se ha abierto la posición limit en long en el par {symbol} por {contratos_por_posicion[i]} contratos a un precio de {prices[i]} USDT')
        # Abrir SL en -300     
            order = client.futures_create_order(symbol=symbol, positionSide='LONG', side='SELL', type='STOP', timeInForce='GTC', quantity=contratos_totales, margin_type="CROSSED", hedgeMode=True, price=format( precio_stop, 'f'), stopPrice =format( precio_stop, 'f'))
            update.message.reply_text(f'Se ha abierto stop loss para {symbol} por {contratos_totales} contratos a un precio de { precio_stop} USDT')

    except BinanceAPIException as e:
        # Si se produce un error, responder al usuario con un mensaje de error
        update.message.reply_text(f'Error al abrir la posición limit en long: {e}')

long_handler = CommandHandler('long', open_long_position)



# Add the command handler to the dispatcher
dispatcher.add_handler(long_handler)

# Iniciar el bot
updater.start_polling()




