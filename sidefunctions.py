import streamlit as st
import re
import json
import requests
import pandas as pd
import numpy as np
import unicodedata
import math as mt
import mysql.connector as sql

#-----------------------------------------------------------------------------#
# dir2coddir
#-----------------------------------------------------------------------------#
def coddir(x):
    result = x
    try: result = prefijo(x) + getnewdir(x)
    except:pass
    return result

def getdirformat(x):
    # x    = 'carrera 19a # 103A - 62'
    result = ''
    x      = x.lower()
    x      = re.sub(r'[^0-9a-zA-Z]',' ', x).split(' ')
    for u in range(len(x)):
        i=x[u]
        try: i = i.replace(' ','').strip().lower()
        except: pass
        try:
            float(re.sub(r'[^0-9]',' ', i))
            result = result +'+'+i
        except:
            if i!='': result = result + i
        try:
            if len(re.sub(r'[^+]','',result))>=3:
                try:
                    if 'sur'  in x[u+1]:  result= result + 'sur'
                    if 'este' in x[u+1]:  result= result + 'este'
                except: pass
                break
        except: pass
    return result

def getnewdir(x):
    result = None
    try:
        x      = getdirformat(x).split('+')[1:]
        result = ''
        for i in x:
            result = result + '+' + re.sub(r'[^0-9]','', i)+''.join([''.join(sorted(re.sub(r'[^a-zA-Z]','', i)))])
    except: pass
    if result=='': result = None
    return result

def prefijo(x):
    result = None
    m      = re.search("\d", x).start()
    x      = x[:m].strip()
    prefijos = {'D':{'d','diagonal','dg', 'diag', 'dg.', 'diag.', 'dig'},
                'T':{'t','transv', 'tranv', 'tv', 'tr', 'tv.', 'tr.', 'tranv.', 'transv.', 'transversal', 'tranversal'},
                'C':{'c','avenida calle','avenida cll','avenida cl','calle', 'cl', 'cll', 'cl.', 'cll.', 'ac', 'a calle', 'av calle', 'av cll', 'a cll'},
                'AK':{'avenida carrera','avenida cr','avenida kr','ak', 'av cr', 'av carrera', 'av cra'},
                'K':{'k','carrera', 'cr', 'cra', 'cr.', 'cra.', 'kr', 'kr.', 'kra.', 'kra'},
                'A':{'av','avenida'}}
    for key, values in prefijos.items():
        if x.lower() in values:
            result = key
            break
    return result

#-----------------------------------------------------------------------------#
# Georreferenciacion
#-----------------------------------------------------------------------------#
def georreferenciacion(direccion):
    direccion     = formato_direccion(direccion)
    direccion     = f'{direccion},bogota,colombia'
    googlemapskey = 'AIzaSyAgT26vVoJnpjwmkoNaDl1Aj3NezOlSpKs'
    punto         = requests.get(f'https://maps.googleapis.com/maps/api/geocode/json?address={direccion}&key={googlemapskey}')
    response      = json.loads(punto.text)['results']
    result        = {'latitud':response[0]["geometry"]["location"]['lat'],'longitud':response[0]["geometry"]["location"]['lng'],'direccion':response[0]["formatted_address"]}
    return result

#-----------------------------------------------------------------------------#
# formato_direccion
#-----------------------------------------------------------------------------#
def formato_direccion(x):
    resultado = x
    try:
        address = ''
        x       = x.upper()
        x       = re.sub('[^A-Za-z0-9]',' ', x).strip() 
        x       = re.sub(re.compile(r'\s+'),' ', x).strip()
        numbers = re.sub(re.compile(r'\s+'),' ', re.sub('[^0-9]',' ', x)).strip().split(' ')
        vector  = ['ESTE','OESTE','SUR']
        for i in range(0,min(3,len(numbers))):
            try:
                initial = x.find(numbers[i],0)
                z       = x.find(numbers[i+1],initial+len(numbers[i]))
                result  = x[0:z].strip()
            except:
                result = x
            if i==2:
                if any([w in result.upper() for w in vector]):
                    result = numbers[i]+' '+[w for w in vector if w in result.upper()][0]
                else:
                    result = numbers[i]            
            address = address+' '+result
            z = x.find(result)
            x = x[(z+len(result)):].strip()
        resultado = address.strip()
        try: 
            #resultado = re.sub("[A-Za-z]+", lambda ele: " " + ele[0] + " ", resultado)
            resultado = re.sub(re.compile(r'\s+'),' ', resultado).strip()
            resultado = indicador_via(resultado)
        except: pass
    except: pass
    try: resultado = re.sub(re.compile(r'\s+'),'+', resultado).strip()
    except: pass
    return resultado

def indicador_via(x):
    m       = re.search("\d", x).start()
    tipovia = x[:m].strip()
    prefijos = {'D':{'d','diagonal','dg', 'diag', 'dg.', 'diag.', 'dig'},
                'T':{'t','transv', 'tranv', 'tv', 'tr', 'tv.', 'tr.', 'tranv.', 'transv.', 'transversal', 'tranversal'},
                'C':{'c','avenida calle','avenida cll','avenida cl','calle', 'cl', 'cll', 'cl.', 'cll.', 'ac', 'a calle', 'av calle', 'av cll', 'a cll'},
                'AK':{'avenida carrera','avenida cr','avenida kr','ak', 'av cr', 'av carrera', 'av cra'},
                'K':{'k','carrera', 'cr', 'cra', 'cr.', 'cra.', 'kr', 'kr.', 'kra.', 'kra'},
                'A':{'av','avenida'}}
    for key, values in prefijos.items():
        if tipovia.lower() in values:
            x = x.replace(tipovia,key)
            break
    return x

#-----------------------------------------------------------------------------#
# Rango de tiempo de construido
#-----------------------------------------------------------------------------#
def antiguedad2model(x):
    if x<=1:   result = 'menora1ano'
    elif x<=8: result = '1a8anos'
    elif x<=15:result = '9a15anos'
    elif x<=30:result = '16a30anos'
    else: result = 'masde30anos'
    return result

#-----------------------------------------------------------------------------#
# precio_compra
#-----------------------------------------------------------------------------#
def precio_compra(inputvar):
    #inputvar = {'precio_venta':400000000,'areaconstruida':85,'admon':320000,'ganancia':0.06,'comision_compra':0.003,'comision_venta':0.003,'nmonths':6,'provisionmt2':100000,'pinturamt2':13000}
    
    ganancia        = 0.06 # (6%)
    comision_compra = 0.003 # (0.3%)
    comision_venta  = 0.003 # (0.3%)
    nmonths         = 6
    provisionmt2    = 100000  # Para reparaciones / colchon financiero
    pinturamt2      = 13000
    IVA             = 0.19
    p1              = None
    admon           = None
    areaconstruida  = None
    
    if 'precio_venta' in inputvar:
        p1 = inputvar['precio_venta']
    if 'ganancia' in inputvar and inputvar['ganancia']>0 and inputvar['ganancia']<100: 
        ganancia = inputvar['ganancia']
    if 'areaconstruida' in inputvar:
        areaconstruida = inputvar['areaconstruida']
    if 'nmonths' in inputvar: 
        nmonths = inputvar['nmonths']
    if 'admon' in inputvar and inputvar['admon']>0: 
        admon = inputvar['admon']*1.1 # Es usual que reporten un menor valor de la administracion
    else: 
        admon = 5500*areaconstruida
    if 'pinturamt2' in inputvar: 
        pinturamt2 = inputvar['pinturamt2']
    if 'provisionmt2' in inputvar: 
        provisionmt2 = inputvar['provisionmt2']
    
    PRECIO_GANANCIA  = p1/(1+ganancia)
    GN_VENTA         = 164000+0.0033*p1  # (regresion)
    COMISION_VENTA   = comision_venta*p1
    PINTURA          = pinturamt2*(1+IVA)*areaconstruida
    ADMON            = admon*nmonths
    PROVISION        = provisionmt2*areaconstruida
    X                = PRECIO_GANANCIA-GN_VENTA-COMISION_VENTA-PINTURA-ADMON-PROVISION
    preciocompra     = (X-57000)/(1+(0.0262+comision_compra))
    preciocompra     = np.round(preciocompra, int(-(mt.floor(mt.log10(preciocompra))-2)))
    gn_compra        = 57000+0.0262*preciocompra
    gn_compra        = np.round(gn_compra, int(-(mt.floor(mt.log10(gn_compra))-2)))
    gn_venta         = np.round(GN_VENTA, int(-(mt.floor(mt.log10(GN_VENTA))-2)))
    COMISION_COMPRA  = (preciocompra*comision_compra)
    retorno_bruto_esperado = p1/preciocompra-1
    retorno_neto_esperado  = (p1-COMISION_COMPRA-COMISION_VENTA-PINTURA-ADMON-PROVISION)/preciocompra-1
    return {'precio_venta':p1,'preciocompra':preciocompra,'retorno_bruto_esperado':retorno_bruto_esperado,'retorno_neto_esperado':retorno_neto_esperado,'gn_compra':gn_compra,'gn_venta':gn_venta,'comisiones':COMISION_VENTA+COMISION_COMPRA,'otros_gastos':PINTURA+ADMON+PROVISION}

#-----------------------------------------------------------------------------#
# Forecat ANN
#-----------------------------------------------------------------------------#
@st.cache
def datamodelo(filename):
    salida = pd.read_pickle(filename)
    return salida
    
def pricingforecast(inputvar):
    
    tiponegocio  = inputvar['tiponegocio']
    if 'venta' in tiponegocio.lower() or 'sell' in tiponegocio.lower():
        filename = r'D:\Dropbox\Empresa\Buydepa\COLOMBIA\DESARROLLO\proyecto_market_analisis\data\resultado modelo\salida_venta_bogota'
    if 'venta' in tiponegocio.lower() or 'rent' in tiponegocio.lower():
        filename = r'D:\Dropbox\Empresa\Buydepa\COLOMBIA\DESARROLLO\proyecto_market_analisis\data\resultado modelo\salida_arriendo_bogota'
    
    delta         = 0
    salida        = datamodelo(filename)
    salida        = json.loads(salida['salida'].iloc[0])
    options       = salida['options']
    varlist       = salida['varlist']
    coef          = salida['coef']
    minmax        = salida['minmax']
    variables     = pd.DataFrame(0, index=np.arange(1), columns=varlist)
    
    for i in inputvar:
        value = inputvar[i]
        idd   = [z==elimina_tildes(i) for z in varlist]
        if sum(idd)==0:
            try:
                idd = [re.findall(elimina_tildes(i)+'#'+str(int(value)), z)!=[] for z in varlist]
            except:
                try:
                    idd = [re.findall(elimina_tildes(i)+'#'+elimina_tildes(value), z)!=[] for z in varlist]
                except:
                    pass
            value = 1                   
        if sum(idd)>0:
            row                = [j for j, x in enumerate(idd) if x]
            varname            = varlist[row[0]]
            variables[varname] = value
            
    # Transform MinMax
    a = variables.iloc[0]
    a = a[a!=0]
    for i in a.index:
        mini         = minmax[i]['min']
        maxi         = minmax[i]['max']
        variables[i] = (variables[i]-mini)/(maxi-mini)
        
    x     = variables.values
    value = ForecastFun(coef,x.T,options)
    if options['ytrans']=='log':
        value = np.exp(value)
        
    value         = value*(1-delta)
    valorestimado = np.round(value, int(-(mt.floor(mt.log10(value)) - 2))) 
    valuem2       = value/inputvar['areaconstruida']
    valortotal = np.round(value, int(-(mt.floor(mt.log10(value)) - 2))) 
    valuem2    = valortotal/inputvar['areaconstruida']
    return {'valorestimado': valorestimado[0][0], 'valorestimado_mt2':valuem2[0][0]}

def ForecastFun(coef,x,options):

    hiddenlayers = options['hiddenlayers']
    lambdavalue  = options['lambdavalue']
    biasunit     = options['biasunit']
    tipofun      = options['tipofun']
    numvar       = x.shape[0]
    nodos        = [numvar]
    for i in hiddenlayers:
        nodos.append(i)
    nodos.append(1)
        
    k          = len(nodos)
    suma       = 0
    theta      = [[] for i in range(k-1)]
    lambdac    = [[] for i in range(k-1)]
    lambdavect = np.nan
    for i in range(k-1):
        theta[i]   = np.reshape(coef[0:(nodos[i]+suma)*nodos[i+1]], (nodos[i]+suma, nodos[i+1]), order='F').T
        lambdac[i] =lambdavalue*np.ones(theta[i].shape)
        coef       = coef[(nodos[i]+suma)*nodos[i+1]:]
        if biasunit=='on':
            suma = 1
            lambdac[i][:,0] = 0
        [fil,col]  = lambdac[i].shape
        lambdavect = np.c_[lambdavect,np.reshape(lambdac[i],(fil*col,1)).T ]
        
    lambdac = lambdavect[:,1:].T
        
    # Forward Propagation
    a    = [[] for i in range(k)]
    z    = [[] for i in range(k)]
    g    = [[] for i in range(k)]
    a[0] = x
    numN = x.shape[1]
    for i in range(k-1):
        z[i+1]      = np.dot(theta[i],a[i])
        [ai,g[i+1]] = ANNFun(z[i+1],tipofun)
        if ((i+1)!=(k-1)) & (biasunit=='on'):
            a[i+1] = np.vstack((np.ones((1,numN)),ai))
        else:
            a[i+1] = ai
    return a[-1]

def ANNFun(z, tipofun):
    z = np.asarray(z)
    if tipofun=='lineal':
        f = z
        g = 1
    if tipofun=='logistica':
        f = 1/(1+mt.exp(-z))
        g = f*(1-f)
    if tipofun=='exp':
        f = np.exp(z)
        g = np.exp(z)
    if tipofun=='cuadratica':
        f = z + 0.5*(z*z)
        g = 1 + z
    if tipofun=='cubica':
        f = z + 0.5*(z*z)+(1/3.0)*(z*z*z)
        g = 1 + z + z*z
    return [f,g]

#-----------------------------------------------------------------------------#
# elimina_tildes
#-----------------------------------------------------------------------------#
def elimina_tildes(s):
    s = s.replace(' ','').lower().strip()
    return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))