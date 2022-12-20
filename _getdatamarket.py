import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import  Point,Polygon
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sidefunctions import coddir, precio_compra


@st.cache(allow_output_mutation=True)
def getdatamarketcoddir(filename,fcoddir):
    data = pd.read_pickle(filename)
    data = data[data['coddir']==fcoddir]
    return data

@st.cache(allow_output_mutation=True)
def getdatamarketsimilar(filename,inputvar):
    data = pd.read_pickle(filename)
    idd  = True
    if 'areaconstruida' in inputvar and inputvar['areaconstruida']>0:
        areamin = inputvar['areaconstruida']*0.85
        areamax = inputvar['areaconstruida']*1.15
        idd     = (idd) & (data['areaconstruida']>=areamin)  & (data['areaconstruida']<=areamax)
    if 'habitaciones' in inputvar and inputvar['habitaciones']>0:
        idd     = (idd) & (data['habitaciones']==inputvar['habitaciones'])
    if 'banos' in inputvar and inputvar['banos']>0:
        idd     = (idd) & (data['banos']==inputvar['banos'])
    if 'garajes' in inputvar and inputvar['garajes']>0:
        idd     = (idd) & (data['garajes']==inputvar['garajes'])
    if 'estrato' in inputvar and inputvar['estrato']>0:
        idd     = (idd) & (data['estrato']==inputvar['estrato'])
    if 'tipoinmueble' in inputvar and inputvar['tipoinmueble']!='':
        idd     = (idd) & (data['tipoinmueble']==inputvar['tipoinmueble'])
    data = data[idd]
    return data

@st.cache(allow_output_mutation=True)
def getpolygon(metros,lat,lng):
    grados   = np.arange(-180, 190, 10)
    Clat     = ((metros/1000.0)/6371.0)*180/np.pi
    Clng     = Clat/np.cos(lat*np.pi/180.0)
    theta    = np.pi*grados/180.0
    longitud = lng + Clng*np.cos(theta)
    latitud  = lat + Clat*np.sin(theta)
    return Polygon([[x, y] for x,y in zip(longitud,latitud)])
        

def building_market_data(inputvar):
      
    preferencia    = None
    cifrasnegocio  = {'retorno_bruto_esperado': None,'retorno_neto_esperado': None,'gn_compra': None,'gn_venta': None,'comisiones': None,'otros_gastos': None}
    tiponegocio    = 'Venta'
    tipoinmueble   = 'Apartamento'
    areaconstruida = 0
    habitaciones   = 0
    banos          = 0
    garajes        = 0
    estrato        = 0
    fcoddir        = ''
    latitud        = 0
    longitud       = 0
    metros         = 300
    
    if 'tiponegocio' in inputvar:     tiponegocio    = inputvar['tiponegocio']
    if 'tipoinmueble' in inputvar:    tipoinmueble   = inputvar['tipoinmueble']
    if 'areaconstruida' in inputvar:  areaconstruida = inputvar['areaconstruida']
    if 'habitaciones' in inputvar:    habitaciones   = inputvar['habitaciones']
    if 'banos'    in inputvar:        banos          = inputvar['banos']
    if 'garajes'  in inputvar:        garajes        = inputvar['garajes']
    if 'coddir'  in inputvar:         fcoddir        = inputvar['coddir']
    if 'estrato'  in inputvar:        estrato        = inputvar['estrato']
    if 'latitud'  in inputvar:        latitud        = inputvar['latitud']
    if 'longitud' in inputvar:        longitud       = inputvar['longitud']
    if 'metros'   in inputvar:        metros         = inputvar['metros']

    areamin               = areaconstruida*0.95
    areamax               = areaconstruida*1.05
    todaynum              = datetime.now()
    fechainicial_conjunto = todaynum+relativedelta(months=-12)
    fechainicial_conjunto = fechainicial_conjunto.strftime("%Y-%m-%d")
    fechainicial_market   = todaynum+relativedelta(months=-6)
    fechainicial_market   = fechainicial_market.strftime("%Y-%m-%d")
    if fcoddir=='' and 'direccion' in inputvar and inputvar['direccion']!='':
        fcoddir = coddir(inputvar['direccion'])
    
    if 'venta' in tiponegocio.lower():
        #filename_oferta = r'D:\Dropbox\Empresa\Buydepa\COLOMBIA\DESARROLLO\DATA\data_market_venta_bogota'
        filename_oferta = 'data/data_market_venta_bogota'
        vardep          = 'valorventa'
    if 'arriendo' in tiponegocio.lower():
        #filename_oferta = r'D:\Dropbox\Empresa\Buydepa\COLOMBIA\DESARROLLO\DATA\data_market_arriendo_bogota'
        filename_oferta = 'data/data_market_arriendo_bogota'
        vardep          = 'valorarriendo'

    #-------------------------------------------------------------------------#
    # datos del mismo conjunto
    dataconjunto = getdatamarketcoddir(filename_oferta,fcoddir)
    
    if dataconjunto.empty is False:
        dataconjunto['minarea'] = abs(dataconjunto['areaconstruida']-areaconstruida)
        dataconjunto            = dataconjunto.sort_values(by=['minarea','valorventa','fecha_inicial'],ascending=[True,False,False])
        dataconjunto.drop(columns=['minarea'],inplace=True)
        
        datanalisis = dataconjunto[(dataconjunto['areaconstruida']>=areamin) & (dataconjunto['areaconstruida']<=areamax) & (dataconjunto['fecha_inicial']>=fechainicial_conjunto)]
        if len(datanalisis)>4:
            preferencia  = dataconjunto[vardep].median()*0.95
            if 'venta' in tiponegocio.lower():
                admon = None
                if 'adminsitracion' in inputvar: admon = inputvar['adminsitracion']
                presult     = precio_compra({'precio_venta':preferencia,'areaconstruida':areaconstruida,'admon':admon,'ganancia':0.08})
                preferencia = presult['preciocompra']
                cifrasnegocio.update(presult)
                if 'precioventa' in inputvar and inputvar['precioventa']>0:
                    preferencia = min(preferencia,inputvar['precioventa']*0.94)

    #-------------------------------------------------------------------------#
    # datos de inmuebles similares misma zona
    inputvar            = {'areaconstruida':areaconstruida,'habitaciones':habitaciones,'banos':banos,'estrato':estrato,'garajes':garajes,'tipoinmueble':tipoinmueble}
    datasimilares       = getdatamarketsimilar(filename_oferta,inputvar)
    dataexportsimilares = pd.DataFrame()
    if datasimilares.empty is False:
        poly                      = getpolygon(metros,latitud,longitud)
        datasimilares['geometry'] = datasimilares.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        datasimilares             = gpd.GeoDataFrame(datasimilares, geometry='geometry')
        idd                       = datasimilares['geometry'].apply(lambda x: poly.contains(x))
        if sum(idd)>0:
            dataexportsimilares   = datasimilares[idd]
    if dataexportsimilares.empty is False:
        idd = dataexportsimilares['coddir']==fcoddir
        dataexportsimilares = dataexportsimilares[~idd]
        dataexportsimilares = dataexportsimilares[(dataexportsimilares['areaconstruida']>=areamin) & (dataexportsimilares['areaconstruida']<=areamax) & (dataexportsimilares['fecha_inicial']>=fechainicial_market)]
        
    #-------------------------------------------------------------------------#
    # datos de inmuebles similares ibuyers
        
    
    return dataconjunto,dataexportsimilares,preferencia,cifrasnegocio