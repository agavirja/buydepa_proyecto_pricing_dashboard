import streamlit as st
import re
import folium
import string
import random
import pandas as pd
import mysql.connector as sql
from streamlit_folium import st_folium
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine

from sidefunctions import coddir, precio_compra
from _getcatastro import getcatastro
from _forecastmodel import getforecast
from _getdatamarket import building_market_data

# streamlit run D:\Dropbox\Empresa\Buydepa\COLOMBIA\DESARROLLO\buydepa_proyecto_pricing_dashboard\ejecutable.py
# https://streamlit.io/
# pipreqs --encoding utf-8 "D:\Dropbox\Empresa\Buydepa\COLOMBIA\DESARROLLO\buydepa_proyecto_pricing_dashboard"
st.set_page_config(layout="wide")

fontsize        = 13
fontfamily      = 'sans-serif'
backgroundcolor = '#FFFFFF'
        
# Credenciales
user     = st.secrets["user"]
password = st.secrets["password"]
host     = st.secrets["host"]
database = st.secrets["database"]

# Parametros iniciales:
latitud             = None
longitud            = None
ganancia            = 0.08
forecastpriceresult = None
preferencia         = None
gn_compra           = None
gn_venta            = None 
comisioncompra      = None
totalgasto          = 0
cifrasnegocio       = {}

dataconjunto        = pd.DataFrame()
dataexportsimilares = pd.DataFrame()

idcontinue = True

@st.cache(allow_output_mutation=True)
def randomone(x):
    return random.random()

@st.cache(allow_output_mutation=True)
def id_generator(size=6, chars=string.ascii_uppercase + string.digits, changeinput=0):
    return ''.join(random.choice(chars) for _ in range(size))

@st.cache
def convert_df(df):
   return df.to_csv(index=False,encoding='utf-8')


with st.sidebar:
    ciudad      = st.selectbox('Ciudad',options=['Bogota'])
    id_inmueble = st.number_input('ID inmueble aplicativo (opcional)',min_value=0)
    col1,col2   = st.columns(2)
    tipoinmueble = col1.selectbox('Tipo inmueble',options=['Apartamento'])
    tiponegocio  = col2.selectbox('Negocio',options=['Venta'])

    col1,col2,col3,col4  = st.columns(4)
    tipovia      = col1.selectbox('Dirección',options=['CL','KR','TR','DG'])
    complemento1 = col2.text_input('',value="")
    complemento2 = col3.text_input(' ',value="")
    complemento3 = col4.text_input('  ',value="")
    complemento1 = re.sub(r'\s+',' ',re.sub('[^0-9a-zA-Z]',' ',complemento1))
    complemento2 = re.sub(r'\s+',' ',complemento2)
    complemento3 = re.sub(r'\s+',' ',complemento3)
    direccion_formato = ''
    fcoddir           = ''
    if complemento1!='' and complemento2!='' and complemento3!='':
        direccion_formato = f'{tipovia} {complemento1} {complemento2} {complemento3}, {ciudad}'
        col1,col2 = st.columns(2)
        col1.text('Direccion: ')
        col2.write(direccion_formato)
        fcoddir = coddir(direccion_formato)
        
    # Inputs de catastro
    nombre_edificio = ''        
    estrato         = 3
    anos_antiguedad = 10
    
    datacatastro  = getcatastro(direccion_formato)
    if datacatastro.empty is False:
        latitud  = datacatastro['latitud'].iloc[0]
        longitud = datacatastro['longitud'].iloc[0]
        if 'nombre_conjunto' in datacatastro: 
            nombre_edificio = datacatastro['nombre_conjunto'].iloc[0]
        if 'estrato' in datacatastro:
            try: 
                estrato_catastro = datacatastro['estrato'].iloc[0]
                estrato          = int(estrato_catastro)
            except: pass
        if 'vetustez_median' in datacatastro:
            try:
                antiguedad_catastro = datacatastro['vetustez_median'].iloc[0]
                anos_antiguedad     = int(datetime.now().year-antiguedad_catastro)
            except: pass
        
    nombre_edificio    = st.text_input('Nombre del conjunto: ',value=nombre_edificio).upper()
    areaconstruida     = st.slider('Area construida',min_value=30,max_value=150,value=50)
    habitaciones       = st.selectbox('# Habitaciones',options=[1,2,3,4],index=2)
    banos              = st.selectbox('# Banos',options=[1,2,3,4,5],index=1)
    garajes            = st.selectbox('# Garajes',options=[0,1,2,3],index=1)
    estrato            = st.selectbox('Estrato',options=[1,2,3,4,5,6],index=(estrato-1))
    num_piso           = st.slider('Numero de piso',min_value=1,max_value=30,value=5)
    anos_antiguedad    = st.slider('Anos de antiguedad',min_value=0,max_value=50,value=anos_antiguedad)
    num_ascensores     = st.selectbox('Asensores en el ED, Torre o Unidad',options=[0,1,2,3,4],index=1)
    numerodeniveles    = st.selectbox('Numero de niveles',options=[1,2,3],index=0)
    precioventa        = st.number_input('Precio de oferta en venta',min_value=100000000,max_value=1000000000,value=300000000,step=10000000)
    adminsitracion     = st.number_input('Valor de la adminsitracion',min_value=80000,max_value=1500000,value=250000,step=10000)
    preciorenta        = st.text_input('Precio de oferta en renta',value='')
    valorremodelacion  = st.number_input('Valor estimado remodelacion',min_value=0,max_value=100000000,value=round(precioventa*0.03),step=1000000)
    comisioncompra     = st.slider('Comisión de compra',min_value=0.0,max_value=6.0,value=0.3)
    comisionventa      = st.slider('Comisión de venta',min_value=0.0,max_value=6.0,value=0.3)
    urlinmueble        = st.text_input('URL inmueble (opcional)',value='')

    formato    = {'Ciudad':ciudad,'Dirección':direccion_formato,'Nombre del conjunto':nombre_edificio,'Area construida':areaconstruida,	'# Habitaciones':habitaciones,'# Banos':banos,'# Garajes':garajes,'Estrato':estrato,	'Numero de piso':num_piso,'Anos de antiguedad':anos_antiguedad,'Asensores':num_ascensores,'Numero de niveles':numerodeniveles,'Valor de la adminsitracion':adminsitracion,'Precio de oferta en venta':precioventa}
    for keys,value in formato.items():
        if idcontinue:
            if value is None or value=='':
                idcontinue = False
                st.markdown(f"""<div style="color: red;">Falta incluir {keys}</div>""",unsafe_allow_html=True)  

with st.container():
    inputvar = {
                "id_inmueble": id_inmueble,  
                "ciudad":ciudad,
                "tipoinmueble":tipoinmueble,
                "tiponegocio":tiponegocio,
                "direccion":direccion_formato,
                'nombre_edificio':nombre_edificio,
                'areaconstruida':areaconstruida,
                'habitaciones':habitaciones,
                'banos':banos,
                'garajes':garajes,
                'estrato':estrato,
                'num_piso':num_piso,
                'anos_antiguedad':anos_antiguedad,
                'num_ascensores':num_ascensores,
                'numerodeniveles':numerodeniveles,
                'adminsitracion':adminsitracion,
                'precioventa':precioventa,
                'preciorenta':preciorenta,
                'comisioncompra':comisioncompra,
                'comisionventa':comisionventa,
                'valorremodelacion':valorremodelacion,
                'url':urlinmueble,
                'coddir':fcoddir,
                'latitud': latitud,
                'longitud': longitud,
                'metros':300        
        }

    col1, col2, col3, col4 = st.columns(4)
    fecha_consulta   = datetime.now().strftime("%Y-%m-%d")
    sku              = id_generator(changeinput=randomone(1))
    inputvar.update({'fecha_consulta':fecha_consulta,'sku':sku})
    col1.write(f'Fecha: {fecha_consulta}')
    col2.write(f'SKU: {sku}')
    if (isinstance(id_inmueble, int) or isinstance(id_inmueble, float)) and id_inmueble>0:
        col3.write(f'Id inmueble: {id_inmueble}')
    savedata1 = col4.button('Guardar')
    
    # Informacion catastral
    if datacatastro.empty is False:
        inputvar.update(datacatastro.to_dict(orient='records')[0])
        
    col1, col2 = st.columns(2)
    with col1:
        if (isinstance(latitud, int) or isinstance(latitud, float)) and (isinstance(longitud, int) or isinstance(longitud, float)): 
            map = folium.Map(location=[latitud, longitud],zoom_start=17,tiles="cartodbpositron")
            folium.Marker(location=[latitud, longitud]).add_to(map)
            st_map = st_folium(map, width=600, height=300)


    with col2:
        #---------------------------------------------------------------------#
        # Detalle de la zona
        #---------------------------------------------------------------------#
        localidad            = ''
        barrio               = '' 
        nombre_conjunto_disp = ''
        estrato_disp         = ''
        antiguedad           = ''
        direccion_disp       = ''
        unidades_edificio    = ''
        if 'locnombre' in inputvar: localidad = inputvar['locnombre']
        if 'barrio' in inputvar: barrio = inputvar['barrio']
        if 'nombre_conjunto' in inputvar: nombre_conjunto_disp = inputvar['nombre_conjunto'].upper()
        if nombre_conjunto_disp=='' and 'nombre_edificio' in inputvar: nombre_conjunto_disp = inputvar['nombre_edificio'].upper()
        if 'estrato' in inputvar and (isinstance(inputvar['estrato'], int) or isinstance(inputvar['estrato'], float)):
            estrato_disp = int(inputvar['estrato'])
        if 'vetustez_max' in inputvar: antiguedad = inputvar['vetustez_max']
        if antiguedad=='' and 'anos_antiguedad' in inputvar: 
            antiguedad = datetime.now().year-inputvar['anos_antiguedad']
        if direccion_formato!='': direccion_disp = direccion_formato.upper().split(',')[0]
        if 'vetustez_max' in inputvar: antiguedad = inputvar['vetustez_max']
        
        texto = f""" 
        <table style="background-color:{backgroundcolor};width:100%;border-radius:100px;">
          <tr style="background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Ciudad</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{ciudad}</td>
          </tr>
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Tipo de inmueble</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{tipoinmueble}</td>
          </tr>
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Tipo de negocio</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{tiponegocio}</td>
          </tr>
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Dirección</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{direccion_disp}</td>
          </tr>
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Nombre del edificio</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{nombre_conjunto_disp}</td>
          </tr>
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Estrato</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{estrato_disp}</td>
          </tr>
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Localidad</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{localidad}</td>
          </tr>
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Barrio</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{barrio}</td>
          </tr>
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Antiguedad</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{antiguedad}</td>
          </tr>
          <tr style="background-color:{backgroundcolor};">
          </tr>
        </table>
            """ 
        st.markdown(texto,unsafe_allow_html=True)  
        
        
    col1, col2 = st.columns(2)
    with col1:
        #---------------------------------------------------------------------#
        # Detalle del inmueble
        #---------------------------------------------------------------------#
        texto = "<i>Caracteristicas del inmueble</i>"
        st.markdown(texto,unsafe_allow_html=True) 
        
        maxpiso_disp = ''
        if 'maxpiso' in inputvar and (isinstance(inputvar['maxpiso'], int) or isinstance(inputvar['maxpiso'], float)):
            maxpiso      = int(inputvar['maxpiso'])
            maxpiso_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;"># Pisos Edificio</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{maxpiso}</td></tr>'
        
        texto = f""" 
        <table style="background-color:{backgroundcolor};width:100%;border-radius:100px;">
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Area construida</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{areaconstruida}</td>
          </tr>
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Habitaciones</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{habitaciones}</td>
          </tr>        
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Banos</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{banos}</td>
          </tr>            
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Garajes</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{garajes}</td>
          </tr>            
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Piso</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{num_piso}</td>
          </tr>   
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Ascensores</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{num_ascensores}</td>
          </tr>     
          <tr style="border-style: none;background-color:{backgroundcolor};">
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Niveles</td>
            <td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{numerodeniveles}</td>
          </tr> 
          {maxpiso_disp}
        </table>
         """
        st.markdown(texto,unsafe_allow_html=True) 
         
    with col2:
        #---------------------------------------------------------------------#
        # Precios
        #---------------------------------------------------------------------#

        texto = "<i>Analisis de precios</i>"
        st.markdown(texto,unsafe_allow_html=True) 
        backgroundcolor_seccionprecios = '#EEEEEE'
        
        precioventa = None
        admon       = None
        if 'precioventa' in inputvar and (isinstance(inputvar['precioventa'], int) or isinstance(inputvar['precioventa'], float)):
            precioventa = inputvar['precioventa']
        if 'adminsitracion' in inputvar and (isinstance(inputvar['adminsitracion'], int) or isinstance(inputvar['adminsitracion'], float)): 
            admon = inputvar['adminsitracion']

        #---------------------------------------------------------------------#
        # Forecast
        forecastpriceresult = getforecast(inputvar)

        #---------------------------------------------------------------------#
        # Precio de compra  
        dataconjunto,dataexportsimilares,preferencia,cifrasnegocio = building_market_data(inputvar)
        
        # Si no hay precio de referencia: 
            # 1. Comparativo entre precio forecast y precio de venta
        if preferencia is None and (isinstance(forecastpriceresult, int) or isinstance(forecastpriceresult, float)) and 'precioventa' in inputvar and precioventa is not None: 
            p1    = min(forecastpriceresult,inputvar['precioventa']*0.94)
            presult     = precio_compra({'precio_venta':p1,'areaconstruida':areaconstruida,'admon':admon,'ganancia':ganancia})
            preferencia = presult['preciocompra']
            cifrasnegocio.update(presult)
            
            # 2. Comparativo entre precio forecast y precio de venta
        if preferencia is None and dataconjunto.empty is False and len(dataconjunto)>5:
            p1    = dataconjunto['valormt2'].median()*areaconstruida*0.94
            presult     = precio_compra({'precio_venta':p1,'areaconstruida':areaconstruida,'admon':admon,'ganancia':ganancia})
            preferencia = presult['preciocompra']
            cifrasnegocio.update(presult)
            
        if (isinstance(preferencia, int) or isinstance(preferencia, float)) and preferencia>0 and precioventa is not None:
            preferencia = min(preferencia,inputvar['precioventa']*0.94)
            
        
        #---------------------------------------------------------------------#
        precioventa_disp     = '' # Precio que estan pidiendo por el inmueble
        forecastprice_disp   = '' # Forecast comercial del inmueble
        admon_disp           = '' # Valor de la adminsitracion
        preciorenta_disp     = '' # Precio al que se tiene rentando
        ofertas_building     = '' # Ofertas activas en el edificio
        unidades_disp        = '' # Unidades del edificio

        try:
            precioventa_disp = f'${precioventa:,.0f}' 
            precioventa_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Precio de oferta</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{precioventa_disp}</td></tr>'
            inputvar.update({'precioventa':precioventa})
        except: pass
        try:
            forecastprice_disp = f'${forecastpriceresult:,.0f}'
            forecastprice_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Forecast precio</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{forecastprice_disp}</td></tr>'
            inputvar.update({'forecastpriceresult':forecastpriceresult})
        except: pass
        try:
            admon_disp = f'${admon:,.0f}' 
            admon_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Administracion</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{admon_disp}</td></tr>'
            inputvar.update({'admon':admon})
        except: pass
        try: 
            preciorenta      = float(preciorenta)
            preciorenta_disp = f'${preciorenta:,.0f}'
            preciorenta_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Precio de renta</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{preciorenta_disp}</td></tr>'
            inputvar.update({'preciorenta':preciorenta})
        except: pass
        if dataconjunto.empty is False:
            try:
                areamin               = areaconstruida*0.95
                areamax               = areaconstruida*1.05
                todaynum              = datetime.now()
                fechainicial_conjunto = todaynum+relativedelta(months=-12)
                fechainicial_conjunto = fechainicial_conjunto.strftime("%Y-%m-%d")
                datanalisis           = dataconjunto[(dataconjunto['areaconstruida']>=areamin) & (dataconjunto['areaconstruida']<=areamax) & (dataconjunto['fecha_inicial']>=fechainicial_conjunto)]
                if datanalisis.empty is False:
                    ofertas_building = len(datanalisis)
                    ofertas_building = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Ofertas en el edificio</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{ofertas_building}</td></tr>'     
                    inputvar.update({'ofertas_building':len(datanalisis)})
            except: pass
        try: 
            if 'unidades' in inputvar: 
                unidades      = inputvar['unidades']
                unidades_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Total unidades en Conjunto</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{unidades}</td></tr>'
                inputvar.update({'unidades':unidades})
        except: pass

        texto = f'<table style="background-color:{backgroundcolor_seccionprecios};width:100%;border-radius:100px;">{precioventa_disp}{forecastprice_disp}{admon_disp}{preciorenta_disp}{ofertas_building}{unidades_disp}</table>'
        st.markdown(texto,unsafe_allow_html=True) 
        
    st.write('---')
    col1, col2 = st.columns(2)
    with col1:
        prefcompra  = f'${preferencia:,.0f}'
        preferencia = st.slider(f'Precio al que se compra (millones) Precio sugerido: {prefcompra}',min_value=100,max_value=1000,value=int(preferencia/1000000))
        preferencia = preferencia*1000000
        inputvar.update({'preferencia':preferencia})
        st.write(f'${preferencia:,.0f}' )
        
    with col2:
        precioalquesevende = st.slider('Precio al que se vendería (millones)',min_value=100,max_value=1000,value=int(precioventa/1000000))
        precioalquesevende = precioalquesevende*1000000
        st.write(f'${precioalquesevende:,.0f}' )
        inputvar.update({'precioalquesevende':precioalquesevende})
        
    st.write('---')
    col1, col2 = st.columns(2)
    with col1:
        if 'venta' in tiponegocio.lower():
            #-----------------------------------------------------------------#
            # Gastos del negocio
            #-----------------------------------------------------------------#
            texto = "<i>Gastos del negocio</i>"
            st.markdown(texto,unsafe_allow_html=True) 
            
            gn_compra_disp         = ''
            gn_venta_disp          = ''
            comision_compra_disp   = ''
            comision_venta_disp    = ''
            valorremodelacion_disp = ''
            otros_gastos_disp      = ''
            totalgasto             = 0
            
            if (isinstance(preferencia, int) or isinstance(preferencia, float)) and preferencia>0 and precioventa is not None:
                gn_compra      = 57000+0.0262*preferencia # (resultado de la regresion)
                totalgasto     = totalgasto+gn_compra
                gn_compra_disp = f'${gn_compra:,.0f}' 
                gn_compra_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Gastos notariales comprador + beneficiencia y registro </td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{gn_compra_disp}</td></tr>'
                
                comisioncompra  = preferencia*comisioncompra/100
                totalgasto      = totalgasto+comisioncompra
                comision_compra_disp = f'${comisioncompra:,.0f}' 
                comision_compra_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Comisión por la compra</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{comision_compra_disp}</td></tr>'
                inputvar.update({'gn_compra':gn_compra,'comisioncompra':comisioncompra})
                
            if (isinstance(precioalquesevende, int) or isinstance(precioalquesevende, float)) and precioalquesevende>0 and precioalquesevende is not None:
                gn_venta      = 164000+0.0033*precioalquesevende  # (resultado de la regresion)
                totalgasto    = totalgasto+gn_venta
                gn_venta_disp = f'${gn_venta:,.0f}' 
                gn_venta_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Gastos notariales vendedor</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{gn_venta_disp}</td></tr>'

                comisionventa       = precioalquesevende*comisionventa/100
                totalgasto          = totalgasto+comisionventa
                comision_venta_disp = f'${comisionventa:,.0f}' 
                comision_venta_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Comisión por la venta</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{comision_venta_disp}</td></tr>'
                inputvar.update({'gn_venta':gn_venta,'comisionventa':comisionventa})

            if 'otros_gastos' in cifrasnegocio and cifrasnegocio['otros_gastos'] is not None:
                
                provisionmt2 = 80000  # colchon financiero
                nmonths      = 6      # Numero de meses maximo para la venta
                admoncoef    = 5500   # Coeficiente de administracion por mt2 (en caso de no tener valor de admon)
                
                provision    = provisionmt2*areaconstruida
                if (isinstance(admon, int) or isinstance(admon, float)) and admon is not None and admon>0:
                    admon_gasto = admon*nmonths
                else:
                    admon_gasto = admoncoef*nmonths
                total_gasto_provision = provision+admon_gasto
                
                totalgasto        = totalgasto+total_gasto_provision
                otros_gastos_disp = f'${total_gasto_provision:,.0f}' 
                otros_gastos_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Gastos provisión</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{otros_gastos_disp}</td></tr>'
                inputvar.update({'total_gasto_provision':total_gasto_provision})

            totalgasto             = totalgasto+valorremodelacion
            totalgasto_disp        = f'${totalgasto:,.0f}'
            totalgasto_disp        = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Gasto total</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;"><b>{totalgasto_disp}</b></td></tr>'
            
            valorremodelacion_disp = f'${valorremodelacion:,.0f}' 
            valorremodelacion_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Valor remodelación</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{valorremodelacion_disp}</td></tr>'
            inputvar.update({'totalgasto':totalgasto,'valorremodelacion':valorremodelacion})

            texto = f'<table style="background-color:{backgroundcolor};width:100%;border-radius:100px;">{gn_compra_disp}{gn_venta_disp}{comision_compra_disp}{comision_venta_disp}{valorremodelacion_disp}{otros_gastos_disp}{totalgasto_disp}</table>'
            st.markdown(texto,unsafe_allow_html=True) 
            
    with col2:
        if 'venta' in tiponegocio.lower():
            #-----------------------------------------------------------------#
            # Retorno del negocio
            #-----------------------------------------------------------------#
            texto = "<i>Retornos del negocio</i>"
            st.markdown(texto,unsafe_allow_html=True) 
            
            preferencia_disp            = '' # Precio al que se deberia comprar
            precioparaventa_disp        = '' # Precio al que se cree que se puede vender
            retorno_bruto_esperado_disp = ''
            retorno_neto_esperado_disp  = ''
            ganancia_neta_disp          = ''
            diferencia_disp             = '' # diferencia porcentual

            try: 
                preferencia_disp = f'${preferencia:,.0f}'  
                preferencia_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Precio de compra</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;"><b>{preferencia_disp}</b></td></tr>'
            except: pass
            try:
                precioparaventa_disp = f'${precioalquesevende:,.0f}'
                precioparaventa_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Precio al que se puede vender</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{precioparaventa_disp}</td></tr>'
            except: pass
            try:
                retorno_bruto_esperado = precioalquesevende/preferencia-1
                retorno_bruto_esperado_disp = "{:.1%}".format(retorno_bruto_esperado)
                retorno_bruto_esperado_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Retorno bruto esperado</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{retorno_bruto_esperado_disp}</td></tr>'
                inputvar.update({'retorno_bruto_esperado':retorno_bruto_esperado})
            except: pass
            try:
                retorno_neto_esperado = (precioalquesevende-totalgasto)/preferencia-1
                retorno_neto_esperado_disp = "{:.1%}".format(retorno_neto_esperado)
                retorno_neto_esperado_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Retorno neto esperado</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{retorno_neto_esperado_disp}</td></tr>'
                inputvar.update({'retorno_neto_esperado':retorno_neto_esperado})
            except: pass
            try:
                ganancia_neta      = precioalquesevende-preferencia-totalgasto
                ganancia_neta_disp = f'${ganancia_neta:,.0f}' 
                ganancia_neta_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Ganancia neta</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{ganancia_neta_disp}</td></tr>'
                inputvar.update({'ganancia_neta':ganancia_neta})
            except: pass   
            try:
                diferencia_pricing = preferencia/precioventa-1
                diferencia_disp    = "{:.1%}".format(diferencia_pricing)
                diferencia_disp    = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Diferencia (precio de compra vs precio de venta</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;"><b>{diferencia_disp}</b></td></tr>'
                inputvar.update({'diferencia_pricing':diferencia_pricing})
            except: pass

            texto = f'<table style="background-color:{backgroundcolor_seccionprecios};width:100%;border-radius:100px;">{preferencia_disp}{precioparaventa_disp}{retorno_bruto_esperado_disp}{retorno_neto_esperado_disp}{ganancia_neta_disp}{diferencia_disp}</table>'
            st.markdown(texto,unsafe_allow_html=True) 
        

    #-----------------------------------------------------------------#
    # Ofertas del mismo edificio
    #-----------------------------------------------------------------#
    if dataconjunto.empty is False and len(dataconjunto)>0:
        st.write('---')
        texto = "<i>Inmuebles en oferta en el mismo edificio</i>"
        st.markdown(texto,unsafe_allow_html=True) 
        
        col1, col2 = st.columns([1,5])
        with col1: 
            dataconjunto['availablecomp'] = dataconjunto['available'].replace([0,1],['No','Si'])
            available_select              = st.multiselect(label='Disponible',options=list(dataconjunto['availablecomp'].unique()),default=list(dataconjunto['availablecomp'].unique()))
            areaconstruida_datafiltermin,areaconstruida_datafiltermax = st.slider('Filtro por area',min_value=int(dataconjunto['areaconstruida'].min()),max_value=int(dataconjunto['areaconstruida'].max())+1,value=[int(dataconjunto['areaconstruida'].min()),int(dataconjunto['areaconstruida'].max())+1],step=1)
            valorventa_datafiltermin,valorventa_datafiltermax         = st.slider('Filtro por valor',min_value=int(dataconjunto['valorventa'].min()/1000000),max_value=int(dataconjunto['valorventa'].max()/1000000)+1,value=[int(dataconjunto['valorventa'].min()/1000000),int(dataconjunto['valorventa'].max()/1000000)+1],step=1)
            valorventa_datafiltermin   = valorventa_datafiltermin*1000000
            valorventa_datafiltermax   = valorventa_datafiltermax*1000000
            dataconjunto['fuentecomp'] = dataconjunto['fuente'].replace(['H','GI'],['Habi','Galeria'])
            fuentes_select             = st.multiselect(label='Fuentes',options=list(dataconjunto['fuentecomp'].unique()),default=list(dataconjunto['fuentecomp'].unique()))
            
        with col2:
            variables        = [x for x in ['available','availablecomp','direccion','tiponegocio','tipoinmueble','fecha_inicial','areaconstruida','habitaciones','banos','garajes','valorventa','valormt2','fuente','fuentecomp','url','telefono1','telefono2','telefono3'] if x in dataconjunto]
            dataconjuntodisp = dataconjunto[variables]
            dataconjuntodisp = dataconjuntodisp[dataconjuntodisp['availablecomp'].isin(available_select)]
            dataconjuntodisp = dataconjuntodisp[(dataconjuntodisp['areaconstruida']>=areaconstruida_datafiltermin) & (dataconjuntodisp['areaconstruida']<=areaconstruida_datafiltermax)]
            dataconjuntodisp = dataconjuntodisp[(dataconjuntodisp['valorventa']>=valorventa_datafiltermin) & (dataconjuntodisp['valorventa']<=valorventa_datafiltermax)]
            dataconjuntodisp = dataconjuntodisp[dataconjuntodisp['fuentecomp'].isin(fuentes_select)]
            if 'availablecomp' in dataconjuntodisp: dataconjuntodisp.drop(columns=['availablecomp'],inplace=True)
            if 'fuentecomp'    in dataconjuntodisp: dataconjuntodisp.drop(columns=['fuentecomp'],inplace=True)
            dataconjuntodisp.index = range(len(dataconjuntodisp))
            if 'fecha_inicial' in dataconjuntodisp:
                try: dataconjuntodisp['fecha_inicial'] = dataconjuntodisp['fecha_inicial'].apply(lambda x: x.strftime("%Y-%m-%d"))
                except: pass
            dataconjuntodisp.rename(columns={'available':'disponible','direccion':'direccion','tiponegocio':'tipo de negocio','tipoinmueble':'tipo de inmueble','fecha_inicial':'fecha inicial','areaconstruida':'area construida','valorventa':'valor de venta','valormt2':'valor por mt2'},inplace=True)
            st.dataframe(data=dataconjuntodisp)
            csv   = convert_df(dataconjuntodisp)
            st.download_button(
               "descargar data conjuntos",
               csv,
               "data_conjuntos.csv",
               "text/csv",
               key='download-data-conjuntos'
            )
        
    #-----------------------------------------------------------------#
    # Ofertas en la misma zona
    #-----------------------------------------------------------------#
    if dataexportsimilares.empty is False and len(dataexportsimilares)>0:
        st.write('---')
        texto = "<i>Inmuebles en oferta en la misma zona</i>"
        st.markdown(texto,unsafe_allow_html=True) 
        
        col1, col2 = st.columns([1,5])
        with col1: 
            dataexportsimilares['availablecomp'] = dataexportsimilares['available'].replace([0,1],['No','Si'])
            available_select              = st.multiselect(label='Disponible ',options=list(dataexportsimilares['availablecomp'].unique()),default=list(dataexportsimilares['availablecomp'].unique()))
            areaconstruida_datafiltermin,areaconstruida_datafiltermax = st.slider('Filtro por area ',min_value=int(dataexportsimilares['areaconstruida'].min()),max_value=int(dataexportsimilares['areaconstruida'].max())+1,value=[int(dataexportsimilares['areaconstruida'].min()),int(dataexportsimilares['areaconstruida'].max())+1],step=1)
            valorventa_datafiltermin,valorventa_datafiltermax         = st.slider('Filtro por valor ',min_value=int(dataexportsimilares['valorventa'].min()/1000000),max_value=int(dataexportsimilares['valorventa'].max()/1000000)+1,value=[int(dataexportsimilares['valorventa'].min()/1000000),int(dataexportsimilares['valorventa'].max()/1000000)+1],step=1)
            valorventa_datafiltermin   = valorventa_datafiltermin*1000000
            valorventa_datafiltermax   = valorventa_datafiltermax*1000000
            dataexportsimilares['fuentecomp'] = dataexportsimilares['fuente'].replace(['H','GI'],['Habi','Galeria'])
            fuentes_select             = st.multiselect(label='Fuentes ',options=list(dataexportsimilares['fuentecomp'].unique()),default=list(dataexportsimilares['fuentecomp'].unique()))
            
        with col2:
            variables        = [x for x in ['available','availablecomp','direccion','tiponegocio','tipoinmueble','fecha_inicial','areaconstruida','habitaciones','banos','garajes','valorventa','valormt2','fuente','fuentecomp','url','telefono1','telefono2','telefono3'] if x in dataexportsimilares]
            dataexportsimilaresdisp = dataexportsimilares[variables]
            dataexportsimilaresdisp = dataexportsimilaresdisp[dataexportsimilaresdisp['availablecomp'].isin(available_select)]
            dataexportsimilaresdisp = dataexportsimilaresdisp[(dataexportsimilaresdisp['areaconstruida']>=areaconstruida_datafiltermin) & (dataexportsimilaresdisp['areaconstruida']<=areaconstruida_datafiltermax)]
            dataexportsimilaresdisp = dataexportsimilaresdisp[(dataexportsimilaresdisp['valorventa']>=valorventa_datafiltermin) & (dataexportsimilaresdisp['valorventa']<=valorventa_datafiltermax)]
            dataexportsimilaresdisp = dataexportsimilaresdisp[dataexportsimilaresdisp['fuentecomp'].isin(fuentes_select)]
            if 'availablecomp' in dataexportsimilaresdisp: dataexportsimilaresdisp.drop(columns=['availablecomp'],inplace=True)
            if 'fuentecomp'    in dataexportsimilaresdisp: dataexportsimilaresdisp.drop(columns=['fuentecomp'],inplace=True)
            dataexportsimilaresdisp.index = range(len(dataexportsimilaresdisp))
            if 'fecha_inicial' in dataexportsimilaresdisp:
                try: dataexportsimilaresdisp['fecha_inicial'] = dataexportsimilaresdisp['fecha_inicial'].apply(lambda x: x.strftime("%Y-%m-%d"))
                except: pass
            dataexportsimilaresdisp.rename(columns={'available':'disponible','direccion':'direccion','tiponegocio':'tipo de negocio','tipoinmueble':'tipo de inmueble','fecha_inicial':'fecha inicial','areaconstruida':'area construida','valorventa':'valor de venta','valormt2':'valor por mt2'},inplace=True)
            st.dataframe(data=dataexportsimilaresdisp)
            csv   = convert_df(dataexportsimilaresdisp)
            st.download_button(
               "descargar data zona",
               csv,
               "data_zona.csv",
               "text/csv",
               key='download-data-zona'
            )
        
    #-------------------------------------------------------------------------#
    # Recorrido
    #-------------------------------------------------------------------------#
    if fcoddir!='' and fcoddir is not None and len(fcoddir)>=3:
        db_connection     = sql.connect(user=user, password=password, host=host, database=database)
        datastockventanas = pd.read_sql(f"""SELECT * FROM colombia.app_recorredor_stock_ventanas WHERE coddir='{fcoddir}'""" , con=db_connection)
        db_connection.close()
        if datastockventanas.empty is False:
            
            st.write('---')
            texto = "<i>Informacion de recorrido</i>"
            st.markdown(texto,unsafe_allow_html=True) 
            
            col1, col2, col3 = st.columns([1,1,4])
            with col1:
                try:
                    fotofachada = datastockventanas[datastockventanas['url_foto_fachada'].notnull()]['url_foto_fachada'].iloc[-1]
                    st.image(fotofachada,use_column_width='auto')
                except: pass
            with col2:
                try:
                    fotodireccion = datastockventanas[datastockventanas['url_foto_direccion'].notnull()]['url_foto_direccion'].iloc[-1]
                    st.image(fotodireccion,use_column_width='auto')
                except: pass            
                
            with col3:             
                variables             = [x for x in ['fecha_recorrido','nombre_conjunto','direccion_formato','tipo_negocio','telefono1','telefono2','telefono3'] if x in datastockventanas]
                datastockventanasdisp = datastockventanas[variables]
                if 'fecha_recorrido' in datastockventanasdisp:
                    try: datastockventanasdisp['fecha_recorrido'] = datastockventanasdisp['fecha_recorrido'].apply(lambda x: x.strftime("%Y-%m-%d"))
                    except: pass
                datastockventanasdisp.rename(columns={'fecha_recorrido':'Fecha recorrido','nombre_conjunto':'Nombre conjunto','direccion_formato':'Direccion','tipo_negocio':'Tipo de negocio'},inplace=True)
                datastockventanasdisp.index = range(len(datastockventanasdisp))
                st.dataframe(data=datastockventanasdisp)
                csv   = convert_df(datastockventanasdisp)
                st.download_button(
                   "descargar data recorrido",
                   csv,
                   "data_recorrido.csv",
                   "text/csv",
                   key='download-data-recorrido'
                )

    #-------------------------------------------------------------------------#
    # Fotos del inmueble
    #-------------------------------------------------------------------------#
    if (isinstance(id_inmueble, int) or isinstance(id_inmueble, float)) and id_inmueble is not None and id_inmueble>0:
        db_connection     = sql.connect(user=user, password=password, host=host, database=database)
        datafotosinmueble = pd.read_sql(f"""SELECT ambiente,url_foto FROM colombia.app_seguimiento_fotos_visitas WHERE id_inmueble={id_inmueble}""" , con=db_connection)
        db_connection.close()
        if datafotosinmueble.empty is False and sum(datafotosinmueble['url_foto'].notnull())>0:
            datafotosinmueble = datafotosinmueble[datafotosinmueble['url_foto'].notnull()]
            datafotosinmueble['ambientesort'] = datafotosinmueble['ambiente'].replace(['HABITACIÓN','COCINA','HABITACIÓN PRINCIPAL','COMEDOR','SALA','ENTORNO','BAÑO','BAÑO PRINCIPAL','FACHADA','PARQUEADERO','ZONA DE LAVANDERÍA','ZONAS COMUNES','PORTERÍA','ZONA DE NIÑOS','ASCENSOR','BALCÓN','BODEGA','SALÓN COMUNAL','ESTUDIO','ZONA DE BBQ','PISCINA','ZONAS VERDES','HALL DE ALCOBAS','MULTICANCHA','TERRAZA','CHIMENEA','CUARTO DE SERVICIO','ESCALERA'],[4,	5,	3,	8,	9,	1,	7,	6,	2,	10,	12,	22,	21,	23,	18,	13,	19,	20,	11,	24,	25,	26,	17,	27,	14,	16,	15,	28])
            datafotosinmueble = datafotosinmueble.sort_values(by='ambientesort',ascending=True)
            datafotosinmueble.drop(columns=['ambientesort'],inplace=True)
                                            
            st.write('---')
            texto = "<i>Fotos del inmueble</i>"
            st.markdown(texto,unsafe_allow_html=True) 
            
            ncols    =  st.columns(min(4,len(datafotosinmueble)))
            conteo   = 0
            maxcount = 3
            for fotoiter in datafotosinmueble['url_foto']:
                try: 
                    ncols[conteo].image(fotoiter,use_column_width='auto')
                    conteo += 1
                except: pass
                if conteo>maxcount:
                    conteo = 0
                    
    #-------------------------------------------------------------------------#
    # Guardar informacion
    #-------------------------------------------------------------------------#
    savedata2 = st.button('Guardar ')

    if savedata1 or savedata2:
        
        condicion = ''
        if 'id_inmueble' in inputvar and inputvar['id_inmueble']>0:
            id_inmueble_mysql = inputvar['id_inmueble']
            condicion         = condicion + f' OR `id_inmueble` = {id_inmueble_mysql}'
        if 'sku' in inputvar:
            sku_mysql = inputvar['sku']
            condicion = condicion + f' OR `sku` = "{sku_mysql}"'
        
        if condicion!='':
            condicion = condicion[4:].strip()
            
        #---------------------------------------------------------------------#
        # save data registros
        if 'nombre_conjunto' not in inputvar or ('nombre_conjunto' in inputvar and (inputvar['nombre_conjunto']=='' or inputvar['nombre_conjunto'] is None)):
            if 'nombre_edificio' in inputvar and inputvar['nombre_edificio']!='' and inputvar['nombre_edificio'] is not None:
                inputvar['nombre_conjunto'] = inputvar['nombre_edificio']
        if 'adminsitracion' not in inputvar or ('adminsitracion' in inputvar and (inputvar['adminsitracion'] is None or inputvar['adminsitracion']<=0)):
            if 'admon' in inputvar and (isinstance(inputvar['admon'], int) or isinstance(inputvar['admon'], float)): 
                if inputvar['admon']>0:
                    inputvar['adminsitracion'] = inputvar['admon']
                    
        dataexport = pd.DataFrame([inputvar])
        if 'preferencia' in dataexport: dataexport.rename(columns={'preferencia':'preciocompra'},inplace=True)
        variables  = [x for x in ['id_inmueble','sku','fecha_consulta','tipoinmueble','tiponegocio','ciudad','direccion','coddir','barmanpre','scacodigo','locnombre','barrio','upznombre','nombre_conjunto','anos_antiguedad','areaconstruida','habitaciones','banos','garajes','estrato','num_ascensores','num_piso','numerodeniveles','latitud','longitud','url','vetustez_max','vetustez_median','vetustez_min','unidades','maxpiso','precioventa','preciocompra','precioalquesevende','forecastpriceresult','diferencia_pricing','adminsitracion','preciorenta','gn_compra','gn_venta','valorremodelacion','comisioncompra','comisionventa','total_gasto_provision','totalgasto','ganancia_neta','retorno_bruto_esperado','retorno_neto_esperado','ofertas_building'] if x in dataexport]
        dataexport = dataexport[variables]
        
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{database}')
        dataexport.to_sql('data_app_pricing_registros_historico',engine,if_exists='append', index=False)  
        
        if condicion!='':
            db_connection = sql.connect(user=user, password=password, host=host, database=database)
            cursor        = db_connection.cursor()
            cursor.execute(f"""DELETE FROM `colombia`.`data_app_pricing_registros` WHERE ({condicion}); """)
            db_connection.commit()
            db_connection.close()
            
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{database}')
        dataexport.to_sql('data_app_pricing_registros',engine,if_exists='append', index=False)  
      
        #---------------------------------------------------------------------#
        # save data comparables
    
        data = pd.DataFrame()
        if dataconjunto.empty is False:
            dataconjunto['tipodata']       = 'conjunto'
            dataconjunto['sku']            = sku
            dataconjunto['fecha_consulta'] = fecha_consulta
            if 'id_inmueble' in inputvar and inputvar['id_inmueble']>0:
                dataconjunto['id_inmueble'] = inputvar['id_inmueble']
            data = data.append(dataconjunto)
            
        if dataexportsimilares.empty is False:
            dataexportsimilares['tipodata']       = 'zona'
            dataexportsimilares['sku']            = sku
            dataexportsimilares['fecha_consulta'] = fecha_consulta
            if 'id_inmueble' in inputvar and inputvar['id_inmueble']>0:
                dataexportsimilares['id_inmueble'] = inputvar['id_inmueble']
            data = data.append(dataexportsimilares)            
            
        variables = [x for x in ['id_inmueble','sku','fecha_consulta','tipodata','available','scacodigo','tiponegocio','tipoinmueble','direccion','coddir','fecha_inicial', 'areaconstruida', 'habitaciones', 'banos', 'garajes', 'estrato', 'tiempodeconstruido', 'valorarriendo', 'valorventa', 'valormt2', 'latitud', 'longitud', 'fuente', 'url', 'telefono1', 'telefono2', 'telefono3'] if x in data]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{database}')
        data[variables].to_sql('data_app_pricing_comparables_historico',engine,if_exists='append', index=False,chunksize=100)
       
        if condicion!='':
            db_connection = sql.connect(user=user, password=password, host=host, database=database)
            cursor        = db_connection.cursor()
            cursor.execute(f"""DELETE FROM `colombia`.`data_app_pricing_comparables` WHERE ({condicion}); """)
            db_connection.commit()
            db_connection.close()
     
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{database}')
        data[variables].to_sql('data_app_pricing_comparables',engine,if_exists='append', index=False,chunksize=100)
        st.write(f'Se guardo la data con exito. SKU: {sku}')