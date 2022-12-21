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

# streamlit run D:\Dropbox\Empresa\Buydepa\COLOMBIA\DESARROLLO\buydepa_proyecto_pricing_dashboard\getinfoinmueble.py
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
dataconjunto        = pd.DataFrame()
dataexportsimilares = pd.DataFrame()
#st.session_state.skuchange = False
    
#def sku_onchange():
#    st.session_state.skuchange = True

@st.cache
def convert_df(df):
   return df.to_csv(index=False,encoding='utf-8')

with st.sidebar:
    
    id_inmueble   = st.text_input('id inmueble',value="")
    sku           = st.text_input('SKU',value="")
    
    st.write('---')
    st.markdown('Filtros para sugerencia de id inmueble o sku',unsafe_allow_html=True)  

    col1, col2    = st.columns(2)
    todaynum      = datetime.now()
    fechainicial  = todaynum+relativedelta(months=-6)
    fecha_inicial = st.date_input("Fecha inicial",fechainicial)
    fecha_final   = st.date_input("Fecha inicial",todaynum)
    
    db_connection = sql.connect(user=user, password=password, host=host, database=database)
    uniquelist    = pd.read_sql(f"""SELECT DISTINCT ciudad, direccion, nombre_conjunto FROM colombia.data_app_pricing_registros WHERE fecha_consulta>="{fecha_inicial}" AND fecha_consulta<="{fecha_final}" ORDER BY fecha_consulta DESC""" , con=db_connection)
    db_connection.close()
    
    if uniquelist.empty is False:
    
        ciudad          = st.selectbox('Ciudad',options=sorted(uniquelist['ciudad'].unique()))
        nombre_conjunto = st.selectbox('Nombde del conjunto',options=sorted(uniquelist['nombre_conjunto'].unique()))
        direccion       = st.selectbox('Dirección',options=sorted(uniquelist['direccion'].unique()))
        
        db_connection = sql.connect(user=user, password=password, host=host, database=database)
        listaids      = pd.read_sql(f"""SELECT DISTINCT id_inmueble, sku FROM colombia.data_app_pricing_registros WHERE fecha_consulta>="{fecha_inicial}" AND fecha_consulta<="{fecha_final}" AND ciudad="{ciudad}" AND (nombre_conjunto="{nombre_conjunto}" OR direccion="{direccion}") ORDER BY fecha_consulta DESC""" , con=db_connection)
        db_connection.close()
        
        st.selectbox('Sugerencias de id inmueble',options=sorted(listaids['id_inmueble'].unique()))
        st.selectbox('Sugerencias de SKU',options=sorted(listaids['sku'].unique()))

with st.container():
    
    if id_inmueble!="" or sku!="":

        if sku!="": 
            condicion = f' sku="{sku}" '
        if id_inmueble!="": 
            try: id_inmueble = int(id_inmueble)
            except: pass
            condicion = f' id_inmueble="{id_inmueble}" '
        
        db_connection   = sql.connect(user=user, password=password, host=host, database=database)
        dataregistros   = pd.read_sql(f"""SELECT * FROM colombia.data_app_pricing_registros WHERE {condicion}""" , con=db_connection)
        datacomparables = pd.read_sql(f"""SELECT * FROM colombia.data_app_pricing_comparables WHERE {condicion}""" , con=db_connection)
        db_connection.close()
        
        if datacomparables.empty is False:
            dataconjunto        = datacomparables[datacomparables['tipodata']=='conjunto']
            dataexportsimilares = datacomparables[datacomparables['tipodata']=='zona']
    
        inputvar = {}
        if dataregistros.empty is False:
            inputvar = dataregistros.to_dict(orient='records')[0]
            col1, col2, col3 = st.columns(3)
            fecha_consulta = inputvar['fecha_consulta']
            sku            = inputvar['sku']
            id_inmueble    = inputvar['id_inmueble']
            col1.write(f'Fecha: {fecha_consulta}')
            col2.write(f'SKU: {sku}')
            if (isinstance(id_inmueble, int) or isinstance(id_inmueble, float)) and id_inmueble>0:
                col3.write(f'Id inmueble: {id_inmueble}')
                
            latitud    = inputvar['latitud']
            longitud   = inputvar['longitud']
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
                ciudad_disp            = ''
                tipoinmueble_disp      = ''
                tiponegocio_disp       = ''
                direccion_disp_disp    = ''
                nombre_conjunto_disp   = ''
                estrato_disp           = ''
                localidad_disp         = ''
                barrio_disp            = ''
                antiguedad_disp        = ''
                unidades_edificio_disp = ''

                try:
                    ciudad = inputvar['ciudad']
                    ciudad_disp = f"""<tr style="background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Ciudad</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{ciudad}</td></tr>"""
                except: pass
                try:
                    tipoinmueble      = inputvar['tipoinmueble']
                    tipoinmueble_disp = f"""<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Tipo de inmueble</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{tipoinmueble}</td></tr>"""
                except: pass            
                try:
                    tiponegocio      = inputvar['tiponegocio']
                    tiponegocio_disp = f"""<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Tipo de negocio</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{tiponegocio}</td></tr>"""
                except: pass            
                try:
                    direccion_disp      = inputvar['direccion']
                    direccion_disp_disp = f"""
                    <tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Dirección</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{direccion_disp}</td></tr>"""
                except: pass
                try:
                    nombre_conjunto_disp = inputvar['nombre_conjunto']
                    nombre_conjunto_disp = f"""<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Nombre del edificio</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{nombre_conjunto_disp}</td></tr>"""
                except: pass
                try:
                    estrato_disp = inputvar['estrato']
                    estrato_disp = f"""<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Estrato</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{estrato_disp}</td></tr>"""
                except: pass
                try:
                    localidad      = inputvar['locnombre']
                    localidad_disp = f"""<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Localidad</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{localidad}</td></tr>"""
                except: pass
                try:
                    barrio      = inputvar['barrio']
                    barrio_disp = f"""<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Barrio</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{barrio}</td></tr>"""
                except: pass 
                try:
                    antiguedad      = inputvar['anos_antiguedad']
                    antiguedad_disp = f"""<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Antiguedad</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{antiguedad}</td></tr>"""
                except: pass
                try:
                    unidades_edificio      = inputvar['unidades']
                    unidades_edificio_disp = f"""<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Unidades edificio</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{unidades_edificio}</td></tr>"""
                except: pass

                texto = f"""<table style="background-color:{backgroundcolor};width:100%;border-radius:100px;">{ciudad_disp}{tipoinmueble_disp}{tiponegocio_disp}{direccion_disp_disp}{nombre_conjunto_disp}{estrato_disp}{localidad_disp}{barrio_disp}{antiguedad_disp}{unidades_edificio_disp}<tr style="background-color:{backgroundcolor};"></tr></table>""" 
                st.markdown(texto,unsafe_allow_html=True)      

            
            col1, col2 = st.columns(2)
            with col1:
                #---------------------------------------------------------------------#
                # Detalle del inmueble
                #---------------------------------------------------------------------#
                texto = "<i>Caracteristicas del inmueble</i>"
                st.markdown(texto,unsafe_allow_html=True) 
                
                areaconstruida  = inputvar['areaconstruida']
                habitaciones    = inputvar['habitaciones']
                banos           = inputvar['banos']
                garajes         = inputvar['garajes']
                num_piso        = inputvar['num_piso']
                num_ascensores  = inputvar['num_ascensores']
                numerodeniveles = inputvar['numerodeniveles']
            
                maxpiso      = inputvar['maxpiso']
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
                
                #---------------------------------------------------------------------#
                precioventa_disp     = '' # Precio que estan pidiendo por el inmueble
                forecastprice_disp   = '' # Forecast comercial del inmueble
                admon_disp           = '' # Valor de la adminsitracion
                preciorenta_disp     = '' # Precio al que se tiene rentando
                ofertas_building     = '' # Ofertas activas en el edificio
                unidades_disp        = '' # Unidades del edificio
        
                try:
                    precioventa      = inputvar['precioventa']
                    precioventa_disp = f'${precioventa:,.0f}' 
                    precioventa_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Precio de oferta</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{precioventa_disp}</td></tr>'
                except: pass
                try:
                    forecastpriceresult = inputvar['forecastpriceresult']
                    forecastprice_disp  = f'${forecastpriceresult:,.0f}'
                    forecastprice_disp  = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Forecast precio</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{forecastprice_disp}</td></tr>'
                except: pass
                try:
                    admon      = inputvar['administracion']
                    admon_disp = f'${admon:,.0f}' 
                    admon_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Administracion</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{admon_disp}</td></tr>'
                except: pass
                try: 
                    preciorenta      = inputvar['preciorenta']
                    preciorenta_disp = f'${preciorenta:,.0f}'
                    preciorenta_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Precio de renta</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{preciorenta_disp}</td></tr>'
                except: pass
                try:
                    ofertas_building = inputvar['ofertas_building']
                    ofertas_building = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Ofertas en el edificio</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{ofertas_building}</td></tr>'     
                except: pass
                try: 
                    unidades      = inputvar['unidades']
                    unidades_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Total unidades en Conjunto</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{unidades}</td></tr>'
                except: pass
        
                texto = f'<table style="background-color:{backgroundcolor_seccionprecios};width:100%;border-radius:100px;">{precioventa_disp}{forecastprice_disp}{admon_disp}{preciorenta_disp}{ofertas_building}{unidades_disp}</table>'
                st.markdown(texto,unsafe_allow_html=True) 
                
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
                    totalgasto_disp        = ''
        
                    try:
                        gn_compra      = inputvar['gn_compra']
                        gn_compra_disp = f'${gn_compra:,.0f}' 
                        gn_compra_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Gastos notariales comprador + beneficiencia y registro </td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{gn_compra_disp}</td></tr>'
                        
                        comisioncompra       = inputvar['comisioncompra']
                        comision_compra_disp = f'${comisioncompra:,.0f}' 
                        comision_compra_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Comisión por la compra</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{comision_compra_disp}</td></tr>'
                    except: pass
                    try:
                        gn_venta      = inputvar['gn_venta']
                        gn_venta_disp = f'${gn_venta:,.0f}' 
                        gn_venta_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Gastos notariales vendedor</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{gn_venta_disp}</td></tr>'
        
                        comisionventa       = inputvar['comisionventa']
                        comision_venta_disp = f'${comisionventa:,.0f}' 
                        comision_venta_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Comisión por la venta</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{comision_venta_disp}</td></tr>'
                    except: pass
                    try:                
                        total_gasto_provision = inputvar['total_gasto_provision']
                        otros_gastos_disp = f'${total_gasto_provision:,.0f}' 
                        otros_gastos_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Gastos provisión</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{otros_gastos_disp}</td></tr>'
                    except: pass
                    try:
                        totalgasto             = inputvar['totalgasto']
                        totalgasto_disp        = f'${totalgasto:,.0f}'
                        totalgasto_disp        = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Gasto total</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;"><b>{totalgasto_disp}</b></td></tr>'
                    except: pass
                    try:
                        valorremodelacion = inputvar['valorremodelacion']
                        valorremodelacion_disp = f'${valorremodelacion:,.0f}' 
                        valorremodelacion_disp = f'<tr style="border-style: none;background-color:{backgroundcolor};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Valor remodelación</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{valorremodelacion_disp}</td></tr>'
                    except: pass
                
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
                        preferencia      = inputvar['preciocompra']
                        preferencia_disp = f'${preferencia:,.0f}'  
                        preferencia_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Precio de compra</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;"><b>{preferencia_disp}</b></td></tr>'
                    except: pass
                    try:
                        precioalquesevende   = inputvar['precioalquesevende']
                        precioparaventa_disp = f'${precioalquesevende:,.0f}'
                        precioparaventa_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Precio al que se puede vender</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{precioparaventa_disp}</td></tr>'
                    except: pass
                    try:
                        retorno_bruto_esperado      = inputvar['retorno_bruto_esperado']
                        retorno_bruto_esperado_disp = "{:.1%}".format(retorno_bruto_esperado)
                        retorno_bruto_esperado_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Retorno bruto esperado</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{retorno_bruto_esperado_disp}</td></tr>'
                    except: pass
                    try:
                        retorno_neto_esperado      = inputvar['retorno_neto_esperado']
                        retorno_neto_esperado_disp = "{:.1%}".format(retorno_neto_esperado)
                        retorno_neto_esperado_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Retorno neto esperado</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{retorno_neto_esperado_disp}</td></tr>'
                    except: pass
                    try:
                        ganancia_neta      = inputvar['ganancia_neta']
                        ganancia_neta_disp = f'${ganancia_neta:,.0f}' 
                        ganancia_neta_disp = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Ganancia neta</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">{ganancia_neta_disp}</td></tr>'
                    except: pass   
                    try:
                        diferencia_pricing = inputvar['diferencia_pricing']
                        diferencia_disp    = "{:.1%}".format(diferencia_pricing)
                        diferencia_disp    = f'<tr style="border-style: none;background-color:{backgroundcolor_seccionprecios};"><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;">Diferencia (precio de compra vs precio de venta</td><td style="border-style: none;font-family:{fontfamily};font-size:{fontsize}px;"><b>{diferencia_disp}</b></td></tr>'
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
        if 'coddir' in inputvar and inputvar['coddir']!='' and inputvar['coddir'] is not None and len(inputvar['coddir'])>=3:
            fcoddir           = inputvar['coddir']
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